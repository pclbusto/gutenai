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

        # Estado de búsqueda
        self.search_visible = False
        self.current_search_text = ""
        self.search_results = []
        self.current_result_index = -1

        # Estado de sincronización
        self._sync_timeout = None
        self._last_sync_line = -1

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

        # Crear controladores de eventos antes del panel de búsqueda
        self.key_controller = Gtk.EventControllerKey()
        self.key_controller.connect('key-pressed', self._on_key_pressed)
        self.source_view.add_controller(self.key_controller)

        self.search_key_controller = Gtk.EventControllerKey()
        self.search_key_controller.connect('key-pressed', self._on_key_pressed)

        # Configurar panel de búsqueda
        self._setup_search_panel()

        # Contenedor principal que incluye editor + panel de búsqueda
        self.main_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.main_container.append(self.editor_scroll)
        self.main_container.append(self.search_overlay)

        # Conectar señales
        self.source_buffer.connect('changed', self._on_text_changed)
        self.source_buffer.connect('cursor-moved', self._on_cursor_moved)
    
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

            # Caso especial: guardar archivo OPF
            if self.current_resource_type == "opf" and self.main_window.core.opf_path:
                self.main_window.core.opf_path.write_text(current_text, encoding='utf-8')
                # Recargar el OPF en el core para actualizar metadatos
                self.main_window.core._parse_opf()
            else:
                # Guardar recurso normal
                self.main_window.core.write_text(self.main_window.current_resource, current_text)

            # Actualizar estado
            self._last_saved_content = current_text
            self._needs_save = False

            # Indicador visual sutil
            self._show_save_indicator()

            # NUEVO: Si estamos editando CSS, actualizar preview del HTML actual
            if self.current_resource_type == KIND_STYLE:
                self._refresh_html_preview_after_css_change()

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
            # Caso especial: archivo OPF (content.opf, package.opf, etc.)
            if href.endswith('.opf') and self.main_window.core.opf_path:
                if href == self.main_window.core.opf_path.name:
                    self._load_opf_file()
                    self._reset_autosave_state()
                    return

            # Determinar tipo de recurso normal
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

        # Sección de asistente IA
        ai_section = Gio.Menu()
        ai_section.append("Asistente IA", "win.ai_correction")

        menu.append_section("Inteligencia Artificial", ai_section)

        # Sección de gestión de documentos
        document_section = Gio.Menu()
        document_section.append("Dividir capítulo aquí", "win.split_chapter")

        menu.append_section("Documento", document_section)

        # # Sección de edición básica
        # edit_section = Gio.Menu()
        # edit_section.append("Cortar", "text.cut")
        # edit_section.append("Copiar", "text.copy")
        # edit_section.append("Pegar", "text.paste")
        # edit_section.append("Seleccionar todo", "text.select-all")

        # menu.append_section("Edición", edit_section)

        return menu

    def _setup_search_panel(self):
        """Configura el panel de búsqueda deslizable"""

        # Contenedor principal del panel de búsqueda
        self.search_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.search_panel.add_css_class("search-panel")
        self.search_panel.set_margin_start(12)
        self.search_panel.set_margin_end(12)
        self.search_panel.set_margin_top(6)
        self.search_panel.set_margin_bottom(6)

        # Fila principal de búsqueda
        search_main_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Campo de búsqueda
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Buscar en el documento...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect('search-changed', self._on_search_changed)
        self.search_entry.connect('activate', self._on_search_next)
        self.search_entry.add_controller(self.search_key_controller)
        search_main_row.append(self.search_entry)

        # Botones de navegación
        self.prev_button = Gtk.Button()
        self.prev_button.set_icon_name("go-up-symbolic")
        self.prev_button.set_tooltip_text("Resultado anterior (Shift+F3)")
        self.prev_button.connect('clicked', self._on_search_prev)
        self.prev_button.set_sensitive(False)
        search_main_row.append(self.prev_button)

        self.next_button = Gtk.Button()
        self.next_button.set_icon_name("go-down-symbolic")
        self.next_button.set_tooltip_text("Siguiente resultado (F3)")
        self.next_button.connect('clicked', self._on_search_next)
        self.next_button.set_sensitive(False)
        search_main_row.append(self.next_button)

        # Contador de resultados
        self.results_label = Gtk.Label()
        self.results_label.set_text("0 de 0")
        self.results_label.add_css_class("dim-label")
        search_main_row.append(self.results_label)

        # Botón de cerrar
        close_button = Gtk.Button()
        close_button.set_icon_name("window-close-symbolic")
        close_button.set_tooltip_text("Cerrar búsqueda (Escape)")
        close_button.connect('clicked', self._on_search_close)
        search_main_row.append(close_button)

        self.search_panel.append(search_main_row)

        # Fila de opciones avanzadas
        options_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        # Opciones de búsqueda
        self.case_sensitive_check = Gtk.CheckButton(label="Mayús/minús")
        self.case_sensitive_check.set_tooltip_text("Coincidencia exacta de mayúsculas/minúsculas")
        self.case_sensitive_check.connect('toggled', self._on_search_options_changed)
        options_row.append(self.case_sensitive_check)

        self.whole_words_check = Gtk.CheckButton(label="Palabras completas")
        self.whole_words_check.set_tooltip_text("Solo palabras completas")
        self.whole_words_check.connect('toggled', self._on_search_options_changed)
        options_row.append(self.whole_words_check)

        self.regex_check = Gtk.CheckButton(label="Regex")
        self.regex_check.set_tooltip_text("Usar expresiones regulares")
        self.regex_check.connect('toggled', self._on_search_options_changed)
        options_row.append(self.regex_check)

        # Opciones avanzadas de regex (solo visibles cuando regex está activo)
        self.dotall_check = Gtk.CheckButton(label=". incluye \\n")
        self.dotall_check.set_tooltip_text("Modo DOTALL: el punto (.) coincide con saltos de línea")
        self.dotall_check.connect('toggled', self._on_search_options_changed)
        self.dotall_check.set_sensitive(False)  # Deshabilitado por defecto
        options_row.append(self.dotall_check)

        # Botón de info sobre flags de regex
        self.regex_info_button = Gtk.Button()
        self.regex_info_button.set_icon_name("dialog-information-symbolic")
        self.regex_info_button.set_tooltip_text("Ver flags de regex activas")
        self.regex_info_button.add_css_class("flat")
        self.regex_info_button.set_sensitive(False)
        self.regex_info_button.connect('clicked', self._on_show_regex_info)
        options_row.append(self.regex_info_button)

        self.search_panel.append(options_row)

        # === FILA DE REEMPLAZO (separada y ocultable) ===
        self.replace_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        # Label para reemplazo
        replace_label = Gtk.Label(label="Reemplazar:")
        replace_label.set_width_chars(10)
        self.replace_row.append(replace_label)

        # Campo de reemplazo
        self.replace_entry = Gtk.Entry()
        self.replace_entry.set_placeholder_text("Texto de reemplazo (soporta \\n, \\t, \\\\, etc.)")
        self.replace_entry.set_hexpand(True)
        self.replace_row.append(self.replace_entry)

        self.replace_button = Gtk.Button(label="Reemplazar")
        self.replace_button.connect('clicked', self._on_replace_current)
        self.replace_button.set_sensitive(False)
        self.replace_row.append(self.replace_button)

        self.replace_all_button = Gtk.Button(label="Reemplazar todo")
        self.replace_all_button.connect('clicked', self._on_replace_all)
        self.replace_all_button.set_sensitive(False)
        self.replace_row.append(self.replace_all_button)

        self.selective_replace_button = Gtk.Button(label="Selectivo...")
        self.selective_replace_button.set_tooltip_text("Reemplazo selectivo con vista previa")
        self.selective_replace_button.connect('clicked', self._on_selective_replace)
        self.selective_replace_button.set_sensitive(False)
        self.replace_row.append(self.selective_replace_button)

        # Revealer para mostrar/ocultar fila de reemplazo
        self.replace_revealer = Gtk.Revealer()
        self.replace_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.replace_revealer.set_transition_duration(150)
        self.replace_revealer.set_child(self.replace_row)
        self.replace_revealer.set_reveal_child(False)  # Oculto por defecto

        self.search_panel.append(self.replace_revealer)

        # Revealer para mostrar/ocultar el panel
        self.search_revealer = Gtk.Revealer()
        self.search_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.search_revealer.set_transition_duration(200)
        self.search_revealer.set_child(self.search_panel)
        self.search_revealer.set_reveal_child(False)

        # Overlay para posicionar el panel en la parte inferior
        self.search_overlay = Gtk.Overlay()
        self.search_overlay.set_child(self.search_revealer)
        self.search_overlay.set_vexpand(False)

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
        return self.main_container
    
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

    def _load_opf_file(self):
        """Carga el archivo OPF para edición"""
        if not self.main_window.core or not self.main_window.core.opf_path:
            return

        # Leer contenido del OPF
        content = self.main_window.core.opf_path.read_text(encoding='utf-8')

        # Configurar resaltado de sintaxis XML
        lang_manager = GtkSource.LanguageManager.get_default()
        language = lang_manager.get_language('xml')

        self.source_buffer.set_language(language)
        self.source_buffer.set_text(content)

        # Marcar que estamos editando el OPF
        self.current_resource_type = "opf"

        # Limpiar preview (el OPF no tiene preview)
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

    def _refresh_html_preview_after_css_change(self):
        """Refresca el preview HTML cuando se modifican archivos CSS"""
        try:
            # Solo refrescar si hay un preview HTML activo
            if (hasattr(self.main_window, 'sidebar_right') and
                hasattr(self.main_window.sidebar_right, 'update_preview')):

                # Usar un pequeño delay para asegurar que el CSS se guardó
                GLib.timeout_add(100, self.main_window.sidebar_right.update_preview)

        except Exception as e:
            print(f"[DEBUG] Error refrescando preview después de cambio CSS: {e}")
    
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

    # === BÚSQUEDA Y REEMPLAZO ===

    def show_search_panel(self, show_replace=False):
        """Muestra el panel de búsqueda

        Args:
            show_replace: Si True, muestra también el panel de reemplazo
        """
        self.search_visible = True
        self.search_revealer.set_reveal_child(True)
        self.replace_revealer.set_reveal_child(show_replace)
        self.search_entry.grab_focus()

    def hide_search_panel(self):
        """Oculta el panel de búsqueda y reemplazo"""
        self.search_visible = False
        self.search_revealer.set_reveal_child(False)
        self.replace_revealer.set_reveal_child(False)
        self._clear_search_highlights()
        self.source_view.grab_focus()

    def toggle_search_panel(self):
        """Alterna la visibilidad del panel de búsqueda (solo búsqueda, sin reemplazo)"""
        if self.search_visible:
            self.hide_search_panel()
        else:
            self.show_search_panel(show_replace=False)

    def show_search_replace_panel(self):
        """Muestra el panel de búsqueda y reemplazo"""
        self.show_search_panel(show_replace=True)

    def _on_search_changed(self, entry):
        """Maneja cambios en el texto de búsqueda"""
        search_text = entry.get_text()
        if search_text:
            self._perform_search(search_text)
        else:
            self._clear_search_results()

    def _on_search_next(self, widget=None):
        """Navega al siguiente resultado"""
        if self.search_results:
            self.current_result_index = (self.current_result_index + 1) % len(self.search_results)
            self._jump_to_result(self.current_result_index)

    def _on_search_prev(self, widget=None):
        """Navega al resultado anterior"""
        if self.search_results:
            self.current_result_index = (self.current_result_index - 1) % len(self.search_results)
            self._jump_to_result(self.current_result_index)

    def _on_search_close(self, widget=None):
        """Cierra el panel de búsqueda"""
        self.hide_search_panel()

    def _on_search_options_changed(self, widget=None):
        """Reejecutar búsqueda cuando cambian las opciones"""
        # Habilitar/deshabilitar opciones avanzadas de regex
        regex_active = self.regex_check.get_active()
        self.dotall_check.set_sensitive(regex_active)
        self.regex_info_button.set_sensitive(regex_active)

        # Deshabilitar "Palabras completas" cuando regex está activo
        if regex_active:
            self.whole_words_check.set_sensitive(False)
        else:
            self.whole_words_check.set_sensitive(True)

        # Reejecutar búsqueda
        search_text = self.search_entry.get_text()
        if search_text:
            self._perform_search(search_text)

    def _on_show_regex_info(self, widget):
        """Muestra información sobre las flags de regex activas"""
        # Construir lista de flags activas
        flags_info = []

        # MULTILINE siempre activo en modo regex
        flags_info.append("✓ <b>MULTILINE</b>: ^ y $ coinciden con inicio/fin de línea")

        if not self.case_sensitive_check.get_active():
            flags_info.append("✓ <b>IGNORECASE</b>: No distingue mayúsculas/minúsculas")
        else:
            flags_info.append("✗ Case-sensitive: Distingue mayúsculas/minúsculas")

        if self.dotall_check.get_active():
            flags_info.append("✓ <b>DOTALL</b>: El punto (.) coincide con saltos de línea (\\n)")
        else:
            flags_info.append("✗ El punto (.) NO coincide con saltos de línea")

        # Crear popover
        popover = Gtk.Popover()
        popover.set_parent(widget)
        popover.set_position(Gtk.PositionType.BOTTOM)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        title = Gtk.Label()
        title.set_markup("<b>Flags de Regex Activas</b>")
        title.set_halign(Gtk.Align.START)
        box.append(title)

        for flag_text in flags_info:
            label = Gtk.Label()
            label.set_markup(f"  {flag_text}")
            label.set_halign(Gtk.Align.START)
            label.set_wrap(True)
            label.set_max_width_chars(40)
            box.append(label)

        # Separador
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        box.append(separator)

        # Ayuda adicional
        help_label = Gtk.Label()
        help_label.set_markup("<small><i>Tip: Usa (?s) en tu regex para activar\nDOTALL solo en ese patrón</i></small>")
        help_label.set_halign(Gtk.Align.START)
        box.append(help_label)

        popover.set_child(box)
        popover.popup()

    def _get_regex_flags(self):
        """Obtiene las flags de regex según las opciones seleccionadas"""
        import re

        flags = re.MULTILINE  # Siempre activo para que ^ y $ funcionen por línea

        if not self.case_sensitive_check.get_active():
            flags |= re.IGNORECASE

        if self.dotall_check.get_active():
            flags |= re.DOTALL  # El punto (.) incluye saltos de línea

        return flags

    def _process_escape_sequences(self, text: str) -> str:
        """Procesa secuencias de escape en el texto de reemplazo

        Soporta:
        - \\n -> salto de línea
        - \\t -> tabulación
        - \\r -> retorno de carro
        - \\\\  -> barra invertida literal
        - \\0 -> carácter nulo

        Args:
            text: Texto con posibles secuencias de escape

        Returns:
            Texto con secuencias de escape procesadas
        """
        # Mapeo de secuencias de escape
        escape_map = {
            '\\n': '\n',
            '\\t': '\t',
            '\\r': '\r',
            '\\0': '\0',
            '\\\\': '\\'
        }

        result = text
        # Procesar en orden: primero \\\\ para evitar conflictos
        for escape_seq, replacement in [('\\\\', '\x00'), ('\\n', '\n'), ('\\t', '\t'), ('\\r', '\r'), ('\\0', '\0')]:
            result = result.replace(escape_seq, replacement)

        # Restaurar barras invertidas literales
        result = result.replace('\x00', '\\')

        return result

    def _on_replace_current(self, widget):
        """Reemplaza la coincidencia actual"""
        if self.current_result_index >= 0 and self.current_result_index < len(self.search_results):
            import re

            start_iter, end_iter = self.search_results[self.current_result_index]
            matched_text = self.source_buffer.get_text(start_iter, end_iter, False)
            replacement_template = self.replace_entry.get_text()

            # Guardar offset donde ocurre el reemplazo
            replace_offset = start_iter.get_offset()

            # Si regex está activo, procesar grupos de captura
            if self.regex_check.get_active():
                try:
                    search_text = self.search_entry.get_text()
                    flags = self._get_regex_flags()
                    pattern = re.compile(search_text, flags)

                    # Usar re.sub para procesar grupos de captura (\1, \2, etc.)
                    replacement = pattern.sub(replacement_template, matched_text)
                    # Procesar secuencias de escape DESPUÉS de re.sub
                    replacement = self._process_escape_sequences(replacement)
                except re.error as e:
                    self.main_window.show_error(f"Error en expresión de reemplazo: {e}")
                    return
            else:
                # Procesar secuencias de escape en modo no-regex
                replacement = self._process_escape_sequences(replacement_template)

            # Reemplazar texto
            self.source_buffer.delete(start_iter, end_iter)
            self.source_buffer.insert(start_iter, replacement)

            # Calcular nuevo offset después del reemplazo
            new_offset = replace_offset + len(replacement)

            # Actualizar búsqueda
            search_text = self.search_entry.get_text()
            if search_text:
                self._perform_search(search_text)

                # Buscar el siguiente resultado después de la posición del reemplazo
                if self.search_results:
                    next_index = -1
                    for i, (s_iter, e_iter) in enumerate(self.search_results):
                        if s_iter.get_offset() >= new_offset:
                            next_index = i
                            break

                    # Si no hay siguiente, volver al primero
                    if next_index == -1:
                        next_index = 0

                    # Saltar al resultado encontrado
                    self._jump_to_result(next_index)

    def _on_replace_all(self, widget):
        """Reemplaza todas las coincidencias"""
        if not self.search_results:
            return

        import re

        search_text = self.search_entry.get_text()
        replacement_template = self.replace_entry.get_text()

        # Preparar patrón si regex está activo
        if self.regex_check.get_active():
            try:
                flags = self._get_regex_flags()
                pattern = re.compile(search_text, flags)
            except re.error as e:
                self.main_window.show_error(f"Error en expresión de reemplazo: {e}")
                return

        # Convertir iteradores a offsets y guardar texto para evitar invalidación
        replacements_data = []
        for start_iter, end_iter in self.search_results:
            start_offset = start_iter.get_offset()
            end_offset = end_iter.get_offset()
            matched_text = self.source_buffer.get_text(start_iter, end_iter, False)

            # Calcular reemplazo según modo
            if self.regex_check.get_active():
                try:
                    # Usar re.sub para procesar grupos de captura (\1, \2, etc.)
                    replacement = pattern.sub(replacement_template, matched_text)
                    # Procesar secuencias de escape DESPUÉS de re.sub
                    replacement = self._process_escape_sequences(replacement)
                except Exception as e:
                    self.main_window.show_error(f"Error procesando reemplazo: {e}")
                    return
            else:
                # Procesar secuencias de escape en modo no-regex
                replacement = self._process_escape_sequences(replacement_template)

            replacements_data.append((start_offset, end_offset, replacement))

        # Comenzar desde el final para evitar invalidar posiciones
        for start_offset, end_offset, replacement in reversed(replacements_data):
            start_iter = self.source_buffer.get_iter_at_offset(start_offset)
            end_iter = self.source_buffer.get_iter_at_offset(end_offset)
            self.source_buffer.delete(start_iter, end_iter)
            self.source_buffer.insert(start_iter, replacement)

        # Mostrar mensaje
        count = len(self.search_results)
        self.main_window.show_info(f"Reemplazadas {count} coincidencias")

        # Limpiar resultados y actualizar interfaz
        self._clear_search_results()

        # Actualizar búsqueda
        if search_text:
            self._perform_search(search_text)

    def _on_selective_replace(self, widget):
        """Abre el diálogo de reemplazo selectivo"""
        if not self.search_results:
            return

        import re
        from gi.repository import Adw

        search_text = self.search_entry.get_text()
        replacement_template = self.replace_entry.get_text()

        # Preparar patrón si regex está activo
        if self.regex_check.get_active():
            try:
                flags = self._get_regex_flags()
                pattern = re.compile(search_text, flags)
            except re.error as e:
                self.main_window.show_error(f"Error en expresión de reemplazo: {e}")
                return

        # Recopilar todas las coincidencias con su reemplazo
        matches_data = []
        for i, (start_iter, end_iter) in enumerate(self.search_results):
            matched_text = self.source_buffer.get_text(start_iter, end_iter, False)

            # Calcular reemplazo
            if self.regex_check.get_active():
                try:
                    replacement = pattern.sub(replacement_template, matched_text)
                    # Procesar secuencias de escape DESPUÉS de re.sub
                    replacement = self._process_escape_sequences(replacement)
                except Exception:
                    replacement = self._process_escape_sequences(replacement_template)
            else:
                # Procesar secuencias de escape en modo no-regex
                replacement = self._process_escape_sequences(replacement_template)

            # Obtener contexto (línea donde aparece)
            line_num = start_iter.get_line() + 1

            matches_data.append({
                'index': i,
                'matched': matched_text,
                'replacement': replacement,
                'line': line_num,
                'start_offset': start_iter.get_offset(),
                'end_offset': end_iter.get_offset(),
                'selected': True  # Por defecto todos seleccionados
            })

        # Crear diálogo
        dialog = Adw.Dialog()
        dialog.set_title("Reemplazo Selectivo")
        dialog.set_content_width(800)
        dialog.set_content_height(600)

        # Contenedor principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)

        # Encabezado con contador
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        count_label = Gtk.Label()
        count_label.set_markup(f"<b>Encontradas {len(matches_data)} coincidencias</b>")
        count_label.set_halign(Gtk.Align.START)
        header_box.append(count_label)
        main_box.append(header_box)

        # Toolbar con botones de selección
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        select_all_btn = Gtk.Button(label="Marcar todos")
        select_all_btn.add_css_class("flat")
        deselect_all_btn = Gtk.Button(label="Desmarcar todos")
        deselect_all_btn.add_css_class("flat")

        toolbar.append(select_all_btn)
        toolbar.append(deselect_all_btn)
        main_box.append(toolbar)

        # ScrolledWindow para la lista
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_min_content_height(400)

        # ListBox para las coincidencias
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("boxed-list")

        # Crear filas para cada coincidencia
        check_buttons = []
        for match_data in matches_data:
            row = Gtk.ListBoxRow()
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row_box.set_margin_top(8)
            row_box.set_margin_bottom(8)
            row_box.set_margin_start(8)
            row_box.set_margin_end(8)

            # Checkbox
            check = Gtk.CheckButton()
            check.set_active(True)
            check.set_valign(Gtk.Align.CENTER)
            check_buttons.append((check, match_data))
            row_box.append(check)

            # Contenedor de columnas
            columns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            columns_box.set_hexpand(True)

            # Columna 1: Línea
            line_label = Gtk.Label()
            line_label.set_markup(f"<span font_family='monospace' color='#999'>L{match_data['line']}</span>")
            line_label.set_width_chars(6)
            line_label.set_xalign(0)
            columns_box.append(line_label)

            # Columna 2: Texto original
            original_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            original_box.set_hexpand(True)

            original_header = Gtk.Label()
            original_header.set_markup("<small>Original:</small>")
            original_header.set_xalign(0)
            original_header.add_css_class("dim-label")

            original_text = Gtk.Label()
            # Truncar texto si es muy largo
            display_text = match_data['matched']
            if len(display_text) > 80:
                display_text = display_text[:77] + "..."
            original_text.set_markup(f"<span font_family='monospace' background='#ffeb3b33'>{GLib.markup_escape_text(display_text)}</span>")
            original_text.set_xalign(0)
            original_text.set_wrap(True)
            original_text.set_wrap_mode(Gtk.WrapMode.CHAR)

            original_box.append(original_header)
            original_box.append(original_text)
            columns_box.append(original_box)

            # Flecha
            arrow_label = Gtk.Label()
            arrow_label.set_text("→")
            arrow_label.set_valign(Gtk.Align.CENTER)
            columns_box.append(arrow_label)

            # Columna 3: Texto reemplazado
            replacement_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            replacement_box.set_hexpand(True)

            replacement_header = Gtk.Label()
            replacement_header.set_markup("<small>Reemplazo:</small>")
            replacement_header.set_xalign(0)
            replacement_header.add_css_class("dim-label")

            replacement_text = Gtk.Label()
            # Truncar texto si es muy largo
            display_replacement = match_data['replacement']
            if len(display_replacement) > 80:
                display_replacement = display_replacement[:77] + "..."
            replacement_text.set_markup(f"<span font_family='monospace' background='#4caf5033'>{GLib.markup_escape_text(display_replacement)}</span>")
            replacement_text.set_xalign(0)
            replacement_text.set_wrap(True)
            replacement_text.set_wrap_mode(Gtk.WrapMode.CHAR)

            replacement_box.append(replacement_header)
            replacement_box.append(replacement_text)
            columns_box.append(replacement_box)

            row_box.append(columns_box)
            row.set_child(row_box)
            listbox.append(row)

        scrolled.set_child(listbox)
        main_box.append(scrolled)

        # Botones de acción
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        actions_box.set_halign(Gtk.Align.END)

        cancel_btn = Gtk.Button(label="Cancelar")
        cancel_btn.connect('clicked', lambda w: dialog.close())

        replace_btn = Gtk.Button(label="Reemplazar seleccionados")
        replace_btn.add_css_class("suggested-action")

        actions_box.append(cancel_btn)
        actions_box.append(replace_btn)
        main_box.append(actions_box)

        # Conectar eventos
        def on_select_all(btn):
            for check, _ in check_buttons:
                check.set_active(True)

        def on_deselect_all(btn):
            for check, _ in check_buttons:
                check.set_active(False)

        def on_replace(btn):
            # Recopilar seleccionados
            selected_matches = []
            for check, match_data in check_buttons:
                if check.get_active():
                    selected_matches.append(match_data)

            if not selected_matches:
                self.main_window.show_info("No hay coincidencias seleccionadas")
                return

            # Ordenar por posición (de atrás hacia adelante para no invalidar offsets)
            selected_matches.sort(key=lambda m: m['start_offset'], reverse=True)

            # Aplicar reemplazos
            for match_data in selected_matches:
                start_iter = self.source_buffer.get_iter_at_offset(match_data['start_offset'])
                end_iter = self.source_buffer.get_iter_at_offset(match_data['end_offset'])
                self.source_buffer.delete(start_iter, end_iter)
                self.source_buffer.insert(start_iter, match_data['replacement'])

            # Mostrar mensaje
            count = len(selected_matches)
            self.main_window.show_info(f"Reemplazadas {count} coincidencias seleccionadas")

            # Cerrar diálogo
            dialog.close()

            # Actualizar búsqueda
            self._perform_search(search_text)

        select_all_btn.connect('clicked', on_select_all)
        deselect_all_btn.connect('clicked', on_deselect_all)
        replace_btn.connect('clicked', on_replace)

        # Configurar y mostrar diálogo
        dialog.set_child(main_box)
        dialog.present(self.main_window)

    def _perform_search(self, search_text):
        """Ejecuta la búsqueda en el documento"""
        import re

        self.current_search_text = search_text
        self.search_results = []

        # Obtener texto completo del buffer
        start_iter = self.source_buffer.get_start_iter()
        end_iter = self.source_buffer.get_end_iter()
        text = self.source_buffer.get_text(start_iter, end_iter, False)

        # Preparar patrón de búsqueda
        if self.regex_check.get_active():
            try:
                # Obtener flags configuradas
                flags = self._get_regex_flags()
                pattern = re.compile(search_text, flags)
            except re.error:
                self._update_search_status("Regex inválido")
                return
        else:
            # Escapar caracteres especiales de regex
            escaped_text = re.escape(search_text)

            # Añadir límites de palabra si está activado
            if self.whole_words_check.get_active():
                escaped_text = r'\b' + escaped_text + r'\b'

            # Usar las mismas flags que regex (sin DOTALL)
            flags = re.MULTILINE
            if not self.case_sensitive_check.get_active():
                flags |= re.IGNORECASE
            pattern = re.compile(escaped_text, flags)

        # Buscar todas las coincidencias
        # NOTA: No usamos timeout con signal.SIGALRM porque puede interferir con GTK/WebKit
        try:
            match_count = 0
            for match in pattern.finditer(text):
                start_pos = match.start()
                end_pos = match.end()

                # Convertir posiciones a iteradores de GTK
                start_iter = self.source_buffer.get_iter_at_offset(start_pos)
                end_iter = self.source_buffer.get_iter_at_offset(end_pos)

                self.search_results.append((start_iter, end_iter))

                # Límite de seguridad: máximo 10000 resultados
                match_count += 1
                if match_count >= 10000:
                    self._update_search_status(f"Más de 10000 resultados (límite alcanzado)")
                    self.main_window.show_error(
                        "Se encontraron más de 10000 coincidencias.\n"
                        "Usa un patrón más específico para evitar sobrecarga."
                    )
                    break

        except Exception as e:
            self._update_search_status(f"Error en búsqueda: {str(e)}")
            self.main_window.show_error(f"Error en búsqueda de regex: {e}")
            return

        # Actualizar interfaz
        self._update_search_results()

    def _update_search_results(self):
        """Actualiza la interfaz con los resultados de búsqueda"""
        count = len(self.search_results)

        # Actualizar contador
        if count > 0:
            self.current_result_index = 0
            self.results_label.set_text(f"1 de {count}")
            self._highlight_search_results()
            self._jump_to_result(0)
        else:
            self.current_result_index = -1
            self.results_label.set_text("0 de 0")
            self._clear_search_highlights()

        # Habilitar/deshabilitar botones
        has_results = count > 0
        self.prev_button.set_sensitive(has_results)
        self.next_button.set_sensitive(has_results)
        self.replace_button.set_sensitive(has_results)
        self.replace_all_button.set_sensitive(has_results)
        self.selective_replace_button.set_sensitive(has_results)

    def _highlight_search_results(self):
        """Resalta todos los resultados de búsqueda"""
        # Limpiar resaltados anteriores
        self._clear_search_highlights()

        # Crear tags para resaltado si no existen
        tag_table = self.source_buffer.get_tag_table()

        # Tag para todas las coincidencias
        search_tag = tag_table.lookup("search-highlight")
        if not search_tag:
            from gi.repository import Gdk
            # Detectar si el tema es claro u oscuro
            is_dark_theme = self._is_dark_theme()

            if is_dark_theme:
                # Colores para tema oscuro
                search_tag = self.source_buffer.create_tag(
                    "search-highlight",
                    background_rgba=Gdk.RGBA(red=0.8, green=0.7, blue=0.1, alpha=0.7),  # Amarillo más suave
                    foreground_rgba=Gdk.RGBA(red=0.0, green=0.0, blue=0.0, alpha=1.0),  # Texto negro
                    weight=600  # Texto semi-bold
                )
            else:
                # Colores para tema claro
                search_tag = self.source_buffer.create_tag(
                    "search-highlight",
                    background_rgba=Gdk.RGBA(red=1.0, green=0.85, blue=0.0, alpha=0.8),  # Amarillo intenso
                    foreground_rgba=Gdk.RGBA(red=0.0, green=0.0, blue=0.0, alpha=1.0),  # Texto negro
                    weight=600  # Texto semi-bold
                )

        # Tag para el resultado actual (más destacado)
        current_tag = tag_table.lookup("search-current")
        if not current_tag:
            from gi.repository import Gdk
            is_dark_theme = self._is_dark_theme()

            if is_dark_theme:
                # Colores para tema oscuro
                current_tag = self.source_buffer.create_tag(
                    "search-current",
                    background_rgba=Gdk.RGBA(red=0.9, green=0.5, blue=0.1, alpha=0.9),  # Naranja suave
                    foreground_rgba=Gdk.RGBA(red=1.0, green=1.0, blue=1.0, alpha=1.0),  # Texto blanco
                    weight=700,  # Texto bold
                    underline=3  # Subrayado
                )
            else:
                # Colores para tema claro
                current_tag = self.source_buffer.create_tag(
                    "search-current",
                    background_rgba=Gdk.RGBA(red=1.0, green=0.4, blue=0.0, alpha=0.9),  # Naranja intenso
                    foreground_rgba=Gdk.RGBA(red=1.0, green=1.0, blue=1.0, alpha=1.0),  # Texto blanco
                    weight=700,  # Texto bold
                    underline=3  # Subrayado
                )

        # Resaltar todas las coincidencias
        for i, (start_iter, end_iter) in enumerate(self.search_results):
            if i == self.current_result_index:
                # Resultado actual con resaltado especial
                self.source_buffer.apply_tag(current_tag, start_iter, end_iter)
            else:
                # Otras coincidencias con resaltado normal
                self.source_buffer.apply_tag(search_tag, start_iter, end_iter)

    def _clear_search_highlights(self):
        """Limpia todos los resaltados de búsqueda"""
        tag_table = self.source_buffer.get_tag_table()
        start_iter = self.source_buffer.get_start_iter()
        end_iter = self.source_buffer.get_end_iter()

        # Limpiar resaltado normal
        search_tag = tag_table.lookup("search-highlight")
        if search_tag:
            self.source_buffer.remove_tag(search_tag, start_iter, end_iter)

        # Limpiar resaltado de resultado actual
        current_tag = tag_table.lookup("search-current")
        if current_tag:
            self.source_buffer.remove_tag(current_tag, start_iter, end_iter)

    def _jump_to_result(self, index):
        """Salta al resultado especificado"""
        if index < 0 or index >= len(self.search_results):
            return

        # Actualizar el índice actual
        self.current_result_index = index
        start_iter, end_iter = self.search_results[index]

        # Actualizar contador
        self.results_label.set_text(f"{index + 1} de {len(self.search_results)}")

        # Actualizar resaltado (esto cambiará el resultado actual)
        self._highlight_search_results()

        # Seleccionar el texto encontrado
        self.source_buffer.select_range(start_iter, end_iter)

        # Hacer scroll para mostrar la selección
        self.source_view.scroll_to_iter(start_iter, 0.0, False, 0.0, 0.5)

        # Sincronizar posición con WebKit
        self._sync_webkit_position(start_iter)

    def _clear_search_results(self):
        """Limpia los resultados de búsqueda"""
        self.search_results = []
        self.current_result_index = -1
        self.results_label.set_text("0 de 0")
        self.prev_button.set_sensitive(False)
        self.next_button.set_sensitive(False)
        self.replace_button.set_sensitive(False)
        self.replace_all_button.set_sensitive(False)
        self.selective_replace_button.set_sensitive(False)
        self._clear_search_highlights()

    def _update_search_status(self, message):
        """Actualiza el estado de búsqueda con un mensaje"""
        self.results_label.set_text(message)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        """Maneja eventos de teclado globales (editor y búsqueda)"""
        from gi.repository import Gdk

        # Escape para cerrar búsqueda
        if keyval == Gdk.KEY_Escape and self.search_visible:
            self.hide_search_panel()
            return True

        return False

    def _is_dark_theme(self) -> bool:
        """Detecta si el tema actual es oscuro"""
        try:
            # Obtener el estilo del editor
            style_context = self.source_view.get_style_context()

            # Obtener el color de fondo
            bg_color = style_context.get_color()

            # Calcular luminosidad usando la fórmula estándar
            # Si la luminosidad es < 0.5, consideramos que es un tema oscuro
            luminance = (0.299 * bg_color.red + 0.587 * bg_color.green + 0.114 * bg_color.blue)

            return luminance < 0.5

        except Exception:
            # En caso de error, asumir tema claro por defecto
            return False

    def _on_cursor_moved(self, buffer):
        """Maneja movimiento del cursor para sincronizar con WebKit"""
        # Solo sincronizar si es un documento HTML
        if (self.current_resource_type == KIND_DOCUMENT and
            self.main_window.current_resource and
            self.main_window.current_resource.endswith(('.html', '.xhtml', '.htm'))):

            # Obtener posición actual del cursor
            cursor_iter = buffer.get_iter_at_mark(buffer.get_insert())
            current_line = cursor_iter.get_line() + 1

            # Throttling: solo sincronizar si la línea cambió
            if current_line != self._last_sync_line:
                # Cancelar sincronización pendiente
                if self._sync_timeout:
                    GLib.source_remove(self._sync_timeout)

                # Programar sincronización con delay
                self._sync_timeout = GLib.timeout_add(150, self._delayed_sync, cursor_iter)
                self._last_sync_line = current_line

    def _delayed_sync(self, text_iter) -> bool:
        """Ejecuta la sincronización con delay para evitar spam"""
        self._sync_webkit_position(text_iter)
        self._sync_timeout = None
        return False  # No repetir

    def _sync_webkit_position(self, text_iter):
        """Sincroniza la posición del WebKit con la posición actual en el editor"""
        try:
            # Solo sincronizar si es un documento HTML
            if not self.main_window.current_resource or not self.main_window.current_resource.endswith(('.html', '.xhtml', '.htm')):
                return

            # Obtener contexto alrededor del cursor
            start_iter = self.source_buffer.get_start_iter()
            end_iter = self.source_buffer.get_end_iter()

            # Obtener el texto antes y después del cursor para tener contexto
            line_start = text_iter.copy()
            line_start.set_line_offset(0)
            line_end = text_iter.copy()
            if not line_end.ends_line():
                line_end.forward_to_line_end()

            # Extraer texto de la línea actual
            current_line_text = self.source_buffer.get_text(line_start, line_end, False)

            # Extraer texto visible (sin tags HTML) cerca del cursor
            context_text = self._extract_visible_text_context(text_iter)
            line_number = text_iter.get_line() + 1

            # JavaScript mejorado para buscar por contenido de texto
            scroll_script = f"""
                (function() {{
                    try {{
                        var contextText = {repr(context_text)};
                        var lineNumber = {line_number};

                        // Función para limpiar texto (remover espacios extra, normalizar)
                        function cleanText(text) {{
                            return text.replace(/\\s+/g, ' ').trim().toLowerCase();
                        }}

                        var foundElement = null;
                        var foundPosition = null;

                        // Si tenemos contexto de texto, buscar por contenido
                        if (contextText && contextText.length > 3) {{
                            var cleanContext = cleanText(contextText);

                            // Buscar en todos los elementos de texto
                            var walker = document.createTreeWalker(
                                document.body,
                                NodeFilter.SHOW_TEXT,
                                {{
                                    acceptNode: function(node) {{
                                        var text = cleanText(node.textContent);
                                        return text.length > 2 ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP;
                                    }}
                                }}
                            );

                            var node;
                            while (node = walker.nextNode()) {{
                                var nodeText = cleanText(node.textContent);
                                if (nodeText.includes(cleanContext) || cleanContext.includes(nodeText)) {{
                                    foundElement = node.parentElement;
                                    break;
                                }}
                            }}
                        }}

                        // Si no encontramos por contexto, usar scroll proporcional
                        if (foundElement) {{
                            // Scroll al elemento encontrado
                            foundElement.scrollIntoView({{
                                behavior: 'smooth',
                                block: 'center',
                                inline: 'nearest'
                            }});

                            // Resaltar temporalmente el elemento
                            var originalStyle = foundElement.style.cssText;
                            foundElement.style.backgroundColor = 'rgba(255, 165, 0, 0.3)';
                            foundElement.style.transition = 'background-color 0.5s';

                            setTimeout(function() {{
                                foundElement.style.backgroundColor = '';
                                setTimeout(function() {{
                                    foundElement.style.cssText = originalStyle;
                                }}, 500);
                            }}, 1000);

                        }} else {{
                            // Fallback: scroll proporcional por línea
                            var totalHeight = document.documentElement.scrollHeight;
                            var viewportHeight = window.innerHeight;
                            var maxScroll = totalHeight - viewportHeight;

                            // Estimar posición basada en contenido HTML vs líneas totales
                            var htmlLines = document.body.innerHTML.split('\\n').length;
                            var percentage = Math.min(lineNumber / Math.max(htmlLines * 0.7, 1), 1.0);
                            var targetScroll = Math.max(0, maxScroll * percentage);

                            window.scrollTo({{
                                top: targetScroll,
                                behavior: 'smooth'
                            }});
                        }}

                        // Indicador visual mejorado
                        var indicator = document.getElementById('cursor-indicator');
                        if (!indicator) {{
                            indicator = document.createElement('div');
                            indicator.id = 'cursor-indicator';
                            indicator.style.cssText = `
                                position: fixed;
                                right: 20px;
                                top: 50%;
                                transform: translateY(-50%);
                                background: rgba(255, 165, 0, 0.9);
                                color: white;
                                padding: 8px 12px;
                                border-radius: 6px;
                                font-size: 11px;
                                font-family: monospace;
                                z-index: 9999;
                                pointer-events: none;
                                transition: opacity 0.3s ease;
                                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                            `;
                            document.body.appendChild(indicator);
                        }}

                        var statusText = foundElement ?
                            'Línea {line_number} ✓' :
                            'Línea {line_number} (~)';
                        indicator.textContent = statusText;
                        indicator.style.opacity = '1';

                        // Ocultar el indicador después de 1.5 segundos
                        setTimeout(function() {{
                            if (indicator) {{
                                indicator.style.opacity = '0';
                                setTimeout(function() {{
                                    if (indicator && indicator.parentNode) {{
                                        indicator.parentNode.removeChild(indicator);
                                    }}
                                }}, 300);
                            }}
                        }}, 1500);

                    }} catch (e) {{
                        console.log('Error en sincronización de scroll:', e);
                    }}
                }})();
            """

            # Ejecutar en WebKit principal
            sidebar_right = self.main_window.sidebar_right
            if sidebar_right and hasattr(sidebar_right, 'web_view'):
                sidebar_right.web_view.evaluate_javascript(scroll_script, -1, None, None, None, None, None)

            # Ejecutar en WebKit fullscreen si está activo
            if sidebar_right and sidebar_right._is_fullscreen_active():
                sidebar_right.fullscreen_web_view.evaluate_javascript(scroll_script, -1, None, None, None, None, None)

        except Exception as e:
            print(f"[DEBUG] Error sincronizando WebKit: {e}")

    def _extract_visible_text_context(self, text_iter):
        """Extrae el texto visible (sin tags HTML) alrededor del cursor"""
        try:
            import re

            # Obtener contexto de ~100 caracteres alrededor del cursor
            start_context = text_iter.copy()
            start_context.backward_chars(50)
            end_context = text_iter.copy()
            end_context.forward_chars(50)

            context_html = self.source_buffer.get_text(start_context, end_context, False)

            # Remover tags HTML y extraer solo texto visible
            # Primero, remover comentarios HTML
            context_html = re.sub(r'<!--.*?-->', '', context_html, flags=re.DOTALL)

            # Remover tags pero mantener el contenido
            visible_text = re.sub(r'<[^>]+>', '', context_html)

            # Limpiar espacios en blanco excesivos
            visible_text = re.sub(r'\s+', ' ', visible_text).strip()

            # Tomar una porción razonable (palabras completas)
            words = visible_text.split()
            if len(words) > 5:
                # Tomar 3-5 palabras del medio para tener un buen contexto
                start_idx = max(0, len(words)//2 - 2)
                end_idx = min(len(words), start_idx + 5)
                visible_text = ' '.join(words[start_idx:end_idx])

            return visible_text[:50]  # Limitar a 50 caracteres

        except Exception as e:
            print(f"[DEBUG] Error extrayendo contexto: {e}")
            return ""

    def scroll_to_line(self, line_number: int):
        """Hace scroll a una línea específica en el editor y sincroniza con WebKit"""
        try:
            # Validar número de línea
            total_lines = self.source_buffer.get_line_count()
            line_number = max(1, min(line_number, total_lines))

            # Obtener iterador para la línea (líneas empiezan en 0)
            line_iter = self.source_buffer.get_iter_at_line(line_number - 1)

            # Mover cursor a la línea
            self.source_buffer.place_cursor(line_iter)

            # Hacer scroll en el editor
            self.source_view.scroll_to_iter(line_iter, 0.0, False, 0.0, 0.5)

            # Enfocar el editor
            self.source_view.grab_focus()

            # Sincronizar con WebKit
            self._sync_webkit_position(line_iter)

        except Exception as e:
            print(f"[DEBUG] Error en scroll_to_line: {e}")

    def get_current_line_number(self) -> int:
        """Obtiene el número de línea actual del cursor"""
        try:
            cursor_iter = self.source_buffer.get_iter_at_mark(self.source_buffer.get_insert())
            return cursor_iter.get_line() + 1  # Las líneas empiezan en 0, pero mostramos desde 1
        except Exception:
            return 1