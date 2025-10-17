"""
ui/sidebar_right.py
Sidebar derecho - Previsualización WebKit y ventana fullscreen
"""
from . import *
from gi.repository import Gtk, Adw, WebKit, GLib
import os
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .main_window import GutenAIWindow


class SidebarRight:
    """Maneja el sidebar derecho con la previsualización"""
    
    def __init__(self, main_window: 'GutenAIWindow'):
        self.main_window = main_window
        self.temp_preview_file: Optional[str] = None
        self.fullscreen_window: Optional[Adw.Window] = None
        
        self._setup_widget()
    
    def _setup_widget(self):
        """Configura el widget principal del sidebar"""
        
        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.sidebar_box.set_size_request(400, -1)
        
        # Header del sidebar
        self._setup_header()
        
        # WebView para previsualización
        self._setup_webview()
    
    def _setup_header(self):
        """Configura el header del sidebar"""
        
        sidebar_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        sidebar_header.set_margin_top(12)
        sidebar_header.set_margin_bottom(12)
        sidebar_header.set_margin_start(12)
        sidebar_header.set_margin_end(12)
        
        sidebar_title = Gtk.Label()
        sidebar_title.set_text("Previsualización")
        sidebar_title.add_css_class("heading")
        sidebar_header.append(sidebar_title)
        
        # Botón para pantalla completa
        fullscreen_btn = Gtk.Button()
        fullscreen_btn.set_icon_name("view-fullscreen-symbolic")
        fullscreen_btn.set_tooltip_text("Abrir previsualización en ventana independiente")
        fullscreen_btn.add_css_class("flat")
        fullscreen_btn.connect('clicked', self._on_fullscreen_preview)
        sidebar_header.append(fullscreen_btn)
        
        self.sidebar_box.append(sidebar_header)
    
    def _setup_webview(self):
        """Configura el WebView para previsualización"""
        
        self.web_view = WebKit.WebView()
        
        web_scroll = Gtk.ScrolledWindow()
        web_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        web_scroll.set_child(self.web_view)
        web_scroll.set_vexpand(True)
        
        self.sidebar_box.append(web_scroll)
    
    def get_widget(self) -> Gtk.Widget:
        """Retorna el widget principal del sidebar"""
        return self.sidebar_box
    
    def update_preview(self):
        """Actualiza la previsualización con el recurso actual"""
        if not self.main_window.core or not self.main_window.current_resource:
            self.web_view.load_html("", None)
            return
        
        # Solo previsualizar documentos HTML
        if not self.main_window.current_resource.endswith(('.html', '.xhtml', '.htm')):
            self.web_view.load_html("<p>Este tipo de archivo no se puede previsualizar.</p>", None)
            return
        
        try:
            content = self.main_window.core.read_text(self.main_window.current_resource)
            self._update_preview_content(content, self.main_window.current_resource)
        except Exception as e:
            error_html = f"<h1>Error</h1><p>No se pudo cargar el contenido: {e}</p>"
            self.web_view.load_html(error_html, None)
    
    def _update_preview_content(self, html_content: str, href: str):
        """Preview seguro usando archivo dedicado SOLO para preview"""
        try:
            # Crear archivo de preview dedicado (no sobreescribir el original)
            preview_file_path = self._get_preview_file_path(href)
            
            # Escribir contenido al archivo de preview
            preview_file_path.write_text(html_content, encoding='utf-8')
            
            # Cargar desde archivo de preview
            file_uri = preview_file_path.as_uri()
            self.web_view.load_uri(file_uri)
            
            # Sincronizar con fullscreen si está activo
            if self._is_fullscreen_active():
                self.fullscreen_web_view.load_uri(file_uri)
                
        except Exception as e:
            # Fallback: HTML inline
            error_msg = f"<p>Error en preview: {e}</p>"
            self.web_view.load_html(error_msg, None)

    def _get_preview_file_path(self, href: str) -> Path:
        """Genera ruta para archivo de preview dedicado"""
        
        # Crear archivo paralelo con sufijo _preview
        original_path = Path(href)
        preview_name = f"{original_path.stem}_preview{original_path.suffix}"
        
        # Mismo directorio que el original para que las rutas relativas funcionen
        preview_path = (self.main_window.core.opf_dir / original_path.parent / preview_name).resolve()
        
        # Asegurar que el directorio existe
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        
        return preview_path
    
    def _update_preview_fallback(self, html_content: str, original_error: Exception):
        """Método fallback usando archivo temporal"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(html_content)
                temp_path = f.name
            
            # Limpiar archivo temporal anterior
            if self.temp_preview_file and os.path.exists(self.temp_preview_file):
                os.unlink(self.temp_preview_file)
            
            self.temp_preview_file = temp_path
            file_uri = Path(temp_path).as_uri()
            self.web_view.load_uri(file_uri)
            
            # Sincronizar con pantalla completa
            if self._is_fullscreen_active():
                self.fullscreen_web_view.load_uri(file_uri)
                
        except Exception as e2:
            error_msg = f"<p>Error en preview: {original_error}<br>Fallback error: {e2}</p>"
            self.web_view.load_html(error_msg, None)
            
            if self._is_fullscreen_active():
                self.fullscreen_web_view.load_uri(file_uri)
    
    def _on_fullscreen_preview(self, button):
        """Abre la previsualización en una ventana independiente"""
        if not self.main_window.core or not self.main_window.current_resource:
            self.main_window.show_error("No hay contenido para mostrar en pantalla completa")
            return
        
        # Si ya existe una ventana, traerla al frente
        if self._is_fullscreen_active():
            self.fullscreen_window.present()
            return
        
        self._create_fullscreen_window()
    
    def _create_fullscreen_window(self):
        """Crea la ventana de previsualización fullscreen"""
        self.fullscreen_window = Adw.Window()
        self.fullscreen_window.set_title("Previsualización - Guten.AI")
        self.fullscreen_window.set_default_size(1000, 700)
        self.fullscreen_window.set_transient_for(self.main_window)
        
        # Header bar
        preview_headerbar = Adw.HeaderBar()
        preview_title = self._get_preview_title()
        preview_headerbar.set_title_widget(Gtk.Label(label=preview_title))
        
        # Botones del header
        self._setup_fullscreen_buttons(preview_headerbar)
        
        # WebView independiente
        self.fullscreen_web_view = WebKit.WebView()
        
        web_scroll = Gtk.ScrolledWindow()
        web_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        web_scroll.set_child(self.fullscreen_web_view)
        web_scroll.set_vexpand(True)
        web_scroll.set_hexpand(True)
        
        # Layout de la ventana
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(preview_headerbar)
        toolbar_view.set_content(web_scroll)
        self.fullscreen_window.set_content(toolbar_view)
        
        # Sincronizar contenido inicial
        self._sync_fullscreen_content()
        
        # Conectar evento de cierre
        self.fullscreen_window.connect('destroy', self._on_fullscreen_destroyed)
        
        # Mostrar ventana
        self.fullscreen_window.present()
    
    def _setup_fullscreen_buttons(self, headerbar: Adw.HeaderBar):
        """Configura los botones del header de la ventana fullscreen"""
        
        # Botón cerrar
        close_btn = Gtk.Button()
        close_btn.set_icon_name("window-close-symbolic")
        close_btn.set_tooltip_text("Cerrar ventana de previsualización")
        close_btn.connect('clicked', lambda btn: self.fullscreen_window.destroy())
        headerbar.pack_end(close_btn)
        
        # Botón recargar
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Recargar previsualización")
        refresh_btn.connect('clicked', self._on_refresh_fullscreen)
        headerbar.pack_end(refresh_btn)
        
        # Botón navegador externo
        external_btn = Gtk.Button()
        external_btn.set_icon_name("web-browser-symbolic")
        external_btn.set_tooltip_text("Abrir en navegador externo")
        external_btn.connect('clicked', self._on_open_external)
        headerbar.pack_start(external_btn)
    
    def _get_preview_title(self) -> str:
        """Obtiene el título para la ventana de previsualización"""
        if self.main_window.current_resource:
            try:
                mi = self.main_window.core._get_item(self.main_window.current_resource)
                return f"Vista previa: {Path(mi.href).name}"
            except:
                pass
        return "Vista previa"
    
    def _sync_fullscreen_content(self):
        """Sincroniza el contenido del WebView principal con el fullscreen"""
        if not self._is_fullscreen_active():
            return
        
        if not self.main_window.core or not self.main_window.current_resource:
            self.fullscreen_web_view.load_html("<h1>Sin contenido</h1><p>No hay documento seleccionado para mostrar.</p>", None)
            return
        
        try:
            # Obtener la URI actual del WebView principal
            main_uri = self.web_view.get_uri()
            if main_uri:
                # Cargar la misma URI en el WebView de pantalla completa
                self.fullscreen_web_view.load_uri(main_uri)
            else:
                # Fallback: cargar el HTML actual del recurso
                content = self.main_window.core.read_text(self.main_window.current_resource)
                self._update_fullscreen_content(content)
                
        except Exception as e:
            error_html = f"<h1>Error</h1><p>No se pudo cargar el contenido: {e}</p>"
            self.fullscreen_web_view.load_html(error_html, None)
    
    def _update_fullscreen_content(self, html_content: str):
        """Actualiza fullscreen usando archivo de preview dedicado"""
        if not self._is_fullscreen_active() or not self.main_window.current_resource:
            return
        
        try:
            preview_file_path = self._get_preview_file_path(self.main_window.current_resource)
            preview_file_path.write_text(html_content, encoding='utf-8')
            
            file_uri = preview_file_path.as_uri()
            self.fullscreen_web_view.load_uri(file_uri)
            
        except Exception as e:
            self.fullscreen_web_view.load_html(f"<h1>Error en fullscreen</h1><p>{e}</p>", None)
    
    def cleanup(self):
        """Limpia recursos incluyendo archivos de preview"""
        
        # Limpiar archivos temporales normales
        if self.temp_preview_file and os.path.exists(self.temp_preview_file):
            os.unlink(self.temp_preview_file)
        
        # Limpiar archivos de preview dedicados
        if self.main_window.core:
            try:
                # Buscar archivos *_preview.* en todo el proyecto
                for preview_file in self.main_window.core.opf_dir.rglob("*_preview.*"):
                    if preview_file.is_file():
                        try:
                            preview_file.unlink()
                            print(f"[CLEANUP] Removed preview file: {preview_file}")
                        except:
                            pass
            except:
                pass
        
        if self.fullscreen_window:
            self.fullscreen_window.destroy()
    def _on_refresh_fullscreen(self, button):
        """Recarga la previsualización fullscreen"""
        self._sync_fullscreen_content()
    
    def _on_open_external(self, button):
        """Abre el archivo HTML en navegador externo"""
        if not self.main_window.core or not self.main_window.current_resource:
            self.main_window.show_error("No hay documento para abrir")
            return
        
        try:
            html_file_path = (self.main_window.core.opf_dir / self.main_window.current_resource).resolve()
            
            if not html_file_path.exists():
                self.main_window.show_error("El archivo no existe en disco")
                return
            
            file_uri = html_file_path.as_uri()
            
            # Intentar abrir según el sistema
            try:
                subprocess.run(['xdg-open', file_uri], check=True)  # Linux
            except (subprocess.CalledProcessError, FileNotFoundError):
                try:
                    subprocess.run(['open', file_uri], check=True)  # macOS
                except (subprocess.CalledProcessError, FileNotFoundError):
                    try:
                        os.startfile(file_uri)  # Windows
                    except (OSError, AttributeError):
                        self.main_window.show_error("No se pudo abrir el navegador externo")
                        return
            
            self.main_window.show_info("Archivo abierto en navegador externo")
            
        except Exception as e:
            self.main_window.show_error(f"Error abriendo en navegador externo: {e}")
    
    def _on_fullscreen_destroyed(self, window):
        """Limpia referencias cuando se destruye la ventana fullscreen"""
        self.fullscreen_window = None
        if hasattr(self, 'fullscreen_web_view'):
            delattr(self, 'fullscreen_web_view')
    
    def _is_fullscreen_active(self) -> bool:
        """Verifica si la ventana fullscreen está activa"""
        return (self.fullscreen_window is not None and 
                hasattr(self, 'fullscreen_web_view'))
    
    def cleanup(self):
        """Limpia recursos al cerrar la aplicación"""
        if self.temp_preview_file and os.path.exists(self.temp_preview_file):
            os.unlink(self.temp_preview_file)
        
        if self.fullscreen_window:
            self.fullscreen_window.destroy()