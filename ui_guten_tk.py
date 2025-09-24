# ui_guten_tk.py
from __future__ import annotations

import tempfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

# --- Tu core (ruta corregida) ---
from core.guten_core import (
    GutenCore,
    KIND_DOCUMENT, KIND_STYLE, KIND_IMAGE, KIND_FONT, KIND_AUDIO, KIND_VIDEO
)

# --- Resaltado (opcional) ---
try:
    from pygments import lex
    from pygments.lexers import HtmlLexer, CssLexer
    from pygments.token import Token
    _HAS_PYGMENTS = True
except Exception:
    _HAS_PYGMENTS = False

# --- Imágenes ---
try:
    from PIL import Image, ImageTk
    _HAS_PIL = True
except Exception:
    _HAS_PIL = False

APP_TITLE = "GutenAI — Explorador EPUB (Tk)"
SECTION_KEYS_ORDER = ["TEXT", "STYLES", "IMAGES", "FONTS", "AUDIO", "VIDEO"]


def guess_kind_by_extension(filename: str) -> str:
    fn = filename.lower()
    if fn.endswith((".xhtml", ".html", ".htm")):
        return KIND_DOCUMENT
    if fn.endswith(".css"):
        return KIND_STYLE
    if fn.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif")):
        return KIND_IMAGE
    if fn.endswith((".ttf", ".otf", ".woff", ".woff2")):
        return KIND_FONT
    if fn.endswith((".mp3", ".m4a", ".aac", ".ogg", ".opus")):
        return KIND_AUDIO
    if fn.endswith((".mp4", ".m4v", ".webm", ".ogv")):
        return KIND_VIDEO
    return "other"

class TocEditorDialog(tk.Toplevel):
    """
    Diálogo para seleccionar qué capítulos y headings incluir en el TOC.
    - Muestra capítulos (spine) y sus H1/H2/H3 (configurable).
    - Checkboxes ☑/☐ para incluir/excluir capítulos completos o headings individuales.
    - Botones: Seleccionar todo / Nada, Expandir / Colapsar, Refrescar (re-escanea),
      Generar (escribe nav.xhtml) y Cancelar.
    """
    CHECK_ON  = "☑"
    CHECK_OFF = "☐"

    def __init__(self, parent: tk.Tk, core):
        super().__init__(parent)
        self.core = core
        self.title("Editar TOC (selección manual)")
        self.transient(parent)
        self.resizable(True, True)
        self.minsize(800, 500)

        # variables de niveles
        self.var_h1 = tk.BooleanVar(value=True)
        self.var_h2 = tk.BooleanVar(value=True)
        self.var_h3 = tk.BooleanVar(value=True)

        # modelo en memoria: list[DocToc]
        self.toc_model = []  # se llena con collect_headings(...)
        self._nav_href_result = None
        self._row_index = {} 

        self._build_ui()
        self._load_model()

        # centrar sobre parent
        self.update_idletasks()
        self.geometry(self._center_on_parent(parent))

        # Bind para toggles en la primer columna
        self.tree.bind("<Button-1>", self._on_tree_click)

        # Modal
        self.grab_set()

    # ---------- UI ----------
    def _build_ui(self):
        # Top: opciones
        top = ttk.Frame(self)
        top.pack(side="top", fill="x", padx=10, pady=(10, 6))

        ttk.Label(top, text="Incluir niveles:").pack(side="left")
        ttk.Checkbutton(top, text="H1", variable=self.var_h1, command=self._reload_levels).pack(side="left", padx=6)
        ttk.Checkbutton(top, text="H2", variable=self.var_h2, command=self._reload_levels).pack(side="left", padx=6)
        ttk.Checkbutton(top, text="H3", variable=self.var_h3, command=self._reload_levels).pack(side="left", padx=6)

        ttk.Button(top, text="Refrescar", command=self._load_model).pack(side="right")
        ttk.Button(top, text="Colapsar todo", command=lambda: self._expand_all(False)).pack(side="right", padx=(0,6))
        ttk.Button(top, text="Expandir todo", command=lambda: self._expand_all(True)).pack(side="right", padx=(0,6))

        ttk.Button(top, text="Nada", command=self._select_none).pack(side="right", padx=(0,6))
        ttk.Button(top, text="Todo", command=self._select_all).pack(side="right", padx=(0,6))

        # Centro: árbol
        center = ttk.Frame(self)
        center.pack(fill="both", expand=True, padx=10, pady=6)

        cols = ("incl", "title", "ref")
        self.tree = ttk.Treeview(center, columns=cols, show="headings")
        self.tree.heading("incl", text="✔")
        self.tree.heading("title", text="Título")
        self.tree.heading("ref", text="Referencia")
        self.tree.column("incl", width=40, anchor="center")
        self.tree.column("title", width=380, anchor="w")
        self.tree.column("ref", width=220, anchor="w")

        ysb = ttk.Scrollbar(center, orient="vertical", command=self.tree.yview)
        xsb = ttk.Scrollbar(center, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=ysb.set, xscroll=xsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")
        center.rowconfigure(0, weight=1)
        center.columnconfigure(0, weight=1)

        # Bottom: acciones
        bottom = ttk.Frame(self)
        bottom.pack(side="bottom", fill="x", padx=10, pady=(6,10))
        ttk.Button(bottom, text="Cancelar", command=self._on_cancel).pack(side="right")
        ttk.Button(bottom, text="Generar TOC", command=self._on_generate).pack(side="right", padx=8)

    # ---------- Modelo ----------
    def _levels_tuple(self):
        levels = []
        if self.var_h1.get(): levels.append(1)
        if self.var_h2.get(): levels.append(2)
        if self.var_h3.get(): levels.append(3)
        return tuple(levels) or (1,)  # al menos H1

    def _load_model(self):
        # Lee del core el modelo (todos en include=True por defecto)
        try:
            self.toc_model = self.core.collect_headings(
                levels=self._levels_tuple(),
                source="spine",
                add_missing_ids=True,
                max_items_per_doc=500,
            )
        except Exception as e:
            messagebox.showerror("TOC", f"No se pudo recolectar headings:\n{e}")
            self.toc_model = []
        self._populate_tree()

    def _reload_levels(self):
        self._load_model()

    # ---------- Tree ----------
    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        self._row_index.clear()  # <-- NEW

        for chap_idx, chap in enumerate(self.toc_model):
            incl = self.CHECK_ON if getattr(chap, "include", True) else self.CHECK_OFF
            chap_text = chap.title or Path(chap.href).name

            chap_id = self.tree.insert(
                "", "end",
                values=(incl, chap_text, chap.href),
                open=False
            )
            self._row_index[chap_id] = ("C", chap_idx)   # <-- NEW

            for item_idx, h in enumerate(getattr(chap, "items", [])):
                incl_h = self.CHECK_ON if getattr(h, "include", True) else self.CHECK_OFF
                ref = f"{Path(chap.href).name}#{h.anchor}"
                node_id = self.tree.insert(
                    chap_id, "end",
                    values=(incl_h, f"{'  ' * max(0, h.level-1)}H{h.level} — {h.title}", ref),
                )
                self._row_index[node_id] = ("H", chap_idx, item_idx)  # <-- NEW

        # Hack: Treeview no soporta columnas ocultas; usamos item tags extra
        # Guardamos el índice en 'incl_idx' vía self.tree.set(...)

    def _expand_all(self, expand=True):
        for iid in self.tree.get_children(""):
            self.tree.item(iid, open=expand)
            for c in self.tree.get_children(iid):
                self.tree.item(c, open=expand)

    def _select_all(self):
        for chap in self.toc_model:
            chap.include = True
            for h in chap.items:
                h.include = True
        self._populate_tree()

    def _select_none(self):
        for chap in self.toc_model:
            chap.include = False
            for h in chap.items:
                h.include = False
        self._populate_tree()

    def _on_tree_click(self, event):
        # Solo toggle si clic en la primer columna ("incl")
        if self.tree.identify("region", event.x, event.y) != "cell":
            return
        if self.tree.identify_column(event.x) != "#1":
            return

        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return

        key = self._row_index.get(row_id)   # <-- NEW
        if not key:
            return

        if key[0] == "C":
            chap_idx = key[1]
            chap = self.toc_model[chap_idx]
            chap.include = not getattr(chap, "include", True)
            for h in chap.items:
                h.include = chap.include
        elif key[0] == "H":
            _, ci, hi = key
            chap = self.toc_model[ci]
            h = chap.items[hi]
            h.include = not getattr(h, "include", True)
            # sincronicemos el estado del capítulo
            chap.include = any(it.include for it in chap.items)

        self._populate_tree()


    # ---------- Acciones ----------
    def _on_generate(self):
        try:
            nav_href = self.core.render_nav_from_model(
                self.toc_model,
                nav_href=None,           # por defecto en Text/nav.xhtml
                overwrite=True,
                epub_version=3,
                lang="es"
            )
        except Exception as e:
            messagebox.showerror("TOC", f"No se pudo escribir nav.xhtml:\n{e}")
            return
        self._nav_href_result = nav_href
        self.destroy()

    def _on_cancel(self):
        self._nav_href_result = None
        self.destroy()

    def _center_on_parent(self, parent):
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        w, h = 900, 560
        x = px + (pw - w)//2
        y = py + (ph - h)//2
        return f"{w}x{h}+{max(0,x)}+{max(0,y)}"

    # API pública
    def show(self):
        self.wait_window(self)
        return self._nav_href_result


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        try:
            self.state("zoomed")
        except tk.TclError:
            self.attributes("-zoomed", True)
        self.minsize(1000, 650)

        self.core: GutenCore | None = None
        self.temp_workspace: Path | None = None

        self._build_menu()
        self._build_layout()
        self._build_context_menu()
        self._update_title()

    # ------------- Menú superior -------------
    def _build_menu(self):
        menubar = tk.Menu(self)

        # Archivo
        m_file = tk.Menu(menubar, tearoff=False)
        m_file.add_command(label="Abrir EPUB…", command=self.on_open_epub)
        m_file.add_command(label="Abrir carpeta…", command=self.on_open_folder)
        m_file.add_separator()
        m_file.add_command(label="Exportar EPUB…", command=self.on_export_epub)
        m_file.add_separator()
        m_file.add_command(label="Salir", command=self.destroy)
        menubar.add_cascade(label="Archivo", menu=m_file)

        # Herramientas
        m_tools = tk.Menu(menubar, tearoff=False)
        m_tools.add_command(label="Generar TOC (H1–H3)", accelerator="Ctrl+T", command=self.on_generate_toc)
        m_tools.add_separator()
        m_tools.add_command(label="Editar TOC…", accelerator="Ctrl+E", command=self.on_edit_toc)
        menubar.add_cascade(label="Herramientas", menu=m_tools)

        self.bind_all("<Control-e>", lambda e: self.on_edit_toc())

        self.bind_all("<Control-t>", lambda e: self.on_generate_toc())

        self.config(menu=menubar)


    # ------------- Layout -------------
    def _build_layout(self):
        paned = ttk.Panedwindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        # Izquierda
        left = ttk.Frame(paned)
        paned.add(left, weight=1)

        self.tree = ttk.Treeview(left, show="tree")
        ysb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        ysb.pack(side="right", fill="y")

        # Bindings
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        # Click derecho (Windows/Linux) y Ctrl-Click (mac) para menú contextual
        self.tree.bind("<Button-3>", self.on_tree_right_click)
        self.tree.bind("<Control-Button-1>", self.on_tree_right_click)

        # Derecha (visor)
        right = ttk.Frame(paned)
        paned.add(right, weight=3)

        topbar = ttk.Frame(right)
        topbar.pack(side="top", fill="x")
        self.path_label = ttk.Label(topbar, text="—", anchor="w")
        self.path_label.pack(side="left", padx=8, pady=6, fill="x")

        self.viewer_stack = ttk.Frame(right)
        self.viewer_stack.pack(fill="both", expand=True)

        # Texto
        self.text_frame = ttk.Frame(self.viewer_stack)
        self.text = tk.Text(self.text_frame, wrap="none", undo=False)
        self.text.configure(font=("DejaVu Sans Mono", 11))
        self.text_scroll_y = ttk.Scrollbar(self.text_frame, orient="vertical", command=self.text.yview)
        self.text_scroll_x = ttk.Scrollbar(self.text_frame, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=self.text_scroll_y.set, xscrollcommand=self.text_scroll_x.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        self.text_scroll_y.grid(row=0, column=1, sticky="ns")
        self.text_scroll_x.grid(row=1, column=0, sticky="ew")
        self.text_frame.rowconfigure(0, weight=1)
        self.text_frame.columnconfigure(0, weight=1)

        # Imagen
        self.image_frame = ttk.Frame(self.viewer_stack)
        self.canvas = tk.Canvas(self.image_frame, highlightthickness=0, background="#111")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self._original_image = None
        self._tk_image = None
        self._current_img_path: Path | None = None

        # Mensaje vacío
        self.empty_label = ttk.Label(
            self.viewer_stack,
            text="Abrí un EPUB o una carpeta para ver su estructura.\nDoble clic en un recurso para previsualizar.",
            justify="center", anchor="center"
        )
        self.empty_label.pack(fill="both", expand=True, padx=24, pady=24)

        # Stack
        self.text_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.image_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._show_empty()

    # ------------- Menú contextual -------------
    def _build_context_menu(self):
        self.ctx = tk.Menu(self, tearoff=False)
        self.ctx.add_command(label="Nuevo HTML…", command=self._action_new_html)
        self.ctx.add_command(label="Nuevo CSS…", command=self._action_new_css)

    def on_edit_toc(self):
        if not self.core:
            messagebox.showinfo("TOC", "Abrí un proyecto primero.")
            return
        dlg = TocEditorDialog(self, self.core)
        nav_href = dlg.show()
        if nav_href:
            # refrescá el árbol, seleccioná y mostrà el nav
            self._populate_tree()
            self._select_href(nav_href)
            try:
                nav_text = self.core.read_text(nav_href)
                self._show_text(nav_text, nav_href)
            except Exception:
                pass
            messagebox.showinfo("TOC", f"TOC actualizado en:\n{nav_href}")

    
    def on_generate_toc(self):
        if not self.core:
            messagebox.showinfo("TOC", "Abrí un proyecto primero.")
            return

        # Opcional: confirmar sobreescritura
        if self.core.nav_exists():
            if not messagebox.askyesno("TOC", "Ya existe un nav.xhtml.\n¿Reemplazarlo?", default="yes"):
                return

        try:
            nav_href = self.core.generate_nav_from_headings(levels=(1,2,3), overwrite=True, add_missing_ids=True)
        except Exception as e:
            messagebox.showerror("TOC", f"No se pudo generar el TOC:\n{e}")
            return

        # Refrescar árbol y seleccionar el nav
        self._populate_tree()
        self._select_href(nav_href)

        # Mostrar en el visor (texto)
        try:
            nav_text = self.core.read_text(nav_href)
            self._show_text(nav_text, nav_href)
        except Exception:
            pass

        messagebox.showinfo("TOC", f"TOC regenerado en:\n{nav_href}")


    def on_tree_right_click(self, event):
        # Seleccionar el item bajo el cursor y popup menú
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            self.tree.focus(iid)
        self.ctx.tk_popup(event.x_root, event.y_root)

    # Acciones del menú contextual
    def _action_new_html(self):
        if not self.core:
            messagebox.showinfo("Nuevo HTML", "Abrí un proyecto primero.")
            return

        # Preguntar nombre base (sin ruta) y título
        name = simpledialog.askstring("Nuevo HTML", "Nombre de archivo (ej: cap_nuevo.xhtml):", parent=self)
        if not name:
            return
        if not name.lower().endswith((".xhtml", ".html", ".htm")):
            name += ".xhtml"
        title = simpledialog.askstring("Nuevo HTML", "Título (opcional):", parent=self) or Path(name).stem

        # Carpeta destino: la de Text del layout
        text_dir = Path(self.core.layout["TEXT"]).name
        try:
            mi = self.core.create_document(name, title=title)  # ya lo guarda en Text/, lo añade a manifest y spine
        except Exception as e:
            messagebox.showerror("Nuevo HTML", f"No se pudo crear el documento:\n{e}")
            return

        self._populate_tree()
        self._select_href(mi.href)

    def _action_new_css(self):
        if not self.core:
            messagebox.showinfo("Nuevo CSS", "Abrí un proyecto primero.")
            return

        name = simpledialog.askstring("Nuevo CSS", "Nombre de archivo (ej: extra.css):", parent=self)
        if not name:
            return
        if not name.lower().endswith(".css"):
            name += ".css"

        styles_dir = Path(self.core.layout["STYLES"]).name
        href = f"{styles_dir}/{name}"
        try:
            self.core.write_text(href, "/* nuevo stylesheet */\n")
            new_id = self.core._unique_id(Path(name).stem)
            self.core.add_to_manifest(new_id, href, media_type="text/css")
        except Exception as e:
            messagebox.showerror("Nuevo CSS", f"No se pudo crear el stylesheet:\n{e}")
            return

        self._populate_tree()
        self._select_href(href)

    # ------------- Acciones archivo -------------
    def on_open_epub(self):
        path = filedialog.askopenfilename(title="Abrir EPUB", filetypes=[("EPUB", "*.epub"), ("Todos", "*.*")])
        if not path:
            return
        self._cleanup_temp_workspace()
        tmp_root = Path(tempfile.mkdtemp(prefix="gutenai_"))
        try:
            self.core = GutenCore.open_epub(Path(path), tmp_root)
            self.temp_workspace = self.core.workdir
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el EPUB:\n{e}")
            self.core = None
            self.temp_workspace = None
            return
        self._populate_tree()

    def on_open_folder(self):
        folder = filedialog.askdirectory(title="Abrir carpeta de trabajo (workdir)")
        if not folder:
            return
        try:
            self.core = GutenCore.open_folder(Path(folder))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n{e}")
            self.core = None
            return
        self._populate_tree()

    def on_export_epub(self):
        if not self.core:
            messagebox.showinfo("Exportar", "Primero abrí un proyecto.")
            return
        out = filedialog.asksaveasfilename(title="Exportar EPUB", defaultextension=".epub",
                                           filetypes=[("EPUB", "*.epub")])
        if not out:
            return
        try:
            self.core.export_epub(Path(out))
            messagebox.showinfo("Exportar", f"EPUB exportado:\n{out}")
        except Exception as e:
            messagebox.showerror("Exportar", f"Fallo al exportar:\n{e}")

    # ------------- Árbol / buckets -------------
    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        self._show_empty()
        if not self.core:
            self._update_title()
            return

        project_name = self.core.workdir.name
        root_id = self.tree.insert("", "end", text=f"{project_name}", open=True)

        layout = self.core.layout.copy()
        extra_dirs = self._detect_extra_dirs(layout)
        buckets = self._build_buckets(layout, extra_dirs)

        for key in SECTION_KEYS_ORDER:
            sect_name = Path(layout[key]).name
            files = buckets.get(sect_name, [])
            node = self._insert_section(root_id, sect_name, files)
            for mi in files:
                self._insert_item(node, mi)

        otros_name = "Otros"
        other_files = buckets.get(otros_name, [])
        node_otros = self._insert_section(root_id, otros_name, other_files)
        for mi in other_files:
            self._insert_item(node_otros, mi)

        self._update_title()

    def _insert_section(self, parent, section_label: str, files: list) -> str:
        count = len(files)
        label = f"{section_label} ({count})"
        return self.tree.insert(parent, "end", text=label, open=False)

    def _insert_item(self, parent, manifest_item) -> str:
        name = Path(manifest_item.href).name
        return self.tree.insert(parent, "end",
                                text=f"{name}    [{manifest_item.id}]",
                                values=(manifest_item.href,))

    def _build_buckets(self, layout: dict, extra_dirs: set[str]) -> dict[str, list]:
        assert self.core is not None
        buckets: dict[str, list] = {}
        for key in SECTION_KEYS_ORDER:
            buckets[Path(layout[key]).name] = []
        buckets["Otros"] = []
        items = self.core.list_items()
        for mi in items:
            top = self._top_folder_of_href(mi.href)
            matched = False
            for key in SECTION_KEYS_ORDER:
                sect = Path(layout[key]).name
                if top == sect:
                    buckets[sect].append(mi)
                    matched = True
                    break
            if not matched:
                buckets["Otros"].append(mi)
        for d in sorted(extra_dirs):
            buckets.setdefault(d, [])
        return buckets

    def _top_folder_of_href(self, href: str) -> str:
        parts = Path(href).as_posix().split("/")
        return parts[0] if parts else ""

    def _detect_extra_dirs(self, layout: dict) -> set[str]:
        assert self.core is not None
        standard = {Path(layout[k]).name for k in layout}
        extras = set()
        for mi in self.core.list_items():
            top = self._top_folder_of_href(mi.href)
            if top and top not in standard and top != "META-INF":
                extras.add(top)
        return extras

    # ------------- Doble clic en recurso -------------
    def on_tree_double_click(self, _event):
        if not self.core:
            return
        sel = self.tree.focus()
        if not sel:
            return
        if self.tree.get_children(sel):
            return  # es sección
        vals = self.tree.item(sel, "values")
        if not vals:
            return
        href = vals[0]
        abs_path = (self.core.opf_dir / href).resolve()
        self.path_label.config(text=str(abs_path))

        kind = guess_kind_by_extension(href)
        if kind in (KIND_DOCUMENT, KIND_STYLE):
            try:
                text = self.core.read_text(href)
            except Exception as e:
                messagebox.showerror("Abrir", f"No se pudo leer el archivo:\n{e}")
                return
            self._show_text(text, href)
        elif kind == KIND_IMAGE:
            if not _HAS_PIL:
                self._show_text("(Instalá pillow para previsualizar imágenes)", href)
                return
            if not abs_path.exists():
                self._show_text("(La imagen no existe en disco)", href)
                return
            self._show_image(abs_path)
        else:
            try:
                data = (self.core.opf_dir / href).read_bytes()
                preview = data[:4096].hex(" ")
                self._show_text(f"(Tipo no soportado para preview)\n\n{href}\n\nBytes (hex, primeros 4KB):\n{preview}", href)
            except Exception:
                self._show_text(f"(Tipo no soportado para preview)\n\n{href}", href)

    # ------------- Visor: stack -------------
    def _show_empty(self):
        self.text_frame.lower(self.image_frame)
        self.empty_label.lift()

    def _show_text(self, content: str, href: str):
        self.empty_label.lower()
        self.image_frame.lower(self.text_frame)
        self.text_frame.lift()
        self._render_text(content, href)

    def _show_image(self, path: Path):
        self.empty_label.lower()
        self.text_frame.lower(self.image_frame)
        self.image_frame.lift()
        self._load_image(path)

    # ------------- Texto con (opcional) Pygments -------------
    def _render_text(self, content: str, href: str):
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        for tag in self.text.tag_names():
            self.text.tag_delete(tag)

        if not _HAS_PYGMENTS:
            self.text.insert("1.0", content)
            self.text.config(state="disabled")
            return

        fn = href.lower()
        if fn.endswith((".xhtml", ".html", ".htm")):
            lexer = HtmlLexer()
        elif fn.endswith(".css"):
            lexer = CssLexer()
        else:
            lexer = None

        if not lexer:
            self.text.insert("1.0", content)
            self.text.config(state="disabled")
            return

        style_map = {
            Token.Comment:               {"foreground": "#6a9955"},
            Token.Name.Attribute:        {"foreground": "#9a6e3a"},
            Token.Name.Tag:              {"foreground": "#800000", "font": ("DejaVu Sans Mono", 11, "bold")},
            Token.String:                {"foreground": "#a31515"},
            Token.Number:                {"foreground": "#098658"},
            Token.Operator:              {"foreground": "#000000"},
            Token.Punctuation:           {"foreground": "#000000"},
            Token.Keyword:               {"foreground": "#0000ff"},
            Token.Name:                  {"foreground": "#001080"},
            Token.Literal:               {"foreground": "#a31515"},
            Token.Error:                 {"foreground": "#ffffff", "background": "#e51400"},
        }
        for tok, conf in style_map.items():
            self.text.tag_configure(str(tok), **conf)

        idx = "1.0"
        for tok, val in lex(content, lexer):
            tag = style_map.get(tok)
            if tag is None:
                base = None
                for parent_tok in (tok.parent, Token.Text):
                    if parent_tok in style_map:
                        base = parent_tok
                        break
                tag_name = str(base) if base else None
            else:
                tag_name = str(tok)
            if tag_name:
                self.text.insert(idx, val, (tag_name,))
            else:
                self.text.insert(idx, val)
            idx = self.text.index("end-1c")

        self.text.config(state="disabled")

    # ------------- Imagen con auto-escala -------------
    def _load_image(self, path: Path):
        if not _HAS_PIL:
            self.canvas.delete("all")
            self.canvas.create_text(10, 10, anchor="nw", fill="white",
                                    text="Pillow no instalado — sin vista de imagen")
            return
        self._current_img_path = path
        try:
            self._original_image = Image.open(path)
        except Exception as e:
            self.canvas.delete("all")
            self.canvas.create_text(10, 10, anchor="nw", fill="white", text=f"Error abriendo imagen:\n{e}")
            self._original_image = None
            self._tk_image = None
            return
        self._redraw_canvas_image()

    def _on_canvas_resize(self, _event):
        if self._original_image is not None:
            self._redraw_canvas_image()

    def _redraw_canvas_image(self):
        if self._original_image is None:
            return
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        img = self._original_image.copy()
        img.thumbnail((cw, ch), Image.LANCZOS)
        self._tk_image = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        x = (cw - self._tk_image.width()) // 2
        y = (ch - self._tk_image.height()) // 2
        self.canvas.create_image(x, y, anchor="nw", image=self._tk_image)

    # ------------- utilidades -------------
    def _select_href(self, href: str):
        # Encuentra el nodo por href en values[0] y lo selecciona
        for node in self.tree.get_children(""):
            self._select_href_recursive(node, href)

    def _select_href_recursive(self, node, href: str) -> bool:
        for child in self.tree.get_children(node):
            vals = self.tree.item(child, "values")
            if vals and len(vals) > 0 and vals[0] == href:
                self.tree.selection_set(child)
                self.tree.focus(child)
                self.tree.see(child)
                return True
            if self._select_href_recursive(child, href):
                return True
        return False

    def _update_title(self):
        if not self.core:
            self.title(APP_TITLE)
            self.path_label.config(text="—")
            return
        meta = self.core.get_metadata()
        t = meta.get("title") or self.core.workdir.name
        self.title(f"{APP_TITLE} — {t}")

    def _cleanup_temp_workspace(self):
        if self.temp_workspace and self.temp_workspace.exists():
            try:
                import shutil
                shutil.rmtree(self.temp_workspace, ignore_errors=True)
            except Exception:
                pass
        self.temp_workspace = None

    def destroy(self):
        self._cleanup_temp_workspace()
        super().destroy()


if __name__ == "__main__":
    App().mainloop()
