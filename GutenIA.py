#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib
import ebooklib
from ebooklib import epub
import sys

class GutenAIWindow(Gtk.ApplicationWindow):  # Cambio de Adw.ApplicationWindow a Gtk.ApplicationWindow
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.epub_data = None
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

        # Menú hamburguesa (lado derecho)
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_tooltip_text("Menú principal")
        
        # Crear el menú
        menu = Gio.Menu()
        menu.append("Acerca de", "app.about")
        menu_button.set_menu_model(menu)
        header_bar.pack_end(menu_button)

        # Contenido principal con sidebar
        self.main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_child(self.main_paned)
        
        # Sidebar izquierdo
        self.sidebar = self.create_sidebar()
        self.main_paned.set_start_child(self.sidebar)
        self.main_paned.set_resize_start_child(False)
        self.main_paned.set_shrink_start_child(False)
        
        # Contenido principal
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_paned.set_end_child(self.main_box)

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
        """Toggle visibility del sidebar"""
        if button.get_active():
            self.main_paned.set_start_child(self.sidebar)
            button.set_icon_name("sidebar-hide-symbolic")
        else:
            self.main_paned.set_start_child(None)
            button.set_icon_name("sidebar-show-symbolic")

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
        """Mostrar la estructura del EPUB en la interfaz"""
        # Limpiar contenido anterior
        self.main_box.remove(self.status_page)

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

        # Estructura de archivos
        structure_info = Adw.PreferencesGroup()
        structure_info.set_title("Estructura del EPUB")
        
        structure = self.epub_data['structure']
        
        # Crear filas para cada categoría
        categories = [
            ('text', '📄 Texto', 'Capítulos y contenido HTML'),
            ('styles', '🎨 Estilos', 'Archivos CSS'),
            ('images', '🖼️ Imágenes', 'Imágenes y gráficos'),
            ('fonts', '🔤 Fuentes', 'Tipografías embebidas'),
            ('audio', '🎵 Audio', 'Archivos de audio'),
            ('video', '🎥 Video', 'Archivos de video'),
            ('others', '📦 Otros', 'Recursos misceláneos')
        ]
        
        for category_key, category_name, category_desc in categories:
            items = structure[category_key]
            if items:  # Solo mostrar si hay elementos
                category_row = Adw.ActionRow()
                category_row.set_title(f"{category_name} ({len(items)})")
                category_row.set_subtitle(category_desc)
                
                # Lista de archivos como subtitle expandido
                files_text = "\n".join([f"• {item['name']}" for item in items[:5]])
                if len(items) > 5:
                    files_text += f"\n... y {len(items) - 5} más"
                
                category_row.set_subtitle(f"{category_desc}\n{files_text}")
                structure_info.add(category_row)
        
        content_box.append(structure_info)
        
        main_view.set_child(content_box)
        self.main_box.append(main_view)

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
        about = Adw.AboutWindow(transient_for=self.win)
        about.set_application_name("Guten.AI")
        about.set_application_icon("com.gutenai.editor")
        about.set_version("1.0.0")
        about.set_comments("Editor de libros EPUB con inteligencia artificial")
        
        # Desarrollador y traductor
        about.set_developer_name("Busto Pedro")
        about.set_translator_credits("Busto Pedro")
        
        # Documentación (hipervínculo)
        about.set_website("https://github.com/pclbusto/gutenai")

        
        # Créditos
        about.add_credit_section("Código fuente", ["Busto Pedro"])
        about.add_credit_section("Diseño", ["Busto Pedro"])
        about.add_credit_section("Arte", ["Busto Pedro"])
        
        # Información legal
        about.set_copyright("© 2017–2022 Purism SPC\n© 2023-2024 GNOME Foundation Inc.")
        about.set_license("Este programa viene SIN NINGUNA GARANTÍA. "
                         "Consulte la Licencia Pública General Reducida de GNU, "
                         "versión 2.1 o posterior para obtener más detalles.")
        
        about.present()

def main():
    app = GutenAIApplication()
    return app.run(sys.argv)

if __name__ == '__main__':
    main()