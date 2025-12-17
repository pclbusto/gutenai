"""
GutenCore — núcleo único (modelo + workspace) para editar EPUBs.

Diseño:
- La UI interactúa SOLO con esta clase.
- Administra carpeta de trabajo descomprimida (workdir) y el OPF (manifest/spine/metadata/nav).
- Usa ebooklib SOLO para empaquetar y (opcionalmente) importar.

Dependencias recomendadas (instalar en tu venv):
    pip install ebooklib
Opcional: watchdog (si luego querés un watcher).

Notas importantes:
- No implementa reescritura de enlaces internos al mover/renombrar. Muestra
  un warning (hook) para que lo agregues cuando quieras.
- Mantiene invariantes básicas: todo archivo añadido al proyecto debe existir
  en el manifest y, si es documento, puede estar en el spine.
- OPF es la fuente de verdad en disco; el core mantiene un árbol ElementTree
  en memoria y lo persiste tras operaciones estructurales.
"""
from __future__ import annotations

import os
import io
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Iterable, Dict, List, Tuple
import mimetypes
import shutil
import xml.etree.ElementTree as ET
import os
import html
import re
import uuid
from datetime import datetime

try:
    from ebooklib import epub
    _HAS_EBOOKLIB = True
except Exception:
    _HAS_EBOOKLIB = False


# -----------------------------
# Constantes y namespaces
# -----------------------------
NS = {
    "ocf": "urn:oasis:names:tc:opendocument:xmlns:container",
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "xhtml": "http://www.w3.org/1999/xhtml",
}

# Registrar namespaces para que ET serialice sin prefijos "html:"
try:
    ET.register_namespace("", "http://www.w3.org/1999/xhtml")           # default xmlns (sin prefijo)
    ET.register_namespace("epub", "http://www.idpf.org/2007/ops")
except Exception:
    pass


# -----------------------------
# Constantes y namespaces
# -----------------------------
NS = {
    "ocf": "urn:oasis:names:tc:opendocument:xmlns:container",
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "xhtml": "http://www.w3.org/1999/xhtml",
}

EPUB_MIMETYPE = b"application/epub+zip"

# Folders por defecto (podés cambiar con new_project(layout=...))
DEFAULT_LAYOUT = {
    "TEXT": "OEBPS/Text",
    "STYLES": "OEBPS/Styles",
    "IMAGES": "OEBPS/Images",
    "FONTS": "OEBPS/Fonts",
    "AUDIO": "OEBPS/Audio",
    "VIDEO": "OEBPS/Video",
}

# Mapa básico de media-types (completar si necesitás más)
MT_MAP = {
    ".xhtml": "application/xhtml+xml",
    ".html": "text/html",
    ".htm": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".opus": "audio/opus",
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".webm": "video/webm",
}

# Tipos lógicos (para listar)
KIND_DOCUMENT = "document"
KIND_STYLE = "style"
KIND_IMAGE = "image"
KIND_FONT = "font"
KIND_AUDIO = "audio"
KIND_VIDEO = "video"
KIND_SCRIPT = "script"
KIND_VECTOR = "vector"
KIND_NAV = "navigation"
KIND_COVER = "cover"
KIND_SMIL = "smil"

MEDIA_TO_KIND = {
    "application/xhtml+xml": KIND_DOCUMENT,
    "text/html": KIND_DOCUMENT,
    "text/css": KIND_STYLE,
    "application/javascript": KIND_SCRIPT,
    "text/javascript": KIND_SCRIPT,
    "image/svg+xml": KIND_VECTOR,
    "application/smil+xml": KIND_SMIL,
    "image/png": KIND_IMAGE,
    "image/jpeg": KIND_IMAGE,
    "image/gif": KIND_IMAGE,
    "image/webp": KIND_IMAGE,
    "image/avif": KIND_IMAGE,
    "font/ttf": KIND_FONT,
    "font/otf": KIND_FONT,
    "font/woff": KIND_FONT,
    "font/woff2": KIND_FONT,
    "audio/mpeg": KIND_AUDIO,
    "audio/mp4": KIND_AUDIO,
    "audio/ogg": KIND_AUDIO,
    "video/mp4": KIND_VIDEO,
    "video/ogg": KIND_VIDEO,
    "video/webm": KIND_VIDEO,
}

# -----------------------------
# Helpers
# -----------------------------

def guess_media_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in MT_MAP:
        return MT_MAP[ext]
    mt, _ = mimetypes.guess_type(filename)
    return (mt or "application/octet-stream").lower()


def _text(elem: Optional[ET.Element]) -> str:
    if elem is None:
        return ""
    return (elem.text or "").strip()


# -----------------------------
# Data holders
# -----------------------------
@dataclass
class ManifestItem:
    id: str
    href: str  # relativo al OPF
    media_type: str
    properties: str = ""  # e.g., "nav", "cover-image"

@dataclass
class HeadingItem:
    level: int          # 1..6
    title: str          # texto visible del Hn
    anchor: str         # id del heading en el doc
    include: bool = True

@dataclass
class DocToc:
    href: str           # href del documento (relativo al OPF)
    title: str          # título del documento (o fallback)
    items: list[HeadingItem] = field(default_factory=list)
    include: bool = True  # permitir excluir el capítulo entero desde UI


# -----------------------------
# GutenCore (núcleo único)
# -----------------------------
class GutenCore:
    """
    Única API para la UI. Administra carpeta de trabajo y OPF.
    Mantiene manifest/spine/metadata/nav y escribe el OPF en disco
    cuando hay cambios estructurales.
    """

    def __init__(self, workdir: Path):
        self.workdir = Path(workdir).resolve()
        self.container_path: Optional[Path] = None
        self.opf_path: Optional[Path] = None
        self.opf_dir: Optional[Path] = None
        self.opf_tree: Optional[ET.ElementTree] = None
        self.layout = DEFAULT_LAYOUT.copy()

        # índices
        self.items_by_id: Dict[str, ManifestItem] = {}
        self.items_by_href: Dict[str, ManifestItem] = {}

        # Sistema de hooks (índice de id's en HTML)
        from .hook_index_manager import HookIndexManager
        self.hook_index = HookIndexManager(self)

    # -------------------------
    # Proyecto / apertura
    # -------------------------
    @classmethod
    def open_epub(cls, epub_path: Path, workdir: Path) -> "GutenCore":
        """Descomprime el EPUB en workdir/<epub_sin_extension> y prepara el core."""
        book_name = Path(epub_path).stem
        target_dir = Path(workdir) / book_name
        target_dir = target_dir.resolve()
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(epub_path, "r") as zf:
            zf.extractall(target_dir)
        core = cls(target_dir)
        core._load_container_and_opf()
        core._parse_opf()
        return core

    @classmethod
    def open_folder(cls, workdir: Path) -> "GutenCore":
        core = cls(workdir)
        core._load_container_and_opf()
        core._parse_opf()
        return core

    @classmethod
    def new_project(cls, root: Path, layout: Dict[str, str] | None = None,
                    title: str = "Untitled", lang: str = "en") -> "GutenCore":
        """Crea esqueleto mínimo de proyecto EPUB en disco y lo abre."""
        root = Path(root).resolve()
        if root.exists() and any(root.iterdir()):
            raise RuntimeError("El directorio de destino no está vacío.")
        (root / "META-INF").mkdir(parents=True, exist_ok=True)
        lay = (layout or DEFAULT_LAYOUT).copy()
        for key, rel in lay.items():
            (root / rel).mkdir(parents=True, exist_ok=True)

        # mimetype en la raíz (el empaquetado final se hará con ebooklib)
        (root / "mimetype").write_bytes(EPUB_MIMETYPE)

        # container.xml → apunta al OPF
        opf_rel = Path(lay["TEXT"]).parent / "content.opf"
        container_xml = f"""<?xml version='1.0' encoding='UTF-8'?>
<container version="1.0" xmlns="{NS['ocf']}">
  <rootfiles>
    <rootfile full-path="{opf_rel.as_posix()}" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""
        (root / "META-INF" / "container.xml").write_text(container_xml, encoding="utf-8")

        # OPF mínimo con UUID válido y dcterms:modified
        book_uuid = str(uuid.uuid4())
        modified_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        opf_xml = f"""<?xml version='1.0' encoding='UTF-8'?>
<package version="3.0" unique-identifier="bookid" xmlns="{NS['opf']}" xml:lang="{lang}">
  <metadata xmlns:dc="{NS['dc']}" xmlns:dcterms="http://purl.org/dc/terms/">
    <dc:identifier id="bookid">urn:uuid:{book_uuid}</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:language>{lang}</dc:language>
    <meta property="dcterms:modified">{modified_date}</meta>
  </metadata>
  <manifest>
    <item id="style" href="{Path(lay['STYLES']).name}/style.css" media-type="text/css"/>
    <item id="chap1" href="{Path(lay['TEXT']).name}/chap1.xhtml" media-type="application/xhtml+xml"/>
    <item id="nav" href="{Path(lay['TEXT']).name}/nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
  </manifest>
  <spine>
    <itemref idref="chap1"/>
  </spine>
</package>"""
        opf_abs = (root / opf_rel)
        opf_abs.write_text(opf_xml, encoding="utf-8")

        # archivos iniciales
        (root / lay["STYLES"] / "style.css").write_text("body{font-family:serif;}", encoding="utf-8")
        # Crear nav.xhtml que apunte al primer documento del spine
        first_doc_href = f"{Path(lay['TEXT']).name}/chap1.xhtml"  # Por defecto
        nav_xhtml = f"""<?xml version='1.0' encoding='UTF-8'?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en" xml:lang="en">
<head><title>TOC</title><meta charset="utf-8"/></head>
<body>
<nav epub:type="toc" id="toc"><ol><li><a href="chap1.xhtml">Chapter 1</a></li></ol></nav>
</body></html>"""
        (root / lay["TEXT"] / "nav.xhtml").write_text(nav_xhtml, encoding="utf-8")
        chap1 = """<?xml version='1.0' encoding='UTF-8'?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">
<head>
  <title>Chapter 1</title>
  <meta charset="utf-8"/>
  <link rel="stylesheet" type="text/css" href="../Styles/style.css"/>
</head>
<body><h1>Chapter 1</h1><p>Hello, EPUB!</p></body></html>"""
        (root / lay["TEXT"] / "chap1.xhtml").write_text(chap1, encoding="utf-8")

        core = cls.open_folder(root)
        core.layout = lay
        return core

    # -------------------------
    # Lectura de container/OPF
    # -------------------------
    def _load_container_and_opf(self) -> None:
        self.container_path = self.workdir / "META-INF" / "container.xml"
        if not self.container_path.exists():
            raise RuntimeError("No se encontró META-INF/container.xml en el proyecto")
        cont = ET.parse(self.container_path).getroot()
        rootfile = cont.find(".//ocf:rootfile", NS)
        if rootfile is None:
            raise RuntimeError("container.xml inválido: falta rootfile")
        full_path = rootfile.get("full-path")
        self.opf_path = (self.workdir / full_path).resolve()
        self.opf_dir = self.opf_path.parent
        self.opf_tree = ET.parse(self.opf_path)

    def _parse_opf(self) -> None:
        assert self.opf_tree is not None
        root = self.opf_tree.getroot()
        # manifest
        self.items_by_id.clear()
        self.items_by_href.clear()
        for it in root.findall(".//opf:manifest/opf:item", NS):
            mid = it.get("id") or ""
            href = it.get("href") or ""
            mt = (it.get("media-type") or guess_media_type(href))
            props = it.get("properties") or ""
            mi = ManifestItem(mid, href, mt, props)
            self.items_by_id[mid] = mi
            self.items_by_href[href] = mi

        # Construir índice de hooks inicial (lazy/async si el proyecto es grande)
        # Por ahora lo hacemos síncrono en el hilo principal
        stats = self.hook_index.build_full_index()
        print(f"[HookIndex] Indexados {stats['files_indexed']} archivos, "
              f"{stats['hooks_found']} hooks en {stats['time_ms']}ms")

    # -------------------------
    # Inventario y metadata
    # -------------------------
    def list_items(self, kind: Optional[str] = None) -> List[ManifestItem]:
        if kind is None:
            return list(self.items_by_id.values())
        out: List[ManifestItem] = []
        for mi in self.items_by_id.values():
            if self._kind_of(mi) == kind:
                out.append(mi)
        return out

    def _kind_of(self, mi: ManifestItem) -> str:
        mt = (mi.media_type or "").lower().split(";")[0].strip()
        props = (mi.properties or "").split()

        # ÚNICO caso especial por properties: NAV (XHTML con properties="nav")
        if "nav" in props:
            return KIND_NAV

        # Clasificación por media-type (priorizar patrones amplios)
        if mt in ("application/xhtml+xml", "text/html"):
            return KIND_DOCUMENT
        if mt == "text/css":
            return KIND_STYLE
        if mt in ("application/javascript", "text/javascript"):
            return KIND_SCRIPT
        if mt == "application/smil+xml":
            return KIND_SMIL
        if mt == "image/svg+xml":
            return KIND_VECTOR
        if mt.startswith("image/"):
            return KIND_IMAGE
        if mt.startswith("font/"):
            return KIND_FONT
        if mt.startswith("audio/"):
            return KIND_AUDIO
        if mt.startswith("video/"):
            return KIND_VIDEO

        # Fallback a mapa (por si tenés algo exótico en MT_MAP)
        return MEDIA_TO_KIND.get(mt, "other")


    def get_metadata(self) -> Dict[str, str]:
        assert self.opf_tree is not None
        root = self.opf_tree.getroot()
        title = _text(root.find(".//dc:title", NS))
        lang = _text(root.find(".//dc:language", NS))
        ident = _text(root.find(".//dc:identifier[@id]", NS)) or _text(root.find(".//dc:identifier", NS))
        return {"title": title, "language": lang, "identifier": ident}

    def set_metadata(self, title: Optional[str] = None, language: Optional[str] = None,
                     identifier: Optional[str] = None) -> None:
        assert self.opf_tree is not None
        root = self.opf_tree.getroot()
        metadata_changed = False

        if title is not None:
            el = root.find(".//dc:title", NS)
            if el is None:
                md = root.find(".//opf:metadata", NS)
                el = ET.SubElement(md, f"{{{NS['dc']}}}title") if md is not None else None
            if el is not None:
                el.text = title
                metadata_changed = True

        if language is not None:
            el = root.find(".//dc:language", NS)
            if el is None:
                md = root.find(".//opf:metadata", NS)
                el = ET.SubElement(md, f"{{{NS['dc']}}}language") if md is not None else None
            if el is not None:
                el.text = language
                metadata_changed = True

        if identifier is not None:
            el = root.find(".//dc:identifier[@id]", NS) or root.find(".//dc:identifier", NS)
            if el is None:
                md = root.find(".//opf:metadata", NS)
                el = ET.SubElement(md, f"{{{NS['dc']}}}identifier", {"id": "bookid"}) if md is not None else None
            if el is not None:
                el.text = identifier
                metadata_changed = True

        # Actualizar dcterms:modified si se cambió algún metadato
        if metadata_changed:
            self._update_modified_date()

        self._save_opf()

    def _update_modified_date(self):
        """Actualiza o agrega el elemento dcterms:modified"""
        assert self.opf_tree is not None
        root = self.opf_tree.getroot()
        modified_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        # Buscar elemento existente
        modified_el = root.find(".//opf:meta[@property='dcterms:modified']", NS)
        if modified_el is not None:
            modified_el.text = modified_date
        else:
            # Crear nuevo elemento
            md = root.find(".//opf:metadata", NS)
            if md is not None:
                # Asegurar que el namespace dcterms esté declarado
                if "xmlns:dcterms" not in md.attrib:
                    md.set("xmlns:dcterms", "http://purl.org/dc/terms/")
                ET.SubElement(md, "meta", {"property": "dcterms:modified"}).text = modified_date

    # -------------------------
    # Spine
    # -------------------------
    def get_spine(self) -> List[str]:
        assert self.opf_tree is not None
        root = self.opf_tree.getroot()
        return [it.get("idref") or "" for it in root.findall(".//opf:spine/opf:itemref", NS)]

    def set_spine(self, idrefs: List[str]) -> None:
        assert self.opf_tree is not None
        root = self.opf_tree.getroot()
        spine = root.find(".//opf:spine", NS)
        for it in list(spine.findall("opf:itemref", NS)):
            spine.remove(it)
        for idr in idrefs:
            ET.SubElement(spine, f"{{{NS['opf']}}}itemref", {"idref": idr})
        self._save_opf()

    def spine_insert(self, idref: str, index: Optional[int] = None) -> None:
        ids = self.get_spine()
        if idref in ids:
            return
        if index is None:
            ids.append(idref)
        else:
            ids.insert(max(0, min(index, len(ids))), idref)
        self.set_spine(ids)

    def spine_move(self, idref: str, new_index: int) -> None:
        ids = self.get_spine()
        if idref not in ids:
            raise ValueError(f"{idref} no está en el spine")
        ids.remove(idref)
        ids.insert(max(0, min(new_index, len(ids))), idref)
        self.set_spine(ids)

    def spine_remove(self, idref: str) -> None:
        ids = self.get_spine()
        if idref in ids:
            ids.remove(idref)
            self.set_spine(ids)

    # -------------------------
    # Manifest (altas/bajas/rename)
    # -------------------------
    def add_to_manifest(self, id_: str, href: str, media_type: Optional[str] = None,
                        properties: str = "") -> ManifestItem:
        assert self.opf_tree is not None
        root = self.opf_tree.getroot()
        man = root.find(".//opf:manifest", NS)
        if id_ in self.items_by_id:
            raise ValueError(f"Ya existe id {id_}")
        if href in self.items_by_href:
            raise ValueError(f"Ya existe href {href}")
        mt = (media_type or guess_media_type(href))
        el = ET.SubElement(man, f"{{{NS['opf']}}}item", {
            "id": id_, "href": href, "media-type": mt
        })
        if properties:
            el.set("properties", properties)
        mi = ManifestItem(id_, href, mt, properties)
        self.items_by_id[id_] = mi
        self.items_by_href[href] = mi
        self._save_opf()
        return mi

    def remove_from_manifest(self, id_or_href: str) -> None:
        assert self.opf_tree is not None
        root = self.opf_tree.getroot()
        man = root.find(".//opf:manifest", NS)
        mi = self._get_item(id_or_href)
        # sacar del spine si está
        self.spine_remove(mi.id)
        # borrar archivo en disco (si existe)
        p = (self.opf_dir / mi.href).resolve()
        if p.exists():
            p.unlink()
        # quitar del manifest
        for it in man.findall("opf:item", NS):
            if it.get("id") == mi.id:
                man.remove(it)
                break
        self.items_by_id.pop(mi.id, None)
        self.items_by_href.pop(mi.href, None)
        self._save_opf()

    def rename_item(self, id_or_href: str, new_name: str, update_references: bool = False) -> str:
        """
        Renombra un recurso del manifest y su archivo físico.
        
        Args:
            id_or_href: ID o href del recurso a renombrar
            new_name: Nuevo nombre (solo el nombre, sin ruta)
            update_references: Si actualizar referencias en otros archivos
        
        Returns:
            str: Nuevo href completo del recurso
        """
        mi = self._get_item(id_or_href)
        old_href = mi.href
        old_path = Path(old_href)
        
        # Validar nuevo nombre
        if not new_name or not new_name.strip():
            raise ValueError("El nuevo nombre no puede estar vacío")
        
        # Limpiar nombre (remover caracteres problemáticos)
        clean_name = self._sanitize_filename(new_name.strip())
        
        # Preservar extensión si no se especifica
        if '.' not in clean_name and old_path.suffix:
            clean_name += old_path.suffix
        
        # Construir nuevo href
        new_href = str(old_path.parent / clean_name)
        
        # Verificar que no existe ya
        if new_href in self.items_by_href and new_href != old_href:
            raise ValueError(f"Ya existe un recurso con el nombre '{clean_name}'")
        
        # Mover archivo físico
        src_path = (self.opf_dir / old_href).resolve()
        dst_path = (self.opf_dir / new_href).resolve()
        
        if src_path.exists():
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            src_path.rename(dst_path)
        
        # Actualizar manifest
        root = self.opf_tree.getroot()
        for item_elem in root.findall(".//opf:manifest/opf:item", NS):
            if item_elem.get("id") == mi.id:
                item_elem.set("href", new_href)
                break
        
        # Actualizar índices
        self.items_by_href.pop(old_href, None)
        mi.href = new_href
        self.items_by_href[new_href] = mi
        
        # Guardar cambios
        self._save_opf()
        
        # Actualizar referencias si se solicita
        if update_references:
            self._update_references_after_rename(old_href, new_href)
        
        return new_href

    def _update_references_after_rename(self, old_href: str, new_href: str):
        """
        Actualiza referencias al archivo renombrado en otros recursos.
        
        Por ahora solo actualiza enlaces relativos simples.
        Una implementación completa requeriría parser HTML/CSS más sofisticado.
        """
        old_name = Path(old_href).name
        new_name = Path(new_href).name
        
        # Solo actualizar si están en el mismo directorio
        if Path(old_href).parent != Path(new_href).parent:
            print(f"[WARNING] Renombrado a diferente directorio. Referencias manuales requeridas.")
            return
        
        # Buscar referencias en documentos HTML/XHTML
        for doc_item in self.list_items(KIND_DOCUMENT):
            try:
                content = self.read_text(doc_item.href)
                
                # Buscar referencias simples (href, src)
                if old_name in content:
                    # Reemplazar solo coincidencias exactas de nombre de archivo
                    pattern = r'\b' + re.escape(old_name) + r'\b'
                    updated_content = re.sub(pattern, new_name, content)
                    
                    if updated_content != content:
                        self.write_text(doc_item.href, updated_content)
                        print(f"[RENAME] Updated references in {doc_item.href}")
                        
            except Exception as e:
                print(f"[WARNING] Could not update references in {doc_item.href}: {e}")
        
        # Buscar referencias en archivos CSS
        for style_item in self.list_items(KIND_STYLE):
            try:
                content = self.read_text(style_item.href)

                if old_name in content:
                    pattern = r'\b' + re.escape(old_name) + r'\b'
                    updated_content = re.sub(pattern, new_name, content)

                    if updated_content != content:
                        self.write_text(style_item.href, updated_content)
                        print(f"[RENAME] Updated references in {style_item.href}")

            except Exception as e:
                print(f"[WARNING] Could not update references in {style_item.href}: {e}")

        # Actualizar referencias en nav.xhtml específicamente
        nav_href = self.get_nav_href()
        if nav_href:
            try:
                nav_content = self.read_text(nav_href)

                if old_name in nav_content:
                    # Para nav.xhtml, ser más específico con los patrones de enlaces
                    patterns = [
                        rf'href="{re.escape(old_name)}"',
                        rf"href='{re.escape(old_name)}'",
                        rf'href="{re.escape(old_href)}"',
                        rf"href='{re.escape(old_href)}'"
                    ]

                    updated_nav = nav_content
                    for pattern in patterns:
                        # Reemplazar con nuevo nombre, manteniendo las comillas
                        if '"' in pattern:
                            replacement = f'href="{new_name}"'
                        else:
                            replacement = f"href='{new_name}'"
                        updated_nav = re.sub(pattern, replacement, updated_nav)

                    if updated_nav != nav_content:
                        self.write_text(nav_href, updated_nav)
                        print(f"[RENAME] Updated navigation references in {nav_href}")

            except Exception as e:
                print(f"[WARNING] Could not update references in nav.xhtml: {e}")

        # Si se renombró el primer documento del spine, regenerar navegación básica
        spine_items = self.get_spine()
        if spine_items:
            first_doc_id = spine_items[0]
            first_doc = self.items_by_id.get(first_doc_id)
            if first_doc and first_doc.href == new_href:
                try:
                    self.generate_nav_basic(overwrite=True)
                    print(f"[RENAME] Regenerated navigation for first spine document")
                except Exception as e:
                    print(f"[WARNING] Could not regenerate navigation: {e}")

    def batch_rename_items(self, renames: list[tuple[str, str]], update_references: bool = False) -> dict[str, str]:
        """
        Renombra múltiples recursos de una vez.
        
        Args:
            renames: Lista de tuplas (id_or_href, new_name)
            update_references: Si actualizar referencias
        
        Returns:
            dict: {old_href: new_href} para los renombrados exitosos
        """
        results = {}
        errors = []
        
        for id_or_href, new_name in renames:
            try:
                old_href = self._get_item(id_or_href).href
                new_href = self.rename_item(id_or_href, new_name, update_references=False)
                results[old_href] = new_href
            except Exception as e:
                errors.append(f"{id_or_href}: {e}")
        
        # Actualizar referencias una sola vez al final si se solicita
        if update_references and results:
            for old_href, new_href in results.items():
                try:
                    self._update_references_after_rename(old_href, new_href)
                except Exception as e:
                    errors.append(f"References for {old_href}: {e}")
        
        if errors:
            print(f"[WARNING] Rename errors: {errors}")
        
        return results

    def suggest_filename(self, base_name: str, resource_type: str = None) -> str:
        """
        Sugiere un nombre de archivo único basado en el nombre base.
        
        Args:
            base_name: Nombre base deseado
            resource_type: Tipo de recurso para determinar extensión
        
        Returns:
            str: Nombre único disponible
        """
        clean_name = self._sanitize_filename(base_name)
        
        # Agregar extensión por defecto si es necesario
        if '.' not in clean_name and resource_type:
            extensions = {
                KIND_DOCUMENT: '.xhtml',
                KIND_STYLE: '.css',
                KIND_IMAGE: '.png',  # Por defecto, pero se debería especificar
                KIND_FONT: '.ttf',
                KIND_AUDIO: '.mp3',
                KIND_VIDEO: '.mp4'
            }
            if resource_type in extensions:
                clean_name += extensions[resource_type]
        
        # Encontrar nombre único
        original_name = clean_name
        stem = Path(clean_name).stem
        suffix = Path(clean_name).suffix
        counter = 1
        
        # Determinar directorio apropiado
        folder = self._folder_for_kind(resource_type) if resource_type else "Text"
        
        while True:
            test_href = f"{folder}/{clean_name}"
            if test_href not in self.items_by_href:
                break
            
            counter += 1
            clean_name = f"{stem}_{counter}{suffix}"
        
        return clean_name

    def validate_rename(self, id_or_href: str, new_name: str) -> tuple[bool, str]:
        """
        Valida si un renombrado es posible sin ejecutarlo.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            mi = self._get_item(id_or_href)
            old_path = Path(mi.href)
            
            # Validaciones básicas
            if not new_name or not new_name.strip():
                return False, "El nombre no puede estar vacío"
            
            clean_name = self._sanitize_filename(new_name.strip())
            
            if clean_name != new_name.strip():
                return False, f"Nombre contiene caracteres inválidos. Sugerencia: '{clean_name}'"
            
            # Preservar extensión si no se especifica
            if '.' not in clean_name and old_path.suffix:
                clean_name += old_path.suffix
            
            new_href = str(old_path.parent / clean_name)
            
            # Verificar colisión
            if new_href in self.items_by_href and new_href != mi.href:
                return False, f"Ya existe un recurso llamado '{clean_name}'"
            
            return True, ""
            
        except Exception as e:
            return False, str(e)
            
    def _sanitize_filename(self, filename: str) -> str:
        """Limpia un nombre de archivo de caracteres problemáticos"""
        
        # Remover/reemplazar caracteres problemáticos
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remover espacios múltiples y al inicio/final
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        # Evitar nombres reservados del sistema
        reserved_names = {'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 
                        'com5', 'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2', 
                        'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'}
        
        name_without_ext = Path(sanitized).stem.lower()
        if name_without_ext in reserved_names:
            sanitized = f"_{sanitized}"
        
        return sanitized

    def _get_item(self, id_or_href: str) -> ManifestItem:
        if id_or_href in self.items_by_id:
            return self.items_by_id[id_or_href]
        if id_or_href in self.items_by_href:
            return self.items_by_href[id_or_href]
        raise KeyError(id_or_href)

    # -------------------------
    # Contenido (archivos)
    # -------------------------
    def read_text(self, href: str, encoding: str = "utf-8") -> str:
        p = (self.opf_dir / href).resolve()
        return p.read_text(encoding=encoding)

    def write_text(self, href: str, text: str, encoding: str = "utf-8") -> None:
        p = (self.opf_dir / href).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        
        # DEBUG: Log quién está llamando
        import traceback
        print(f"\n[CORE-WRITE] {href}")
        print("Stack trace:")
        for line in traceback.format_stack()[-4:-1]:
            print(f"  {line.strip()}")
        
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(text, encoding=encoding)
        tmp.replace(p)
        
        print(f"[CORE-WRITE] Completed: {p}")


    def read_bytes(self, href: str) -> bytes:
        p = (self.opf_dir / href).resolve()
        return p.read_bytes()

    def write_bytes(self, href: str, data: bytes) -> None:
        p = (self.opf_dir / href).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(p)

    # -------------------------
    # Operaciones compuestas (UX)
    # -------------------------
    def create_document(self, filename: str, title: str = "") -> ManifestItem:
        """Crea un XHTML con boilerplate en la carpeta de textos y lo agrega al manifest."""
        text_dir = Path(self.layout["TEXT"]).name
        href = f"{text_dir}/{filename}"
        if not href.lower().endswith(('.xhtml', '.html', '.htm')):
            href += ".xhtml"
        # contenido mínimo
        title = title or Path(filename).stem
        boiler = f"""<?xml version='1.0' encoding='UTF-8'?>
<!DOCTYPE html>
<html xmlns=\"{NS['xhtml']}\" lang=\"es\" xml:lang=\"es\">
<head>
  <title>{title}</title>
  <meta charset=\"utf-8\"/>
  <link rel=\"stylesheet\" type=\"text/css\" href=\"../{Path(self.layout['STYLES']).name}/style.css\"/>
</head>
<body><h1>{title}</h1><p>…</p></body></html>"""
        self.write_text(href, boiler)
        # id único
        base_id = Path(filename).stem
        id_ = self._unique_id(base_id)
        mi = self.add_to_manifest(id_, href, media_type="application/xhtml+xml")
        # al final del spine
        self.spine_insert(id_)
        return mi

    def create_asset_from_disk(self, src: Path, kind: str, dest_name: Optional[str] = None,
                               set_as_cover: bool = False) -> ManifestItem:
        """Copia un recurso externo a la carpeta correspondiente y lo añade al manifest."""
        src = Path(src)
        dest_name = dest_name or src.name
        folder = self._folder_for_kind(kind)
        href = f"{folder}/{dest_name}"
        data = src.read_bytes()
        self.write_bytes(href, data)
        id_ = self._unique_id(Path(dest_name).stem)
        mt = guess_media_type(dest_name)
        props = "cover-image" if (set_as_cover and kind == KIND_IMAGE) else ""
        mi = self.add_to_manifest(id_, href, media_type=mt, properties=props)
        return mi

    def delete_item(self, id_or_href: str, remove_from_nav: bool = False) -> None:
        # (remove_from_nav queda para cuando implementes edición de nav.xhtml)
        self.remove_from_manifest(id_or_href)

    # -------------------------
    # NAV (cargar / generar simple)
    # -------------------------
    def nav_exists(self) -> bool:
        return any("nav" in (mi.properties or "").split() for mi in self.items_by_id.values())

    def get_nav_href(self) -> Optional[str]:
        for mi in self.items_by_id.values():
            if "nav" in (mi.properties or "").split():
                return mi.href
        return None

    def generate_nav_basic(self, overwrite: bool = False) -> str:
        """Genera un nav.xhtml básico a partir del orden del spine y los titles de los documentos.
        Si ya existe nav y overwrite=False, reutiliza el existente.
        Devuelve el href del nav.
        """
        if self.nav_exists() and not overwrite:
            return self.get_nav_href()

        spine = self.get_spine()
        ol_items = []
        for idref in spine:
            mi = self.items_by_id.get(idref)
            if not mi:
                continue
            title = self._extract_title_from_xhtml(mi.href) or Path(mi.href).stem
            rel = Path(mi.href).name  # nav suele vivir junto a Text, referenciamos por nombre corto
            ol_items.append(f"<li><a href=\"{rel}\">{title}</a></li>")
        # Si no hay elementos, usar el primer documento del spine como fallback
        if not ol_items:
            spine_items = self.get_spine()
            if spine_items:
                first_doc_id = spine_items[0]
                first_doc = self.items_by_id.get(first_doc_id)
                if first_doc:
                    first_doc_name = Path(first_doc.href).name
                    ol_items.append(f"<li><a href=\"{first_doc_name}\">Inicio</a></li>")

        ol_html = "\n      ".join(ol_items) or "<li>Sin documentos</li>"

        text_dir = Path(self.layout["TEXT"]).name
        nav_href = f"{text_dir}/nav.xhtml"
        nav_xhtml = f"""<?xml version='1.0' encoding='UTF-8'?>
<!DOCTYPE html>
<html xmlns=\"{NS['xhtml']}\" xmlns:epub=\"http://www.idpf.org/2007/ops\" lang=\"es\" xml:lang=\"es\">
<head><title>Índice</title><meta charset=\"utf-8\"/></head>
<body>
  <nav epub:type=\"toc\" id=\"toc\"><ol>
      {ol_html}
  </ol></nav>
</body></html>"""
        self.write_text(nav_href, nav_xhtml)
        # alta en manifest con properties="nav" (si no existe)
        existing = self.get_nav_href()
        if existing is None:
            self.add_to_manifest("nav", nav_href, media_type="application/xhtml+xml", properties="nav")
        else:
            # si existía pero lo reescribimos, no tocamos el manifest
            pass
        return nav_href

    # --- TOC desde headings (EPUB3 nav.xhtml) -------------------------------------
    def generate_nav_from_headings(
        self,
        levels: tuple[int, ...] = (1, 2, 3),
        overwrite: bool = True,
        add_missing_ids: bool = True,
        max_items_per_doc: int = 200,
    ) -> str:
        toc = self.collect_headings(
            levels=levels,
            source="spine",
            add_missing_ids=add_missing_ids,
            max_items_per_doc=max_items_per_doc,
        )
        return self.render_nav_from_model(toc, nav_href=None, overwrite=overwrite, epub_version=3)

    # --- Paso 1: recolección (no renderiza nada) ---

    def collect_headings(
        self,
        levels: tuple[int, ...] = (1, 2, 3),
        source: str = "spine",   # "spine" o "manifest"
        add_missing_ids: bool = True,
        max_items_per_doc: int = 200,
    ) -> list[DocToc]:
        """
        Recorre spine/manifest, extrae Hn y devuelve un modelo de TOC serializable para UI.
        Si add_missing_ids=True, persiste IDs faltantes en los xhtml.
        """
        # Elegir recorrido
        idrefs = (self.get_spine() if source == "spine" else [it.id for it in self.list_items()])
        toc: list[DocToc] = []

        for idref in idrefs:
            mi = self.items_by_id.get(idref)
            if not mi:
                continue
            mt = (mi.media_type or "").lower()
            if mt not in {"application/xhtml+xml", "text/html"}:
                continue

            try:
                raw = self.read_text(mi.href)
            except Exception:
                continue

            # Tu extractor actual (devuelve result, new_raw)
            # result: {"doc_title": str|None, "entries": [{"level": int, "title": str, "anchor": str}, ...]}
            result, new_raw = self._extract_and_optionally_tag_headings(
                raw, levels=levels, max_items=max_items_per_doc, add_missing_ids=add_missing_ids
            )

            # Persistir IDs si se agregaron
            if add_missing_ids and new_raw and new_raw != raw:
                try:
                    self.write_text(mi.href, new_raw)
                except Exception:
                    pass  # evitamos romper el flujo de colecta

            doc_title = (result.get("doc_title") or Path(mi.href).stem or "").strip()
            items = [
                HeadingItem(level=e["level"], title=e["title"].strip(), anchor=e["anchor"].strip(), include=True)
                for e in result.get("entries", [])
            ]
            toc.append(DocToc(href=mi.href, title=doc_title, items=items, include=True))

        return toc

    # --- Paso 2: render (consume el modelo y escribe nav.xhtml) ---

    def render_nav_from_model(
        self,
        toc: list[DocToc],
        nav_href: str | None = None,
        overwrite: bool = True,
        epub_version: int = 3,             # 3 => NAV (XHTML5); 2 => (futuro) NCX
        default_on_empty: str = "",  # Se calculará dinámicamente
        lang: str = "es",
    ) -> str:
        """
        Genera y escribe nav.xhtml a partir del modelo toc (que podés filtrar/editar desde UI).
        Devuelve el href de nav.xhtml (relativo al OPF).
        """
        if epub_version != 3:
            raise NotImplementedError("EPUB2 requiere NCX; implementarlo por separado.")

        # Respetar overwrite
        if self.nav_exists() and not overwrite:
            existing = self.get_nav_href()
            if existing:
                return existing

        # Destino por defecto junto a TEXT/
        if nav_href is None:
            text_dir = Path(self.layout["TEXT"]).name  # e.g. "Text"
            nav_href = f"{text_dir}/nav.xhtml"
        nav_dir = Path(nav_href).parent

        # Construir los <li> por capítulo (aplicando include y escapando)
        chapter_blocks: list[str] = []
        for chapter in toc:
            if not chapter.include:
                continue

            # ruta del capítulo relativa al nav
            rel_doc = os.path.relpath(chapter.href, start=nav_dir)
            chap_title = html.escape(chapter.title or Path(chapter.href).stem, quote=True)

            # headings seleccionados (por UI)
            selected = [h for h in chapter.items if h.include]

            if selected:
                # anidar según niveles (H1..H6) manteniendo jerarquía
                nested = self._nest_headings(selected)
                children_html = self._render_nested_list(rel_doc, nested)
            else:
                children_html = ""

            chapter_blocks.append(
                f'<li><a href="{rel_doc}">{chap_title}</a>{children_html}</li>'
            )

        # Si vacío, meter un link mínimo
        if not chapter_blocks:
            # Calcular dinámicamente el primer documento si no se especifica default_on_empty
            if not default_on_empty:
                spine_items = self.get_spine()
                if spine_items:
                    first_doc_id = spine_items[0]
                    first_doc = self.items_by_id.get(first_doc_id)
                    if first_doc:
                        default_on_empty = Path(first_doc.href).name

            if default_on_empty:
                chapter_blocks = [f'<li><a href="{html.escape(default_on_empty, True)}">Inicio</a></li>']
            else:
                chapter_blocks = ['<li>Sin documentos</li>']

        # Plantilla EPUB3 (XHTML5 serializado)
        nav_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE html>
    <html xmlns="http://www.w3.org/1999/xhtml" lang="{html.escape(lang, True)}" xml:lang="{html.escape(lang, True)}" xmlns:epub="http://www.idpf.org/2007/ops">
    <head>
    <meta charset="utf-8"/>
    <title>Índice</title>
    </head>
    <body>
    <nav epub:type="toc" id="toc">
        <ol>
        {'\n      '.join(chapter_blocks)}
        </ol>
    </nav>
    </body>
    </html>"""

        # Escribir archivo
        self.write_text(nav_href, nav_xhtml)

        # Registrar/actualizar en manifest con properties="nav"
        existing = self.get_nav_href()
        if existing is None:
            self.add_to_manifest("nav", nav_href, media_type="application/xhtml+xml", properties="nav")
        elif existing != nav_href:
            self.rename_item("nav", nav_href)

        return nav_href

    # --- Helpers de anidado/render ---

    def _nest_headings(self, items: list[HeadingItem]):
        """
        Convierte una lista plana de headings ordenados por aparición
        en una estructura árbol según level (1..6).
        Devuelve lista de nodos: {"item": HeadingItem, "children": [...]}
        """
        root: list[dict] = []
        # stack de (nivel, children_list)
        stack: list[tuple[int, list]] = [(0, root)]

        for it in items:
            lvl = max(1, min(6, int(it.level)))
            # cerrar niveles hasta el padre inmediato
            while stack and lvl <= stack[-1][0]:
                stack.pop()
            parent_children = stack[-1][1]
            node = {"item": it, "children": []}
            parent_children.append(node)
            stack.append((lvl, node["children"]))

        return root

    def _render_nested_list(self, doc_rel: str, nodes: list[dict]) -> str:
        """
        Renderiza <ol> recursivo para los headings anidados de un capítulo.
        """
        if not nodes:
            return ""
        li_parts = []
        for n in nodes:
            it: HeadingItem = n["item"]
            href = f'{doc_rel}#{html.escape(it.anchor, True)}'
            text = html.escape(it.title, True)
            child_html = self._render_nested_list(doc_rel, n["children"])
            if child_html:
                li_parts.append(f'<li><a href="{href}">{text}</a>{child_html}</li>')
            else:
                li_parts.append(f'<li><a href="{href}">{text}</a></li>')
        return "<ol>\n" + "\n".join(li_parts) + "\n</ol>"

    def _extract_and_optionally_tag_headings(
        self,
        raw: str,
        *,
        levels: tuple[int, ...] = (1, 2, 3),
        max_items: int = 200,
        add_missing_ids: bool = True,
    ):
        """
        Extrae headings (H1..H6) en orden de aparición y, si add_missing_ids=True,
        agrega id= a los que no tengan, asegurando unicidad dentro del documento.

        Devuelve:
        - result: {
            "doc_title": str|None,
            "entries": [{"level": int, "title": str, "anchor": str}, ...]
            }
        - new_raw: str (igual a raw si no hubo cambios)
        """

        # Namespace XHTML (fallback si no está definido)
        xhtml_ns = (NS.get("xhtml") if isinstance(globals().get("NS"), dict) else None) or "http://www.w3.org/1999/xhtml"

        # Helpers ---------------

        def _gettext(el):
            """Texto visible 'plano' de un elemento (concatena descendientes)."""
            parts = []
            if el.text:
                parts.append(el.text)
            for c in el:
                parts.append(_gettext(c))
                if c.tail:
                    parts.append(c.tail)
            return "".join(parts).strip()

        def _level_from_tag(tag: str) -> int | None:
            """Devuelve nivel 1..6 si es un hN con namespace XHTML; si no, None."""
            # Esperado: tag == '{NS}hN'
            if tag.startswith("{") and "}" in tag:
                local = tag[tag.rfind("}") + 1 :]
            else:
                local = tag
            if len(local) == 2 and local[0] == "h" and local[1].isdigit():
                n = int(local[1])
                if 1 <= n <= 6:
                    return n
            return None

        def _collect_existing_ids(root_el):
            s = set()
            for el in root_el.iter():
                _id = el.get("id")
                if _id:
                    s.add(_id)
            return s

        def _unique_id(base: str, existing: set[str]) -> str:
            cand = base
            k = 1
            while cand in existing:
                k += 1
                cand = f"{base}-{k}"
            existing.add(cand)
            return cand

        # Parseo ---------------

        changed = False
        # Guardar prólogo (xml decl y doctype) para reinyectarlo si serializamos
        prolog_match = re.match(r"^\s*(?P<xml><\?xml[^>]*\?>\s*)?(?P<doctype><!DOCTYPE[^>]+>\s*)?", raw, flags=re.IGNORECASE | re.DOTALL)
        prolog = ""
        if prolog_match:
            prolog = (prolog_match.group("xml") or "") + (prolog_match.group("doctype") or "")

        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            # Si no se puede parsear, devolvemos vacío y sin cambios
            return {"doc_title": None, "entries": []}, raw

        # Título del documento (opcional)
        title = None
        title_tag = f"{{{xhtml_ns}}}title"
        head_tag = f"{{{xhtml_ns}}}head"
        html_tag = f"{{{xhtml_ns}}}html"
        try:
            # buscar <head><title>
            if root.tag == html_tag:
                head = root.find(head_tag)
                if head is not None:
                    t = head.find(title_tag)
                    if t is not None:
                        title = _gettext(t) or None
            else:
                # fallback: buscar en todo el árbol
                t = root.find(f".//{title_tag}")
                if t is not None:
                    title = _gettext(t) or None
        except Exception:
            title = None

        # Recolectar headings EN ORDEN DE APARICIÓN
        levels_set = set(int(n) for n in levels)
        existing_ids = _collect_existing_ids(root)

        entries = []
        count = 0

        for el in root.iter():  # respeta orden del documento
            lvl = _level_from_tag(el.tag)
            if lvl is None or lvl not in levels_set:
                continue
            if count >= max_items:
                break

            text = _gettext(el) or f"H{lvl} sin título"
            anchor = el.get("id")

            if not anchor:
                if not add_missing_ids:
                    # Sin id y no queremos modificar el doc → evitamos links rotos
                    continue
                # Generar un id único, estable-ish (basado en orden)
                base = f"auto-h{lvl}-{count+1}"
                # Asegurar unicidad por si ya existe "auto-h1-1" en otro lado
                anchor = _unique_id(base, existing_ids)
                el.set("id", anchor)
                changed = True

            entries.append({"level": lvl, "title": text, "anchor": anchor})
            count += 1

        result = {
            "doc_title": title,
            "entries": entries,
        }

        # Serializar sólo si hubo cambios
        if changed:
            # xml.etree no preserva doctype; reinyectamos prólogo capturado (si había)
            body = ET.tostring(root, encoding="unicode")
            new_raw = f"{prolog}{body}" if prolog else body
            return result, new_raw
        else:
            return result, raw


    def _escape(text: str) -> str:
        return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


    def _extract_title_from_xhtml(self, href: str) -> str:
        try:
            raw = self.read_text(href)
            root = ET.fromstring(raw)
            t = root.find(".//xhtml:head/xhtml:title", NS)
            return _text(t)
        except Exception:
            return ""

    # -------------------------
    # Exportar
    # -------------------------
    def export_epub(self, out_path: Path, include_unreferenced: bool = False) -> None:
        """
        Empaqueta el workdir como EPUB sin usar ebooklib.
        - Escribe mimetype primero (sin compresión).
        - Incluye META-INF/container.xml, el OPF y TODOS los items del manifest.
        - Si include_unreferenced=True, agrega también cualquier archivo del workdir
        que no esté en el manifest (útil si tenés extras).
        """
        # --- Validaciones mínimas ---
        if self.container_path is None or not self.container_path.exists():
            raise RuntimeError("Falta META-INF/container.xml")
        if self.opf_path is None or not self.opf_path.exists():
            raise RuntimeError("No se resolvió el OPF")
        spine = self.get_spine()
        if not spine:
            raise RuntimeError("Spine vacío: agregá documentos al <spine> antes de exportar")

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Normalizador de rutas relativas (con '/')
        def rel(p: Path) -> str:
            return str(p.relative_to(self.workdir).as_posix())

        # --- Construir lista de entradas a zipear ---
        entries: list[tuple[Path, str, int]] = []  # (path_absoluto, arcname_relativo, compression)

        # 1) mimetype obligatorio en la raíz, sin compresión y PRIMERO
        mimetype_path = (self.workdir / "mimetype")
        if not mimetype_path.exists():
            # si no está, crearlo
            mimetype_path.write_bytes(EPUB_MIMETYPE)
        entries.append((mimetype_path, "mimetype", zipfile.ZIP_STORED))

        # 2) META-INF/container.xml (y otros META-INF si querés)
        meta_inf_dir = self.workdir / "META-INF"
        if not meta_inf_dir.exists():
            raise RuntimeError("Falta carpeta META-INF")
        container_xml = meta_inf_dir / "container.xml"
        if not container_xml.exists():
            raise RuntimeError("Falta META-INF/container.xml")
        # container.xml
        entries.append((container_xml, "META-INF/container.xml", zipfile.ZIP_DEFLATED))
        # (opcional) incluir cualquier otro archivo dentro de META-INF
        for extra in meta_inf_dir.rglob("*"):
            if extra.is_file() and extra != container_xml:
                entries.append((extra, rel(extra), zipfile.ZIP_DEFLATED))

        # 3) OPF + todos los items del manifest
        entries.append((self.opf_path, rel(self.opf_path), zipfile.ZIP_DEFLATED))
        # set de rutas ya añadidas para evitar duplicados
        added = { "mimetype", "META-INF/container.xml", rel(self.opf_path) }

        for mi in self.list_items():
            abs_path = (self.opf_dir / mi.href).resolve()
            arcname = rel(abs_path)
            if not abs_path.exists():
                raise FileNotFoundError(f"Falta en disco el recurso del manifest: {mi.href}")
            if arcname not in added:
                entries.append((abs_path, arcname, zipfile.ZIP_DEFLATED))
                added.add(arcname)

        # 4) (Opcional) incluir archivos no referenciados por el manifest
        if include_unreferenced:
            for p in self.workdir.rglob("*"):
                if p.is_file():
                    arcname = rel(p)
                    # excluir temporales y lo ya agregado
                    if arcname in added:
                        continue
                    if any(arcname.endswith(suf) for suf in (".tmp", ".swp", ".DS_Store")):
                        continue
                    entries.append((p, arcname, zipfile.ZIP_DEFLATED))
                    added.add(arcname)

        # --- Escribir ZIP/EPUB respetando el orden (mimetype 1º) ---
        with zipfile.ZipFile(out_path, mode="w") as z:
            for path_abs, arcname, comp in entries:
                # asegurar separador '/'
                arcname = arcname.replace("\\", "/")
                # zipinfo para fijar permisos legibles (no imprescindible)
                z.write(path_abs, arcname=arcname, compress_type=comp)

        # Validación amistosa
        # Chequeo rápido: abrir el OPF dentro del .epub y verificar que el spine no esté vacío
        # (no reemplaza epubcheck, pero da feedback inmediato)
        try:
            with zipfile.ZipFile(out_path, "r") as z:
                # localizar el OPF según container.xml dentro del ZIP
                with z.open("META-INF/container.xml") as f:
                    cont = ET.fromstring(f.read())
                rootfile = cont.find(".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile")
                full_path = rootfile.get("full-path") if rootfile is not None else None
                if not full_path or full_path not in z.namelist():
                    raise RuntimeError("El EPUB exportado no contiene el OPF declarado en container.xml")
                with z.open(full_path) as f:
                    opf_root = ET.fromstring(f.read())
                spine_ids = [ir.get("idref") for ir in opf_root.findall(".//{http://www.idpf.org/2007/opf}spine/{http://www.idpf.org/2007/opf}itemref")]
                if not any(spine_ids):
                    raise RuntimeError("El EPUB exportado tiene <spine> vacío")
        except Exception as e:
            # No abortamos la exportación si este chequeo falla, pero avisamos
            print(f"[WARN] Validación post-export: {e}")


    # -------------------------
    # Persistir OPF
    # -------------------------
    def _save_opf(self) -> None:
        assert self.opf_tree is not None and self.opf_path is not None
        self.opf_tree.write(self.opf_path, encoding="utf-8", xml_declaration=True)
        # refrescar índices
        self._parse_opf()

    # -------------------------
    # Utilidades
    # -------------------------
    def _folder_for_kind(self, kind: str) -> str:
        if kind == KIND_DOCUMENT:
            return Path(self.layout["TEXT"]).name
        if kind == KIND_STYLE:
            return Path(self.layout["STYLES"]).name
        if kind in (KIND_IMAGE, KIND_VECTOR):
            return Path(self.layout["IMAGES"]).name
        if kind == KIND_FONT:
            return Path(self.layout["FONTS"]).name
        if kind == KIND_AUDIO:
            return Path(self.layout["AUDIO"]).name
        if kind == KIND_VIDEO:
            return Path(self.layout["VIDEO"]).name
        return Path(self.layout["TEXT"]).name

    def _unique_id(self, base: str) -> str:
        base = "".join(ch for ch in base if ch.isalnum() or ch in ("_", "-")) or "item"
        cand = base
        i = 1
        while cand in self.items_by_id:
            i += 1
            cand = f"{base}-{i}"
        return cand
    
    # core/guten_core.py (dentro de GutenCore)

    def xform_plaintext_to_xhtml_fragment(
        self,
        plain_text: str,
        keep_single_newline_as_br: bool = True,
        collapse_whitespace: bool = True,
    ) -> str:
        """Convierte texto plano → fragmento XHTML con <p> y <br/> (sin <html>/<body>)."""
        txt = plain_text.replace("\r\n", "\n").replace("\r", "\n")
        if collapse_whitespace:
            txt = re.sub(r"[ \t]+\n", "\n", txt)
            txt = re.sub(r"[ \t]{2,}", " ", txt)
        paras = [p.strip("\n ") for p in re.split(r"\n{2,}", txt)]
        paras = [p for p in paras if p.strip() != ""]

        def esc(s: str) -> str:
            return (s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))

        out = []
        for block in paras:
            if keep_single_newline_as_br:
                body = "<br/>\n".join(esc(line) for line in block.split("\n"))
            else:
                body = esc(block.replace("\n"," "))
            out.append(f"<p>{body}</p>")
        return "\n".join(out) if out else "<p></p>"

    def xform_html_to_xhtml_fragment(self, raw_html: str) -> str:
        """Limpia HTML pegado y devuelve un fragmento XHTML seguro (sin <html>/<body>)."""
        try:
            from bs4 import BeautifulSoup
        except Exception as e:
            raise RuntimeError("Falta beautifulsoup4: pip install beautifulsoup4") from e

        soup = BeautifulSoup(raw_html, "html.parser")

        # remove scripts/iframes/etc
        for t in soup(["script","iframe","form","object","embed","noscript","style"]):
            t.decompose()

        # si viene un documento completo, quedate con <body> o todo
        root = soup.body or soup
        # normalizar etiquetas básicas <b>/<i> → <strong>/<em>
        for b in root.find_all("b"): b.name = "strong"
        for i in root.find_all("i"): i.name = "em"

        # quitar la mayoría de estilos inline (dejá alt/title/href/src)
        ALLOWED_ATTR = {"href","title","alt","src","id"}
        for tag in root.find_all(True):
            attrs = dict(tag.attrs)
            for k in list(attrs.keys()):
                if k not in ALLOWED_ATTR:
                    del tag.attrs[k]

        # serializar solo el contenido del body (fragmento)
        frag = "".join(str(c) for c in root.contents).strip()
        # ensure XHTML self-closing for <br> <hr> <img ...>
        frag = frag.replace("<br>", "<br/>").replace("<hr>", "<hr/>")
        return frag
    
    def set_styles_for_documents(
        self,
        docs: list[str],
        styles: list[str],
        *,
        clear_existing: bool = True,
        add_to_manifest_if_missing: bool = True,
    ) -> dict[str, list[str]]:
        """
        Aplica la MISMA lista de estilos a VARIOS documentos XHTML/HTML.

        - docs: lista de ids de manifest o hrefs relativos al OPF (p.ej. "Text/0003.xhtml").
        - styles: lista de nombres de archivo CSS o hrefs relativos al OPF.
        * Si pasás solo el nombre (ej. "extra.css"), se asume en la carpeta STYLES del layout.
        * Si pasás "Styles/extra.css" (relativo al OPF), se usa tal cual.
        - clear_existing: elimina los <link rel="stylesheet"> actuales del <head> antes de insertar.
        - add_to_manifest_if_missing: si un CSS existe en disco pero no está en el manifest, lo agrega.

        Retorna: dict { href_doc: [href_relativos_insertados...] }
                (los hrefs insertados son relativos al documento, típicamente "../Styles/*.css")
        """
        # 1) Normalizar lista de estilos a HREFS relativos al OPF y asegurar manifest si corresponde
        styles_dir_name = Path(self.layout["STYLES"]).name
        styles_opf_hrefs: list[str] = []

        for s in styles:
            s = s.replace("\\", "/")
            if "/" not in s:  # solo nombre → carpeta STYLES
                opf_href = f"{styles_dir_name}/{s}"
            else:
                opf_href = s.lstrip("/")
            styles_opf_hrefs.append(opf_href)

            if add_to_manifest_if_missing and opf_href not in self.items_by_href:
                abs_path = (self.opf_dir / opf_href).resolve()
                if abs_path.exists():
                    css_id = self._unique_id(Path(opf_href).stem)
                    self.add_to_manifest(css_id, opf_href, media_type="text/css")

        results: dict[str, list[str]] = {}

        # 2) Aplicar a cada documento
        for d in docs:
            mi_doc = self._get_item(d)
            mt = (mi_doc.media_type or "").split(";")[0].strip().lower()
            is_doc_by_mt = mt in ("application/xhtml+xml", "text/html")

            ext = Path(mi_doc.href).suffix.lower()
            is_doc_by_ext = ext in (".xhtml", ".html", ".htm")

            if not (is_doc_by_mt or is_doc_by_ext):
                raise ValueError(f"'{d}' no es un documento XHTML/HTML (media-type={mi_doc.media_type})")

            # hrefs RELATIVOS al documento (../Styles/foo.css)
            from posixpath import relpath as posix_relpath
            doc_dir = Path(mi_doc.href).parent.as_posix()
            rel_links = [
                posix_relpath(opf_href, start=doc_dir) if doc_dir else opf_href
                for opf_href in styles_opf_hrefs
            ]

            # Editar el XHTML: limpiar/insertar <link>
            import xml.etree.ElementTree as ET
            raw = self.read_text(mi_doc.href)
            try:
                root = ET.fromstring(raw)
            except ET.ParseError as e:
                raise RuntimeError(f"XHTML mal formado en {mi_doc.href}: {e}")

            head = root.find(".//xhtml:head", NS)
            if head is None:
                html = root if root.tag.endswith("html") else None
                if html is None:
                    raise RuntimeError(f"No se encontró <head> ni <html> en {mi_doc.href}")
                head = ET.SubElement(html, f"{{{NS['xhtml']}}}head")

            if clear_existing:
                for link in list(head.findall("xhtml:link", NS)):
                    if (link.get("rel") or "").lower() == "stylesheet":
                        head.remove(link)

            for rel_href in rel_links:
                ET.SubElement(head, f"{{{NS['xhtml']}}}link", {
                    "rel": "stylesheet",
                    "type": "text/css",
                    "href": rel_href
                })

            # Guardar (ET no preserva DOCTYPE; válido para EPUB3)
            new_xml = ET.tostring(root, encoding="unicode")
            self.write_text(mi_doc.href, new_xml)

            results[mi_doc.href] = rel_links

        return results

    def _update_item_properties(self, id_or_href: str, new_properties: str = "") -> None:
        """
        Actualiza las propiedades de un item en el manifest.

        Args:
            id_or_href: ID o href del item a actualizar
            new_properties: Nueva cadena de propiedades (ej. "cover-image", "nav")
        """
        assert self.opf_tree is not None
        root = self.opf_tree.getroot()
        man = root.find(".//opf:manifest", NS)

        # Obtener el item del manifest
        mi = self._get_item(id_or_href)

        # Encontrar el elemento XML correspondiente
        for item_elem in man.findall("opf:item", NS):
            if item_elem.get("id") == mi.id:
                # Actualizar propiedades en el XML
                if new_properties.strip():
                    item_elem.set("properties", new_properties.strip())
                else:
                    # Remover atributo properties si está vacío
                    if "properties" in item_elem.attrib:
                        del item_elem.attrib["properties"]

                # Actualizar en memoria
                mi.properties = new_properties.strip()

                # Guardar cambios
                self._save_opf()
                return

        raise ValueError(f"No se encontró item con id/href: {id_or_href}")

    def find_items(self,
               *, 
               kind: str | None = None,
               media_types: tuple[str, ...] | None = None,
               ext: tuple[str, ...] | None = None,
               in_spine: bool | None = None,
               folder: str | None = None,
               properties_contains: str | None = None):
        """
        Filtros combinables:
        - kind: usa las constantes KIND_*
        - media_types: ej ('application/xhtml+xml','text/html')
        - ext: ej ('.xhtml','.html','.css','.png')
        - in_spine: True solo los que están en <spine>, False los que no; None = todos
        - folder: prefijo de href, ej 'Text/' o 'Images/'
        - properties_contains: substring en 'properties' (ej. 'nav', 'cover-image')
        """
        items = self.list_items(kind) if kind else self.list_items()
        if media_types:
            mts = tuple(m.lower() for m in media_types)
            items = [mi for mi in items if mi.media_type.lower() in mts]
        if ext:
            exts = tuple(e.lower() for e in ext)
            items = [mi for mi in items if Path(mi.href).suffix.lower() in exts]
        if folder:
            prefix = folder if folder.endswith("/") else (folder + "/")
            items = [mi for mi in items if mi.href.startswith(prefix)]
        if properties_contains:
            items = [mi for mi in items if properties_contains in (mi.properties or "")]
        if in_spine is not None:
            spine_set = set(self.get_spine())
            items = [mi for mi in items if ((mi.id in spine_set) == in_spine)]
        return items



# -----------------------------
# Fin del módulo
# -----------------------------

if __name__ == "__main__":
    # core = GutenCore.open_epub(epub_path=Path("/home/pedro/PycharmProjects/gutenai/Ready Player Two - Ernest Cline.epub"), workdir=Path("/home/pedro/PycharmProjects/gutenai/libros/"))
    core = GutenCore.open_folder("/home/pedro/Documentos/GutenAI-books/Amadeo/NuevoEPUB")
    # print(core.get_metadata())          # {'title': ..., 'language': ..., 'identifier': ...}
    # print(core.get_spine())             # ['chap1', 'chap2', ...] (idref en orden)
    for item in core.find_items(kind=KIND_IMAGE):      # manifest completo
        print(item.id, item.href, item.media_type)
    # core.set_styles_for_documents(["Prólogo"], ["style.css"])
