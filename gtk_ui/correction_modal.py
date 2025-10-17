"""
GutenAI - Modal de corrección ortográfica y gramatical
Integración con Gemini 1.5 para corrección inteligente
"""

from gi.repository import Gtk, Adw, GLib, Pango
from pathlib import Path
from typing import Optional, TYPE_CHECKING
import json
import threading

from .gemini_corrector import GeminiCorrector, extraer_texto_html

if TYPE_CHECKING:
    from .main_window import GutenAIWindow


class CorrectionModal(Adw.Window):
    """Modal para corrección de texto con IA"""

    def __init__(self, parent_window: 'GutenAIWindow', api_key: str):
        super().__init__()

        self.parent_window = parent_window
        self.corrector = GeminiCorrector(api_key)
        self.original_html = ""
        self.texto_limpio = ""
        self.resultado_correccion = None

        self._setup_ui()
        self._connect_signals()

        # Configurar ventana
        self.set_title("GutenAI - Corrector Inteligente")
        self.set_default_size(1100, 750)
        self.set_modal(True)
        self.set_transient_for(parent_window)

    def _setup_ui(self):
        """Configura la interfaz de la modal"""

        # HeaderBar
        header_bar = Adw.HeaderBar()
        header_bar.set_title_widget(Gtk.Label(label="Corrector Inteligente"))

        # Botón cancelar
        cancel_btn = Gtk.Button(label="Cancelar")
        cancel_btn.connect('clicked', self._on_cancel)
        header_bar.pack_start(cancel_btn)

        # Botón aplicar (inicialmente deshabilitado)
        self.apply_btn = Gtk.Button(label="Aplicar Correcciones")
        self.apply_btn.set_css_classes(["suggested-action"])
        self.apply_btn.set_sensitive(False)
        self.apply_btn.connect('clicked', self._on_apply_corrections)
        header_bar.pack_end(self.apply_btn)

        # Contenido principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Toast overlay para mensajes
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(main_box)

        # Toolbar con información y controles
        self._create_info_toolbar(main_box)

        # Panel dividido: original vs corregido
        self._create_comparison_panel(main_box)

        # Panel de errores encontrados
        self._create_errors_panel(main_box)

        # Configurar ventana
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header_bar)
        toolbar_view.set_content(self.toast_overlay)
        self.set_content(toolbar_view)

    def _create_info_toolbar(self, parent_box):
        """Crea la barra de información y controles"""

        info_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        info_bar.set_margin_start(12)
        info_bar.set_margin_end(12)
        info_bar.set_margin_top(12)
        info_bar.set_margin_bottom(6)

        # Información de uso de API
        self.usage_label = Gtk.Label()
        self.usage_label.set_css_classes(["caption"])
        self._update_usage_info()

        # Botón correccir
        self.correct_btn = Gtk.Button(label="Corregir con IA")
        self.correct_btn.set_css_classes(["suggested-action"])
        self.correct_btn.connect('clicked', self._on_start_correction)

        # Spinner para indicar procesamiento
        self.spinner = Gtk.Spinner()

        info_bar.append(self.usage_label)
        info_bar.append(Gtk.Box())  # Espaciador
        info_bar.append(self.spinner)
        info_bar.append(self.correct_btn)

        parent_box.append(info_bar)

    def _create_comparison_panel(self, parent_box):
        """Crea el panel de comparación texto original vs corregido"""

        # Grupo de comparación
        comparison_group = Adw.PreferencesGroup()
        comparison_group.set_title("Comparación de Texto")
        comparison_group.set_margin_start(12)
        comparison_group.set_margin_end(12)

        # Paned horizontal para dividir original vs corregido
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_resize_start_child(True)
        paned.set_resize_end_child(True)
        paned.set_shrink_start_child(False)
        paned.set_shrink_end_child(False)

        # Panel izquierdo - Texto original
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left_label = Gtk.Label(label="Texto Original")
        left_label.set_css_classes(["heading"])
        left_label.set_halign(Gtk.Align.START)

        self.original_textview = Gtk.TextView()
        self.original_textview.set_editable(False)
        self.original_textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.original_textview.set_vexpand(True)

        original_scroll = Gtk.ScrolledWindow()
        original_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        original_scroll.set_child(self.original_textview)
        original_scroll.set_min_content_height(300)

        left_box.append(left_label)
        left_box.append(original_scroll)

        # Panel derecho - Texto corregido
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        right_label = Gtk.Label(label="Texto Corregido")
        right_label.set_css_classes(["heading"])
        right_label.set_halign(Gtk.Align.START)

        self.corrected_textview = Gtk.TextView()
        self.corrected_textview.set_editable(True)
        self.corrected_textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.corrected_textview.set_vexpand(True)

        corrected_scroll = Gtk.ScrolledWindow()
        corrected_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        corrected_scroll.set_child(self.corrected_textview)
        corrected_scroll.set_min_content_height(300)

        right_box.append(right_label)
        right_box.append(corrected_scroll)

        # Configurar paned
        paned.set_start_child(left_box)
        paned.set_end_child(right_box)
        paned.set_position(400)  # Posición inicial del divisor

        comparison_group.add(paned)
        parent_box.append(comparison_group)

    def _create_errors_panel(self, parent_box):
        """Crea el panel de errores encontrados"""

        # Grupo de errores
        errors_group = Adw.PreferencesGroup()
        errors_group.set_title("Errores Encontrados")
        errors_group.set_margin_start(12)
        errors_group.set_margin_end(12)
        errors_group.set_margin_bottom(12)

        # Lista de errores
        self.errors_listbox = Gtk.ListBox()
        self.errors_listbox.set_css_classes(["boxed-list"])
        self.errors_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.errors_listbox.connect('row-selected', self._on_error_selected)

        errors_scroll = Gtk.ScrolledWindow()
        errors_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        errors_scroll.set_min_content_height(200)
        errors_scroll.set_max_content_height(300)
        errors_scroll.set_child(self.errors_listbox)

        errors_group.add(errors_scroll)
        parent_box.append(errors_group)

    def _connect_signals(self):
        """Conecta señales de la interfaz"""
        self.connect('close-request', self._on_close_request)

        # Configurar tags de resaltado para los TextViews
        self._setup_text_highlighting()

    def show_for_text(self, html_content: str):
        """Muestra la modal para corregir el texto dado"""
        self.original_html = html_content

        # Extraer texto limpio del HTML
        self.texto_limpio = extraer_texto_html(html_content)

        # Mostrar texto original
        buffer = self.original_textview.get_buffer()
        buffer.set_text(self.texto_limpio)

        # Limpiar panel corregido
        corrected_buffer = self.corrected_textview.get_buffer()
        corrected_buffer.set_text("")

        # Limpiar errores
        self._clear_errors_list()

        # Actualizar estado
        self.resultado_correccion = None
        self.apply_btn.set_sensitive(False)
        self.correct_btn.set_sensitive(True)

        # Mostrar modal
        self.present()

    def _setup_text_highlighting(self):
        """Configura tags de resaltado para los TextViews"""

        # Tags para el texto original
        original_buffer = self.original_textview.get_buffer()

        # Tag para resaltar errores en texto original
        self.tag_error_original = original_buffer.create_tag(
            "error_highlight",
            background="#ffebee",  # Rojo muy claro
            foreground="#c62828"   # Rojo oscuro
        )

        # Tags para el texto corregido
        corrected_buffer = self.corrected_textview.get_buffer()

        # Tag para resaltar correcciones en texto corregido
        self.tag_correction = corrected_buffer.create_tag(
            "correction_highlight",
            background="#e8f5e8",  # Verde muy claro
            foreground="#2e7d32"   # Verde oscuro
        )

        # Tag para resaltar correcciones deshabilitadas
        self.tag_correction_disabled = corrected_buffer.create_tag(
            "correction_disabled",
            background="#f5f5f5",  # Gris muy claro
            foreground="#9e9e9e",  # Gris oscuro
            strikethrough=True     # Tachado
        )

    def _on_error_selected(self, listbox, row):
        """Maneja la selección de un error en la lista"""
        if not row:
            self._clear_highlights()
            return

        # Obtener el error asociado a esta fila
        error_data = getattr(row, 'error_data', None)
        if not error_data:
            return

        # Resaltar el error en ambos paneles
        self._highlight_error_in_texts(error_data)

    def _highlight_error_in_texts(self, error_data):
        """Resalta un error específico en ambos paneles de texto"""

        # Limpiar resaltados anteriores
        self._clear_highlights()

        original_text = error_data.get('original', '')
        corrected_text = error_data.get('corregido', '')

        if not original_text:
            return

        # Resaltar en texto original
        self._highlight_text_in_buffer(
            self.original_textview.get_buffer(),
            original_text,
            self.tag_error_original
        )

        # Resaltar en texto corregido (verificar si está habilitado)
        if corrected_text:
            # Verificar si esta corrección está habilitada
            row = self.errors_listbox.get_selected_row()
            is_enabled = True
            if row and hasattr(row, 'correction_checkbox'):
                is_enabled = row.correction_checkbox.get_active()

            tag_to_use = self.tag_correction if is_enabled else self.tag_correction_disabled

            self._highlight_text_in_buffer(
                self.corrected_textview.get_buffer(),
                corrected_text,
                tag_to_use
            )

    def _highlight_text_in_buffer(self, buffer, search_text, tag):
        """Busca y resalta texto en un buffer específico"""

        # Obtener todo el texto del buffer
        start_iter = buffer.get_start_iter()
        end_iter = buffer.get_end_iter()
        full_text = buffer.get_text(start_iter, end_iter, False)

        # Buscar todas las ocurrencias
        search_lower = search_text.lower()
        full_lower = full_text.lower()

        start_pos = 0
        found_positions = []

        while True:
            pos = full_lower.find(search_lower, start_pos)
            if pos == -1:
                break
            found_positions.append((pos, pos + len(search_text)))
            start_pos = pos + 1

        # Aplicar resaltado a todas las ocurrencias
        for start_pos, end_pos in found_positions:
            start_iter = buffer.get_iter_at_offset(start_pos)
            end_iter = buffer.get_iter_at_offset(end_pos)
            buffer.apply_tag(tag, start_iter, end_iter)

            # Desplazar vista a la primera ocurrencia
            if found_positions.index((start_pos, end_pos)) == 0:
                # Scroll a la posición del error
                if hasattr(self.original_textview, 'scroll_to_iter'):
                    self.original_textview.scroll_to_iter(start_iter, 0.0, False, 0.0, 0.0)
                if hasattr(self.corrected_textview, 'scroll_to_iter'):
                    self.corrected_textview.scroll_to_iter(start_iter, 0.0, False, 0.0, 0.0)

    def _clear_highlights(self):
        """Limpia todos los resaltados de ambos paneles"""

        # Limpiar texto original
        original_buffer = self.original_textview.get_buffer()
        start_iter = original_buffer.get_start_iter()
        end_iter = original_buffer.get_end_iter()
        original_buffer.remove_tag(self.tag_error_original, start_iter, end_iter)

        # Limpiar texto corregido
        corrected_buffer = self.corrected_textview.get_buffer()
        start_iter = corrected_buffer.get_start_iter()
        end_iter = corrected_buffer.get_end_iter()
        corrected_buffer.remove_tag(self.tag_correction, start_iter, end_iter)
        corrected_buffer.remove_tag(self.tag_correction_disabled, start_iter, end_iter)

    def _on_correction_toggled(self, checkbox, correction_index):
        """Maneja cuando se marca/desmarca una corrección"""
        # Actualizar la vista de texto corregido basándose en las selecciones
        self._update_corrected_text_preview()

    def _update_corrected_text_preview(self):
        """Actualiza el texto corregido basándose en las correcciones seleccionadas"""
        if not self.resultado_correccion:
            return

        # Obtener texto original
        texto_base = self.texto_limpio

        # Aplicar solo las correcciones seleccionadas
        errores_seleccionados = []

        # Recorrer todas las filas de errores
        child = self.errors_listbox.get_first_child()
        while child:
            if hasattr(child, 'correction_checkbox') and hasattr(child, 'error_data'):
                if child.correction_checkbox.get_active():
                    errores_seleccionados.append(child.error_data)
            child = child.get_next_sibling()

        # Aplicar solo las correcciones seleccionadas
        texto_con_correcciones = self._aplicar_correcciones_selectivas(texto_base, errores_seleccionados)

        # Actualizar el panel derecho
        corrected_buffer = self.corrected_textview.get_buffer()
        corrected_buffer.set_text(texto_con_correcciones)

        # Actualizar el resaltado si hay una fila seleccionada
        selected_row = self.errors_listbox.get_selected_row()
        if selected_row and hasattr(selected_row, 'error_data'):
            self._highlight_error_in_texts(selected_row.error_data)

    def _aplicar_correcciones_selectivas(self, texto_original: str, errores_seleccionados: list) -> str:
        """Aplica solo las correcciones seleccionadas al texto"""
        texto_resultado = texto_original

        # Ordenar errores por posición (de atrás hacia adelante para no alterar posiciones)
        errores_ordenados = sorted(errores_seleccionados,
                                 key=lambda e: e.get("posicion_inicio", 0),
                                 reverse=True)

        for error in errores_ordenados:
            original = error.get("original", "")
            corregido = error.get("corregido", "")

            if original and corregido and original in texto_resultado:
                # Reemplazar primera ocurrencia para ser más preciso
                texto_resultado = texto_resultado.replace(original, corregido, 1)

        return texto_resultado

    def _on_start_correction(self, button):
        """Inicia el proceso de corrección con IA"""
        if not self.texto_limpio.strip():
            self._show_toast("No hay texto para corregir")
            return

        # Deshabilitar botón y mostrar spinner
        button.set_sensitive(False)
        self.spinner.start()

        # Ejecutar corrección en hilo separado
        def correction_thread():
            try:
                resultado = self.corrector.corregir_texto(self.texto_limpio, idioma="es")

                # Actualizar UI en hilo principal
                GLib.idle_add(self._on_correction_completed, resultado)

            except Exception as e:
                GLib.idle_add(self._on_correction_error, str(e))

        threading.Thread(target=correction_thread, daemon=True).start()

    def _on_correction_completed(self, resultado):
        """Callback cuando la corrección se completa exitosamente"""

        # Detener spinner y rehabilitar botón
        self.spinner.stop()
        self.correct_btn.set_sensitive(True)

        # Guardar resultado
        self.resultado_correccion = resultado

        # Mostrar texto corregido
        corrected_buffer = self.corrected_textview.get_buffer()
        corrected_buffer.set_text(resultado["texto_corregido"])

        # Limpiar resaltados anteriores
        self._clear_highlights()

        # Mostrar errores encontrados
        self._show_errors(resultado["errores_encontrados"])

        # Habilitar botón aplicar si hay cambios
        if resultado["cambios_aplicados"] > 0:
            self.apply_btn.set_sensitive(True)
            self._show_toast(f"✓ {resultado['cambios_aplicados']} errores corregidos ({resultado['fuente']})")
        else:
            self._show_toast("✓ No se encontraron errores (texto correcto)")

        # Actualizar información de uso
        self._update_usage_info()

    def _on_correction_error(self, error_message):
        """Callback cuando hay error en la corrección"""

        # Detener spinner y rehabilitar botón
        self.spinner.stop()
        self.correct_btn.set_sensitive(True)

        # Mostrar error
        self._show_toast(f"Error: {error_message}")

    def _show_errors(self, errores: list):
        """Muestra la lista de errores encontrados"""

        # Limpiar lista actual
        self._clear_errors_list()

        if not errores:
            # Mostrar mensaje de no errores
            no_errors_row = Adw.ActionRow()
            no_errors_row.set_title("No se encontraron errores")
            no_errors_row.set_subtitle("El texto parece estar correcto")
            self.errors_listbox.append(no_errors_row)
            return

        # Agregar cada error con checkbox para selección individual
        for i, error in enumerate(errores):
            error_row = Adw.ActionRow()

            # Formato más claro mostrando antes y después
            original = error.get('original', '')
            corregido = error.get('corregido', '')
            error_row.set_title(f"'{original}' → '{corregido}'")
            error_row.set_subtitle(f"{error.get('tipo', 'error').title()}: {error.get('razon', '')}")

            # Checkbox para seleccionar si aplicar esta corrección
            checkbox = Gtk.CheckButton()
            checkbox.set_active(True)  # Por defecto todas seleccionadas
            checkbox.set_valign(Gtk.Align.CENTER)
            checkbox.connect('toggled', self._on_correction_toggled, i)
            error_row.add_prefix(checkbox)

            # Icono según tipo de error
            icon_name = self._get_error_icon(error.get('tipo', ''))
            if icon_name:
                icon = Gtk.Image.new_from_icon_name(icon_name)
                error_row.add_suffix(icon)

            # Asociar datos del error con la fila para el resaltado
            error_row.error_data = error
            error_row.correction_checkbox = checkbox
            error_row.correction_index = i

            self.errors_listbox.append(error_row)

    def _get_error_icon(self, tipo_error: str) -> str:
        """Retorna el icono apropiado para el tipo de error"""
        icons = {
            "ortografia": "tools-check-spelling-symbolic",
            "gramatica": "document-edit-symbolic",
            "puntuacion": "insert-text-symbolic"
        }
        return icons.get(tipo_error, "dialog-warning-symbolic")

    def _clear_errors_list(self):
        """Limpia la lista de errores"""
        # Limpiar resaltados cuando se limpia la lista
        self._clear_highlights()

        child = self.errors_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.errors_listbox.remove(child)
            child = next_child

    def _on_apply_corrections(self, button):
        """Aplica las correcciones al documento original"""
        if not self.resultado_correccion:
            return

        # Obtener texto editado del panel derecho (por si el usuario hizo cambios)
        corrected_buffer = self.corrected_textview.get_buffer()
        start_iter = corrected_buffer.get_start_iter()
        end_iter = corrected_buffer.get_end_iter()
        final_text = corrected_buffer.get_text(start_iter, end_iter, False)

        # Aplicar el texto corregido al HTML original
        # NOTA: Aquí necesitarías implementar la lógica para reemplazar
        # el contenido de texto en el HTML preservando las etiquetas
        try:
            # Por simplicidad, reemplazamos todo el contenido del editor
            # Una implementación más sofisticada preservaría mejor el HTML
            if hasattr(self.parent_window, 'central_editor'):
                self.parent_window.central_editor.set_text(
                    self._integrate_text_to_html(self.original_html, final_text)
                )

            self._show_toast(f"✓ Correcciones aplicadas ({self.resultado_correccion['cambios_aplicados']} cambios)")

            # Cerrar modal después de aplicar
            GLib.timeout_add(1000, self.close)

        except Exception as e:
            self._show_toast(f"Error aplicando correcciones: {e}")

    def _integrate_text_to_html(self, html_original: str, texto_corregido: str) -> str:
        """
        Integra el texto corregido preservando la estructura HTML original.
        """
        try:
            from bs4 import BeautifulSoup
            import re

            # Parsear HTML original
            soup_original = BeautifulSoup(html_original, 'html.parser')

            # Extraer texto original para mapear cambios
            texto_original_limpio = self._extraer_texto_preservando_estructura(soup_original)

            # Si el texto no cambió mucho, aplicar cambios palabra por palabra
            if self._textos_similares(texto_original_limpio, texto_corregido):
                return self._aplicar_cambios_preservando_estructura(soup_original, texto_original_limpio, texto_corregido)
            else:
                # Si cambió mucho, usar método más conservador
                return self._reemplazar_texto_conservando_html(html_original, texto_corregido)

        except ImportError:
            # Fallback básico
            return self._reemplazar_texto_conservando_html(html_original, texto_corregido)

    def _extraer_texto_preservando_estructura(self, soup):
        """Extrae texto manteniendo información de estructura SOLO del body"""

        # Buscar solo el contenido del body
        body = soup.find('body')
        if body is None:
            # Si no hay body, usar todo el soup pero ignorar head
            head = soup.find('head')
            if head:
                # No modificar el original, crear copia
                soup_copy = soup.__copy__()
                head_copy = soup_copy.find('head')
                if head_copy:
                    head_copy.decompose()
                body = soup_copy
            else:
                body = soup

        elementos_texto = []

        # Buscar elementos que contienen texto SOLO en el body
        for elemento in body.find_all(['p', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            if elemento.get_text(strip=True):
                elementos_texto.append(elemento.get_text(strip=True))

        # Si no hay elementos estructurados, extraer todo el texto del body
        if not elementos_texto:
            return body.get_text(separator=' ', strip=True)

        return '\n\n'.join(elementos_texto)

    def _textos_similares(self, original: str, corregido: str) -> bool:
        """Verifica si los textos son suficientemente similares para preservar estructura"""
        import difflib
        similitud = difflib.SequenceMatcher(None, original, corregido).ratio()
        return similitud > 0.7  # 70% similar

    def _aplicar_cambios_preservando_estructura(self, soup, texto_original: str, texto_corregido: str):
        """Aplica cambios manteniendo la estructura HTML existente"""
        import difflib

        # Crear mapeo de cambios
        differ = difflib.unified_diff(
            texto_original.splitlines(keepends=True),
            texto_corregido.splitlines(keepends=True),
            lineterm=''
        )

        # Por simplicidad, reemplazar contenido de texto manteniendo etiquetas
        elementos_con_texto = soup.find_all(['p', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

        if elementos_con_texto:
            # Dividir texto corregido en párrafos
            parrafos_corregidos = [p.strip() for p in texto_corregido.split('\n\n') if p.strip()]

            # Aplicar a elementos existentes
            for i, elemento in enumerate(elementos_con_texto):
                if i < len(parrafos_corregidos):
                    # Preservar atributos del elemento pero cambiar contenido
                    elemento.clear()
                    elemento.string = parrafos_corregidos[i]

        return str(soup)

    def _reemplazar_texto_conservando_html(self, html_original: str, texto_corregido: str) -> str:
        """Método más conservador que preserva estructura básica"""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_original, 'html.parser')

            # Buscar body o contenedor principal
            body = soup.find('body')
            if not body:
                # Si no hay body, buscar div principal o usar el html completo
                body = soup.find('div') or soup

            # Preservar head si existe
            head = soup.find('head')

            # Crear nueva estructura preservando elementos importantes
            parrafos = [p.strip() for p in texto_corregido.split('\n\n') if p.strip()]

            # Limpiar solo elementos de texto, preservar head, meta, etc.
            for elemento in body.find_all(['p', 'div'], recursive=False):
                if elemento.name in ['p', 'div'] and elemento.get_text(strip=True):
                    elemento.decompose()

            # Agregar párrafos corregidos
            for parrafo in parrafos:
                if parrafo.strip():
                    p_tag = soup.new_tag('p')
                    p_tag.string = parrafo.strip()
                    body.append(p_tag)

            return str(soup)

        except:
            # Fallback ultra-básico que al menos mantiene algo de estructura
            parrafos = [p.strip() for p in texto_corregido.split('\n\n') if p.strip()]
            html_parrafos = ''.join(f'<p>{p}</p>\n' for p in parrafos)

            # Intentar preservar head del original
            if '<head>' in html_original and '</head>' in html_original:
                start = html_original.find('<head>')
                end = html_original.find('</head>') + 7
                head_original = html_original[start:end]
                return f'<html>{head_original}<body>{html_parrafos}</body></html>'
            else:
                return f'<html><body>{html_parrafos}</body></html>'

    def _update_usage_info(self):
        """Actualiza la información de uso de la API"""
        try:
            stats = self.corrector.obtener_estadisticas()
            self.usage_label.set_text(
                f"Consultas: {stats['consultas_realizadas']}/{stats['consultas_restantes'] + stats['consultas_realizadas']} "
                f"| Cache: {stats['cache_entradas']} entradas"
            )
        except:
            self.usage_label.set_text("Información de uso no disponible")

    def _show_toast(self, message: str):
        """Muestra un mensaje toast"""
        toast = Adw.Toast()
        toast.set_title(message)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)

    def _on_cancel(self, button):
        """Cancela la corrección y cierra la modal"""
        self.close()

    def _on_close_request(self, window):
        """Maneja el cierre de la ventana"""
        # Detener spinner si está activo
        self.spinner.stop()
        return False


def integrate_correction_modal_with_editor(central_editor):
    """Integra la modal de corrección con el editor central"""

    # Agregar acción de corrección al editor
    from gi.repository import Gio

    correction_action = Gio.SimpleAction.new("ai_correction", None)
    correction_action.connect("activate", lambda a, p: _show_correction_modal(central_editor))
    central_editor.main_window.add_action(correction_action)

    print("[GutenAI] Modal de corrección integrada. Usa Ctrl+Shift+F7 o menú contextual.")


def _show_correction_modal(central_editor):
    """Muestra la modal de corrección para el texto actual"""

    # Verificar que hay contenido
    current_text = central_editor.get_current_text()
    if not current_text.strip():
        central_editor.main_window.show_error("No hay contenido para corregir")
        return

    # Obtener API key de configuración
    from .settings_manager import get_settings
    settings = get_settings()

    if not settings.is_gemini_enabled():
        central_editor.main_window.show_error("Corrección con IA deshabilitada. Ve a Preferencias para configurar.")
        return

    api_key = settings.get_gemini_api_key()
    if not api_key:
        central_editor.main_window.show_error("Configura tu API key de Gemini en Preferencias")
        return

    try:
        # Crear y mostrar modal
        modal = CorrectionModal(central_editor.main_window, api_key)
        modal.show_for_text(current_text)

    except Exception as e:
        central_editor.main_window.show_error(f"Error abriendo corrector: {e}")