"""
gtk_ui/smart_hook_inserter.py
Sistema de inserción inteligente de hooks (anclajes/id) en HTML

Características:
- Normalización automática de texto a ID válido
- Detección inteligente de bloque vs fragmento
- Validación de duplicados con sufijos incrementales
- Popover de confirmación con sugerencia editable
- Marcadores visuales en preview
"""

import re
import unicodedata
from gi.repository import Gtk, GLib, Gdk, Gio
from typing import Optional, Tuple
from bs4 import BeautifulSoup


class SmartHookInserter:
    """
    Gestor de inserción inteligente de hooks en el editor HTML
    """

    def __init__(self, central_editor):
        """
        Inicializa el insertor de hooks

        Args:
            central_editor: Instancia de CentralEditor
        """
        self.central_editor = central_editor
        self.main_window = central_editor.main_window

        # Diálogo de confirmación (NO usar Popover por problemas de grab)
        self.hook_dialog: Optional[Gtk.Window] = None
        self.hook_popover: Optional[Gtk.Popover] = None  # Mantener para destrucción si existe
        self.hook_entry: Optional[Gtk.Entry] = None

        # Estado temporal
        self._pending_selection: Optional[Tuple[int, int]] = None  # (start_offset, end_offset)
        self._suggested_id: Optional[str] = None

    # =====================================================
    # NORMALIZACIÓN DE TEXTO A ID
    # =====================================================

    def _extract_text_content(self, html_text: str) -> str:
        """
        Extrae solo el contenido de texto, eliminando todos los tags HTML

        Args:
            html_text: Texto que puede contener HTML (ej: "<h1>Título</h1>")

        Returns:
            Solo el texto sin tags (ej: "Título")
        """
        try:
            # Usar BeautifulSoup para extraer texto limpio
            soup = BeautifulSoup(html_text, 'lxml')
            text = soup.get_text(strip=True)
            return text if text else html_text
        except:
            # Fallback: regex simple para quitar tags
            import re
            text = re.sub(r'<[^>]+>', '', html_text)
            return text.strip()

    def normalize_text_to_id(self, text: str) -> str:
        """
        Convierte texto arbitrario en un ID válido para HTML

        Proceso:
        1. Quita tildes y diacríticos
        2. Convierte a minúsculas
        3. Reemplaza espacios y caracteres no alfanuméricos por guiones
        4. Elimina guiones consecutivos
        5. Limpia guiones al inicio/final

        Args:
            text: Texto original (ej: "El Inicio de la Batalla")

        Returns:
            ID normalizado (ej: "el-inicio-de-la-batalla")
        """
        # 1. Normalización NFD para separar diacríticos
        text = unicodedata.normalize('NFD', text)

        # 2. Remover caracteres diacríticos (tildes, acentos, etc.)
        text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')

        # 3. Convertir a minúsculas
        text = text.lower()

        # 4. Reemplazar caracteres no alfanuméricos por guiones
        # Mantener solo: a-z, 0-9, y convertir todo lo demás en guiones
        text = re.sub(r'[^a-z0-9]+', '-', text)

        # 5. Eliminar guiones consecutivos
        text = re.sub(r'-+', '-', text)

        # 6. Limpiar guiones al inicio y final
        text = text.strip('-')

        # 7. Si quedó vacío, generar ID genérico
        if not text:
            text = "hook"

        return text

    # =====================================================
    # VALIDACIÓN Y RESOLUCIÓN DE DUPLICADOS
    # =====================================================

    def ensure_unique_id(self, proposed_id: str, current_file: str) -> str:
        """
        Asegura que el ID sea único en el archivo actual

        Si el ID ya existe, agrega sufijo incremental: -2, -3, etc.

        Args:
            proposed_id: ID propuesto
            current_file: Archivo actual (href)

        Returns:
            ID único garantizado
        """
        if not self.main_window.core or not hasattr(self.main_window.core, 'hook_index'):
            return proposed_id

        hook_index = self.main_window.core.hook_index

        # Verificar si existe en el archivo actual
        if not hook_index.hook_exists(proposed_id, current_file):
            return proposed_id

        # Buscar sufijo disponible
        counter = 2
        while True:
            candidate = f"{proposed_id}-{counter}"
            if not hook_index.hook_exists(candidate, current_file):
                return candidate
            counter += 1

            # Límite de seguridad
            if counter > 100:
                # Usar timestamp como último recurso
                import time
                return f"{proposed_id}-{int(time.time() * 1000)}"

    # =====================================================
    # DETECCIÓN DE CONTEXTO (BLOQUE VS FRAGMENTO)
    # =====================================================

    def detect_selection_context(self, start_offset: int, end_offset: int, html_content: str) -> dict:
        """
        Analiza la selección para determinar si es bloque o fragmento

        Args:
            start_offset: Offset de inicio de la selección
            end_offset: Offset de fin de la selección
            html_content: Contenido HTML completo del archivo

        Returns:
            {
                "type": "block" | "fragment",
                "parent_tag": str (ej: "p", "h2", "div") si es block,
                "selected_text": str,
                "block_start": int (offset donde empieza el tag de apertura),
                "block_end": int (offset donde termina el tag de cierre)
            }
        """
        # Extraer el texto seleccionado
        selected_text = html_content[start_offset:end_offset]

        # Tags de bloque que queremos detectar
        block_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'section', 'blockquote', 'li', 'td', 'th']

        try:
            # Estrategia 1: Verificar si la selección incluye UN tag completo
            # (empieza con <tag y termina con </tag>)
            stripped = selected_text.strip()
            if stripped.startswith('<') and stripped.endswith('>'):
                # Intentar extraer el tag name del inicio
                tag_match = re.match(r'<([a-zA-Z][a-zA-Z0-9]*)', stripped)
                if tag_match:
                    tag_name = tag_match.group(1)
                    # Verificar que termina con el tag de cierre correspondiente
                    if stripped.endswith(f'</{tag_name}>') and tag_name in block_tags:
                        return {
                            "type": "block",
                            "parent_tag": tag_name,
                            "selected_text": selected_text,
                            "block_start": start_offset,
                            "block_end": end_offset
                        }

            # Estrategia 2: Buscar hacia atrás el tag de apertura más cercano
            # Esto detecta cuando seleccionas el CONTENIDO de un tag pero no el tag mismo
            # Ejemplo: seleccionas "texto aquí" dentro de <p>texto aquí</p>

            # Buscar hacia atrás desde start_offset
            search_start = max(0, start_offset - 500)  # Buscar hasta 500 chars atrás
            before_selection = html_content[search_start:start_offset]

            # Buscar el último tag de apertura antes de la selección
            opening_tags = re.finditer(r'<(' + '|'.join(block_tags) + r')(\s+[^>]*)?>', before_selection)
            last_opening = None
            last_opening_tag = None
            for match in opening_tags:
                last_opening = search_start + match.start()
                last_opening_tag = match.group(1)

            if last_opening is not None:
                # Buscar el tag de cierre correspondiente después de la selección
                search_end = min(len(html_content), end_offset + 500)
                after_selection = html_content[end_offset:search_end]

                closing_pattern = f'</{last_opening_tag}>'
                closing_match = re.search(re.escape(closing_pattern), after_selection)

                if closing_match:
                    closing_pos = end_offset + closing_match.end()

                    # Verificar que no hay otros tags del mismo tipo entre medio (anidamiento)
                    between = html_content[last_opening:closing_pos]
                    nested_count = between.count(f'<{last_opening_tag}') - 1  # -1 por el tag de apertura inicial

                    if nested_count == 0:
                        # No hay anidamiento, la selección está dentro de este tag
                        return {
                            "type": "block",
                            "parent_tag": last_opening_tag,
                            "selected_text": selected_text,
                            "block_start": last_opening,
                            "block_end": closing_pos
                        }

            # Por defecto, considerar FRAGMENTO
            return {
                "type": "fragment",
                "parent_tag": None,
                "selected_text": selected_text,
                "block_start": None,
                "block_end": None
            }

        except Exception as e:
            print(f"[SmartHook] Error detectando contexto: {e}")
            import traceback
            traceback.print_exc()
            # Fallback: considerar fragmento
            return {
                "type": "fragment",
                "parent_tag": None,
                "selected_text": selected_text,
                "block_start": None,
                "block_end": None
            }

    # =====================================================
    # INYECCIÓN DE HOOK EN HTML
    # =====================================================

    def get_hook_operation(self, html_content: str, start_offset: int, end_offset: int, hook_id: str) -> Tuple[int, int, str]:
        """
        Calcula la operación necesaria para inyectar el hook
        
        Args:
            html_content: Contenido HTML completo
            start_offset: Inicio de la selección
            end_offset: Fin de la selección
            hook_id: ID a insertar
            
        Returns:
            (replace_start, replace_end, replacement_text)
        """
        context = self.detect_selection_context(start_offset, end_offset, html_content)
        
        selected_text = context["selected_text"]
        
        if context["type"] == "block":
            # MODO BLOQUE: Agregar id al tag existente
            return self._calculate_block_hook_op(html_content, start_offset, end_offset, hook_id, context)
        else:
            # MODO FRAGMENTO: Envolver en <span id="...">
            return self._calculate_fragment_hook_op(start_offset, end_offset, hook_id, selected_text)

    def _calculate_block_hook_op(self, html: str, start: int, end: int, hook_id: str, context: dict) -> Tuple[int, int, str]:
        """
        Calcula la operación para inyectar hook en bloque
        """
        # Obtener los límites del bloque
        block_start = context.get('block_start')
        block_end = context.get('block_end')
        
        # Siempre usar block_start/block_end si están disponibles
        if block_start is not None and block_end is not None:
            search_offset = block_start
            search_text = html[block_start:block_end]
        else:
            # Fallback: buscar en la selección
            search_offset = start
            search_text = html[start:end]
            
        # Buscar el tag de apertura
        match = re.search(r'<([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>', search_text)
        
        if not match:
            return self._calculate_fragment_hook_op(start, end, hook_id, html[start:end])
            
        tag_attrs = match.group(2)
        tag_offset = search_offset + match.start()
        tag_full = match.group(0)
        tag_name = match.group(1)
        
        # Verificar si ya tiene id
        if re.search(r'\bid\s*=', tag_attrs):
            # Ya tiene id, reemplazar
            new_attrs = re.sub(r'\bid\s*=\s*["\']?[^"\'>\s]*["\']?', f'id="{hook_id}"', tag_attrs)
        else:
            # Agregar id
            new_attrs = f'{tag_attrs} id="{hook_id}"'.strip()
            
        # Reconstruir tag
        new_tag = f'<{tag_name} {new_attrs}>'
        
        return (tag_offset, tag_offset + len(tag_full), new_tag)

    def _calculate_fragment_hook_op(self, start: int, end: int, hook_id: str, selected_text: str) -> Tuple[int, int, str]:
        """
        Calcula la operación para envolver fragmento
        """
        # Crear span con id
        wrapped = f'<span id="{hook_id}">{selected_text}</span>'
        return (start, end, wrapped)

    # =====================================================
    # INTERFAZ DE USUARIO (POPOVER)
    # =====================================================

    def show_hook_insertion_dialog(self):
        """
        Muestra el popover de inserción de hook sobre la selección actual
        """
        buffer = self.central_editor.source_buffer

        # Verificar que hay selección
        if not buffer.get_has_selection():
            self.main_window.show_error("Selecciona texto para crear un hook")
            return

        # Obtener selección
        start_iter, end_iter = buffer.get_selection_bounds()
        selected_text = buffer.get_text(start_iter, end_iter, False)

        # Guardar offsets para posterior inserción
        self._pending_selection = (start_iter.get_offset(), end_iter.get_offset())

        # Limpiar tags HTML del texto antes de normalizarlo
        clean_text = self._extract_text_content(selected_text)

        # Generar sugerencia de ID
        suggested_id = self.normalize_text_to_id(clean_text)
        suggested_id = self.ensure_unique_id(
            suggested_id,
            self.main_window.current_resource
        )
        self._suggested_id = suggested_id

        # Crear o actualizar popover
        self._create_hook_popover(start_iter, end_iter, suggested_id)

    def _create_hook_popover(self, start_iter, end_iter, suggested_id: str):
        """
        Crea el popover de confirmación de hook
        """
        # DESTRUIR diálogo/popover anterior completamente para evitar problemas de estado
        if self.hook_dialog:
            self.hook_dialog.destroy()
            self.hook_dialog = None
            self.hook_entry = None

        if self.hook_popover:
            self.hook_popover.unparent()
            self.hook_popover = None

        # Crear nuevo popover desde cero
        # SOLUCIÓN AL BUG: Usar Adw.Dialog en lugar de Popover para evitar grab issues
        from gi.repository import Adw

        # Cambiar a usar un diálogo simple en lugar de popover
        self.hook_dialog = Adw.Window()
        self.hook_dialog.set_transient_for(self.main_window)
        self.hook_dialog.set_modal(False)  # NO modal para evitar grab
        self.hook_dialog.set_default_size(400, 200)
        self.hook_dialog.set_resizable(False)
        self.hook_dialog.set_title("Crear Hook (Anclaje)")

        # Conectar señal de cierre
        self.hook_dialog.connect('close-request', self._on_dialog_closed)

        # Contenedor
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)

        # Título
        title = Gtk.Label()
        title.set_markup("<b>Crear Hook (Anclaje)</b>")
        title.set_halign(Gtk.Align.START)
        box.append(title)

        # Label explicativo
        desc = Gtk.Label()
        desc.set_text("ID sugerido (editable):")
        desc.set_halign(Gtk.Align.START)
        desc.add_css_class("dim-label")
        box.append(desc)

        # Entry para el ID
        self.hook_entry = Gtk.Entry()
        self.hook_entry.set_text(suggested_id)
        self.hook_entry.set_width_chars(30)
        self.hook_entry.select_region(0, -1)  # Seleccionar todo para fácil edición
        box.append(self.hook_entry)

        # Botones
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_halign(Gtk.Align.END)

        cancel_btn = Gtk.Button(label="Cancelar")
        cancel_btn.connect('clicked', self._on_cancel_hook)
        button_box.append(cancel_btn)

        insert_btn = Gtk.Button(label="Insertar Hook")
        insert_btn.add_css_class("suggested-action")
        insert_btn.connect('clicked', self._on_insert_hook_confirmed)
        button_box.append(insert_btn)

        box.append(button_box)

        # Conectar Enter en el entry
        self.hook_entry.connect('activate', self._on_insert_hook_confirmed)

        # Configurar diálogo
        self.hook_dialog.set_content(box)

        # Mostrar
        self.hook_dialog.present()

        # Enfocar el entry
        GLib.timeout_add(100, lambda: self.hook_entry.grab_focus())

    def _on_dialog_closed(self, dialog):
        """Callback cuando el diálogo se cierra - limpieza completa"""
        # Restaurar foco al editor
        GLib.timeout_add(50, lambda: (self.central_editor.source_view.grab_focus(), False)[1])
        return False  # Permitir que se cierre

    def _on_cancel_hook(self, widget):
        """Cancela la inserción del hook y devuelve el foco al editor"""
        self.hook_dialog.close()

    def _on_insert_hook_confirmed(self, widget):
        """
        Callback cuando el usuario confirma la inserción del hook
        """
        if not self._pending_selection or not self.hook_entry:
            return

        # Obtener ID final (puede haber sido editado)
        hook_id = self.hook_entry.get_text().strip()

        if not hook_id:
            self.main_window.show_error("El ID no puede estar vacío")
            return

        # Validar que el ID sea válido (HTML ID rules)
        if not re.match(r'^[a-zA-Z][\w:.-]*$', hook_id):
            self.main_window.show_error("ID inválido. Debe empezar con letra y contener solo letras, números, guiones, puntos o dos puntos")
            return

        # Verificar unicidad
        if (self.main_window.core and
            hasattr(self.main_window.core, 'hook_index') and
            self.main_window.core.hook_index.hook_exists(hook_id, self.main_window.current_resource)):

            # Preguntar si desea continuar
            response = self.main_window.show_question(
                f"El ID '{hook_id}' ya existe en este archivo.\n¿Deseas crear un duplicado de todas formas?"
            )
            if not response:
                return

        # Insertar hook
        self._insert_hook(hook_id)

        # Cerrar diálogo (el callback 'close-request' restaurará el foco)
        self.hook_dialog.close()

    def _insert_hook(self, hook_id: str):
        """
        Inserta el hook en el HTML usando operaciones de buffer para soportar UNDO
        """
        start_offset, end_offset = self._pending_selection
        buffer = self.central_editor.source_buffer
        
        # Obtener contenido completo para análisis
        full_text = self.central_editor.get_current_text()
        
        # Calcular operación
        replace_start, replace_end, new_text = self.get_hook_operation(
            full_text,
            start_offset,
            end_offset,
            hook_id
        )
        
        # Ejecutar cambios con soporte para UNDO
        buffer.begin_user_action()
        try:
            # 1. Borrar texto original
            start_iter = buffer.get_iter_at_offset(replace_start)
            end_iter = buffer.get_iter_at_offset(replace_end)
            buffer.delete(start_iter, end_iter)
            
            # 2. Insertar nuevo texto (hook)
            start_iter = buffer.get_iter_at_offset(replace_start)
            buffer.insert(start_iter, new_text)
            
            # 3. Posicionar cursor al final de la inserción
            new_cursor_offset = replace_start + len(new_text)
            new_iter = buffer.get_iter_at_offset(new_cursor_offset)
            buffer.place_cursor(new_iter)
            
        finally:
            buffer.end_user_action()
            
        # Actualizar preview y estado (fuera del user action)
        
        # Actualizar el estado de auto-guardado
        if hasattr(self.central_editor, '_needs_save'):
            self.central_editor._needs_save = True
            
        # Actualizar preview
        if hasattr(self.central_editor, '_update_preview_after_edit'):
            self.central_editor._update_preview_after_edit()
            
        # Mostrar confirmación
        self.main_window.show_info(f"Hook '{hook_id}' creado exitosamente")
        
        # Forzar guardado y re-indexación inmediata
        if self.main_window.core:
            # Obtener texto actualizado del buffer
            final_text = self.central_editor.get_current_text()
            
            # Guardar el archivo
            self.main_window.core.write_text(self.main_window.current_resource, final_text)
            
            # Re-indexar
            if hasattr(self.main_window.core, 'hook_index'):
                self.main_window.core.hook_index.update_file_index(
                    self.main_window.current_resource
                )


def integrate_smart_hook_inserter(central_editor):
    """
    Integra el sistema de hooks inteligentes con el editor central

    Args:
        central_editor: Instancia de CentralEditor
    """
    # Crear instancia
    hook_inserter = SmartHookInserter(central_editor)

    # Guardar referencia
    central_editor.smart_hook_inserter = hook_inserter

    # Registrar acción
    insert_hook_action = Gio.SimpleAction.new("insert_smart_hook", None)
    insert_hook_action.connect("activate", lambda a, p: hook_inserter.show_hook_insertion_dialog())
    central_editor.main_window.add_action(insert_hook_action)

    # Agregar atajo de teclado (Ctrl+K)
    if hasattr(central_editor.main_window, 'application') and central_editor.main_window.application:
        central_editor.main_window.application.set_accels_for_action(
            "win.insert_smart_hook",
            ["<Primary>k"]
        )

    return hook_inserter
