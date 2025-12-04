#!/usr/bin/env python3
"""
Guten.AI GTK4 + libadwaita - EPUB Editor
Interfaz gráfica para el editor de EPUBs usando GutenCore
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('GtkSource', '5')
gi.require_version('WebKit', '6.0')

from gi.repository import Gtk, Adw, GtkSource, WebKit, GObject, Gio, GLib, Gdk  
import os
from pathlib import Path
from typing import Optional, Dict, List
import tempfile

# Importar nuestro core
from core.guten_core import GutenCore, KIND_DOCUMENT, KIND_STYLE, KIND_IMAGE, KIND_FONT, KIND_AUDIO, KIND_VIDEO



class GutenAIWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Estado de la aplicación
        self.core: Optional[GutenCore] = None
        self.current_resource: Optional[str] = None
        self.temp_preview_file: Optional[str] = None
        
        # Configuración básica de la ventana
        self.set_default_size(1400, 900)
        self.set_title("Guten.AI - EPUB Editor")
        
        # Crear la interfaz
        self._setup_ui()
        self._setup_actions()
        
    def _setup_ui(self):
        """Configura toda la interfaz de usuario"""
        
        # HeaderBar principal (usando Adw.HeaderBar)
        self.header_bar = Adw.HeaderBar()
        
        # Título dual en el headerbar (libro + recurso actual)
        self.title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.book_title = Gtk.Label()
        self.book_title.set_text("Sin libro abierto")
        self.book_title.add_css_class("title")
        
        self.resource_title = Gtk.Label()
        self.resource_title.set_text("Ningún recurso seleccionado")
        self.resource_title.add_css_class("subtitle")
        
        self.title_box.append(self.book_title)
        self.title_box.append(self.resource_title)
        self.header_bar.set_title_widget(self.title_box)
        
        # Botones del headerbar
        # Botón para mostrar/ocultar sidebar izquierdo
        self.left_sidebar_btn = Gtk.ToggleButton()
        self.left_sidebar_btn.set_icon_name("sidebar-show-symbolic")
        self.left_sidebar_btn.set_tooltip_text("Mostrar/ocultar estructura")
        self.left_sidebar_btn.set_active(True)
        self.header_bar.pack_start(self.left_sidebar_btn)
        
        # Botón para mostrar/ocultar sidebar derecho
        self.right_sidebar_btn = Gtk.ToggleButton()
        self.right_sidebar_btn.set_icon_name("view-reveal-symbolic")
        self.right_sidebar_btn.set_tooltip_text("Mostrar/ocultar previsualización")
        self.right_sidebar_btn.set_active(True)
        self.header_bar.pack_end(self.right_sidebar_btn)
        
        # Botón de menú principal
        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("open-menu-symbolic")
        menu_builder = Gtk.Builder()
        menu_builder.add_from_string('''
        <interface>
          <menu id="main_menu">
            <section>
              <item>
                <attribute name="label">Abrir EPUB</attribute>
                <attribute name="action">win.open_epub</attribute>
              </item>
              <item>
                <attribute name="label">Abrir carpeta proyecto</attribute>
                <attribute name="action">win.open_folder</attribute>
              </item>
              <item>
                <attribute name="label">Nuevo proyecto</attribute>
                <attribute name="action">win.new_project</attribute>
              </item>
              <item>
                <attribute name="label">Exportar EPUB</attribute>
                <attribute name="action">win.export_epub</attribute>
              </item>
            </section>
            <section>
              <item>
                <attribute name="label">Preferencias</attribute>
                <attribute name="action">win.preferences</attribute>
              </item>
            </section>
          </menu>
        </interface>
        ''')
        menu_btn.set_menu_model(menu_builder.get_object("main_menu"))
        self.header_bar.pack_end(menu_btn)
        
        # Crear el contenido principal con toast overlay
        self.toast_overlay = Adw.ToastOverlay()
        
        # Layout principal con 3 paneles usando Adw.OverlaySplitView
        self.main_overlay = Adw.OverlaySplitView()
        self.toast_overlay.set_child(self.main_overlay)
        
        # Panel principal (centro + derecha)
        self.content_split = Adw.OverlaySplitView()
        self.content_split.set_sidebar_position(Gtk.PackType.END)
        self.main_overlay.set_content(self.content_split)
        
        # Crear ToolbarView para contener headerbar y contenido
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(self.header_bar)
        toolbar_view.set_content(self.toast_overlay)
        self.set_content(toolbar_view)
        
        # === SIDEBAR IZQUIERDO (Estructura EPUB) ===
        self._setup_left_sidebar()
        
        # === PANEL CENTRAL (Editor) ===
        self._setup_central_panel()
        
        # === SIDEBAR DERECHO (Preview) ===
        self._setup_right_sidebar()
        
        # Conectar toggles de sidebars
        self.left_sidebar_btn.connect('toggled', self._on_left_sidebar_toggle)
        self.right_sidebar_btn.connect('toggled', self._on_right_sidebar_toggle)
        
    def _setup_left_sidebar(self):
        """Configura el sidebar izquierdo con la estructura del EPUB usando ListView moderno"""
        
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar_box.set_size_request(280, -1)
        
        # Header del sidebar
        sidebar_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        sidebar_header.set_margin_top(12)
        sidebar_header.set_margin_bottom(12)
        sidebar_header.set_margin_start(12)
        sidebar_header.set_margin_end(12)
        
        sidebar_title = Gtk.Label()
        sidebar_title.set_text("Estructura EPUB")
        sidebar_title.add_css_class("heading")
        sidebar_header.append(sidebar_title)
        sidebar_box.append(sidebar_header)
        
        # Usar ListBox en lugar de TreeView (más moderno en GTK4)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        
        self.resource_listbox = Gtk.ListBox()
        self.resource_listbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.resource_listbox.add_css_class("navigation-sidebar")
        
        scrolled.set_child(self.resource_listbox)
        sidebar_box.append(scrolled)
        
        self.main_overlay.set_sidebar(sidebar_box)

        # *** CONFIGURAR ESTILOS MEJORADOS ***
        self._setup_selection_styling()
        
        # Conectar señal para manejar cambios de selección
        self.resource_listbox.connect('selected-rows-changed', self._on_selection_changed)
        
    def _setup_selection_styling(self):
        """Configura CSS personalizado para mejorar la visualización de selección"""
        css_provider = Gtk.CssProvider()
        css_data = """
        /* Mejorar la visualización de elementos seleccionados */
        listbox row:selected {
            background-color: @accent_color;
            color: @accent_fg_color;
            border-left: 4px solid @accent_bg_color;
        }
        
        /* Hacer más visible el hover */
        listbox row:hover {
            background-color: alpha(@accent_color, 0.1);
        }
        
        /* Selección múltiple más visible */
        listbox.navigation-sidebar row:selected {
            background: linear-gradient(90deg, @accent_color, alpha(@accent_color, 0.8));
            border-radius: 6px;
            margin: 2px;
            font-weight: bold;
        }
        
        /* Iconos en elementos seleccionados */
        listbox row:selected image {
            color: @accent_fg_color;
        }
        
        /* Categorías vacías con estilo diferente */
        .empty-category {
            opacity: 0.7;
        }
        
        .empty-category .title {
            font-style: italic;
        }
        """
        
        css_provider.load_from_data(css_data.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
    def _on_selection_changed(self, listbox):
        """Maneja cambios en la selección"""
        selected_rows = listbox.get_selected_rows()
        print(f"Seleccionados: {len(selected_rows)} elementos")
        
        # Opcional: mostrar información sobre la selección en la UI
        if len(selected_rows) > 1:
            self.resource_title.set_text(f"{len(selected_rows)} recursos seleccionados")
        elif len(selected_rows) == 1:
            # Lógica existente para un solo elemento seleccionado
            pass
        else:
            self.resource_title.set_text("Ningún recurso seleccionado")

        
    def _setup_central_panel(self):
        """Configura el panel central con el editor de código"""
        
        # SourceView para el editor
        self.source_buffer = GtkSource.Buffer()
        self.source_view = GtkSource.View(buffer=self.source_buffer)
        self.source_view.set_show_line_numbers(True)
        self.source_view.set_highlight_current_line(True)
        self.source_view.set_tab_width(2)
        self.source_view.set_insert_spaces_instead_of_tabs(True)
        self.source_view.set_auto_indent(True)
        self.source_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)

        # Configurar esquema de colores
        style_manager = GtkSource.StyleSchemeManager.get_default()
        scheme = style_manager.get_scheme('Adwaita-dark')
        if scheme:
            self.source_buffer.set_style_scheme(scheme)
        
        # *** MENÚ CONTEXTUAL PERSONALIZADO ***
        self._setup_context_menu()
        
        # ScrolledWindow para el editor
        editor_scroll = Gtk.ScrolledWindow()
        editor_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        editor_scroll.set_child(self.source_view)
        editor_scroll.set_vexpand(True)
        editor_scroll.set_hexpand(True)
        
        # Conectar cambios en el texto
        self.source_buffer.connect('changed', self._on_text_changed)
        
        self.content_split.set_content(editor_scroll)
    
    def _setup_context_menu(self):
        """Configura el menú contextual del editor"""
        
        # Crear acciones personalizadas
        self._setup_editor_actions()
        
        # Crear el modelo de menú contextual
        menu_model = self._create_context_menu_model()
        
        # Reemplazar el menú contextual nativo con nuestro menú personalizado
        self.source_view.set_extra_menu(menu_model)

    def _on_wrap_paragraph(self, action, param):
        """Envuelve el texto seleccionado en etiquetas <p>"""
        self._wrap_selection("p")

    def _on_wrap_heading(self, action, param, level):
        """Envuelve el texto seleccionado en etiquetas de encabezado"""
        self._wrap_selection(f"h{level}")

    def _on_wrap_blockquote(self, action, param):
        """Envuelve el texto seleccionado en etiquetas <blockquote>"""
        self._wrap_selection("blockquote")

    def _wrap_selection(self, tag):
        """Envuelve la selección actual con la etiqueta especificada"""
        buffer = self.source_buffer
        
        # Verificar si hay texto seleccionado
        if not buffer.get_has_selection():
            self._show_error("Selecciona texto para aplicar formato")
            return
        
        # Obtener la selección
        start, end = buffer.get_selection_bounds()
        selected_text = buffer.get_text(start, end, False).strip()
        
        if not selected_text:
            return
        
        # Crear el texto envuelto
        wrapped_text = self.core.xform_plaintext_to_xhtml_fragment(selected_text)
        # wrapped_text = f"<{tag}>{selected_text}</{tag}>"
        
        # Reemplazar la selección
        buffer.delete(start, end)
        buffer.insert(start, wrapped_text)
        
        # Actualizar preview si es necesario
        if hasattr(self, 'current_resource') and self.current_resource:
            if self.current_resource.endswith(('.html', '.xhtml', '.htm')):
                full_text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
                self._update_preview(full_text, self.current_resource)
                
    def _setup_right_sidebar(self):
        """Configura el sidebar derecho con WebKit preview"""
        
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar_box.set_size_request(400, -1)
        
        # Header del sidebar
        sidebar_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        sidebar_header.set_margin_top(12)
        sidebar_header.set_margin_bottom(12)
        sidebar_header.set_margin_start(12)
        sidebar_header.set_margin_end(12)
        
        sidebar_title = Gtk.Label()
        sidebar_title.set_text("Previsualización")
        sidebar_title.add_css_class("heading")
        sidebar_header.append(sidebar_title)
        
        # Botón para pantalla completa - AHORA FUNCIONAL
        fullscreen_btn = Gtk.Button()
        fullscreen_btn.set_icon_name("view-fullscreen-symbolic")
        fullscreen_btn.set_tooltip_text("Abrir previsualización en ventana independiente")
        fullscreen_btn.add_css_class("flat")
        fullscreen_btn.connect('clicked', self._on_fullscreen_preview)
        sidebar_header.append(fullscreen_btn)
        
        sidebar_box.append(sidebar_header)
        
        # WebView
        self.web_view = WebKit.WebView()
        web_scroll = Gtk.ScrolledWindow()
        web_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        web_scroll.set_child(self.web_view)
        web_scroll.set_vexpand(True)
        sidebar_box.append(web_scroll)
        
        self.content_split.set_sidebar(sidebar_box)
        
        # Variable para rastrear la ventana de pantalla completa
        self.fullscreen_window = None
        
    def _create_category_row(self, name: str, count: int, icon: str, category_type: str) -> Adw.ExpanderRow:
        """Crea una fila expandible para una categoría"""
        expander = Adw.ExpanderRow()
        expander.set_title(f"{name} ({count})")
        expander.set_subtitle("Categoría de recursos")
        expander.add_prefix(Gtk.Label(label=icon))
        
        # Agregar botón de acción según el tipo de categoría
        if category_type in [KIND_DOCUMENT, KIND_STYLE]:
            # Botón para crear nuevo recurso de texto
            add_btn = Gtk.Button()
            add_btn.set_icon_name("list-add-symbolic")
            add_btn.set_tooltip_text(f"Crear nuevo {name.lower()}")
            add_btn.add_css_class("flat")
            add_btn.connect('clicked', self._on_create_new_resource, category_type)
            expander.add_suffix(add_btn)
            
        elif category_type in [KIND_IMAGE, KIND_FONT]:
            # Botón para importar recurso desde archivo
            import_btn = Gtk.Button()
            import_btn.set_icon_name("folder-open-symbolic")
            import_btn.set_tooltip_text(f"Importar {name.lower()}")
            import_btn.add_css_class("flat")
            import_btn.connect('clicked', self._on_import_resource, category_type)
            expander.add_suffix(import_btn)
            
        return expander
        
    def _create_resource_row(self, name: str, href: str, resource_type: str) -> Adw.ActionRow:
        """Crea una fila para un recurso individual"""
        row = Adw.ActionRow()
        row.set_title(name)
        row.set_subtitle(href)
        
        # Icono según el tipo
        icon_name = {
            KIND_DOCUMENT: "text-x-generic-symbolic",
            KIND_STYLE: "text-css-symbolic", 
            KIND_IMAGE: "image-x-generic-symbolic",
            KIND_FONT: "font-x-generic-symbolic",
            KIND_AUDIO: "audio-x-generic-symbolic",
            KIND_VIDEO: "video-x-generic-symbolic"
        }.get(resource_type, "text-x-generic-symbolic")
        
        icon = Gtk.Image.new_from_icon_name(icon_name)
        row.add_prefix(icon)
        
        # Hacer la fila activable y conectar el signal
        row.set_activatable(True)
        row.connect('activated', self._on_resource_row_activated, href, resource_type, name)
        
        return row
        
    def _populate_tree(self):
        """Puebla el ListBox con la estructura del EPUB"""
        if not self.core:
            return
            
        # Limpiar listbox
        child = self.resource_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.resource_listbox.remove(child)
            child = next_child
        
        # Categorías principales - SIEMPRE mostrar todas
        categories = [
            ("📄 Texto", KIND_DOCUMENT),
            ("🎨 Estilos", KIND_STYLE), 
            ("🖼️ Imágenes", KIND_IMAGE),
            ("🔤 Fuentes", KIND_FONT),
            ("🎵 Audio", KIND_AUDIO),
            ("🎥 Video", KIND_VIDEO),
        ]
        
        for category_name, kind in categories:
            items = self.core.list_items(kind=kind)
            
            # Mostrar SIEMPRE la categoría, pero adaptar el título
            if items:
                # Categoría con elementos
                category_row = self._create_category_row(category_name, len(items), "", kind)
                self.resource_listbox.append(category_row)
                
                # Agregar los recursos
                for item in items:
                    resource_row = self._create_resource_row(
                        Path(item.href).name,
                        item.href,
                        kind
                    )
                    category_row.add_row(resource_row)
            else:
                # Categoría vacía - mostrar con indicador visual
                empty_title = f"{category_name} (vacía)"
                category_row = self._create_category_row(empty_title, 0, "", kind)
                
                # Opcional: agregar estilo visual para categorías vacías
                category_row.add_css_class("empty-category")
                
                self.resource_listbox.append(category_row)
                
                # Agregar una fila informativa
                if kind in [KIND_DOCUMENT, KIND_STYLE]:
                    info_row = Adw.ActionRow()
                    info_row.set_title("Sin elementos")
                    info_row.set_subtitle(f"Haz clic en + para crear un nuevo {category_name.split()[1].lower()}")
                    info_row.set_sensitive(False)  # No clickeable
                    category_row.add_row(info_row)
                elif kind in [KIND_IMAGE, KIND_FONT]:
                    info_row = Adw.ActionRow()
                    info_row.set_title("Sin elementos")
                    info_row.set_subtitle(f"Haz clic en 📁 para importar {category_name.split()[1].lower()}")
                    info_row.set_sensitive(False)
                    category_row.add_row(info_row)
    
    def _create_category_row(self, name: str, count: int, icon: str, category_type: str) -> Adw.ExpanderRow:
        """Crea una fila expandible para una categoría"""
        expander = Adw.ExpanderRow()
        expander.set_title(name)
        
        # Subtitle diferente si está vacía
        if count == 0:
            expander.set_subtitle("Categoría vacía - usa los botones para agregar contenido")
        else:
            expander.set_subtitle("Categoría de recursos")
        
        if icon:
            expander.add_prefix(Gtk.Label(label=icon))
        
        # Agregar botón de acción según el tipo de categoría
        if category_type in [KIND_DOCUMENT, KIND_STYLE]:
            # Botón para crear nuevo recurso de texto
            add_btn = Gtk.Button()
            add_btn.set_icon_name("list-add-symbolic")
            add_btn.set_tooltip_text(f"Crear nuevo {name.split()[1].lower() if ' ' in name else 'recurso'}")
            add_btn.add_css_class("flat")
            add_btn.connect('clicked', self._on_create_new_resource, category_type)
            expander.add_suffix(add_btn)
            
        elif category_type in [KIND_IMAGE, KIND_FONT, KIND_AUDIO, KIND_VIDEO]:
            # Botón para importar recurso desde archivo
            import_btn = Gtk.Button()
            import_btn.set_icon_name("folder-open-symbolic")
            import_btn.set_tooltip_text(f"Importar {name.split()[1].lower() if ' ' in name else 'archivo'}")
            import_btn.add_css_class("flat")
            import_btn.connect('clicked', self._on_import_resource, category_type)
            expander.add_suffix(import_btn)
            
        return expander

    def _on_resource_row_activated(self, row, href, resource_type, name):
        """Maneja la activación de una fila de recurso"""
        print(f"Recurso activado: {href} (Tipo: {resource_type})")
        
        self.current_resource = href
        self.resource_title.set_text(f"Recurso: {name}")
        
        # Cargar contenido según el tipo
        if resource_type in [KIND_DOCUMENT, KIND_STYLE]:
            self._load_text_resource(href, resource_type)
        else:
            self._load_non_text_resource(href, resource_type)
            
    def _on_create_new_resource(self, button, resource_type):
        """Maneja la creación de un nuevo recurso de texto"""
        if not self.core:
            self._show_error("No hay proyecto abierto")
            return
            
        # Crear diálogo para pedir el nombre del archivo
        dialog = Adw.AlertDialog()
        dialog.set_heading("Crear nuevo recurso")
        
        if resource_type == KIND_DOCUMENT:
            dialog.set_body("Nombre para el nuevo capítulo/documento HTML:")
            placeholder = "capitulo_nuevo"
            extension = ".xhtml"
        else:  # KIND_STYLE
            dialog.set_body("Nombre para el nuevo archivo CSS:")
            placeholder = "estilo_nuevo"
            extension = ".css"
            
        # Entry para el nombre
        entry = Gtk.Entry()
        entry.set_placeholder_text(placeholder)
        entry.set_text(placeholder)
        dialog.set_extra_child(entry)
        
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("create", "Crear")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        
        dialog.connect("response", self._on_create_resource_response, resource_type, entry, extension)
        dialog.present(self)
        
    def _on_create_resource_response(self, dialog, response, resource_type, entry, extension):
        """Maneja la respuesta del diálogo de creación"""
        if response != "create":
            return
            
        filename = entry.get_text().strip()
        if not filename:
            self._show_error("El nombre no puede estar vacío")
            return
            
        try:
            if resource_type == KIND_DOCUMENT:
                # Crear documento HTML
                item = self.core.create_document(filename)
                self._show_info(f"Documento '{filename}' creado correctamente")
            else:  # KIND_STYLE
                # Crear archivo CSS básico
                if not filename.endswith('.css'):
                    filename += '.css'
                    
                styles_dir = Path(self.core.layout["STYLES"]).name
                href = f"{styles_dir}/{filename}"
                
                # Contenido CSS básico
                css_content = """/* Estilos para el EPUB */

body {
    font-family: serif;
    line-height: 1.4;
    margin: 1em;
}

h1, h2, h3, h4, h5, h6 {
    font-family: sans-serif;
    margin: 1em 0 0.5em 0;
}

p {
    margin: 0 0 0.5em 0;
    text-indent: 1em;
}

.center {
    text-align: center;
}

.bold {
    font-weight: bold;
}

.italic {
    font-style: italic;
}
"""
                
                self.core.write_text(href, css_content)
                
                # Generar ID único
                base_id = Path(filename).stem
                id_ = self.core._unique_id(base_id)
                
                # Agregar al manifest
                item = self.core.add_to_manifest(id_, href, media_type="text/css")
                self._show_info(f"Archivo CSS '{filename}' creado correctamente")
            
            # Actualizar la lista y seleccionar el nuevo recurso
            self._populate_tree()
            
        except Exception as e:
            self._show_error(f"Error creando recurso: {e}")
            
    def _on_import_resource(self, button, resource_type):
        """Maneja la importación de recursos desde archivo"""
        if not self.core:
            self._show_error("No hay proyecto abierto")
            return
            
        dialog = Gtk.FileDialog()
        
        if resource_type == KIND_IMAGE:
            dialog.set_title("Importar imagen")
            # Filtro para imágenes
            filter_images = Gtk.FileFilter()
            filter_images.set_name("Imágenes")
            filter_images.add_pattern("*.png")
            filter_images.add_pattern("*.jpg")
            filter_images.add_pattern("*.jpeg")
            filter_images.add_pattern("*.gif")
            filter_images.add_pattern("*.svg")
            filter_images.add_pattern("*.webp")
            filters = Gio.ListStore()
            filters.append(filter_images)
            dialog.set_filters(filters)
            
        elif resource_type == KIND_FONT:
            dialog.set_title("Importar fuente")
            # Filtro para fuentes
            filter_fonts = Gtk.FileFilter()
            filter_fonts.set_name("Fuentes")
            filter_fonts.add_pattern("*.ttf")
            filter_fonts.add_pattern("*.otf")
            filter_fonts.add_pattern("*.woff")
            filter_fonts.add_pattern("*.woff2")
            filters = Gio.ListStore()
            filters.append(filter_fonts)
            dialog.set_filters(filters)
            
        dialog.open(self, None, self._on_import_resource_response, resource_type)
        
    def _on_import_resource_response(self, dialog, result, resource_type):
        """Maneja la respuesta del diálogo de importación"""
        try:
            file = dialog.open_finish(result)
            if file:
                src_path = Path(file.get_path())
                
                # Importar el archivo usando GutenCore
                item = self.core.create_asset_from_disk(
                    src_path, 
                    resource_type,
                    dest_name=src_path.name,
                    set_as_cover=(resource_type == KIND_IMAGE)  # Primera imagen como portada
                )
                
                tipo_nombre = "imagen" if resource_type == KIND_IMAGE else "fuente"
                self._show_info(f"{tipo_nombre.title()} '{src_path.name}' importada correctamente")
                
                # Actualizar la lista
                self._populate_tree()
                
        except Exception as e:
            self._show_error(f"Error importando archivo: {e}")
            
    def _load_text_resource(self, href: str, resource_type: str):
        """Carga un recurso de texto en el editor"""
        if not self.core:
            return
            
        try:
            content = self.core.read_text(href)
            
            # Configurar resaltado de sintaxis
            lang_manager = GtkSource.LanguageManager.get_default()
            if resource_type == KIND_DOCUMENT:
                language = lang_manager.get_language('html')
            elif resource_type == KIND_STYLE:
                language = lang_manager.get_language('css')
            else:
                language = lang_manager.get_language('xml')
                
            self.source_buffer.set_language(language)
            self.source_buffer.set_text(content)
            
            # Actualizar preview si es un documento HTML
            if resource_type == KIND_DOCUMENT:
                self._update_preview(content, href)
                
        except Exception as e:
            self._show_error(f"Error cargando recurso: {e}")
            
    def _load_non_text_resource(self, href: str, resource_type: str):
        """Maneja recursos no textuales"""
        # Para imágenes, fuentes, etc., mostrar info en el editor
        info_text = f"Recurso: {href}\nTipo: {resource_type}\n\n"
        info_text += "Este tipo de recurso no es editable como texto."
        
        self.source_buffer.set_language(None)
        self.source_buffer.set_text(info_text)
        
        # Limpiar preview
        self.web_view.load_html("", None)
        
    def _update_preview(self, html_content: str, href: str):
        """Actualiza la previsualización WebKit"""
        if not self.core:
            return
            
        try:
            # Opción 1: Cargar directamente desde el directorio del EPUB usando file:// URI
            # Esto permite que las rutas relativas funcionen correctamente
            
            # Obtener la ruta absoluta del archivo HTML en el proyecto
            html_file_path = (self.core.opf_dir / href).resolve()
            
            # Escribir el contenido actualizado al archivo original temporalmente
            original_content = None
            if html_file_path.exists():
                original_content = html_file_path.read_text(encoding='utf-8')
                
            # Escribir el contenido editado
            html_file_path.write_text(html_content, encoding='utf-8')
            
            # Cargar desde la ubicación original (esto permite que las rutas relativas funcionen)
            file_uri = html_file_path.as_uri()
            self.web_view.load_uri(file_uri)
            
            # Programar restaurar el contenido original después de un momento
            # (solo si había contenido original diferente)
            if original_content and original_content != html_content:
                def restore_original():
                    try:
                        html_file_path.write_text(original_content, encoding='utf-8')
                    except:
                        pass
                    return False
                
                # Restaurar después de 2 segundos (tiempo para que WebKit cargue)
                GLib.timeout_add(2000, restore_original)
            
        except Exception as e:
            # Fallback: método anterior con archivo temporal
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                    f.write(html_content)
                    temp_path = f.name
                    
                if self.temp_preview_file and os.path.exists(self.temp_preview_file):
                    os.unlink(self.temp_preview_file)
                    
                self.temp_preview_file = temp_path
                file_uri = Path(temp_path).as_uri()
                self.web_view.load_uri(file_uri)
                
            except Exception as e2:
                self.web_view.load_html(f"<p>Error en preview: {e}<br>Fallback error: {e2}</p>", None)
            
    def _on_text_changed(self, buffer):
        """Maneja cambios en el texto del editor"""
        if not self.core or not self.current_resource:
            return
            
        # Obtener el texto actual
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        text = buffer.get_text(start, end, False)
        
        # Guardar cambios (con un pequeño delay para evitar guardado excesivo)
        if hasattr(self, '_save_timeout'):
            GLib.source_remove(self._save_timeout)
        self._save_timeout = GLib.timeout_add(1000, self._save_current_text, text)
        
        # Si es HTML, actualizar preview inmediatamente
        if self.current_resource and self.current_resource.endswith(('.html', '.xhtml', '.htm')):
            self._update_preview(text, self.current_resource)
            
    def _save_current_text(self, text: str):
        """Guarda el texto actual en el archivo"""
        if not self.core or not self.current_resource:
            return False
            
        try:
            self.core.write_text(self.current_resource, text)
        except Exception as e:
            self._show_error(f"Error guardando: {e}")
            
        return False  # No repetir el timeout
        
    def _on_left_sidebar_toggle(self, button):
        """Toggle del sidebar izquierdo"""
        self.main_overlay.set_show_sidebar(button.get_active())
        
    def _on_right_sidebar_toggle(self, button):
        """Toggle del sidebar derecho"""
        self.content_split.set_show_sidebar(button.get_active())
        
    def _setup_actions(self):
        """Configura las acciones de la aplicación"""
        
        # Abrir EPUB
        open_action = Gio.SimpleAction.new("open_epub", None)
        open_action.connect("activate", self._on_open_epub)
        self.add_action(open_action)
        
        # Abrir carpeta proyecto
        open_folder_action = Gio.SimpleAction.new("open_folder", None)
        open_folder_action.connect("activate", self._on_open_folder)
        self.add_action(open_folder_action)
        
        # Nuevo proyecto
        new_action = Gio.SimpleAction.new("new_project", None)
        new_action.connect("activate", self._on_new_project)
        self.add_action(new_action)
        
        # Exportar EPUB
        export_action = Gio.SimpleAction.new("export_epub", None)
        export_action.connect("activate", self._on_export_epub)
        self.add_action(export_action)
        
        # Preferencias
        prefs_action = Gio.SimpleAction.new("preferences", None)
        prefs_action.connect("activate", self._on_preferences)
        self.add_action(prefs_action)
        
    def _on_open_epub(self, action, param):
        """Abre un archivo EPUB"""
        dialog = Gtk.FileDialog()
        dialog.set_title("Abrir EPUB")
        
        # Filtro para archivos EPUB
        filter_epub = Gtk.FileFilter()
        filter_epub.set_name("Archivos EPUB")
        filter_epub.add_pattern("*.epub")
        filters = Gio.ListStore()
        filters.append(filter_epub)
        dialog.set_filters(filters)
        
        dialog.open(self, None, self._on_open_epub_response)
        
    def _on_open_epub_response(self, dialog, result):
        """Maneja la respuesta del diálogo de apertura"""
        try:
            file = dialog.open_finish(result)
            if file:
                epub_path = Path(file.get_path())
                workdir = Path.home() / "GutenAI" / "temp"
                workdir.mkdir(parents=True, exist_ok=True)
                
                self.core = GutenCore.open_epub(epub_path, workdir)
                
                # Actualizar UI
                metadata = self.core.get_metadata()
                self.book_title.set_text(metadata.get("title", "EPUB sin título"))
                self._populate_tree()
                
        except Exception as e:
            self._show_error(f"Error abriendo EPUB: {e}")
    
    def _on_open_folder(self, action, param):
        """Abre una carpeta proyecto existente"""
        dialog = Gtk.FileDialog()
        dialog.set_title("Abrir carpeta proyecto EPUB")
        dialog.select_folder(self, None, self._on_open_folder_response)
        
    def _on_open_folder_response(self, dialog, result):
        """Maneja la respuesta del diálogo de apertura de carpeta"""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                project_dir = Path(folder.get_path())
                
                # Verificar que es una carpeta de proyecto EPUB válida
                container_path = project_dir / "META-INF" / "container.xml"
                if not container_path.exists():
                    self._show_error("La carpeta seleccionada no contiene un proyecto EPUB válido (falta META-INF/container.xml)")
                    return
                
                self.core = GutenCore.open_folder(project_dir)
                
                # Actualizar UI
                metadata = self.core.get_metadata()
                book_title = metadata.get("title", "EPUB sin título")
                if not book_title or book_title == "EPUB sin título":
                    book_title = project_dir.name  # Usar nombre de carpeta como fallback
                    
                self.book_title.set_text(book_title)
                self._populate_tree()
                
                self._show_info(f"Proyecto '{book_title}' abierto correctamente")
                
        except Exception as e:
            self._show_error(f"Error abriendo carpeta proyecto: {e}")
            
    def _on_new_project(self, action, param):
        """Crea un nuevo proyecto EPUB"""
        dialog = Gtk.FileDialog()
        dialog.set_title("Crear nuevo proyecto EPUB")
        dialog.select_folder(self, None, self._on_new_project_response)
        
    def _on_new_project_response(self, dialog, result):
        """Maneja la respuesta del diálogo de nuevo proyecto"""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                project_dir = Path(folder.get_path()) / "NuevoEPUB"
                self.core = GutenCore.new_project(
                    project_dir, 
                    title="Nuevo Libro",
                    lang="es"
                )
                
                # Actualizar UI
                self.book_title.set_text("Nuevo Libro")
                self._populate_tree()
                
        except Exception as e:
            self._show_error(f"Error creando proyecto: {e}")
            
    def _on_export_epub(self, action, param):
        """Exporta el EPUB actual"""
        if not self.core:
            self._show_error("No hay ningún proyecto abierto")
            return
            
        dialog = Gtk.FileDialog()
        dialog.set_title("Exportar EPUB")
        dialog.set_initial_name("libro.epub")
        dialog.save(self, None, self._on_export_epub_response)
        
    def _on_export_epub_response(self, dialog, result):
        """Maneja la respuesta del diálogo de exportación"""
        try:
            file = dialog.save_finish(result)
            if file:
                output_path = Path(file.get_path())
                self.core.export_epub(output_path)
                self._show_info("EPUB exportado correctamente")
        except Exception as e:
            self._show_error(f"Error exportando: {e}")
            
    def _on_preferences(self, action, param):
        """Abre las preferencias"""
        # TODO: Implementar ventana de preferencias
        self._show_info("Preferencias - Por implementar")
        
    def _show_error(self, message: str):
        """Muestra un mensaje de error"""
        toast = Adw.Toast()
        toast.set_title(message)
        toast.set_timeout(5)
        self.toast_overlay.add_toast(toast)
        
    def _show_info(self, message: str):
        """Muestra un mensaje informativo"""
        toast = Adw.Toast()
        toast.set_title(message)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)
        
    def do_close_request(self):
        """Limpieza al cerrar la aplicación"""
        if self.temp_preview_file and os.path.exists(self.temp_preview_file):
            os.unlink(self.temp_preview_file)
        return False

    def _create_context_menu_model(self):
        """Crea el modelo de menú contextual"""
        menu = Gio.Menu()
        
        # Sección de formato HTML - solo si hay texto seleccionado
        format_section = Gio.Menu()
        format_section.append("Párrafo <p>", "win.wrap_paragraph")
        format_section.append("Encabezado H1", "win.wrap_h1")
        format_section.append("Encabezado H2", "win.wrap_h2") 
        format_section.append("Encabezado H3", "win.wrap_h3")
        format_section.append("Cita <blockquote>", "win.wrap_blockquote")
        
        menu.append_section("Formato HTML", format_section)
        
        # Nueva sección para gestión de estilos - solo para documentos HTML
        style_section = Gio.Menu()
        style_section.append("Vincular estilos CSS", "win.link_styles")
        
        menu.append_section("Estilos", style_section)
        
        # Sección de edición (mantener funciones básicas)
        edit_section = Gio.Menu()
        edit_section.append("Cortar", "text.cut")
        edit_section.append("Copiar", "text.copy")
        edit_section.append("Pegar", "text.paste")
        edit_section.append("Seleccionar todo", "text.select-all")
        
        menu.append_section("Edición", edit_section)
        
        return menu

    def _setup_editor_actions(self):
        """Crea acciones específicas del editor"""
        
        # Acciones de formato existentes...
        wrap_paragraph_action = Gio.SimpleAction.new("wrap_paragraph", None)
        wrap_paragraph_action.connect("activate", self._on_wrap_paragraph)
        self.add_action(wrap_paragraph_action)
        
        wrap_h1_action = Gio.SimpleAction.new("wrap_h1", None)
        wrap_h1_action.connect("activate", self._on_wrap_heading, 1)
        self.add_action(wrap_h1_action)
        
        wrap_h2_action = Gio.SimpleAction.new("wrap_h2", None)
        wrap_h2_action.connect("activate", self._on_wrap_heading, 2)
        self.add_action(wrap_h2_action)
        
        wrap_h3_action = Gio.SimpleAction.new("wrap_h3", None)
        wrap_h3_action.connect("activate", self._on_wrap_heading, 3)
        self.add_action(wrap_h3_action)
        
        wrap_blockquote_action = Gio.SimpleAction.new("wrap_blockquote", None)
        wrap_blockquote_action.connect("activate", self._on_wrap_blockquote)
        self.add_action(wrap_blockquote_action)
        
        # *** NUEVA ACCIÓN PARA VINCULAR ESTILOS ***
        link_styles_action = Gio.SimpleAction.new("link_styles", None)
        link_styles_action.connect("activate", self._on_link_styles)
        self.add_action(link_styles_action)

    def _on_link_styles(self, action, param):
        """Abre el diálogo para vincular estilos CSS al documento actual"""
        if not self.core or not self.current_resource:
            self._show_error("No hay documento seleccionado")
            return
        
        # Verificar que es un documento HTML
        try:
            mi = self.core._get_item(self.current_resource)
            mt = (mi.media_type or "").split(";")[0].strip().lower()
            ext = Path(mi.href).suffix.lower()
            
            is_html = (mt in ("application/xhtml+xml", "text/html") or 
                    ext in (".xhtml", ".html", ".htm"))
            
            if not is_html:
                self._show_error("Solo se pueden vincular estilos a documentos HTML/XHTML")
                return
                
        except KeyError:
            self._show_error("Documento no encontrado en el manifest")
            return
        
        # Mostrar diálogo de selección de estilos
        self._show_style_selection_dialog()

    def _show_style_selection_dialog(self):
        """Muestra diálogo para seleccionar estilos CSS"""
        
        # Obtener estilos disponibles
        css_items = self.core.list_items(kind=KIND_STYLE)
        
        if not css_items:
            self._show_error("No hay archivos CSS en el proyecto")
            return
        
        # Crear el diálogo usando Adw.AlertDialog con contenido personalizado
        dialog = Adw.AlertDialog()
        dialog.set_heading("Vincular estilos CSS")
        dialog.set_body("Selecciona los archivos CSS que deseas vincular a este documento:")
        
        # Crear contenido personalizado con checkboxes
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.set_spacing(8)
        content_box.set_margin_top(12)
        content_box.set_margin_bottom(12)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)
        
        # Almacenar checkboxes para acceder después
        self._style_checkboxes = {}
        
        # Crear lista scrolleable de estilos
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_max_content_height(300)
        scrolled.set_propagate_natural_height(True)
        
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        list_box.add_css_class("boxed-list")
        
        for css_item in css_items:
            row = Adw.ActionRow()
            row.set_title(Path(css_item.href).name)
            row.set_subtitle(css_item.href)
            
            # Checkbox para selección
            checkbox = Gtk.CheckButton()
            checkbox.set_active(True)  # Por defecto seleccionado
            row.add_prefix(checkbox)
            
            # Guardar referencia al checkbox
            self._style_checkboxes[css_item.href] = checkbox
            
            list_box.append(row)
        
        scrolled.set_child(list_box)
        content_box.append(scrolled)
        
        # Opciones adicionales
        options_group = Adw.PreferencesGroup()
        options_group.set_title("Opciones")
        
        # Checkbox para limpiar estilos existentes
        clear_row = Adw.ActionRow()
        clear_row.set_title("Limpiar estilos existentes")
        clear_row.set_subtitle("Elimina todos los <link> de CSS antes de agregar los nuevos")
        
        self._clear_existing_checkbox = Gtk.CheckButton()
        self._clear_existing_checkbox.set_active(True)
        clear_row.add_prefix(self._clear_existing_checkbox)
        
        options_group.add(clear_row)
        content_box.append(options_group)
        
        dialog.set_extra_child(content_box)
        
        # Botones del diálogo
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("apply", "Aplicar estilos")
        dialog.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        
        # Conectar respuesta
        dialog.connect("response", self._on_style_dialog_response)
        
        # Mostrar diálogo
        dialog.present(self)

    def _on_style_dialog_response(self, dialog, response):
        """Maneja la respuesta del diálogo de estilos"""
        if response != "apply":
            return
        
        if not self.core or not self.current_resource:
            return
        
        # Obtener estilos seleccionados
        selected_styles = []
        for href, checkbox in self._style_checkboxes.items():
            if checkbox.get_active():
                # Pasar solo el nombre del archivo (core.set_styles_for_documents lo convertirá)
                style_name = Path(href).name
                selected_styles.append(style_name)
        
        if not selected_styles:
            self._show_error("Debes seleccionar al menos un archivo CSS")
            return
        
        try:
            # Obtener el ID del documento actual
            mi = self.core._get_item(self.current_resource)
            doc_id = mi.id
            
            # Aplicar estilos usando el método del core
            clear_existing = self._clear_existing_checkbox.get_active()
            
            results = self.core.set_styles_for_documents(
                docs=[doc_id],
                styles=selected_styles,
                clear_existing=clear_existing,
                add_to_manifest_if_missing=True
            )
            
            # Mostrar resultado
            applied_count = len(results.get(mi.href, []))
            self._show_info(f"Se vincularon {applied_count} archivos CSS al documento")
            
            # Recargar el contenido en el editor para ver los cambios
            self._load_text_resource(self.current_resource, KIND_DOCUMENT)
            
        except Exception as e:
            self._show_error(f"Error vinculando estilos: {e}")
        
        # Limpiar referencias
        self._style_checkboxes = {}
        self._clear_existing_checkbox = None

class GutenAIApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="gutenai")
        self.connect('activate', self._on_activate)
        
    def _on_activate(self, app):
        """Crea la ventana principal"""
        win = GutenAIWindow(application=app)
        win.present()


def main():
    """Función principal"""
    app = GutenAIApplication()
    return app.run(None)


if __name__ == "__main__":
    main()