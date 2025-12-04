#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('GtkSource', '5')
gi.require_version('WebKit', '6.0')

from gi.repository import Gtk, Adw, Gio, GLib, GtkSource, WebKit, Gdk
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

        # Área central con información del libro y archivo actual
        self.title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.title_box.set_halign(Gtk.Align.CENTER)
        self.title_box.set_valign(Gtk.Align.CENTER)

        # Título del EPUB (más grande)
        self.epub_title_label = Gtk.Label()
        self.epub_title_label.set_text("Guten.AI")
        self.epub_title_label.add_css_class("title")
        self.epub_title_label.set_ellipsize(3)  # Ellipsize en el medio
        self.title_box.append(self.epub_title_label)

        # Archivo actual (más pequeño)
        self.current_file_label = Gtk.Label()
        self.current_file_label.set_text("")
        self.current_file_label.add_css_class("subtitle")
        self.current_file_label.set_ellipsize(3)  # Ellipsize en el medio
        self.current_file_label.set_visible(False)  # Oculto inicialmente
        self.title_box.append(self.current_file_label)

        header_bar.set_title_widget(self.title_box)
        
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
        menu.append("Atajos de teclado", "app.shortcuts")
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
        
        # Configurar atajos de teclado
        self.setup_window_shortcuts()

    def setup_window_shortcuts(self):
        """Configurar atajos de teclado de la ventana"""
        # Crear controller de atajos
        shortcut_controller = Gtk.ShortcutController()
        self.add_controller(shortcut_controller)
        
        # Abrir archivo (Ctrl+O)
        open_shortcut = Gtk.Shortcut()
        open_shortcut.set_trigger(Gtk.ShortcutTrigger.parse_string("<Ctrl>o"))
        open_shortcut.set_action(Gtk.CallbackAction.new(lambda w, a: self.on_open_clicked(None)))
        shortcut_controller.add_shortcut(open_shortcut)
        
        # Guardar (Ctrl+S)
        save_shortcut = Gtk.Shortcut()
        save_shortcut.set_trigger(Gtk.ShortcutTrigger.parse_string("<Ctrl>s"))
        save_shortcut.set_action(Gtk.CallbackAction.new(lambda w, a: self.on_save_clicked(None) if hasattr(self, 'save_button') else None))
        shortcut_controller.add_shortcut(save_shortcut)
        
        # Toggle sidebar izquierdo (F9)
        sidebar_shortcut = Gtk.Shortcut()
        sidebar_shortcut.set_trigger(Gtk.ShortcutTrigger.parse_string("F9"))
        sidebar_shortcut.set_action(Gtk.CallbackAction.new(lambda w, a: self.sidebar_button.set_active(not self.sidebar_button.get_active())))
        shortcut_controller.add_shortcut(sidebar_shortcut)
        
        # Toggle preview (Ctrl+P)
        preview_shortcut = Gtk.Shortcut()
        preview_shortcut.set_trigger(Gtk.ShortcutTrigger.parse_string("<Ctrl>p"))
        preview_shortcut.set_action(Gtk.CallbackAction.new(lambda w, a: self.preview_button.set_active(not self.preview_button.get_active())))
        shortcut_controller.add_shortcut(preview_shortcut)
        
        # Preview fullscreen (Ctrl+Shift+P)
        fullscreen_shortcut = Gtk.Shortcut()
        fullscreen_shortcut.set_trigger(Gtk.ShortcutTrigger.parse_string("<Ctrl><Shift>p"))
        fullscreen_shortcut.set_action(Gtk.CallbackAction.new(lambda w, a: self.on_preview_fullscreen(None)))
        shortcut_controller.add_shortcut(fullscreen_shortcut)

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

        # Actualizar headerbar con el título del EPUB
        self.update_headerbar_title()

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
            if items or section_type in ['text', 'styles', 'images', 'fonts']:  # Mostrar siempre estas secciones
                # Crear ExpanderRow para cada sección
                expander_row = Adw.ExpanderRow()
                expander_row.set_title(f"{icon} {title}")
                expander_row.set_subtitle(f"{subtitle} ({len(items)})")
                
                # Agregar botón de acción según el tipo de sección
                if section_type in ['text', 'styles']:
                    add_button = Gtk.Button()
                    add_button.set_icon_name("list-add-symbolic")
                    add_button.set_tooltip_text(f"Agregar nuevo {title.lower()}")
                    add_button.connect("clicked", lambda btn, stype=section_type: self.add_new_file(stype))
                    add_button.set_valign(Gtk.Align.CENTER)
                    expander_row.add_suffix(add_button)
                elif section_type in ['images', 'fonts']:
                    import_button = Gtk.Button()
                    import_button.set_icon_name("document-open-symbolic")
                    import_button.set_tooltip_text(f"Importar {title.lower()}")
                    import_button.connect("clicked", lambda btn, stype=section_type: self.import_files(stype))
                    import_button.set_valign(Gtk.Align.CENTER)
                    expander_row.add_suffix(import_button)
                
                # Agregar cada item como una fila anidada
                for item in items:
                    nested_row = Adw.ActionRow()
                    nested_row.set_title(item['name'])
                    nested_row.set_subtitle(item.get('media_type', 'Archivo'))
                    
                    # Hacer la fila activable/seleccionable
                    nested_row.set_activatable(True)
                    
                    # Agregar botón de renombrar para texto y estilos
                    if section_type in ['text', 'styles']:
                        rename_button = Gtk.Button()
                        rename_button.set_icon_name("document-edit-symbolic")
                        rename_button.set_tooltip_text("Renombrar archivo")
                        rename_button.connect("clicked", lambda btn, itm=item, stype=section_type: self.rename_file(itm, stype))
                        rename_button.set_valign(Gtk.Align.CENTER)
                        nested_row.add_suffix(rename_button)
                    
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
    
    def update_headerbar_title(self):
        """Actualizar título en la headerbar según el EPUB y archivo actual"""
        if hasattr(self, 'epub_data') and self.epub_data:
            # Mostrar título del EPUB
            epub_title = self.epub_data['metadata']['title']
            self.epub_title_label.set_text(epub_title)
            
            # Mostrar archivo actual si existe
            if hasattr(self, 'current_file') and self.current_file:
                file_name = self.current_file['name']
                # Mostrar solo el nombre del archivo sin la ruta
                display_name = file_name.split('/')[-1] if '/' in file_name else file_name
                self.current_file_label.set_text(display_name)
                self.current_file_label.set_visible(True)
            else:
                self.current_file_label.set_visible(False)
        else:
            # Sin EPUB cargado
            self.epub_title_label.set_text("Guten.AI")
            self.current_file_label.set_visible(False)
            
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
                    content = epub_item.get_content()
                    # Verificar si es bytes o string
                    if isinstance(content, bytes):
                        content = content.decode('utf-8')
                    # Si ya es string, usarlo directamente
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
            self.update_headerbar_title()
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
                original_content = epub_item.get_content()
                
                # Asegurar que ambos contenidos sean strings para comparación
                if isinstance(original_content, bytes):
                    original_content = original_content.decode('utf-8')
                # Si ya es string, usarlo directamente
                
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

    def add_new_file(self, section_type):
        """Agregar nuevo archivo HTML o CSS"""
        if section_type == 'text':
            title = "Nuevo capítulo HTML"
            default_name = "nuevo_capitulo.xhtml"
            template_content = """<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE html>
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <title>Nuevo Capítulo</title>
    </head>
    <body>
        <h1>Nuevo Capítulo</h1>
        <p>Contenido del capítulo...</p>
    </body>
    </html>"""
        elif section_type == 'styles':
            title = "Nuevo archivo CSS"
            default_name = "nuevo_estilo.css"
            template_content = """/* Nuevo archivo de estilos */
    body {
        font-family: serif;
        line-height: 1.6;
        margin: 0;
        padding: 20px;
    }

    h1, h2, h3, h4, h5, h6 {
        margin-top: 1.5em;
        margin-bottom: 0.5em;
    }

    p {
        margin-bottom: 1em;
    }
    """
        else:
            return
        
        # Diálogo para nombre del archivo
        dialog = Adw.MessageDialog.new(self, title, "Ingresa el nombre del archivo:")
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("create", "Crear")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        
        entry = Gtk.Entry()
        entry.set_text(default_name)
        entry.set_margin_top(12)
        entry.set_margin_bottom(12)
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        
        dialog.set_extra_child(entry)
        dialog.connect("response", lambda d, r: self.on_new_file_response(d, r, entry, section_type, template_content))
        dialog.present()

    def on_new_file_response(self, dialog, response, entry, section_type, template_content):
        """Callback para crear nuevo archivo"""
        if response == "create":
            filename = entry.get_text().strip()
            if filename:
                self.create_new_file(filename, section_type, template_content)
        dialog.destroy()

    def create_new_file(self, filename, section_type, content):
        """Crear nuevo archivo en el EPUB"""
        try:
            book = self.epub_data['book_object']
            
            # Asegurar extensión correcta
            if section_type == 'text' and not filename.endswith(('.html', '.xhtml')):
                filename += '.xhtml'
            elif section_type == 'styles' and not filename.endswith('.css'):
                filename += '.css'
            
            # Crear path dentro de la estructura EPUB
            if section_type == 'text':
                file_path = f"Text/{filename}"
                media_type = "application/xhtml+xml"
            elif section_type == 'styles':
                file_path = f"Styles/{filename}"
                media_type = "text/css"
            
            # Verificar que no exista ya
            existing_item = book.get_item_with_href(file_path)
            if existing_item:
                self.show_error_dialog(f"Ya existe un archivo con el nombre '{file_path}'")
                return
            
            # Crear nuevo item - IMPORTANTE: convertir contenido a bytes
            content_bytes = content.encode('utf-8') if isinstance(content, str) else content
            
            if section_type == 'text':
                new_item = epub.EpubHtml(title=filename, file_name=file_path, content=content_bytes)
                book.add_item(new_item)
                # Agregar al spine
                book.spine.append(new_item)
            elif section_type == 'styles':
                new_item = epub.EpubItem(uid=filename, file_name=file_path, media_type=media_type, content=content_bytes)
                book.add_item(new_item)
            
            # Actualizar estructura local
            item_info = {
                'name': file_path,
                'type': new_item.get_type() if hasattr(new_item, 'get_type') else None,
                'media_type': media_type
            }
            self.epub_data['structure'][section_type].append(item_info)
            
            # Refrescar sidebar
            self.update_sidebar_with_epub_structure()
            
            print(f"Archivo creado: {file_path}")
            
        except Exception as e:
            self.show_error_dialog(f"Error al crear archivo: {str(e)}")

    def rename_file(self, item, section_type):
        """Renombrar archivo HTML o CSS"""
        current_name = item['name'].split('/')[-1]  # Solo el nombre sin path
        
        dialog = Adw.MessageDialog.new(self, "Renombrar archivo", f"Nuevo nombre para '{current_name}':")
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("rename", "Renombrar")
        dialog.set_response_appearance("rename", Adw.ResponseAppearance.SUGGESTED)
        
        entry = Gtk.Entry()
        entry.set_text(current_name)
        entry.set_margin_top(12)
        entry.set_margin_bottom(12)
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        
        dialog.set_extra_child(entry)
        dialog.connect("response", lambda d, r: self.on_rename_response(d, r, entry, item, section_type))
        dialog.present()

    def on_rename_response(self, dialog, response, entry, item, section_type):
        """Callback para renombrar archivo"""
        if response == "rename":
            new_name = entry.get_text().strip()
            if new_name and new_name != item['name'].split('/')[-1]:
                self.perform_rename(item, new_name, section_type)
        dialog.destroy()

    def perform_rename(self, item, new_name, section_type):
        """Realizar el renombrado del archivo"""
        try:
            book = self.epub_data['book_object']
            old_href = item['name']
            
            # Asegurar extensión correcta
            if section_type == 'text' and not new_name.endswith(('.html', '.xhtml')):
                new_name += '.xhtml'
            elif section_type == 'styles' and not new_name.endswith('.css'):
                new_name += '.css'
            
            # Crear nuevo path
            path_parts = old_href.split('/')
            path_parts[-1] = new_name
            new_href = '/'.join(path_parts)
            
            # Verificar que no exista ya
            existing_item = book.get_item_with_href(new_href)
            if existing_item:
                self.show_error_dialog(f"Ya existe un archivo con el nombre '{new_href}'")
                return
            
            # Obtener item actual
            epub_item = book.get_item_with_href(old_href)
            if not epub_item:
                self.show_error_dialog("No se pudo encontrar el archivo original")
                return
            
            # Crear nuevo item con el contenido existente
            content = epub_item.get_content()
            
            if section_type == 'text':
                new_item = epub.EpubHtml(title=new_name, file_name=new_href, content=content)
                # Reemplazar en spine
                spine_items = []
                for spine_item in book.spine:
                    if hasattr(spine_item, 'get_name') and spine_item.get_name() == old_href:
                        spine_items.append(new_item)
                    else:
                        spine_items.append(spine_item)
                book.spine = spine_items
            elif section_type == 'styles':
                new_item = epub.EpubItem(
                    uid=new_name, 
                    file_name=new_href, 
                    media_type=item['media_type'], 
                    content=content
                )
            
            # Remover item viejo y agregar nuevo
            book.items.remove(epub_item)
            book.add_item(new_item)
            
            # Actualizar estructura local
            for i, struct_item in enumerate(self.epub_data['structure'][section_type]):
                if struct_item['name'] == old_href:
                    self.epub_data['structure'][section_type][i]['name'] = new_href
                    break
            
            # Si este archivo está siendo editado, actualizar referencia
            if hasattr(self, 'current_file') and self.current_file and self.current_file['name'] == old_href:
                self.current_file['name'] = new_href
                self.update_headerbar_title()
            
            # Actualizar archivos modificados si existe referencia
            if old_href in self.modified_files:
                self.modified_files[new_href] = self.modified_files.pop(old_href)
            
            # Refrescar sidebar
            self.update_sidebar_with_epub_structure()
            
            print(f"Archivo renombrado: {old_href} -> {new_href}")
            
        except Exception as e:
            self.show_error_dialog(f"Error al renombrar archivo: {str(e)}")

    def import_files(self, section_type):
        """Importar archivos desde disco local"""
        if section_type == 'images':
            title = "Importar imágenes"
            filters = [
                ("Imágenes", ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.svg", "*.webp"]),
                ("Todos los archivos", ["*"])
            ]
        elif section_type == 'fonts':
            title = "Importar fuentes"
            filters = [
                ("Fuentes", ["*.ttf", "*.otf", "*.woff", "*.woff2"]),
                ("Todos los archivos", ["*"])
            ]
        else:
            return

        dialog = Gtk.FileChooserDialog(
            title=title,
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )

        dialog.add_buttons(
            "Cancelar", Gtk.ResponseType.CANCEL,
            "Importar", Gtk.ResponseType.ACCEPT
        )

        # Permitir selección múltiple
        dialog.set_select_multiple(True)

        # Agregar filtros
        for filter_name, patterns in filters:
            file_filter = Gtk.FileFilter()
            file_filter.set_name(filter_name)
            for pattern in patterns:
                file_filter.add_pattern(pattern)
            dialog.add_filter(file_filter)

        dialog.connect("response", lambda d, r: self.on_import_response(d, r, section_type))
        dialog.present()

    def on_import_response(self, dialog, response, section_type):
        """Callback para importar archivos"""
        if response == Gtk.ResponseType.ACCEPT:
            files = dialog.get_files()
            for i in range(files.get_n_items()):
                file = files.get_item(i)
                file_path = file.get_path()
                self.import_single_file(file_path, section_type)
        dialog.destroy()

    def import_single_file(self, file_path, section_type):
        """Importar un archivo individual"""
        try:
            import os
            import mimetypes
            
            filename = os.path.basename(file_path)
            book = self.epub_data['book_object']
            
            # Leer contenido del archivo
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # Determinar tipo MIME
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                if section_type == 'images':
                    mime_type = "image/jpeg"  # Default
                elif section_type == 'fonts':
                    mime_type = "font/ttf"    # Default
            
            # Crear path dentro del EPUB
            if section_type == 'images':
                epub_path = f"Images/{filename}"
            elif section_type == 'fonts':
                epub_path = f"Fonts/{filename}"
            
            # Verificar que no exista ya
            existing_item = book.get_item_with_href(epub_path)
            if existing_item:
                # Agregar número al final si ya existe
                name_parts = filename.rsplit('.', 1)
                if len(name_parts) == 2:
                    base_name, extension = name_parts
                    counter = 1
                    while existing_item:
                        new_filename = f"{base_name}_{counter}.{extension}"
                        epub_path = f"{'Images' if section_type == 'images' else 'Fonts'}/{new_filename}"
                        existing_item = book.get_item_with_href(epub_path)
                        counter += 1
                    filename = new_filename
            
            # Crear item EPUB
            epub_item = epub.EpubItem(
                uid=filename,
                file_name=epub_path,
                media_type=mime_type,
                content=content
            )
            
            book.add_item(epub_item)
            
            # Actualizar estructura local
            item_info = {
                'name': epub_path,
                'type': epub_item.get_type() if hasattr(epub_item, 'get_type') else None,
                'media_type': mime_type
            }
            self.epub_data['structure'][section_type].append(item_info)
            
            print(f"Archivo importado: {filename} -> {epub_path}")
            
        except Exception as e:
            print(f"Error al importar {file_path}: {str(e)}")
            self.show_error_dialog(f"Error al importar {os.path.basename(file_path)}: {str(e)}")

    # Al final, refrescar sidebar después de importar todos los archivos
    def on_import_response(self, dialog, response, section_type):
        """Callback para importar archivos"""
        if response == Gtk.ResponseType.ACCEPT:
            files = dialog.get_files()
            imported_count = 0
            for i in range(files.get_n_items()):
                file = files.get_item(i)
                file_path = file.get_path()
                try:
                    self.import_single_file(file_path, section_type)
                    imported_count += 1
                except:
                    continue
            
            if imported_count > 0:
                # Refrescar sidebar
                self.update_sidebar_with_epub_structure()
                print(f"Importados {imported_count} archivos")
        
        dialog.destroy()

class GutenAIApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="gutenai")
        self.connect('activate', self.on_activate)
        self.setup_icon_theme()
        # Crear acción para "Acerca de"
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_action)
        self.add_action(about_action)
        
        # Crear acción para "Atajos de teclado"
        shortcuts_action = Gio.SimpleAction.new("shortcuts", None)
        shortcuts_action.connect("activate", self.on_shortcuts_action)
        self.add_action(shortcuts_action)
        
        # Configurar atajos de teclado globales
        self.setup_shortcuts()

    def setup_shortcuts(self):
        """Configurar atajos de teclado de la aplicación"""
        # Atajo para mostrar ventana de atajos
        self.set_accels_for_action("app.shortcuts", ["<Ctrl>question"])
        
        # Atajos para la aplicación
        self.set_accels_for_action("app.quit", ["<Ctrl>q"])

    def on_activate(self, app):
        self.win = GutenAIWindow(application=app)
        self.win.present()

    def on_about_action(self, action, param):
        """Mostrar diálogo Acerca de"""
        from about import create_about_window
        about = create_about_window(self.win)
        about.set_application_icon("gutenai")
        about.present()

    def on_shortcuts_action(self, action, param):
        """Mostrar ventana de atajos de teclado"""
        from shortcuts_window import create_shortcuts_window
        shortcuts_window = create_shortcuts_window()
        shortcuts_window.set_transient_for(self.win)
        shortcuts_window.present()

    def setup_icon_theme(self):
        """Configurar el tema de iconos para usar iconos personalizados"""
        try:
            # Obtener el tema de iconos por defecto
            icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            
            # Agregar la ruta de iconos personalizados
            current_dir = os.path.dirname(os.path.abspath(__file__))
            icons_dir = os.path.join(current_dir, "data", "icons")
            
            if os.path.exists(icons_dir):
                icon_theme.add_search_path(icons_dir)
                print(f"Iconos personalizados cargados desde: {icons_dir}")
            else:
                print(f"Directorio de iconos no encontrado: {icons_dir}")
                
        except Exception as e:
            print(f"Error al configurar iconos: {e}")


def main():
    app = GutenAIApplication()
    return app.run(sys.argv)

if __name__ == '__main__':
    main()