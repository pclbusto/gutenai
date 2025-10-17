import os

# Desactiva renderizado acelerado por GPU en WebKitGTK
os.environ['WEBKIT_DISABLE_COMPOSITING_MODE'] = '1'

import sys
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')

from gi.repository import Gtk, Gio, GLib


from core.recent_manager import RecentManager
from core.settings_manager import SettingsManager
from core.editor_tab import EditorTab

class GuteniaWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.recent_manager = RecentManager()
        self.settings_manager = SettingsManager()
        self.settings = self.settings_manager.load()
        
        self.tabs = {}
        # --- NUEVO: Guardar referencia a la pestaña activa ---
        self.active_tab = None

        self.setup_window()

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_box)

        self.header_bar = Gtk.HeaderBar()
        self.header_bar.set_show_close_button(True)
        self.header_bar.props.title = "Gutenia"
        self.set_titlebar(self.header_bar)

        self.setup_header_bar_buttons()

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        main_box.pack_start(self.notebook, True, True, 0)
        
        self.notebook.connect("switch-page", self.on_tab_changed)

        self.connect("delete-event", self.on_window_close)
        self.show_all()

    def setup_window(self):
        """Configura el tamaño y posición de la ventana."""
        default_width, default_height = 1024, 768
        self.set_default_size(default_width, default_height)
        self.resize(self.settings.get('width', default_width), self.settings.get('height', default_height))
        if 'x' in self.settings and 'y' in self.settings:
            self.move(self.settings['x'], self.settings['y'])
        else:
            self.set_position(Gtk.WindowPosition.CENTER)

    def setup_header_bar_buttons(self):
        """Crea y conecta los botones de la barra de cabecera."""
        open_button = Gtk.Button(label="Abrir")
        open_button.set_image(Gtk.Image.new_from_icon_name("document-open-symbolic", Gtk.IconSize.BUTTON))
        open_button.connect("clicked", self.on_open_clicked)
        self.header_bar.pack_start(open_button)

        recent_menu = Gtk.Menu()
        self.recent_menu = recent_menu
        recent_button = Gtk.MenuButton(popup=recent_menu)
        recent_button.set_image(Gtk.Image.new_from_icon_name("open-recent-symbolic", Gtk.IconSize.BUTTON))
        recent_button.set_tooltip_text("Abrir un archivo reciente")
        self.header_bar.pack_start(recent_button)
        self.update_recent_menu()

        preview_button = Gtk.Button(label="Visualizar")
        preview_button.set_image(Gtk.Image.new_from_icon_name("view-preview-symbolic", Gtk.IconSize.BUTTON))
        preview_button.connect("clicked", lambda w: self.get_current_tab().on_preview_clicked(w))
        self.header_bar.pack_start(preview_button)

        export_button = Gtk.Button(label="Exportar")
        export_button.set_image(Gtk.Image.new_from_icon_name("document-save-as-symbolic", Gtk.IconSize.BUTTON))
        export_button.connect("clicked", lambda w: self.get_current_tab().on_export_to_text_clicked(w))
        self.header_bar.pack_start(export_button)

        save_button = Gtk.Button(label="Guardar")
        save_button.set_image(Gtk.Image.new_from_icon_name("document-save-symbolic", Gtk.IconSize.BUTTON))
        save_button.connect("clicked", lambda w: self.get_current_tab().on_save_clicked(w))
        self.header_bar.pack_end(save_button)


    def on_open_clicked(self, button):
        """Abre un diálogo para seleccionar y cargar un archivo EPUB en una nueva pestaña."""
        dialog = Gtk.FileChooserDialog(title="Selecciona un archivo EPUB", parent=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons("_Cancelar", Gtk.ResponseType.CANCEL, "_Abrir", Gtk.ResponseType.OK)
        file_filter = Gtk.FileFilter()
        file_filter.set_name("Archivos EPUB")
        file_filter.add_pattern("*.epub")
        dialog.add_filter(file_filter)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            self.create_new_tab(filepath)
        dialog.destroy()

    def create_new_tab(self, file_path):
        """Crea y añade una nueva pestaña para el archivo dado."""
        if not os.path.exists(file_path):
            self.show_error_dialog(f"El archivo '{os.path.basename(file_path)}' ya no existe.")
            self.recent_manager.remove(file_path)
            self.update_recent_menu()
            return
            
        for tab_instance in self.tabs.values():
            if tab_instance.get_current_path() == file_path:
                page_num = self.notebook.page_num(tab_instance.main_box)
                self.notebook.set_current_page(page_num)
                return

        editor_tab = EditorTab(self, self.settings, file_path)
        if editor_tab.is_book_loaded():
            self.notebook.append_page(editor_tab.main_box, editor_tab.get_tab_label_box())
            
            self.tabs[editor_tab.main_box] = editor_tab
            
            GLib.idle_add(lambda: self.notebook.set_current_page(self.notebook.get_n_pages() - 1))

            self.notebook.show_all()
            
            self.recent_manager.add(file_path)
            self.update_recent_menu()

    def close_tab(self, editor_tab):
        """Cierra una pestaña, preguntando si guardar si hay cambios.
           Devuelve True si la pestaña se cerró, False si el usuario canceló."""
        if editor_tab.is_dirty():
            dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                message_type=Gtk.MessageType.QUESTION,
                text=f"¿Guardar los cambios de \"{os.path.basename(editor_tab.current_path)}\" antes de cerrar?",
                secondary_text="Si no los guardas, los cambios se perderán."
            )
            dialog.add_buttons("_Guardar", Gtk.ResponseType.YES, "_No Guardar", Gtk.ResponseType.NO, "_Cancelar", Gtk.ResponseType.CANCEL)
            
            response = dialog.run()
            dialog.destroy()

            if response == Gtk.ResponseType.YES:
                editor_tab.on_save_clicked(None)
            elif response == Gtk.ResponseType.NO:
                pass
            else:
                return False

        # Si la pestaña que se cierra era la activa, la "desactivamos"
        if self.active_tab == editor_tab:
            self.active_tab = None

        editor_tab.destroy()
        
        page_widget = editor_tab.main_box
        page_num = self.notebook.page_num(page_widget)
        
        if page_num != -1:
            self.notebook.remove_page(page_num)
        
        if page_widget in self.tabs:
            del self.tabs[page_widget]

        if self.notebook.get_n_pages() == 0:
            self.header_bar.props.title = "Gutenia"
            self.header_bar.props.subtitle = ""
        
        return True

    def get_current_tab(self):
        """Devuelve la instancia de EditorTab activa."""
        page_num = self.notebook.get_current_page()
        if page_num >= 0:
            current_page_widget = self.notebook.get_nth_page(page_num)
            return self.tabs.get(current_page_widget)
        return None
        

    def on_tab_changed(self, notebook, page, page_num):
        """Actualiza el estilo de las pestañas (activa/inactiva) y el título de la ventana."""
        print(f"Cambiando a la pestaña {page_num} con widget {page}")
        new_active_tab = self.tabs.get(page)

        if new_active_tab == self.active_tab:
            return  # Ya es la pestaña activa, no hacer 
        
        # 1. Quitar negrita de la pestaña ANTERIOR
        if self.active_tab is not None:
            self.active_tab.set_active_style(False)

        # 2. Poner negrita en la pestaña NUEVA
        new_active_tab = self.tabs.get(page)
        if new_active_tab is not None:
            new_active_tab.set_active_style(True)
            new_active_tab.update_window_title()

        # 3. Actualizar la referencia a la pestaña activa
        self.active_tab = new_active_tab


    def on_window_close(self, widget, event):
        """Maneja el evento de cierre de la ventana, revisando pestañas con cambios."""
        for tab in list(self.tabs.values()):
            if not self.close_tab(tab):
                return True

        current_tab = self.active_tab # Usar la referencia guardada
        if current_tab:
            paned_pos = current_tab.main_paned.get_position()
            self.settings['paned_position'] = paned_pos

        width, height = self.get_size()
        x, y = self.get_position()
        self.settings.update({'width': width, 'height': height, 'x': x, 'y': y})
        self.settings_manager.save(self.settings)
        
        return False

    def update_recent_menu(self):
        """Actualiza el menú de archivos recientes."""
        for child in self.recent_menu.get_children():
            self.recent_menu.remove(child)
            
        recent_files = self.recent_manager.get_files()
        if not recent_files:
            self.recent_menu.append(Gtk.MenuItem(label="No hay archivos recientes", sensitive=False))
        else:
            for path in recent_files:
                item = Gtk.MenuItem(label=os.path.basename(path))
                item.connect("activate", lambda w, p=path: self.create_new_tab(p))
                self.recent_menu.append(item)
        self.recent_menu.show_all()

    def toggle_search_bar(self):
        """Muestra/Oculta la barra de búsqueda para la pestaña actual."""
        current_tab = self.get_current_tab()
        if current_tab:
            current_tab.toggle_search_bar()

    def show_error_dialog(self, message, secondary_text=""):
        dialog = Gtk.MessageDialog(transient_for=self, modal=True,
                                   message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.CLOSE,
                                   text=message, secondary_text=secondary_text)
        dialog.run()
        dialog.destroy()


class GuteniaApp(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="org.gutenia.editor", **kwargs)
        self.window = None
        find_action = Gio.SimpleAction.new("find", None)
        find_action.connect("activate", self.on_find_action)
        self.add_action(find_action)
        self.set_accels_for_action("app.find", ["<Control>F"])

    def do_activate(self):
        if not self.window:
            self.window = GuteniaWindow(application=self, title="Gutenia")
        self.window.present()

    def on_find_action(self, action, param):
        """Se activa con Ctrl+F y delega a la ventana activa."""
        active_window = self.get_active_window()
        if active_window:
            active_window.toggle_search_bar()

if __name__ == "__main__":
    app = GuteniaApp()
    sys.exit(app.run(sys.argv))

# export GOOGLE_API_KEY="AIzaSyCM1n0DGPSIWH_bVsuEVEU-KRS1Z-7Rrbk"