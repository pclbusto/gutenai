#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('GtkSource', '5')
gi.require_version('WebKit', '6.0')

from gi.repository import Gtk, Adw, Gio, GLib, GtkSource, WebKit
import ebooklib
from ebooklib import epub
import sys
import base64
import os

class GutenAIWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.epub_data = None
        self.modified_files = {}
        self.current_file = None
        self.current_source_view = None
        self.setup_ui()

    def setup_ui(self):
        # Configurar la ventana
        self.set_title("Guten.AI")
        self.set_default_size(1200, 800)
        self.maximize()

        # Header Bar con botones de ventana
        header_bar = Adw.HeaderBar()
        self.set_titlebar(header_bar)
        
        # Botón para mostrar/ocultar sidebar izquierdo
        self.sidebar_button = Gtk.ToggleButton()
        self.sidebar_button.set_icon_name("sidebar-show-symbolic")
        self.sidebar_button.set_tooltip_text("Mostrar/Ocultar estructura del EPUB")
        self.sidebar_button.connect("toggled", self.on_sidebar_toggled)
        header_bar.pack_start(self.sidebar_button)
        
        # Botón para abrir EPUB
        open_button = Gtk.Button()
        open_button.set_icon_name("document-open-symbolic")
        open_button.set_tooltip_text("Abrir archivo EPUB")
        open_button.connect("clicked", self.on_open_clicked)
        header_bar.pack_start(open_button)

        # Botón para guardar cambios
        self.save_button = Gtk.Button()
        self.save_button.set_icon_name("document-save-symbolic")
        self.save_button.set_tooltip_text("Guardar cambios en EPUB")
        self.save_button.set_sensitive(False)
        self.save_button.connect("clicked", self.on_save_clicked)
        header_bar.pack_start(self.save_button)

        # Botón para mostrar/ocultar sidebar derecho (preview)
        self.preview_button = Gtk.ToggleButton()
        self.preview_button.set_icon_name("view-dual-symbolic")
        self.preview_button.set_tooltip_text("Mostrar/Ocultar previsualización")
        self.preview_button.connect("toggled", self.on_preview_toggled)
        header_bar.pack_end(self.preview_button)

        # Menú hamburguesa (lado derecho)
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_tooltip_text("Menú principal")
        
        # Crear el menú
        menu = Gio.Menu()
        menu.append("Acerca de", "app.about")
        menu_button.set_menu_model(menu)
        header_bar.pack_end(menu_button)

        # Contenido principal con sidebar izquierdo
        self.main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_child(self.main_paned)
        
        # Sidebar izquierdo
        self.sidebar = self.create_sidebar()
        self.main_paned.set_start_child(self.sidebar)
        self.main_paned.set_resize_start_child(False)
        self.main_paned.set_shrink_start_child(False)
        
        # Panel central con sidebar derecho
        self.center_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_paned.set_end_child(self.center_paned)
        
        # Contenido principal (editor)
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.center_paned.set_start_child(self.main_box)
        
        # Sidebar derecho (preview)
        self.preview_sidebar = self.create_preview_sidebar()
        # Por defecto oculto
        self.center_paned.set_end_child(None)

        # Status inicial
        self.status_page = Adw.StatusPage()
        self.status_page.set_title("Bienvenido a Guten.AI")
        self.status_page.set_description("Selecciona un archivo EPUB para comenzar")
        self.status_page.set_icon_name("book-open-variant-symbolic")
        
        self.main_box.append(self.status_page)

    def create_sidebar(self):
        """Crear sidebar con las secciones del EPUB"""
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar_box.set_size_request(300, -1)
        sidebar_box.add_css_class("sidebar")
        
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
        
        # ScrolledWindow para las secciones
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        
        # ListBox para las secciones
        self.sections_listbox = Gtk.ListBox()
        self.sections_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.sections_listbox.add_css_class("navigation-sidebar")
        
        # Crear secciones por defecto (vacías hasta cargar EPUB)
        self.create_empty_sections()
        
        scrolled.set_child(self.sections_listbox)
        sidebar_box.append(scrolled)
        
        return sidebar_box

    def create_preview_sidebar(self):
        """Crear sidebar derecho para previsualización WebKit"""
        preview_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        preview_container.set_size_request(400, -1)
        preview_container.add_css_class("sidebar")
        
        # Header del preview sidebar
        preview_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        preview_header.set_margin_top(12)
        preview_header.set_margin_bottom(12)
        preview_header.set_margin_start(12)
        preview_header.set_margin_end(12)
        
        preview_title = Gtk.Label()
        preview_title.set_text("Previsualización")
        preview_title.add_css_class("heading")
        preview_header.append(preview_title)
        
        # Spacer para empujar el botón a la derecha
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        preview_header.append(spacer)
        
        # Botón para abrir en ventana separada
        fullscreen_button = Gtk.Button()
        fullscreen_button.set_icon_name("view-fullscreen-symbolic")
        fullscreen_button.set_tooltip_text("Abrir en ventana separada")
        fullscreen_button.connect("clicked", self.on_preview_fullscreen)
        preview_header.append(fullscreen_button)
        
        preview_container.append(preview_header)
        
        # Separador
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        preview_container.append(separator)
        
        # Crear WebView para mostrar HTML renderizado
        self.webview = WebKit.WebView()
        self.webview.set_vexpand(True)
        self.webview.set_hexpand(True)
        
        # Configurar WebView
        settings = self.webview.get_settings()
        settings.set_enable_developer_extras(True)
        settings.set_enable_write_console_messages_to_stdout(True)
        
        # ScrolledWindow para el WebView
        self.preview_area = Gtk.ScrolledWindow()
        self.preview_area.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.preview_area.set_vexpand(True)
        self.preview_area.set_margin_start(12)
        self.preview_area.set_margin_end(12)
        self.preview_area.set_margin_bottom(12)
        
        # Placeholder inicial
        self.preview_content = Gtk.Label()
        self.preview_content.set_text("Selecciona un archivo HTML para ver la previsualización")
        self.preview_content.add_css_class("dim-label")
        self.preview_content.set_wrap(True)
        self.preview_content.set_justify(Gtk.Justification.CENTER)
        self.preview_content.set_valign(Gtk.Align.CENTER)
        
        self.preview_area.set_child(self.preview_content)
        preview_container.append(self.preview_area)
        
        return preview_container

    def create_empty_sections(self):
        """Crear secciones vacías en el sidebar"""
        sections = [
            ("📄", "Texto", "Capítulos y contenido HTML", 0),
            ("🎨", "Estilos", "Archivos CSS", 0),
            ("🖼️", "Imágenes", "Imágenes y gráficos", 0),
            ("🔤", "Fuentes", "Tipografías embebidas", 0),
            ("🎵", "Audio", "Archivos de audio", 0),
            ("🎥", "Video", "Archivos de video", 0),
            ("📦", "Otros", "Recursos misceláneos", 0)
        ]
        
        for icon, title, subtitle, count in sections:
            row = Adw.ActionRow()
            row.set_title(f"{icon} {title}")
            row.set_subtitle(f"{subtitle} ({count})")
            self.sections_listbox.append(row)

    def on_sidebar_toggled(self, button):
        """Toggle visibility del sidebar izquierdo"""
        if button.get_active():
            self.main_paned.set_start_child(self.sidebar)
            button.set_icon_name("sidebar-hide-symbolic")
        else:
            self.main_paned.set_start_child(None)
            button.set_icon_name("sidebar-show-symbolic")

    def on_preview_toggled(self, button):
        """Toggle visibility del sidebar derecho (preview)"""
        if button.get_active():
            self.center_paned.set_end_child(self.preview_sidebar)
            self.center_paned.set_resize_end_child(False)
            self.center_paned.set_shrink_end_child(False)
            button.set_icon_name("view-restore-symbolic")
            
            # Actualizar previsualización si hay archivo actual
            self.update_preview()
        else:
            self.center_paned.set_end_child(None)
            button.set_icon_name("view-dual-symbolic")

    def on_preview_fullscreen(self, button):
        """Abrir previsualización en ventana separada"""
        if not hasattr(self, 'current_file') or not self.current_file:
            return
        
        if self.current_file['section_type'] != 'text':
            return
        
        # Crear ventana separada usando Gtk.Window
        fullscreen_window = Gtk.Window()
        fullscreen_window.set_title(f"Previsualización - {self.current_file['name']}")
        fullscreen_window.set_default_size(1000, 700)
        fullscreen_window.set_transient_for(self)
        
        # Header bar para la ventana
        header_bar = Adw.HeaderBar()
        fullscreen_window.set_titlebar(header_bar)
        
        # Botón para cerrar
        close_button = Gtk.Button()
        close_button.set_icon_name("window-close-symbolic")
        close_button.set_tooltip_text("Cerrar ventana")
        close_button.connect("clicked", lambda btn: fullscreen_window.close())
        header_bar.pack_end(close_button)
        
        # Botón para actualizar
        refresh_button = Gtk.Button()
        refresh_button.set_icon_name("view-refresh-symbolic")
        refresh_button.set_tooltip_text("Actualizar previsualización")
        header_bar.pack_end(refresh_button)
        
        # WebView para la ventana separada
        fullscreen_webview = WebKit.WebView()
        settings = fullscreen_webview.get_settings()
        settings.set_enable_developer_extras(True)
        
        # ScrolledWindow para el WebView
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_child(fullscreen_webview)
        
        fullscreen_window.set_child(scrolled)
        
        # Función para actualizar contenido
        def refresh_content():
            if hasattr(self, 'current_source_view') and self.current_source_view:
                buffer = self.current_source_view.get_buffer()
                start = buffer.get_start_iter()
                end = buffer.get_end_iter()
                html_content = buffer.get_text(start, end, False)
                css_content = self.get_epub_styles()
                full_html = self.create_complete_html(html_content, css_content)
                fullscreen_webview.load_html(full_html, None)
        
        # Conectar botón refresh
        refresh_button.connect("clicked", lambda btn: refresh_content())
        
        # Cargar contenido inicial
        refresh_content()
        
        # Mostrar ventana
        fullscreen_window.present()
        
        print(f"Abriendo preview fullscreen de: {self.current_file['name']}")
        

    def update_preview(self):
        """Actualizar contenido de la previsualización"""
        if hasattr(self, 'current_file') and self.current_file:
            if self.current_file['section_type'] == 'text':
                # Para archivos HTML, mostrar renderizado real
                if hasattr(self, 'current_source_view') and self.current_source_view:
                    buffer = self.current_source_view.get_buffer()
                    start = buffer.get_start_iter()
                    end = buffer.get_end_iter()
                    html_content = buffer.get_text(start, end, False)
                    
                    # Obtener CSS del EPUB para aplicar estilos
                    css_content = self.get_epub_styles()
                    
                    # Crear HTML completo con estilos
                    full_html = self.create_complete_html(html_content, css_content)
                    
                    # Cambiar a WebView y cargar HTML
                    self.preview_area.set_child(self.webview)
                    self.webview.load_html(full_html, None)
                    
                    print(f"Actualizando preview HTML de: {self.current_file['name']}")
                else:
                    self.show_preview_placeholder("Cargando previsualización...")
            else:
                self.show_preview_placeholder("Previsualización no disponible para este tipo de archivo")
        else:
            self.show_preview_placeholder("Selecciona un archivo HTML para ver la previsualización")

    def show_preview_placeholder(self, message):
        """Mostrar mensaje placeholder en el preview"""
        self.preview_content.set_text(message)
        self.preview_area.set_child(self.preview_content)

    def get_epub_styles(self):
        """Obtener todos los estilos CSS del EPUB"""
        if not self.epub_data:
            return ""
        
        css_content = ""
        book = self.epub_data['book_object']
        
        # Buscar todos los archivos CSS
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_STYLE:
                try:
                    css_content += item.get_content().decode('utf-8') + "\n"
                except:
                    continue
        
        return css_content

    def create_complete_html(self, html_content, css_content):
        """Crear HTML completo con metadatos y estilos"""
        # Detectar tema del sistema
        settings = Gtk.Settings.get_default()
        prefer_dark = settings.get_property("gtk-application-prefer-dark-theme")
        
        # Estilos base según el tema
        if prefer_dark:
            base_styles = """
            body {
                font-family: -webkit-system-font, system-ui, sans-serif;
                line-height: 1.6;
                margin: 20px;
                background-color: #1e1e1e;
                color: #ffffff;
            }
            """
        else:
            base_styles = """
            body {
                font-family: -webkit-system-font, system-ui, sans-serif;
                line-height: 1.6;
                margin: 20px;
                background-color: #ffffff;
                color: #000000;
            }
            """
        
        # Si el HTML ya es un documento completo, usarlo tal como está
        if html_content.strip().lower().startswith('<!doctype') or html_content.strip().lower().startswith('<html'):
            if css_content and '<head>' in html_content:
                style_tag = f"<style>\n{base_styles}\n{css_content}\n</style>"
                html_content = html_content.replace('</head>', f"{style_tag}\n</head>")
            return html_content
        
        # Si es solo contenido del body, crear documento completo
        complete_html = f"""<!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Vista previa</title>
        <style>
            {base_styles}
            {css_content}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>"""
        
        return complete_html

    def on_open_clicked(self, button):
        """Callback para abrir archivo EPUB"""
        dialog = Gtk.FileChooserDialog(
            title="Seleccionar archivo EPUB",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        
        dialog.add_buttons(
            "Cancelar", Gtk.ResponseType.CANCEL,
            "Abrir", Gtk.ResponseType.ACCEPT
        )

        # Filtro para archivos EPUB
        filter_epub = Gtk.FileFilter()
        filter_epub.set_name("Archivos EPUB")
        filter_epub.add_mime_type("application/epub+zip")
        filter_epub.add_pattern("*.epub")
        dialog.add_filter(filter_epub)

        dialog.connect("response", self.on_file_dialog_response)
        dialog.present()

    def on_file_dialog_response(self, dialog, response):
        """Callback para manejar la respuesta del diálogo de archivo"""
        if response == Gtk.ResponseType.ACCEPT:
            # Usar get_files() en lugar de get_file() para evitar deprecation warning
            files = dialog.get_files()
            if files.get_n_items() > 0:
                file = files.get_item(0)
                file_path = file.get_path()
                self.load_epub(file_path)
        
        dialog.destroy()

    def load_epub(self, file_path):
        """Cargar y procesar archivo EPUB con ebooklib"""
        try:
            # Cargar EPUB
            book = epub.read_epub(file_path)
            
            # Extraer metadatos
            title = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else "Sin título"
            author = book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else "Autor desconocido"
            language = book.get_metadata('DC', 'language')[0][0] if book.get_metadata('DC', 'language') else "No especificado"
            
            # Organizar estructura según categorías
            structure = {
                'text': [],
                'styles': [],
                'images': [],
                'fonts': [],
                'audio': [],
                'video': [],
                'others': []
            }

            # Procesar items del EPUB
            for item in book.get_items():
                item_info = {
                    'name': item.get_name(),
                    'type': item.get_type(),
                    'media_type': item.media_type
                }

                # Categorizar según tipo de contenido
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    structure['text'].append(item_info)
                elif item.get_type() == ebooklib.ITEM_STYLE:
                    structure['styles'].append(item_info)
                elif item.get_type() == ebooklib.ITEM_IMAGE:
                    structure['images'].append(item_info)
                elif 'font' in item.media_type.lower() or item.media_type in ['application/font-woff', 'application/font-woff2', 'font/ttf', 'font/otf']:
                    structure['fonts'].append(item_info)
                elif 'audio' in item.media_type:
                    structure['audio'].append(item_info)
                elif 'video' in item.media_type:
                    structure['video'].append(item_info)
                else:
                    structure['others'].append(item_info)

            # Guardar datos del EPUB
            self.epub_data = {
                'file_path': file_path,
                'metadata': {
                    'title': title,
                    'author': author,
                    'language': language
                },
                'structure': structure,
                'book_object': book
            }

            # Mostrar estructura en la interfaz
            self.display_epub_structure()

        except Exception as e:
            self.show_error_dialog(f"Error al cargar el EPUB: {str(e)}")

    def display_epub_structure(self):
        """Mostrar la estructura del EPUB en la interfaz y actualizar sidebar"""
        # Limpiar contenido anterior
        self.main_box.remove(self.status_page)

        # Actualizar sidebar con estructura real del EPUB
        self.update_sidebar_with_epub_structure()

        # Crear vista principal
        main_view = Gtk.ScrolledWindow()
        main_view.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)

        # Información del libro
        book_info = Adw.PreferencesGroup()
        book_info.set_title("Información del EPUB")
        
        title_row = Adw.ActionRow()
        title_row.set_title("Título")
        title_row.set_subtitle(self.epub_data['metadata']['title'])
        book_info.add(title_row)
        
        author_row = Adw.ActionRow()
        author_row.set_title("Autor")
        author_row.set_subtitle(self.epub_data['metadata']['author'])
        book_info.add(author_row)
        
        language_row = Adw.ActionRow()
        language_row.set_title("Idioma")
        language_row.set_subtitle(self.epub_data['metadata']['language'])
        book_info.add(language_row)
        
        content_box.append(book_info)
        
        main_view.set_child(content_box)
        self.main_box.append(main_view)

    def update_sidebar_with_epub_structure(self):
        """Actualizar el sidebar con la estructura real del EPUB"""
        # Limpiar listbox actual
        while True:
            child = self.sections_listbox.get_first_child()
            if child is None:
                break
            self.sections_listbox.remove(child)
        
        structure = self.epub_data['structure']
        
        # Definir secciones con sus datos reales
        sections = [
            ("📄", "Texto", "Capítulos y contenido HTML", structure['text'], 'text'),
            ("🎨", "Estilos", "Archivos CSS", structure['styles'], 'styles'),
            ("🖼️", "Imágenes", "Imágenes y gráficos", structure['images'], 'images'),
            ("🔤", "Fuentes", "Tipografías embebidas", structure['fonts'], 'fonts'),
            ("🎵", "Audio", "Archivos de audio", structure['audio'], 'audio'),
            ("🎥", "Video", "Archivos de video", structure['video'], 'video'),
            ("📦", "Otros", "Recursos misceláneos", structure['others'], 'others')
        ]
        
        for icon, title, subtitle, items, section_type in sections:
            if items:  # Solo mostrar secciones que tienen contenido
                # Crear ExpanderRow para cada sección
                expander_row = Adw.ExpanderRow()
                expander_row.set_title(f"{icon} {title}")
                expander_row.set_subtitle(f"{subtitle} ({len(items)})")
                
                # Agregar cada item como una fila anidada
                for item in items:
                    nested_row = Adw.ActionRow()
                    nested_row.set_title(item['name'])
                    nested_row.set_subtitle(item.get('media_type', 'Archivo'))
                    
                    # Hacer la fila activable/seleccionable
                    nested_row.set_activatable(True)
                    
                    # Guardar información del item en la fila para acceso posterior
                    nested_row.item_data = {
                        'item': item,
                        'section_type': section_type,
                        'file_path': self.epub_data['file_path']
                    }
                    
                    # Conectar signal para selección
                    nested_row.connect('activated', self.on_file_selected)
                    
                    expander_row.add_row(nested_row)
                
                self.sections_listbox.append(expander_row)

    def on_file_selected(self, row):
        """Callback cuando se selecciona un archivo en el sidebar"""
        item_data = row.item_data
        item = item_data['item']
        section_type = item_data['section_type']
        
        print(f"Archivo seleccionado: {item['name']} (tipo: {section_type})")
        
        # Según el tipo de sección, mostrar contenido diferente en el panel derecho
        if section_type in ['text', 'styles']:
            self.show_file_content(item, section_type)
        elif section_type == 'images':
            self.show_image_preview(item)
        else:
            self.show_file_info(item, section_type)

    def show_file_content(self, item, section_type):
        """Mostrar contenido de archivos de texto/estilos en el panel derecho"""
        try:
            # Guardar cambios del archivo anterior si existe
            self.save_current_file_changes()
            
            # Obtener contenido (del temporal si existe, sino del EPUB original)
            file_key = item['name']
            if file_key in self.modified_files:
                content = self.modified_files[file_key]['content']
                print(f"Cargando desde temporal: {file_key}")
            else:
                book = self.epub_data['book_object']
                epub_item = book.get_item_with_href(item['name'])
                if epub_item:
                    content = epub_item.get_content().decode('utf-8')
                else:
                    return
            
            # Limpiar panel principal completamente
            while True:
                child = self.main_box.get_first_child()
                if child is None:
                    break
                self.main_box.remove(child)
            
            # Crear vista de contenido que ocupe todo el espacio
            content_view = Gtk.ScrolledWindow()
            content_view.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)  # Sin scroll horizontal
            content_view.set_vexpand(True)
            content_view.set_hexpand(True)
            
            # Usar GtkSourceView para resaltado de sintaxis
            source_view = GtkSource.View()
            source_view.set_editable(True)
            source_view.set_monospace(True)
            source_view.set_show_line_numbers(True)
            source_view.set_highlight_current_line(True)
            source_view.set_auto_indent(True)
            source_view.set_indent_on_tab(True)
            source_view.set_tab_width(2)
            source_view.set_insert_spaces_instead_of_tabs(True)
            
            # Configurar word wrap para ajustar líneas al ancho
            source_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            
            # Configurar buffer con resaltado de sintaxis
            buffer = GtkSource.Buffer()
            
            # Obtener language manager y configurar lenguaje según tipo
            lang_manager = GtkSource.LanguageManager.get_default()
            
            if section_type == 'text':
                language = lang_manager.get_language('html')
            elif section_type == 'styles':
                language = lang_manager.get_language('css')
            else:
                language = None
            
            if language:
                buffer.set_language(language)
                buffer.set_highlight_syntax(True)
            
            # Configurar scheme de colores según el tema del sistema
            scheme_manager = GtkSource.StyleSchemeManager.get_default()
            
            # Detectar si estamos en modo oscuro
            settings = Gtk.Settings.get_default()
            prefer_dark = settings.get_property("gtk-application-prefer-dark-theme")
            
            if prefer_dark:
                scheme = scheme_manager.get_scheme('Adwaita-dark')
            else:
                scheme = scheme_manager.get_scheme('Adwaita')
            
            if scheme:
                buffer.set_style_scheme(scheme)
            
            buffer.set_text(content)
            source_view.set_buffer(buffer)
            
            # Conectar signal para detectar cambios
            buffer.connect('changed', self.on_buffer_changed)
            
            content_view.set_child(source_view)
            self.main_box.append(content_view)
            
            # Actualizar archivo actual
            self.current_file = {
                'name': file_key,
                'section_type': section_type,
                'item': item
            }
            self.current_source_view = source_view
            
            # Actualizar previsualización si está visible
            if hasattr(self, 'preview_button') and self.preview_button.get_active():
                self.update_preview()
            
            print(f"Mostrando contenido de {item['name']} con resaltado de sintaxis")
            
        except Exception as e:
            print(f"Error al cargar archivo {item['name']}: {str(e)}")

    def save_current_file_changes(self):
        """Guardar cambios del archivo actual en el diccionario temporal"""
        if hasattr(self, 'current_file') and self.current_file and hasattr(self, 'current_source_view') and self.current_source_view:
            buffer = self.current_source_view.get_buffer()
            start = buffer.get_start_iter()
            end = buffer.get_end_iter()
            current_content = buffer.get_text(start, end, False)
            
            file_key = self.current_file['name']
            
            # Obtener contenido original para comparar
            book = self.epub_data['book_object']
            epub_item = book.get_item_with_href(file_key)
            if epub_item:
                original_content = epub_item.get_content().decode('utf-8')
                
                # Solo guardar si hay cambios
                if current_content != original_content:
                    self.modified_files[file_key] = {
                        'content': current_content,
                        'original_content': original_content,
                        'section_type': self.current_file['section_type'],
                        'item': self.current_file['item']
                    }
                    print(f"Guardando cambios temporales para: {file_key}")
                elif file_key in self.modified_files:
                    # Si el contenido volvió al original, remover de modificados
                    del self.modified_files[file_key]
                    print(f"Contenido restaurado al original: {file_key}")
                
                # Actualizar UI
                self.update_save_button_state()
                self.update_modified_files_indicator()

    def on_buffer_changed(self, buffer):
        """Callback cuando cambia el contenido del buffer"""
        # Marcar que hay cambios pendientes
        if hasattr(self, 'current_file') and self.current_file:
            print(f"Detectado cambio en: {self.current_file['name']}")

    def update_save_button_state(self):
        """Actualizar estado del botón guardar según si hay cambios"""
        has_changes = len(self.modified_files) > 0
        if hasattr(self, 'save_button'):
            self.save_button.set_sensitive(has_changes)

    def update_modified_files_indicator(self):
        """Actualizar indicadores visuales de archivos modificados en el sidebar"""
        # TODO: Marcar en el sidebar cuáles archivos tienen cambios
        if self.modified_files:
            modified_count = len(self.modified_files)
            print(f"Archivos modificados: {modified_count}")
            for file_name in self.modified_files.keys():
                print(f"  - {file_name}")

    def on_save_clicked(self, button):
        """Guardar todos los cambios al EPUB"""
        if not self.modified_files:
            return
        
        try:
            # Guardar cambios del archivo actual primero
            self.save_current_file_changes()
            
            # Aplicar todos los cambios al objeto EPUB
            book = self.epub_data['book_object']
            
            for file_name, file_data in self.modified_files.items():
                epub_item = book.get_item_with_href(file_name)
                if epub_item:
                    new_content = file_data['content'].encode('utf-8')
                    epub_item.set_content(new_content)
                    print(f"Aplicando cambios a: {file_name}")
            
            # Escribir el EPUB modificado
            epub.write_epub(self.epub_data['file_path'], book)
            
            # Limpiar cambios temporales
            self.modified_files.clear()
            self.update_save_button_state()
            self.update_modified_files_indicator()
            
            print("EPUB guardado exitosamente")
            
            # Mostrar confirmación
            toast = Adw.Toast()
            toast.set_title("EPUB guardado exitosamente")
            # TODO: Mostrar toast en la ventana
            
        except Exception as e:
            print(f"Error al guardar EPUB: {str(e)}")
            # TODO: Mostrar error en dialog

    def show_image_preview(self, item):
        """Mostrar preview de imagen"""
        print(f"Mostrando preview de imagen: {item['name']}")
        # TODO: Implementar preview de imágenes

    def show_file_info(self, item, section_type):
        """Mostrar información básica del archivo"""
        print(f"Mostrando info de archivo: {item['name']} (tipo: {section_type})")
        # TODO: Implementar vista de información de archivo

    def show_error_dialog(self, message):
        """Mostrar diálogo de error"""
        dialog = Adw.MessageDialog.new(self, "Error", message)
        dialog.add_response("ok", "OK")
        dialog.present()

class GutenAIApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.gutenai.editor")
        self.connect('activate', self.on_activate)
        
        # Crear acción para "Acerca de"
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_action)
        self.add_action(about_action)

    def on_activate(self, app):
        self.win = GutenAIWindow(application=app)
        self.win.present()

    def on_about_action(self, action, param):
        """Mostrar diálogo Acerca de"""
        from about import create_about_window
        about = create_about_window(self.win)
        about.present()

def main():
    app = GutenAIApplication()
    return app.run(sys.argv)

if __name__ == '__main__':
    main()