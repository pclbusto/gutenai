"""
core/hook_index_manager.py
Sistema de indexación de hooks (id's) en archivos HTML del EPUB

Arquitectura:
- Motor de extracción: BeautifulSoup con lxml y SoupStrainer
- Almacenamiento: Índice maestro en RAM (diccionario anidado)
- Actualización: Lazy/reactiva por eventos (FocusOut, Save)
- Consumo: O(1) lookup para UI/validación
"""

from bs4 import BeautifulSoup, SoupStrainer
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import time


@dataclass
class Hook:
    """Representa un hook (elemento con id) en el HTML"""
    file_href: str  # Archivo donde se encuentra (ej: "Text/capitulo_01.xhtml")
    hook_id: str  # ID técnico (ej: "inicio-batalla")
    context_text: str  # Texto de contexto legible (ej: "El inicio de la gran batalla")
    tag_name: str  # Nombre de la etiqueta (ej: "p", "h1", "div")
    line_number: Optional[int] = None  # Número de línea aproximado (opcional)


class HookIndexManager:
    """
    Gestiona el índice maestro de hooks en memoria

    Estructura del índice:
    {
        "Text/capitulo_01.xhtml": {
            "inicio-batalla": Hook(...),
            "fin-batalla": Hook(...)
        },
        "Text/capitulo_02.xhtml": {
            "encuentro-dragon": Hook(...)
        }
    }
    """

    def __init__(self, guten_core):
        """
        Inicializa el gestor de índice

        Args:
            guten_core: Instancia de GutenCore para acceder a los archivos
        """
        self.core = guten_core

        # Índice maestro: {file_href: {hook_id: Hook}}
        self.index: Dict[str, Dict[str, Hook]] = {}

        # Tracking de cambios para optimización
        self._dirty_files: Set[str] = set()  # Archivos pendientes de re-indexar
        self._last_index_time: Dict[str, float] = {}  # Timestamp de última indexación

        # Configuración
        self.max_context_length = 50  # Longitud máxima del texto de contexto

    # =====================================================
    # INDEXACIÓN INICIAL Y COMPLETA
    # =====================================================

    def build_full_index(self) -> Dict[str, int]:
        """
        Construye el índice completo escaneando todos los archivos HTML del EPUB

        Se llama al abrir el EPUB por primera vez.

        Returns:
            Estadísticas: {"files_indexed": int, "hooks_found": int, "time_ms": int}
        """
        if not self.core or not self.core.opf_dir:
            return {"files_indexed": 0, "hooks_found": 0, "time_ms": 0}

        start_time = time.time()

        # Limpiar índice anterior
        self.index.clear()
        self._dirty_files.clear()
        self._last_index_time.clear()

        # Obtener todos los archivos HTML del manifest
        html_files = self._get_all_html_files()

        total_hooks = 0
        for file_href in html_files:
            hooks_in_file = self._index_file(file_href)
            total_hooks += len(hooks_in_file)

        elapsed_ms = int((time.time() - start_time) * 1000)

        return {
            "files_indexed": len(html_files),
            "hooks_found": total_hooks,
            "time_ms": elapsed_ms
        }

    def _get_all_html_files(self) -> List[str]:
        """Obtiene lista de todos los archivos HTML/XHTML del manifest"""
        html_files = []

        if not self.core or not hasattr(self.core, 'items_by_id'):
            return html_files

        for item in self.core.items_by_id.values():
            media_type = (item.media_type or "").lower()
            href = item.href

            # Filtrar solo HTML/XHTML
            if media_type in ("application/xhtml+xml", "text/html"):
                html_files.append(href)
            elif href.endswith(('.html', '.xhtml', '.htm')):
                html_files.append(href)

        return html_files

    # =====================================================
    # INDEXACIÓN DE ARCHIVO INDIVIDUAL
    # =====================================================

    def _index_file(self, file_href: str) -> Dict[str, Hook]:
        """
        Indexa un archivo individual extrayendo todos sus hooks

        Args:
            file_href: Ruta relativa del archivo (ej: "Text/capitulo_01.xhtml")

        Returns:
            Diccionario {hook_id: Hook} de hooks encontrados
        """
        hooks_dict = {}

        try:
            # Leer contenido del archivo
            content = self.core.read_text(file_href)

            # Parsear SOLO elementos con id (strainer para performance)
            # SoupStrainer filtra al vuelo mientras parsea, es mucho más rápido
            # que parsear todo y filtrar después
            only_elements_with_id = SoupStrainer(id=True)

            soup = BeautifulSoup(
                content,
                'lxml',  # Parser rápido
                parse_only=only_elements_with_id  # ¡Clave del rendimiento!
            )

            # Extraer hooks
            for element in soup.find_all(id=True):
                hook_id = element.get('id')

                if not hook_id:
                    continue

                # Extraer texto de contexto
                context_text = self._extract_context_text(element)

                # Crear objeto Hook
                hook = Hook(
                    file_href=file_href,
                    hook_id=hook_id,
                    context_text=context_text,
                    tag_name=element.name
                )

                hooks_dict[hook_id] = hook

            # Actualizar índice maestro
            self.index[file_href] = hooks_dict
            self._last_index_time[file_href] = time.time()

            # Marcar como limpio
            self._dirty_files.discard(file_href)

        except Exception as e:
            print(f"[HookIndex] Error indexando {file_href}: {e}")
            # En caso de error, mantener entrada vacía
            self.index[file_href] = {}

        return hooks_dict

    def _extract_context_text(self, element) -> str:
        """
        Extrae texto legible de un elemento para mostrar en UI

        Args:
            element: Elemento BeautifulSoup

        Returns:
            Texto de contexto truncado
        """
        # Obtener texto sin tags HTML
        text = element.get_text(strip=True)

        # Truncar si es muy largo
        if len(text) > self.max_context_length:
            text = text[:self.max_context_length] + "..."

        # Si no hay texto, usar nombre de tag + id
        if not text:
            text = f"<{element.name} id='{element.get('id')}'>"

        return text

    # =====================================================
    # ACTUALIZACIÓN REACTIVA (LAZY)
    # =====================================================

    def mark_file_dirty(self, file_href: str):
        """
        Marca un archivo como modificado (pendiente de re-indexación)

        Se llama cuando el usuario edita un archivo, pero NO se re-indexa
        inmediatamente. La re-indexación ocurre en eventos específicos.

        Args:
            file_href: Archivo modificado
        """
        self._dirty_files.add(file_href)

    def update_file_index(self, file_href: str) -> int:
        """
        Re-indexa un archivo específico (actualización reactiva)

        Se llama en eventos: FocusOut, Save, etc.

        Args:
            file_href: Archivo a re-indexar

        Returns:
            Número de hooks encontrados
        """
        hooks = self._index_file(file_href)
        return len(hooks)

    def update_dirty_files(self) -> int:
        """
        Re-indexa todos los archivos marcados como dirty

        Returns:
            Número de archivos actualizados
        """
        dirty_copy = list(self._dirty_files)  # Copiar para evitar modificación durante iteración

        for file_href in dirty_copy:
            self.update_file_index(file_href)

        return len(dirty_copy)

    # =====================================================
    # CONSULTAS (UI/VALIDACIÓN)
    # =====================================================

    def hook_exists(self, hook_id: str, file_href: Optional[str] = None) -> bool:
        """
        Verifica si un hook existe en el índice

        Args:
            hook_id: ID a verificar
            file_href: Si se especifica, busca solo en ese archivo.
                      Si es None, busca en todo el EPUB.

        Returns:
            True si existe, False si no

        Complejidad: O(1) si file_href está especificado, O(n) si busca global
        """
        if file_href:
            # Búsqueda en archivo específico: O(1)
            if file_href in self.index:
                return hook_id in self.index[file_href]
            return False
        else:
            # Búsqueda global: O(n) donde n = número de archivos
            for file_dict in self.index.values():
                if hook_id in file_dict:
                    return True
            return False

    def get_hook(self, hook_id: str, file_href: Optional[str] = None) -> Optional[Hook]:
        """
        Obtiene información completa de un hook

        Args:
            hook_id: ID a buscar
            file_href: Archivo específico (opcional)

        Returns:
            Objeto Hook si existe, None si no
        """
        if file_href:
            if file_href in self.index:
                return self.index[file_href].get(hook_id)
            return None
        else:
            # Búsqueda global
            for file_dict in self.index.values():
                if hook_id in file_dict:
                    return file_dict[hook_id]
            return None

    def get_all_hooks_in_file(self, file_href: str) -> List[Hook]:
        """
        Obtiene todos los hooks de un archivo

        Args:
            file_href: Archivo a consultar

        Returns:
            Lista de hooks ordenados por ID
        """
        if file_href not in self.index:
            return []

        return sorted(self.index[file_href].values(), key=lambda h: h.hook_id)

    def get_all_hooks(self) -> List[Hook]:
        """
        Obtiene todos los hooks del EPUB

        Returns:
            Lista completa de hooks ordenados por archivo y luego por ID
        """
        all_hooks = []

        for file_href in sorted(self.index.keys()):
            all_hooks.extend(self.index[file_href].values())

        return all_hooks

    def search_hooks(self, query: str, max_results: int = 20) -> List[Hook]:
        """
        Búsqueda difusa de hooks por ID o contexto

        Args:
            query: Texto a buscar (case-insensitive)
            max_results: Máximo de resultados a retornar

        Returns:
            Lista de hooks que coinciden con la búsqueda
        """
        query_lower = query.lower()
        results = []

        for file_dict in self.index.values():
            for hook in file_dict.values():
                # Buscar en ID o en texto de contexto
                if (query_lower in hook.hook_id.lower() or
                    query_lower in hook.context_text.lower()):
                    results.append(hook)

                    if len(results) >= max_results:
                        return results

        return results

    def get_hooks_by_file(self) -> Dict[str, List[str]]:
        """
        Obtiene estructura simplificada: archivo -> lista de IDs

        Útil para UI de navegación/árbol

        Returns:
            {"Text/cap1.xhtml": ["id1", "id2"], ...}
        """
        result = {}

        for file_href, hooks_dict in self.index.items():
            result[file_href] = sorted(hooks_dict.keys())

        return result

    # =====================================================
    # ESTADÍSTICAS Y DEBUGGING
    # =====================================================

    def get_stats(self) -> Dict[str, any]:
        """
        Obtiene estadísticas del índice

        Returns:
            Diccionario con métricas útiles
        """
        total_hooks = sum(len(hooks) for hooks in self.index.values())

        return {
            "total_files": len(self.index),
            "total_hooks": total_hooks,
            "dirty_files": len(self._dirty_files),
            "avg_hooks_per_file": total_hooks / len(self.index) if self.index else 0,
            "files_indexed": list(self.index.keys()),
            "dirty_files_list": list(self._dirty_files)
        }

    def validate_index_integrity(self) -> Dict[str, any]:
        """
        Valida la integridad del índice comparando con archivos reales

        Útil para debugging o post-procesamiento

        Returns:
            Reporte de validación
        """
        issues = []

        # Verificar que todos los archivos en el índice existen
        for file_href in self.index.keys():
            try:
                self.core.read_text(file_href)
            except:
                issues.append(f"Archivo en índice no existe: {file_href}")

        # Verificar que todos los archivos HTML están indexados
        all_html = self._get_all_html_files()
        for file_href in all_html:
            if file_href not in self.index:
                issues.append(f"Archivo HTML no está indexado: {file_href}")

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "files_in_index": len(self.index),
            "files_in_epub": len(all_html)
        }
