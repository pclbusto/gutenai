"""
ui/central_editor.py - Auto-guardado corregido
"""
from . import *

from gi.repository import Gtk, GtkSource, Gio, GLib
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from core.guten_core import KIND_DOCUMENT, KIND_STYLE

if TYPE_CHECKING:
    from .main_window import GutenAIWindow


class CentralEditor:
    """Maneja el editor central de código con funcionalidades de formato"""
    
    def __init__(self, main_window: 'GutenAIWindow'):
        self.main_window = main_window
        self.current_resource_type: Optional[str] = None
        
        # Estado del auto-guardado
        self._save_timeout = None
        self._last_saved_content = ""
        self._is_saving = False
        self._needs_save = False
        
        # Configuración del auto-guardado
        self.AUTOSAVE_DELAY = 1500  # 1.5 segundos (un poco más conservador)
        self.AUTOSAVE_INTERVAL = 5000  # Guardado forzado cada 5 segundos si hay cambios
        
        self._setup_widget()
        self._setup_editor_actions()
        self._setup_autosave_timer()

    def _setup_autosave_timer(self):
        """Configura timer de guardado forzado periódico"""
        GLib.timeout_add(self.AUTOSAVE_INTERVAL, self._periodic_save_check)

    def _setup_widget(self):
        """Configura el widget principal del editor"""
        
        # SourceView para el editor
        self.source_buffer = GtkSource.Buffer()
        self.source_view = GtkSource.View(buffer=self.source_buffer)
        
        # Configuración del editor
        self._configure_editor()
        
        # Menú contextual
        self._setup_context_menu()
        
        # ScrolledWindow container
        self.editor_scroll = Gtk.ScrolledWindow()
        self.editor_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.editor_scroll.set_child(self.source_view)
        self.editor_scroll.set_vexpand(True)
        self.editor_scroll.set_hexpand(True)
        
        # Conectar señales
        self.source_buffer.connect('changed', self._on_text_changed)
    
    def _on_text_changed(self, buffer):
        """Maneja cambios en el texto del editor con auto-guardado inteligente"""
        if not self.main_window.core or not self.main_window.current_resource:
            return
        
        # Marcar que hay cambios pendientes
        self._needs_save = True
        
        # Cancelar timeout anterior
        if self._save_timeout:
            GLib.source_remove(self._save_timeout)
        
        # Programar guardado - IMPORTANTE: NO pasar el texto como parámetro
        # para evitar race conditions, lo obtenemos en el momento del guardado
        if not self._is_saving:
            self._save_timeout = GLib.timeout_add(self.AUTOSAVE_DELAY, self._do_auto_save)
        
        # Actualizar preview inmediatamente (más responsive)
        if (self.current_resource_type == KIND_DOCUMENT and 
            self.main_window.current_resource.endswith(('.html', '.xhtml', '.htm'))):
            # Obtener texto actual para preview
            current_text = self.get_current_text()
            self.main_window.sidebar_right._update_preview_content(
                current_text, 
                self.main_window.current_resource
            )
    
    def _do_auto_save(self) -> bool:
        """Ejecuta el auto-guardado obteniendo el texto más reciente"""
        if not self.main_window.core or not self.main_window.current_resource:
            return False
        
        if self._is_saving:
            return False
        
        # Obtener el texto MÁS RECIENTE del buffer
        current_text = self.get_current_text()
        
        # Solo guardar si realmente cambió
        if current_text == self._last_saved_content:
            self._needs_save = False
            self._save_timeout = None
            return False
        
        try:
            self._is_saving = True
            
            # Guardar
            self.main_window.core.write_text(self.main_window.current_resource, current_text)
            
            
            # Actualizar estado
            self._last_saved_content = current_text
            self._needs_save = False
            
            # Indicador visual sutil
            self._show_save_indicator()
            
        except Exception as e:
            self.main_window.show_error(f"Error auto-guardando: {e}")
        finally:
            self._is_saving = False
            self._save_timeout = None
        
        return False  # No repetir el timeout
    
    def _periodic_save_check(self) -> bool:
        """Guardado forzado periódico si hay cambios pendientes"""
        if self._needs_save and not self._is_saving:
            current_text = self.get_current_text()
            if current_text != self._last_saved_content:
                self._do_auto_save()
        
        return True  # Continuar el timer periódico
    
    def force_save(self):
        """Fuerza el guardado inmediato"""
        if self._needs_save or self.get_current_text() != self._last_saved_content:
            self._do_auto_save()
    
    def has_unsaved_changes(self) -> bool:
        """Verifica si hay cambios sin guardar - CORREGIDO"""
        current_text = self.get_current_text()
        return current_text != self._last_saved_content
    
    def load_resource(self, href: str):
        """Carga un recurso en el editor"""
        if not self.main_window.core:
            return
        
        try:
            # Determinar tipo de recurso
            mi = self.main_window.core._get_item(href)
            self.current_resource_type = self._determine_resource_type(mi.media_type, href)
            
            if self.current_resource_type in [KIND_DOCUMENT, KIND_STYLE]:
                self._load_text_resource(href)
            else:
                self._load_non_text_resource(href)
                
        except Exception as e:
            self.main_window.show_error(f"Error cargando recurso: {e}")
        
        # Reset del estado de auto-guardado DESPUÉS de cargar
        self._reset_autosave_state()
    
    def _reset_autosave_state(self):
        """Resetea completamente el estado del auto-guardado"""
        # Cancelar cualquier guardado pendiente
        if self._save_timeout:
            GLib.source_remove(self._save_timeout)
            self._save_timeout = None
        
        # Reset estado
        self._needs_save = False
        self._is_saving = False
        
        # Actualizar contenido guardado al contenido actual
        # Lo hacemos con un pequeño delay para asegurar que el buffer esté listo
        GLib.timeout_add(100, self._update_last_saved_content)
    
    def _update_last_saved_content(self) -> bool:
        """Actualiza el contenido 'guardado' al contenido actual del buffer"""
        self._last_saved_content = self.get_current_text()
        return False  # No repetir
    
    def _show_save_indicator(self):
        """Muestra un indicador sutil de guardado"""
        original_title = self.main_window.resource_title.get_text()
        if not original_title.endswith(" ✓"):
            self.main_window.resource_title.set_text(f"{original_title} ✓")
            
            # Restaurar después de 800ms
            GLib.timeout_add(800, lambda: (
                self.main_window.resource_title.set_text(original_title.rstrip(" ✓")),
                False
            )[1])

    # === RESTO DE MÉTODOS SIN CAMBIOS ===
    
    def _configure_editor(self):
        """Configura las opciones del editor de código"""
        self.source_view.set_show_line_numbers(True)
        self.source_view.set_highlight_current_line(True)
        self.source_view.set_tab_width(2)
        self.source_view.set_insert_spaces_instead_of_tabs(True)
        self.source_view.set_auto_indent(True)
        self.source_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        
        # Agregar estas líneas para asegurar control total:
        self.source_buffer.set_modified(False)  # Reset flag modificado
        
        # Verificar si hay propiedades de auto-save
        print("Buffer properties:", dir(self.source_buffer))
        
        # Desactivar cualquier auto-guardado interno si existe
        if hasattr(self.source_buffer, 'set_auto_save'):
            self.source_buffer.set_auto_save(False)
            
        # Esquema de colores
        style_manager = GtkSource.StyleSchemeManager.get_default()
        scheme = style_manager.get_scheme('Adwaita-dark')
        if scheme:
            self.source_buffer.set_style_scheme(scheme)
    
    def _setup_context_menu(self):
        """Configura el menú contextual del editor"""
        
        menu_model = self._create_context_menu_model()
        self.source_view.set_extra_menu(menu_model)
        from .css_style_context_menu import integrate_dynamic_css_menu
        integrate_dynamic_css_menu(self)
        from .image_selector_dialog import integrate_image_selector_with_editor
        integrate_image_selector_with_editor(self)
        from .correction_modal import integrate_correction_modal_with_editor
        integrate_correction_modal_with_editor(self)

    
    def _create_context_menu_model(self):
        """Crea el modelo del menú contextual"""
        menu = Gio.Menu()
        
        # Sección de formato HTML
        format_section = Gio.Menu()
        format_section.append("Párrafo <p>", "win.wrap_paragraph")
        format_section.append("Encabezado H1", "win.wrap_h1")
        format_section.append("Encabezado H2", "win.wrap_h2")
        format_section.append("Encabezado H3", "win.wrap_h3")
        format_section.append("Cita <blockquote>", "win.wrap_blockquote")
        
        menu.append_section("Formato HTML", format_section)
        
        # Sección de gestión de estilos
        style_section = Gio.Menu()
        style_section.append("Vincular estilos CSS", "win.link_styles")

        menu.append_section("Estilos", style_section)

        # Sección de corrección con IA
        ai_section = Gio.Menu()
        ai_section.append("Corregir con IA", "win.ai_correction")

        menu.append_section("Inteligencia Artificial", ai_section)
        
        # # Sección de edición básica
        # edit_section = Gio.Menu()
        # edit_section.append("Cortar", "text.cut")
        # edit_section.append("Copiar", "text.copy")
        # edit_section.append("Pegar", "text.paste")
        # edit_section.append("Seleccionar todo", "text.select-all")
        
        # menu.append_section("Edición", edit_section)
        
        return menu
    
    def _setup_editor_actions(self):
        """Configura las acciones específicas del editor"""
        
        # Acción para párrafo
        wrap_paragraph_action = Gio.SimpleAction.new("wrap_paragraph", None)
        wrap_paragraph_action.connect("activate", self._on_wrap_paragraph)
        self.main_window.add_action(wrap_paragraph_action)
        
        # Acciones para encabezados
        for level in [1, 2, 3]:
            action = Gio.SimpleAction.new(f"wrap_h{level}", None)
            action.connect("activate", self._on_wrap_heading, level)
            self.main_window.add_action(action)
        
        # Acción para blockquote
        wrap_blockquote_action = Gio.SimpleAction.new("wrap_blockquote", None)
        wrap_blockquote_action.connect("activate", self._on_wrap_blockquote)
        self.main_window.add_action(wrap_blockquote_action)
        
        # Acción para vincular estilos
        link_styles_action = Gio.SimpleAction.new("link_styles", None)
        link_styles_action.connect("activate", self._on_link_styles)
        self.main_window.add_action(link_styles_action)
    
    def get_widget(self) -> Gtk.Widget:
        """Retorna el widget principal del editor"""
        return self.editor_scroll
    
    def _determine_resource_type(self, media_type: str, href: str) -> str:
        """Determina el tipo de recurso basado en media-type y extensión"""
        mt = (media_type or "").split(";")[0].strip().lower()
        ext = Path(href).suffix.lower()
        
        if mt in ("application/xhtml+xml", "text/html") or ext in (".xhtml", ".html", ".htm"):
            return KIND_DOCUMENT
        elif mt == "text/css" or ext == ".css":
            return KIND_STYLE
        else:
            return "other"
    
    def _load_text_resource(self, href: str):
        """Carga un recurso de texto editable"""
        content = self.main_window.core.read_text(href)
        
        # Configurar resaltado de sintaxis
        lang_manager = GtkSource.LanguageManager.get_default()
        if self.current_resource_type == KIND_DOCUMENT:
            language = lang_manager.get_language('html')
        elif self.current_resource_type == KIND_STYLE:
            language = lang_manager.get_language('css')
        else:
            language = lang_manager.get_language('xml')
        
        self.source_buffer.set_language(language)
        self.source_buffer.set_text(content)
        
        # Actualizar preview si es documento HTML
        if self.current_resource_type == KIND_DOCUMENT:
            self.main_window.sidebar_right.update_preview()
    
    def _load_non_text_resource(self, href: str):
        """Muestra información para recursos no editables"""
        info_text = f"Recurso: {href}\n"
        info_text += f"Tipo: {self.current_resource_type}\n\n"
        info_text += "Este tipo de recurso no es editable como texto."
        
        self.source_buffer.set_language(None)
        self.source_buffer.set_text(info_text)
        
        # Limpiar preview
        self.main_window.sidebar_right.web_view.load_html("", None)
    
    def get_current_text(self) -> str:
        """Obtiene el texto actual del editor"""
        return self.source_buffer.get_text(
            self.source_buffer.get_start_iter(),
            self.source_buffer.get_end_iter(),
            False
        )
    
    def set_text(self, text: str):
        """Establece el texto del editor"""
        self.source_buffer.set_text(text)

    # === MÉTODOS DE FORMATO ===
    
    def _on_wrap_paragraph(self, action, param):
        """Convierte la selección en párrafo(s) HTML"""
        self._wrap_selection_as_html()
    
    def _on_wrap_heading(self, action, param, level: int):
        """Convierte la selección en encabezado HTML"""
        self._wrap_selection(f"h{level}")
    
    def _on_wrap_blockquote(self, action, param):
        """Convierte la selección en cita HTML"""
        self._wrap_selection("blockquote")
    
    def _wrap_selection_as_html(self):
        """Convierte texto seleccionado a párrafos HTML usando el core"""
        buffer = self.source_buffer
        
        if not buffer.get_has_selection():
            self.main_window.show_error("Selecciona texto para aplicar formato")
            return
        
        # Obtener selección
        start, end = buffer.get_selection_bounds()
        selected_text = buffer.get_text(start, end, False)
        
        if not selected_text.strip():
            return
        
        try:
            # Usar el transformador del core para convertir texto plano a XHTML
            html_fragment = self.main_window.core.xform_plaintext_to_xhtml_fragment(
                selected_text,
                keep_single_newline_as_br=True,
                collapse_whitespace=True
            )
            
            # Reemplazar selección
            buffer.delete(start, end)
            buffer.insert(start, html_fragment)
            
            self._update_preview_after_edit()
            
        except Exception as e:
            self.main_window.show_error(f"Error aplicando formato: {e}")
    
    def _wrap_selection(self, tag: str):
        """Envuelve la selección con una etiqueta HTML específica"""
        buffer = self.source_buffer
        
        if not buffer.get_has_selection():
            self.main_window.show_error("Selecciona texto para aplicar formato")
            return
        
        # Obtener selección
        start, end = buffer.get_selection_bounds()
        selected_text = buffer.get_text(start, end, False).strip()
        
        if not selected_text:
            return
        
        # Crear texto envuelto
        wrapped_text = f"<{tag}>{selected_text}</{tag}>"
        
        # Reemplazar selección
        buffer.delete(start, end)
        buffer.insert(start, wrapped_text)
        
        self._update_preview_after_edit()
    
    def _update_preview_after_edit(self):
        """Actualiza la previsualización después de una edición"""
        if (self.current_resource_type == KIND_DOCUMENT and 
            hasattr(self, 'main_window') and 
            self.main_window.current_resource):
            
            full_text = self.get_current_text()
            self.main_window.sidebar_right._update_preview_content(
                full_text, 
                self.main_window.current_resource
            )
    
    def _on_link_styles(self, action, param):
        """Abre el diálogo para vincular estilos CSS"""
        if not self.main_window.core or not self.main_window.current_resource:
            self.main_window.show_error("No hay documento seleccionado")
            return
        
        # Verificar que es un documento HTML
        if self.current_resource_type != KIND_DOCUMENT:
            self.main_window.show_error("Solo se pueden vincular estilos a documentos HTML/XHTML")
            return
        
        try:
            # Verificar que el recurso actual es HTML
            mi = self.main_window.core._get_item(self.main_window.current_resource)
            mt = (mi.media_type or "").split(";")[0].strip().lower()
            ext = Path(mi.href).suffix.lower()
            
            is_html = (mt in ("application/xhtml+xml", "text/html") or 
                      ext in (".xhtml", ".html", ".htm"))
            
            if not is_html:
                self.main_window.show_error("Solo se pueden vincular estilos a documentos HTML/XHTML")
                return
            
            # Delegar al dialog manager
            self.main_window.dialog_manager.show_style_linking_dialog()
            
        except KeyError:
            self.main_window.show_error("Documento no encontrado en el manifest")