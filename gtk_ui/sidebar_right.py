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

        # Botón para recargar WebView
        reload_btn = Gtk.Button()
        reload_btn.set_icon_name("view-refresh-symbolic")
        reload_btn.set_tooltip_text("Recargar previsualización (útil si se cuelga)")
        reload_btn.add_css_class("flat")
        reload_btn.connect('clicked', lambda b: self.reload_webview())
        sidebar_header.append(reload_btn)

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
        print("[Preview] Configurando WebView...")

        # Contenedor para poder reemplazar el WebView si falla
        self.webview_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.webview_container.set_vexpand(True)
        self.webview_container.set_hexpand(True)

        # Crear el WebView inicial
        self._create_webview()

        web_scroll = Gtk.ScrolledWindow()
        web_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        web_scroll.set_child(self.webview_container)
        web_scroll.set_vexpand(True)
        web_scroll.set_hexpand(True)

        self.sidebar_box.append(web_scroll)
        print("[Preview] WebView configurado en sidebar_box")

    def _create_webview(self):
        """Crea una nueva instancia de WebView"""
        # Limpiar WebView anterior si existe
        if hasattr(self, 'web_view') and self.web_view:
            try:
                parent = self.web_view.get_parent()
                if parent:
                    parent.remove(self.web_view)
                # Destruir el widget anterior
                self.web_view.unparent()
            except Exception as e:
                print(f"[WebView] Error limpiando WebView anterior: {e}")

        # Crear nuevo WebView
        self.web_view = WebKit.WebView()

        # Hacer visible y expandible
        self.web_view.set_vexpand(True)
        self.web_view.set_hexpand(True)
        self.web_view.set_visible(True)

        # Configurar WebView para ser más tolerante con errores
        try:
            settings = self.web_view.get_settings()
            settings.set_enable_javascript(True)
            # Habilitar herramientas de desarrollo para depuración
            settings.set_enable_developer_extras(True)
            # Intentar habilitar logs en consola si es posible
            if hasattr(settings, 'set_enable_write_console_messages_to_stdout'):
                settings.set_enable_write_console_messages_to_stdout(True)

            # Configurar puente de mensajería (JS -> Python)
            content_manager = self.web_view.get_user_content_manager()
            content_manager.register_script_message_handler("gutenai")
            content_manager.connect("script-message-received::gutenai", self._on_script_message)

            # Conectar señales de error
            self.web_view.connect('load-failed', self._on_load_failed)
            self.web_view.connect('load-changed', self._on_load_changed)
        except Exception as e:
            print(f"[WebView] Error configurando WebView: {e}")

        # Agregar al contenedor
        try:
            self.webview_container.append(self.web_view)
            print("[WebView] WebView creado y agregado al contenedor")

            # Cargar HTML de prueba para verificar que funciona
            test_html = "<html><body><h1>WebKit Listo</h1><p>El preview está funcionando.</p></body></html>"
            self.web_view.load_html(test_html, None)
            print("[WebView] HTML de prueba cargado")
        except Exception as e:
            print(f"[WebView] Error agregando WebView al contenedor: {e}")

    def _on_script_message(self, content_manager, js_result):
        """Maneja mensajes recibidos desde JavaScript"""
        try:
            # Compatibilidad WebKit 6.0 vs 4.x
            # En WebKit 6.0, js_result ya es un JSC.Value
            # En WebKit 4.x, es un JavascriptResult que tiene get_js_value()
            if hasattr(js_result, 'get_js_value'):
                value = js_result.get_js_value()
            else:
                value = js_result

            # Parsear JSON manual
            import json
            try:
                # Obtener representación JSON del valor
                message_str = value.to_json(0)
                data = json.loads(message_str)
                
                # Si el resultado sigue siendo un string (porque JS envió JSON.stringify),
                # parsear nuevamente
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except:
                        pass
            except Exception as e:
                print(f"[ReverseSync] Error decodificando JSON: {e}")
                data = {}

            print(f"[ReverseSync] Mensaje procesado: {type(data)} -> {data}")
            
            if isinstance(data, dict) and data.get('type') == 'click_sync':
                element_id = data.get('id')
                text_snippet = data.get('text')
                
                if element_id:
                    print(f"[ReverseSync] Sincronizando por ID: {element_id}")
                    self.main_window.central_editor.scroll_to_element_by_id(element_id)
                elif text_snippet:
                    print(f"[ReverseSync] Sincronizando por texto: {text_snippet}")
                    self.main_window.central_editor.scroll_to_text(text_snippet)
                    
        except Exception as e:
            print(f"[ReverseSync] Error procesando mensaje: {e}")
            import traceback
            traceback.print_exc()

    def _on_load_failed(self, web_view, load_event, failing_uri, error):
        """Maneja errores de carga de WebKit"""
        print(f"[WebKit] Error de carga: {error.message}")

        # Mostrar mensaje de error amigable
        error_html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: sans-serif; padding: 20px; background: #f5f5f5; }}
                .error-box {{
                    background: #fff;
                    border-left: 4px solid #ff6b6b;
                    padding: 15px;
                    border-radius: 4px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h2 {{ color: #ff6b6b; margin-top: 0; }}
                code {{
                    background: #f0f0f0;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-size: 0.9em;
                }}
                .btn {{
                    background: #4CAF50;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    margin-top: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="error-box">
                <h2>⚠️ Error al cargar la previsualización</h2>
                <p><strong>El HTML puede tener errores de sintaxis.</strong></p>
                <p>URI: <code>{failing_uri}</code></p>
                <p>Error: <code>{error.message}</code></p>
                <p><em>Sugerencia: Usa <kbd>Ctrl+Shift+V</kbd> para validar el EPUB con EPUBCheck.</em></p>
            </div>
        </body>
        </html>
        """

        # Intentar mostrar el error (si WebKit aún responde)
        try:
            web_view.load_html(error_html, None)
        except:
            pass

        return True  # Prevenir comportamiento por defecto

    def _on_load_changed(self, web_view, load_event):
        """Monitorea el estado de carga"""
        if load_event == WebKit.LoadEvent.FINISHED:
            print("[WebKit] Carga completada exitosamente")
        elif load_event == WebKit.LoadEvent.STARTED:
            print("[WebKit] Iniciando carga...")

    def reload_webview(self):
        """Recrea el WebView desde cero (útil cuando se cuelga)"""
        print("[WebKit] Recreando WebView...")
        self._create_webview()
        # Intentar recargar el contenido actual
        if self.main_window.current_resource:
            GLib.timeout_add(200, self.update_preview)
    
    def get_widget(self) -> Gtk.Widget:
        """Retorna el widget principal del sidebar"""
        return self.sidebar_box
    
    def update_preview(self):
        """Actualiza la previsualización con el recurso actual"""
        print(f"[Preview] update_preview() llamado")
        print(f"[Preview] core: {self.main_window.core is not None}")
        print(f"[Preview] current_resource: {self.main_window.current_resource}")

        if not self.main_window.core or not self.main_window.current_resource:
            print("[Preview] No hay core o recurso, mostrando vacío")
            self.web_view.load_html("<p>Selecciona un documento HTML para previsualizar.</p>", None)
            return

        # Solo previsualizar documentos HTML
        if not self.main_window.current_resource.endswith(('.html', '.xhtml', '.htm')):
            print(f"[Preview] Tipo no soportado: {self.main_window.current_resource}")
            self.web_view.load_html("<p>Este tipo de archivo no se puede previsualizar.</p>", None)
            return

        try:
            print(f"[Preview] Leyendo contenido de: {self.main_window.current_resource}")
            content = self.main_window.core.read_text(self.main_window.current_resource)
            print(f"[Preview] Contenido leído: {len(content)} caracteres")
            self._update_preview_content(content, self.main_window.current_resource)
        except Exception as e:
            print(f"[Preview] Error cargando: {e}")
            import traceback
            traceback.print_exc()
            error_html = f"<h1>Error</h1><p>No se pudo cargar el contenido: {e}</p>"
            self.web_view.load_html(error_html, None)
    
    def _update_preview_content(self, html_content: str, href: str):
        """Preview seguro usando archivo dedicado SOLO para preview"""
        print(f"[Preview] _update_preview_content llamado para: {href}")
        try:
            # Validación básica del HTML
            validation_result = self._validate_html_basic(html_content)
            if not validation_result['valid']:
                # Mostrar advertencia pero intentar cargar de todos modos
                print(f"[Preview] Advertencia HTML: {validation_result['error']}")

            # INYECTAR CSS DE MARCADORES DE ANCLAJE (hooks)
            html_content = self._inject_hook_markers_css(html_content)
            
            # INYECTAR JS DE SINCRONIZACIÓN INVERSA
            html_content = self._inject_reverse_sync_js(html_content)

            # Crear archivo de preview dedicado (no sobreescribir el original)
            preview_file_path = self._get_preview_file_path(href)
            print(f"[Preview] Ruta de preview: {preview_file_path}")

            # Escribir contenido al archivo de preview
            preview_file_path.write_text(html_content, encoding='utf-8')
            print(f"[Preview] Archivo de preview escrito: {preview_file_path.exists()}")

            # Cargar desde archivo de preview
            file_uri = preview_file_path.as_uri()
            print(f"[Preview] URI a cargar: {file_uri}")

            # Verificar que el WebView existe y está visible
            print(f"[Preview] WebView existe: {self.web_view is not None}")
            print(f"[Preview] WebView visible: {self.web_view.get_visible() if self.web_view else 'N/A'}")

            self.web_view.load_uri(file_uri)
            print(f"[Preview] load_uri() ejecutado")

            # Sincronizar con fullscreen si está activo
            if self._is_fullscreen_active():
                print(f"[Preview] Sincronizando con fullscreen")
                self.fullscreen_web_view.load_uri(file_uri)

        except Exception as e:
            print(f"[Preview] Error en _update_preview_content: {e}")
            import traceback
            traceback.print_exc()
            # Fallback: HTML inline
            error_msg = f"<p>Error en preview: {e}</p>"
            self.web_view.load_html(error_msg, None)

    def _inject_hook_markers_css(self, html_content: str) -> str:
        """
        Inyecta CSS para mostrar marcadores visuales (⚓) en elementos con id

        Los marcadores son sutiles y no afectan el layout:
        - Aparecen como ::before pseudo-element
        - Solo visibles en hover
        - Color gris claro
        - No se imprimen
        """
        hook_marker_css = """
<style id="gutenai-hook-markers">
/* GutenAI: Marcadores visuales de anclajes (hooks) */
*[id]::before {
    content: "⚓";
    position: absolute;
    left: -20px;
    opacity: 0;
    color: #999;
    font-size: 0.8em;
    transition: opacity 0.2s ease;
    pointer-events: none;
}

*[id]:hover::before {
    opacity: 0.6;
}

/* Asegurar que elementos con id tengan position relative */
*[id] {
    position: relative;
}

/* Ocultar en impresión */
@media print {
    *[id]::before {
        display: none !important;
    }
}
</style>
"""
        # Inyectar antes de </head> si existe, sino antes de <body>
        if '</head>' in html_content:
            html_content = html_content.replace('</head>', f'{hook_marker_css}\n</head>')
        elif '<body' in html_content:
            html_content = html_content.replace('<body', f'{hook_marker_css}\n<body')
        else:
            # Fallback: agregar al inicio
            html_content = hook_marker_css + '\n' + html_content

        return html_content

    def _inject_reverse_sync_js(self, html_content: str) -> str:
        """Inyecta JavaScript para detectar clics y enviarlos a Python"""
        print("[ReverseSync] Inyectando JS en el HTML...")
        # Nota: Usamos CDATA para evitar errores de parseo XML con caracteres como '&' (&&)
        sync_js = """
<script type="text/javascript" id="gutenai-reverse-sync">
//<![CDATA[
(function() {
    // Evitar múltiples inyecciones
    if (window.gutenaiSyncInjected) return;
    window.gutenaiSyncInjected = true;
    console.log("[GutenAI] JS Injected and Ready");

    document.addEventListener('click', function(e) {
        // console.log("[GutenAI] Click detected on", e.target.tagName);
        
        let target = e.target;
        
        // Removed visual feedback
        let foundId = null;
        let foundText = target.innerText ? target.innerText.substring(0, 100) : "";

        // Buscar ID en el elemento o sus padres
        while (target && target !== document.body) {
            if (target.id && !target.id.startsWith('gutenai-')) {
                foundId = target.id;
                break;
            }
            target = target.parentElement;
        }
        
        console.log("[GutenAI] Sending message. ID:", foundId, "Text:", foundText.substring(0, 20));
        
        // Enviar mensaje a Python
        if (window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.gutenai) {
            try {
                window.webkit.messageHandlers.gutenai.postMessage(JSON.stringify({
                    type: 'click_sync',
                    id: foundId,
                    tag: target ? target.tagName : null,
                    text: foundText
                }));
            } catch(err) {
                console.error("[GutenAI] Error sending message:", err);
            }
        } else {
            console.error("[GutenAI] WebKit message handler not found!");
            alert("Error: WebKit bridge broken");
        }
    });
})();
//]]>
</script>
"""
        # Inyectar antes de </body>
        if '</body>' in html_content:
            html_content = html_content.replace('</body>', f'{sync_js}\n</body>')
        else:
            html_content += sync_js
            
        return html_content

    def _validate_html_basic(self, html: str) -> dict:
        """Validación básica de HTML para detectar problemas graves"""
        try:
            # Verificar que no esté vacío
            if not html or not html.strip():
                return {'valid': False, 'error': 'HTML vacío'}

            # Verificar tags básicos
            html_lower = html.lower()

            # Advertir si falta DOCTYPE (no crítico)
            if '<!doctype' not in html_lower:
                print("[WebKit] Advertencia: Falta DOCTYPE")

            # Verificar tags mínimos (no siempre están, pero es buena práctica)
            has_html = '<html' in html_lower
            has_body = '<body' in html_lower

            if not has_html:
                print("[WebKit] Advertencia: No se encontró tag <html>")

            # Verificar balance básico de tags críticos
            critical_tags = ['html', 'head', 'body']
            for tag in critical_tags:
                open_count = html_lower.count(f'<{tag}')
                close_count = html_lower.count(f'</{tag}>')

                if open_count > 0 and close_count > 0 and open_count != close_count:
                    return {
                        'valid': False,
                        'error': f'Tag <{tag}> desbalanceado: {open_count} aperturas, {close_count} cierres'
                    }

            return {'valid': True, 'error': None}

        except Exception as e:
            return {'valid': False, 'error': f'Error validando: {str(e)}'}

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

        # NO usar set_transient_for para permitir maximizar
        # self.fullscreen_window.set_transient_for(self.main_window)

        # Configurar propiedades de la ventana para que sea maximizable
        self.fullscreen_window.set_deletable(True)
        self.fullscreen_window.set_resizable(True)

        # Header bar
        preview_headerbar = Adw.HeaderBar()
        preview_title = self._get_preview_title()
        preview_headerbar.set_title_widget(Gtk.Label(label=preview_title))

        # Agregar doble click para maximizar/restaurar
        gesture_click = Gtk.GestureClick()
        gesture_click.set_button(1)  # Botón izquierdo del ratón
        gesture_click.connect('pressed', self._on_headerbar_double_click)
        preview_headerbar.add_controller(gesture_click)

        # Botones del header
        self._setup_fullscreen_buttons(preview_headerbar)
        
        # WebView independiente
        self.fullscreen_web_view = WebKit.WebView()

        # Configurar WebView para ser más tolerante con errores
        settings = self.fullscreen_web_view.get_settings()
        settings.set_enable_javascript(True)
        settings.set_enable_developer_extras(False)

        # Conectar señales de error
        self.fullscreen_web_view.connect('load-failed', self._on_load_failed)
        self.fullscreen_web_view.connect('load-changed', self._on_load_changed)

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

        # Conectar eventos
        self.fullscreen_window.connect('destroy', self._on_fullscreen_destroyed)

        # Listener para detectar cambios en el estado de maximizado
        # (cuando el usuario usa el botón nativo del WM)
        self.fullscreen_window.connect('notify::maximized', self._on_maximize_state_changed)

        # Mostrar ventana
        self.fullscreen_window.present()

        # Sincronizar contenido inicial con pequeño delay para asegurar que WebKit esté listo
        GLib.timeout_add(100, self._sync_fullscreen_content_delayed)
    
    def _setup_fullscreen_buttons(self, headerbar: Adw.HeaderBar):
        """Configura los botones del header de la ventana fullscreen"""

        # Botón navegador externo (lado izquierdo)
        external_btn = Gtk.Button()
        external_btn.set_icon_name("web-browser-symbolic")
        external_btn.set_tooltip_text("Abrir en navegador externo")
        external_btn.connect('clicked', self._on_open_external)
        headerbar.pack_start(external_btn)

        # Botón recargar (lado derecho)
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Recargar previsualización")
        refresh_btn.connect('clicked', self._on_refresh_fullscreen)
        headerbar.pack_end(refresh_btn)

        # Botón maximizar/restaurar (lado derecho)
        self.maximize_btn = Gtk.Button()
        self.maximize_btn.set_icon_name("view-fullscreen-symbolic")
        self.maximize_btn.set_tooltip_text("Maximizar ventana")
        self.maximize_btn.connect('clicked', self._on_toggle_maximize)
        headerbar.pack_end(self.maximize_btn)
    
    def _get_preview_title(self) -> str:
        """Obtiene el título para la ventana de previsualización"""
        if self.main_window.current_resource:
            try:
                mi = self.main_window.core._get_item(self.main_window.current_resource)
                return f"Vista previa: {Path(mi.href).name}"
            except:
                pass
        return "Vista previa"
    
    def _sync_fullscreen_content_delayed(self):
        """Sincroniza el contenido con delay (llamado por timeout)"""
        self._sync_fullscreen_content()
        return False  # No repetir el timeout

    def _sync_fullscreen_content(self):
        """Sincroniza el contenido del WebView principal con el fullscreen"""
        if not self._is_fullscreen_active():
            print("[Fullscreen] No está activo")
            return

        if not self.main_window.core or not self.main_window.current_resource:
            print("[Fullscreen] No hay core o recurso")
            self.fullscreen_web_view.load_html("<h1>Sin contenido</h1><p>No hay documento seleccionado para mostrar.</p>", None)
            return

        try:
            # Solo previsualizar documentos HTML
            if not self.main_window.current_resource.endswith(('.html', '.xhtml', '.htm')):
                print(f"[Fullscreen] Tipo no soportado: {self.main_window.current_resource}")
                self.fullscreen_web_view.load_html("<p>Este tipo de archivo no se puede previsualizar.</p>", None)
                return

            # Leer el contenido del recurso actual
            content = self.main_window.core.read_text(self.main_window.current_resource)
            print(f"[Fullscreen] Contenido leído: {len(content)} caracteres")

            # Crear archivo de preview y cargarlo
            preview_file_path = self._get_preview_file_path(self.main_window.current_resource)
            preview_file_path.write_text(content, encoding='utf-8')

            file_uri = preview_file_path.as_uri()
            print(f"[Fullscreen] Cargando URI: {file_uri}")
            self.fullscreen_web_view.load_uri(file_uri)

        except Exception as e:
            print(f"[Fullscreen] Error sincronizando: {e}")
            import traceback
            traceback.print_exc()
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
    def _on_close_fullscreen(self, button):
        """Cierra la ventana fullscreen de forma segura"""
        print("[Fullscreen] Botón cerrar presionado")

        if not self.fullscreen_window:
            return

        try:
            # Detener WebView antes de cerrar
            if hasattr(self, 'fullscreen_web_view') and self.fullscreen_web_view:
                self.fullscreen_web_view.stop_loading()

            # Destruir la ventana
            self.fullscreen_window.close()
            print("[Fullscreen] Ventana cerrada")

        except Exception as e:
            print(f"[Fullscreen] Error cerrando ventana: {e}")
            # Forzar limpieza manual
            self._on_fullscreen_destroyed(None)

    def _on_refresh_fullscreen(self, button):
        """Recarga la previsualización fullscreen"""
        self._sync_fullscreen_content()

    def _on_toggle_maximize(self, button):
        """Alterna entre maximizar y restaurar la ventana"""
        if not self.fullscreen_window:
            print("[Fullscreen] No hay ventana fullscreen activa")
            return

        try:
            is_max = self.fullscreen_window.is_maximized()
            print(f"[Fullscreen] Estado actual: is_maximized={is_max}")

            if is_max:
                print("[Fullscreen] Restaurando ventana...")
                self.fullscreen_window.unmaximize()
            else:
                print("[Fullscreen] Maximizando ventana...")
                self.fullscreen_window.maximize()

            # Verificar después de intentar maximizar
            GLib.timeout_add(200, self._check_maximize_state)

        except Exception as e:
            print(f"[Fullscreen] Error toggling maximize: {e}")
            import traceback
            traceback.print_exc()

    def _check_maximize_state(self):
        """Verifica el estado de maximizado después de un cambio"""
        if self.fullscreen_window:
            is_max = self.fullscreen_window.is_maximized()
            print(f"[Fullscreen] Estado después de toggle: is_maximized={is_max}")
        return False  # No repetir

    def _on_headerbar_double_click(self, gesture, n_press, x, y):
        """Maneja doble click en el headerbar para maximizar/restaurar"""
        if n_press == 2:  # Solo en doble click
            self._on_toggle_maximize(None)

    def _on_maximize_state_changed(self, window, param):
        """Actualiza el icono del botón cuando cambia el estado de maximizado"""
        if not hasattr(self, 'maximize_btn'):
            return

        try:
            is_maximized = window.is_maximized()
            print(f"[Fullscreen] Estado maximizado cambió a: {is_maximized}")

            if is_maximized:
                self.maximize_btn.set_icon_name("view-restore-symbolic")
                self.maximize_btn.set_tooltip_text("Restaurar ventana")
            else:
                self.maximize_btn.set_icon_name("view-fullscreen-symbolic")
                self.maximize_btn.set_tooltip_text("Maximizar ventana")
        except Exception as e:
            print(f"[Fullscreen] Error actualizando icono: {e}")

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
        print("[Fullscreen] Destruyendo ventana fullscreen...")

        # Detener cualquier carga en progreso
        if hasattr(self, 'fullscreen_web_view') and self.fullscreen_web_view:
            try:
                self.fullscreen_web_view.stop_loading()
                print("[Fullscreen] WebView detenido")
            except Exception as e:
                print(f"[Fullscreen] Error deteniendo WebView: {e}")

        # Limpiar referencias
        self.fullscreen_window = None

        # Limpiar WebView de fullscreen
        if hasattr(self, 'fullscreen_web_view'):
            try:
                delattr(self, 'fullscreen_web_view')
            except:
                pass

        print("[Fullscreen] Ventana fullscreen destruida")
    
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