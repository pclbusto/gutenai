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
from .about_dialog import AboutDialog

# Importar core
from core.guten_core import GutenCore


class GutenAIWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Estado de la aplicación
        self.core: Optional[GutenCore] = None
        self.current_resource: Optional[str] = None
        self.original_epub_path: Optional[Path] = None  # Para guardar cambios al cerrar
        self.temp_workdir: Optional[Path] = None  # Directorio temporal para EPUBs abiertos
        self.is_new_project: bool = False  # True si es nuevo proyecto, False si es EPUB abierto

        # Configuración básica
        self.set_default_size(1400, 900)
        self.set_title("GutenAI - EPUB Editor")

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

        # Conectar señal de cierre
        self.connect('close-request', self._on_close_request)
    
    def _create_components(self):
        """Crea todos los componentes de la interfaz"""
        
        # Gestores de funcionalidad
        self.action_manager = ActionManager(self)
        self.dialog_manager = DialogManager(self)
        
        # Configurar overlay de ayuda (F1)
        from .shortcuts_window import create_shortcuts_window
        print("[DEBUG] Creando help overlay...")
        help_overlay = create_shortcuts_window(self)
        if help_overlay:
            print("[DEBUG] Estableciendo help overlay en la ventana")
            self.set_help_overlay(help_overlay)
        else:
            print("[DEBUG] No se pudo crear help overlay")

        # Diálogo About
        self.about_dialog = AboutDialog(self)

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

        # Sección de herramientas
        tools_section = Gio.Menu()
        tools_section.append("Buscar en documento", "win.search_in_document")
        tools_section.append("Buscar y reemplazar", "win.search_and_replace")
        tools_section.append("Buscar y reemplazar en todo el libro", "win.global_search_replace")
        tools_section.append("Renombrado en lote", "win.batch_rename")
        tools_section.append("Estadísticas del capítulo actual", "win.show_current_chapter_statistics")
        tools_section.append("Estadísticas del libro completo", "win.show_statistics")
        tools_section.append("Generar tabla de contenidos", "win.generate_nav")
        tools_section.append("Validar EPUB", "win.validate_epub")
        tools_section.append("Recargar previsualización", "win.reload_webkit")
        menu.append_section(None, tools_section)

        # Sección de configuración
        config_section = Gio.Menu()
        config_section.append("Preferencias", "win.preferences")
        menu.append_section(None, config_section)

        # Sección de ayuda
        help_section = Gio.Menu()
        help_section.append("Acerca de", "win.about")
        menu.append_section(None, help_section)
        
        return menu
    
    def _setup_actions(self):
        """Configura todas las acciones de la aplicación"""
        self.action_manager.setup_actions()
        self._setup_keyboard_handlers()

    def _setup_keyboard_handlers(self):
        """Configura manejadores de teclado a nivel de ventana"""
        from gi.repository import Gdk

        # Crear controlador de eventos de teclado
        key_controller = Gtk.EventControllerKey()
        key_controller.connect('key-pressed', self._on_key_pressed)
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.add_controller(key_controller)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Maneja eventos de teclado a nivel de ventana"""
        from gi.repository import Gdk

        # Verificar modificadores
        ctrl = state & Gdk.ModifierType.CONTROL_MASK
        shift = state & Gdk.ModifierType.SHIFT_MASK

        # Ctrl+F - Búsqueda (solo búsqueda, sin reemplazo)
        if ctrl and not shift and keyval == Gdk.KEY_f:
            if hasattr(self, 'central_editor') and self.central_editor:
                self.central_editor.show_search_panel(show_replace=False)
                return True  # Interceptar el evento

        # Ctrl+H - Búsqueda y reemplazo
        elif ctrl and not shift and keyval == Gdk.KEY_h:
            if hasattr(self, 'central_editor') and self.central_editor:
                self.central_editor.show_search_replace_panel()
                return True  # Interceptar el evento

        # Ctrl+Shift+1 - Toggle sidebar izquierdo
        elif ctrl and shift and keyval == Gdk.KEY_1:
            if hasattr(self, 'left_sidebar_btn'):
                self.left_sidebar_btn.set_active(not self.left_sidebar_btn.get_active())
                return True

        # Ctrl+Shift+2 - Toggle sidebar derecho
        elif ctrl and shift and keyval == Gdk.KEY_2:
            if hasattr(self, 'right_sidebar_btn'):
                self.right_sidebar_btn.set_active(not self.right_sidebar_btn.get_active())
                return True

        # Ctrl+S - Guardar
        elif ctrl and keyval == Gdk.KEY_s:
            if hasattr(self, 'central_editor') and self.central_editor:
                self.central_editor.force_save()
                return True

        # F1 - Mostrar atajos
        # Manejado automáticamente por set_help_overlay
        # elif keyval == Gdk.KEY_F1:
        #     self.action_manager._on_show_shortcuts(None, None)
        #     return True

        return False  # Permitir que el evento continúe

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
    
    def _on_close_request(self, window):
        """Intercepta el cierre para preguntar si guardar cambios"""
        # Si no hay proyecto abierto, cerrar directamente
        if not self.core:
            self.sidebar_right.cleanup()
            self._cleanup_temp_dir()
            return False  # Permitir cierre

        # Si es un nuevo proyecto (persistente), solo cerrar
        if self.is_new_project:
            self.sidebar_right.cleanup()
            return False  # Permitir cierre

        # Si es un EPUB abierto (temporal), preguntar si guardar
        if self.original_epub_path:
            # Mostrar diálogo de confirmación
            dialog = Adw.MessageDialog(transient_for=self, modal=True)
            dialog.set_heading("Guardar cambios antes de cerrar")
            dialog.set_body("¿Deseas guardar los cambios en el EPUB antes de cerrar?")

            dialog.add_response("cancel", "Cancelar")
            dialog.add_response("no", "No guardar")
            dialog.add_response("yes", "Guardar")

            dialog.set_response_appearance("yes", Adw.ResponseAppearance.SUGGESTED)
            dialog.set_default_response("yes")
            dialog.set_close_response("cancel")

            def on_response(dlg, response):
                if response == "yes":
                    # Guardar y cerrar
                    self._save_and_close()
                elif response == "no":
                    # Cerrar sin guardar (limpiar temporal)
                    self.sidebar_right.cleanup()
                    self._cleanup_temp_dir()
                    self.destroy()
                # Si response == "cancel", no hacer nada (no cerrar)

            dialog.connect("response", on_response)
            dialog.present()

            return True  # Prevenir cierre automático, lo manejaremos nosotros

        # Fallback: cerrar directamente
        self.sidebar_right.cleanup()
        self._cleanup_temp_dir()
        return False

    def _cleanup_temp_dir(self):
        """Limpia el directorio temporal si existe"""
        import shutil

        if self.temp_workdir and self.temp_workdir.exists():
            try:
                print(f"[Cleanup] Eliminando carpeta temporal: {self.temp_workdir}")
                shutil.rmtree(self.temp_workdir)
                self.temp_workdir = None
            except Exception as e:
                print(f"[Cleanup] Error eliminando carpeta temporal: {e}")

    def _save_and_close(self):
        """Guarda el EPUB y cierra la aplicación"""
        try:
            print(f"[Close] Guardando cambios en {self.original_epub_path}")

            # Guardar cualquier cambio pendiente en el editor
            if hasattr(self.central_editor, 'force_save'):
                self.central_editor.force_save()

            # Exportar el EPUB
            self.core.export_epub(self.original_epub_path)

            print(f"[Close] EPUB guardado exitosamente")

            # Limpiar y cerrar
            self.sidebar_right.cleanup()
            self._cleanup_temp_dir()
            self.destroy()

        except Exception as e:
            print(f"[Close] Error guardando EPUB: {e}")
            import traceback
            traceback.print_exc()

            # Mostrar error al usuario
            error_dialog = Adw.MessageDialog(transient_for=self, modal=True)
            error_dialog.set_heading("Error al guardar")
            error_dialog.set_body(f"No se pudo guardar el EPUB:\n\n{str(e)}\n\n¿Cerrar sin guardar?")

            error_dialog.add_response("cancel", "Cancelar")
            error_dialog.add_response("close_anyway", "Cerrar sin guardar")

            error_dialog.set_response_appearance("close_anyway", Adw.ResponseAppearance.DESTRUCTIVE)
            error_dialog.set_default_response("cancel")
            error_dialog.set_close_response("cancel")

            def on_error_response(dlg, response):
                if response == "close_anyway":
                    self.sidebar_right.cleanup()
                    self._cleanup_temp_dir()
                    self.destroy()

            error_dialog.connect("response", on_error_response)
            error_dialog.present()

    def do_close_request(self):
        """Limpieza al cerrar la aplicación (fallback)"""
        # Este método se llama como fallback si no se previene el cierre
        self.sidebar_right.cleanup()
        return False

    def on_window_close(self):
        """Al cerrar ventana, forzar guardado final"""
        if hasattr(self.central_editor, 'force_save'):
            self.central_editor.force_save()
            

class GutenAIApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="gutenai.com")

        # Configuración básica de la aplicación
        self.set_flags(Gio.ApplicationFlags.DEFAULT_FLAGS)

        # Conectar signals en el orden correcto
        self.connect('startup', self._on_startup)
        self.connect('activate', self._on_activate)

    def _on_startup(self, app):
        """Inicialización de la aplicación"""
        # Establecer icono por defecto para toda la aplicación
        try:
            # En GTK4, solo configuramos el icono por defecto sin verificación previa
            # La verificación se hará en cada ventana individual
            print("Configurando icono por defecto de la aplicación a 'gutenai'")
            Gtk.Window.set_default_icon_name("gutenai.com")

        except Exception as e:
            print(f"Error configurando icono por defecto: {e}")
            Gtk.Window.set_default_icon_name("text-editor")
    
    def _on_activate(self, app):
        """Crea la ventana principal"""
        
        win = GutenAIWindow(application=app)

        # *** CONFIGURAR PROPIEDADES DE VENTANA PARA GNOME ***
        win.set_title("GutenAI")

        # Configurar icono de la ventana
        try:
            icon_theme = Gtk.IconTheme.get_for_display(win.get_display())
            if icon_theme.has_icon("gutenai.com"):
                print("Configurando icono de ventana a 'gutenai'")
                win.set_icon_name("gutenai.com")
            else:
                win.set_icon_name("text-editor")
        except Exception as e:
            print(f"Error configurando icono de ventana: {e}")
        win.present()