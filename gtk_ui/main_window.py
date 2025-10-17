"""
ui/main_window.py
Ventana principal de Guten.AI - Coordina todos los componentes
"""
from . import *

from gi.repository import Gtk, Adw, Gio
import os
from pathlib import Path
from typing import Optional

# Importar componentes
from .sidebar_left import SidebarLeft
from .sidebar_right import SidebarRight  
from .central_editor import CentralEditor
from .actions import ActionManager
from .dialogs import DialogManager

# Importar core
from core.guten_core import GutenCore


class GutenAIWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Estado de la aplicación
        self.core: Optional[GutenCore] = None
        self.current_resource: Optional[str] = None
        
        # Configuración básica
        self.set_default_size(1400, 900)
        self.set_title("Guten.AI - EPUB Editor")
        
        # Establecer ícono si está disponible
        try:
            self.set_icon_name("gutenai")
        except:
            pass
        
        # Crear componentes
        self._create_components()
        
        # Configurar interfaz
        self._setup_ui()
        
        # Configurar acciones
        self._setup_actions()
    
    def _create_components(self):
        """Crea todos los componentes de la interfaz"""
        
        # Gestores de funcionalidad
        self.action_manager = ActionManager(self)
        self.dialog_manager = DialogManager(self)
        
        # Componentes de interfaz
        self.sidebar_left = SidebarLeft(self)
        self.sidebar_right = SidebarRight(self)
        self.central_editor = CentralEditor(self)
    
    def _setup_ui(self):
        """Configura el layout principal de la interfaz"""
        
        # HeaderBar
        self.header_bar = Adw.HeaderBar()
        self._setup_headerbar()
        
        # Toast overlay para mensajes
        self.toast_overlay = Adw.ToastOverlay()
        
        # Layout principal con 3 paneles
        self.main_overlay = Adw.OverlaySplitView()
        self.toast_overlay.set_child(self.main_overlay)
        
        # Panel principal (centro + derecha)
        self.content_split = Adw.OverlaySplitView()
        self.content_split.set_sidebar_position(Gtk.PackType.END)
        self.main_overlay.set_content(self.content_split)
        
        # Conectar componentes al layout
        self.main_overlay.set_sidebar(self.sidebar_left.get_widget())
        self.content_split.set_content(self.central_editor.get_widget())
        self.content_split.set_sidebar(self.sidebar_right.get_widget())
        
        # ToolbarView principal
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(self.header_bar)
        toolbar_view.set_content(self.toast_overlay)
        self.set_content(toolbar_view)
        
        # Conectar toggles de sidebars
        self.left_sidebar_btn.connect('toggled', self._on_left_sidebar_toggle)
        self.right_sidebar_btn.connect('toggled', self._on_right_sidebar_toggle)
    
    def _setup_headerbar(self):
        """Configura la barra de herramientas superior"""
        
        # Título dual (libro + recurso)
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
        
        # Botón sidebar izquierdo
        self.left_sidebar_btn = Gtk.ToggleButton()
        self.left_sidebar_btn.set_icon_name("sidebar-show-symbolic")
        self.left_sidebar_btn.set_tooltip_text("Mostrar/ocultar estructura")
        self.left_sidebar_btn.set_active(True)
        self.header_bar.pack_start(self.left_sidebar_btn)
        
        # Botón sidebar derecho
        self.right_sidebar_btn = Gtk.ToggleButton()
        self.right_sidebar_btn.set_icon_name("view-reveal-symbolic")
        self.right_sidebar_btn.set_tooltip_text("Mostrar/ocultar previsualización")
        self.right_sidebar_btn.set_active(True)
        self.header_bar.pack_end(self.right_sidebar_btn)
        
        # Menú principal
        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("open-menu-symbolic")
        menu_btn.set_menu_model(self._create_main_menu())
        self.header_bar.pack_end(menu_btn)
    
    def _create_main_menu(self):
        """Crea el modelo del menú principal"""
        menu = Gio.Menu()
        
        # Sección de archivo
        file_section = Gio.Menu()
        file_section.append("Abrir EPUB", "win.open_epub")
        file_section.append("Abrir carpeta proyecto", "win.open_folder")
        file_section.append("Nuevo proyecto", "win.new_project")
        file_section.append("Exportar EPUB", "win.export_epub")
        file_section.append("Exportar a texto", "win.export_text")
        menu.append_section(None, file_section)
        
        # Sección de configuración
        config_section = Gio.Menu()
        config_section.append("Preferencias", "win.preferences")
        menu.append_section(None, config_section)
        
        return menu
    
    def _setup_actions(self):
        """Configura todas las acciones de la aplicación"""
        self.action_manager.setup_actions()
    
    # Métodos para comunicación entre componentes
    def set_current_resource(self, href: str, name: str):
        """Establece el recurso actual - VERSIÓN SEGURA"""
    
        # Guardar recurso actual si hay cambios
        if (self.current_resource and 
            self.current_resource != href and 
            hasattr(self.central_editor, 'has_unsaved_changes') and
            self.central_editor.has_unsaved_changes()):
            
            try:
                self.central_editor.force_save()
                self.show_info(f"Guardado: {Path(self.current_resource).name}")
            except Exception as e:
                self.show_error(f"Error guardando: {e}")
        
        # Cambiar recurso
        self.current_resource = href
        self.resource_title.set_text(f"Recurso: {name}")
        
        # Cargar nuevo recurso
        self.central_editor.load_resource(href)
        self.sidebar_right.update_preview()
    
    def update_book_title(self, title: str):
        """Actualiza el título del libro en la headerbar"""
        self.book_title.set_text(title)
    
    def refresh_structure(self):
        """Refresca la estructura del EPUB en el sidebar izquierdo"""
        self.sidebar_left.populate_tree()
    
    # Toggle de sidebars
    def _on_left_sidebar_toggle(self, button):
        """Toggle del sidebar izquierdo"""
        self.main_overlay.set_show_sidebar(button.get_active())
    
    def _on_right_sidebar_toggle(self, button):
        """Toggle del sidebar derecho"""
        self.content_split.set_show_sidebar(button.get_active())
    
    # Métodos de utilidad para mensajes
    def show_error(self, message: str):
        """Muestra un mensaje de error"""
        toast = Adw.Toast()
        toast.set_title(message)
        toast.set_timeout(5)
        self.toast_overlay.add_toast(toast)
    
    def show_info(self, message: str):
        """Muestra un mensaje informativo"""
        toast = Adw.Toast()
        toast.set_title(message)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)
    
    def do_close_request(self):
        """Limpieza al cerrar la aplicación"""
        # Notificar a componentes para limpieza
        self.sidebar_right.cleanup()
        return False

    def on_window_close(self):
        """Al cerrar ventana, forzar guardado final"""
        if hasattr(self.central_editor, 'force_save'):
            self.central_editor.force_save()
            

class GutenAIApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.example.gutenai")
                
        # *** CONFIGURACIÓN PARA GNOME ***
        self.set_resource_base_path("/com/example/gutenai")
        
        # Configurar propiedades de la aplicación
        try:
            # Establecer nombre de clase para window manager
            import gi
            gi.require_version('Gdk', '4.0')
            from gi.repository import Gdk
            
            # Esto ayuda a GNOME a identificar la aplicación
            display = Gdk.Display.get_default()
            if display:
                display.set_cursor_theme("default", 24)
                
        except Exception as e:
            print(f"[WARNING] Could not set display properties: {e}")
        
        self.connect('activate', self._on_activate)
    
    def _on_activate(self, app):
        """Crea la ventana principal"""
        win = GutenAIWindow(application=app)
                # *** CONFIGURAR PROPIEDADES DE VENTANA PARA GNOME ***
        win.set_title("Guten.AI")
        
        # Establecer clase de ventana (importante para GNOME)
        try:
            # Esto es lo más importante para que GNOME reconozca la app
            win.set_wmclass("gutenai", "gutenai")
        except:
            pass
        
        # Establecer ícono de ventana si está disponible
        try:
            win.set_icon_name("gutenai")
        except:
            try:
                win.set_default_icon_name("gutenai")
            except:
                pass
        win.present()