"""
ui/split_chapter_dialog.py
Diálogo para dividir un capítulo en dos archivos HTML
"""
from . import *
from gi.repository import Gtk, Adw, GLib, GtkSource
from pathlib import Path
from typing import TYPE_CHECKING
import re

if TYPE_CHECKING:
    from .main_window import GutenAIWindow


class SplitChapterDialog(Adw.Window):
    """Diálogo para dividir un capítulo en dos archivos"""

    def __init__(self, main_window: 'GutenAIWindow'):
        super().__init__()

        self.main_window = main_window
        self.core = main_window.core

        if not self.core:
            return

        # Verificar que hay un documento actual
        if not main_window.current_resource:
            return

        self.current_href = main_window.current_resource

        # Obtener posición del cursor
        buffer = main_window.central_editor.source_buffer
        cursor_iter = buffer.get_iter_at_mark(buffer.get_insert())
        self.split_offset = cursor_iter.get_offset()

        # Leer contenido HTML actual
        self.html_content = self.core.read_text(self.current_href)

        # Configuración de ventana
        self.set_title("Dividir Capítulo")
        self.set_default_size(700, 600)
        self.set_modal(True)
        self.set_transient_for(main_window)

        # Crear interfaz
        self._setup_ui()

        # Generar nombres por defecto
        self._generate_default_names()

    def _setup_ui(self):
        """Configura la interfaz del diálogo"""

        # HeaderBar
        header_bar = Adw.HeaderBar()

        # Botón cerrar
        close_btn = Gtk.Button(label="Cancelar")
        close_btn.connect('clicked', lambda b: self.close())
        header_bar.pack_start(close_btn)

        # Botón dividir
        self.split_btn = Gtk.Button(label="Dividir Capítulo")
        self.split_btn.add_css_class("suggested-action")
        self.split_btn.connect('clicked', self._on_split)
        header_bar.pack_end(self.split_btn)

        # ScrolledWindow para el contenido
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        # Box principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scrolled.set_child(main_box)

        # Toast overlay
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(scrolled)

        # === INFORMACIÓN ===
        info_group = Adw.PreferencesGroup()
        info_group.set_title("Información")
        info_group.set_margin_start(12)
        info_group.set_margin_end(12)
        info_group.set_margin_top(12)

        # Archivo actual
        current_row = Adw.ActionRow()
        current_row.set_title("Archivo actual")
        current_label = Gtk.Label(label=Path(self.current_href).name)
        current_label.add_css_class("monospace")
        current_row.add_suffix(current_label)
        info_group.add(current_row)

        # Posición de división
        position_row = Adw.ActionRow()
        position_row.set_title("División en el carácter")
        position_label = Gtk.Label(label=f"{self.split_offset} de {len(self.html_content)}")
        position_label.add_css_class("monospace")
        position_row.add_suffix(position_label)
        info_group.add(position_row)

        main_box.append(info_group)

        # === CONFIGURACIÓN DE NOMBRES ===
        names_group = Adw.PreferencesGroup()
        names_group.set_title("Nombres de los Archivos")
        names_group.set_description("Define los nombres para los dos archivos resultantes")
        names_group.set_margin_start(12)
        names_group.set_margin_end(12)
        names_group.set_margin_top(12)

        # Primer archivo (parte 1)
        self.file1_entry = Adw.EntryRow()
        self.file1_entry.set_title("Primer archivo (inicio → cursor)")
        self.file1_entry.connect('changed', self._on_name_changed)
        names_group.add(self.file1_entry)

        # Segundo archivo (parte 2)
        self.file2_entry = Adw.EntryRow()
        self.file2_entry.set_title("Segundo archivo (cursor → final)")
        self.file2_entry.connect('changed', self._on_name_changed)
        names_group.add(self.file2_entry)

        main_box.append(names_group)

        # === VISTA PREVIA ===
        preview_group = Adw.PreferencesGroup()
        preview_group.set_title("Vista Previa del Contenido")
        preview_group.set_margin_start(12)
        preview_group.set_margin_end(12)
        preview_group.set_margin_top(12)
        preview_group.set_margin_bottom(12)

        # Crear vista previa del contenido
        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        preview_box.set_margin_start(12)
        preview_box.set_margin_end(12)
        preview_box.set_margin_top(12)
        preview_box.set_margin_bottom(12)

        # Primer archivo preview
        file1_label = Gtk.Label(label="Contenido del primer archivo:")
        file1_label.add_css_class("heading")
        file1_label.set_halign(Gtk.Align.START)
        preview_box.append(file1_label)

        file1_scroll = Gtk.ScrolledWindow()
        file1_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        file1_scroll.set_min_content_height(120)
        file1_scroll.set_max_content_height(120)

        self.file1_preview = Gtk.TextView()
        self.file1_preview.set_editable(False)
        self.file1_preview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.file1_preview.add_css_class("monospace")
        file1_scroll.set_child(self.file1_preview)
        preview_box.append(file1_scroll)

        # Separador
        separator = Gtk.Separator()
        separator.set_margin_top(6)
        separator.set_margin_bottom(6)
        preview_box.append(separator)

        # Segundo archivo preview
        file2_label = Gtk.Label(label="Contenido del segundo archivo:")
        file2_label.add_css_class("heading")
        file2_label.set_halign(Gtk.Align.START)
        preview_box.append(file2_label)

        file2_scroll = Gtk.ScrolledWindow()
        file2_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        file2_scroll.set_min_content_height(120)
        file2_scroll.set_max_content_height(120)

        self.file2_preview = Gtk.TextView()
        self.file2_preview.set_editable(False)
        self.file2_preview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.file2_preview.add_css_class("monospace")
        file2_scroll.set_child(self.file2_preview)
        preview_box.append(file2_scroll)

        preview_group.add(Adw.PreferencesRow(child=preview_box))
        main_box.append(preview_group)

        # ToolbarView
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header_bar)
        toolbar_view.set_content(self.toast_overlay)
        self.set_content(toolbar_view)

        # Generar vista previa inicial
        self._update_preview()

    def _generate_default_names(self):
        """Genera nombres por defecto para los archivos"""
        current_name = Path(self.current_href).stem
        extension = Path(self.current_href).suffix

        # Intentar detectar si tiene número al final
        match = re.search(r'(.*?)(\d+)$', current_name)

        if match:
            prefix = match.group(1)
            number = int(match.group(2))
            # Calcular dígitos necesarios
            digits = len(match.group(2))

            # Generar nombres
            name1 = f"{prefix}{str(number).zfill(digits)}a{extension}"
            name2 = f"{prefix}{str(number).zfill(digits)}b{extension}"
        else:
            # Sin número, agregar sufijos
            name1 = f"{current_name}_parte1{extension}"
            name2 = f"{current_name}_parte2{extension}"

        self.file1_entry.set_text(name1)
        self.file2_entry.set_text(name2)

    def _on_name_changed(self, entry):
        """Se llama cuando cambian los nombres"""
        # Validar que no estén vacíos
        name1 = self.file1_entry.get_text().strip()
        name2 = self.file2_entry.get_text().strip()

        valid = bool(name1 and name2 and name1 != name2)
        self.split_btn.set_sensitive(valid)

    def _update_preview(self):
        """Actualiza la vista previa del contenido"""
        # Dividir el contenido en el punto del cursor
        part1 = self.html_content[:self.split_offset]
        part2 = self.html_content[self.split_offset:]

        # Mostrar primeros caracteres de cada parte
        preview_length = 500

        buffer1 = self.file1_preview.get_buffer()
        preview1 = part1[-preview_length:] if len(part1) > preview_length else part1
        if len(part1) > preview_length:
            preview1 = "...\n" + preview1
        buffer1.set_text(preview1)

        buffer2 = self.file2_preview.get_buffer()
        preview2 = part2[:preview_length] if len(part2) > preview_length else part2
        if len(part2) > preview_length:
            preview2 = preview2 + "\n..."
        buffer2.set_text(preview2)

    def _on_split(self, button):
        """Realiza la división del capítulo"""
        name1 = self.file1_entry.get_text().strip()
        name2 = self.file2_entry.get_text().strip()

        if not name1 or not name2:
            self._show_toast("Los nombres no pueden estar vacíos")
            return

        if name1 == name2:
            self._show_toast("Los nombres deben ser diferentes")
            return

        try:
            print(f"\n[SplitChapter] Dividiendo {self.current_href}")
            print(f"[SplitChapter] Archivo 1: {name1}")
            print(f"[SplitChapter] Archivo 2: {name2}")
            print(f"[SplitChapter] Punto de división: {self.split_offset}")

            # Dividir el contenido HTML
            part1_content, part2_content = self._split_html_content()

            # Obtener directorio del archivo actual
            current_path = Path(self.current_href)
            target_dir = current_path.parent

            # Construir hrefs completos
            href1 = str(target_dir / name1)
            href2 = str(target_dir / name2)

            print(f"[SplitChapter] Nuevo href 1: {href1}")
            print(f"[SplitChapter] Nuevo href 2: {href2}")

            # Obtener el idref del documento actual
            current_idref = None
            spine = self.core.get_spine()
            for idref in spine:
                item = self.core._get_item(idref)
                if item.href == self.current_href:
                    current_idref = idref
                    break

            if not current_idref:
                raise Exception("No se pudo encontrar el documento en el spine")

            # Renombrar el archivo actual al primer nombre
            print(f"[SplitChapter] Renombrando archivo actual a: {name1}")
            self.core.rename_item(self.current_href, name1, update_references=False)

            # Actualizar el contenido del primer archivo
            print(f"[SplitChapter] Escribiendo contenido del archivo 1")
            self.core.write_text(href1, part1_content)

            # Crear el segundo archivo
            print(f"[SplitChapter] Creando segundo archivo: {name2}")
            # Escribir el contenido del archivo
            self.core.write_text(href2, part2_content)

            # Agregar al manifest
            new_id = self.core._unique_id(Path(name2).stem)
            new_item = self.core.add_to_manifest(
                new_id,
                href2,
                media_type="application/xhtml+xml"
            )
            new_idref = new_item.id

            # Insertar el segundo archivo en el spine después del primero
            print(f"[SplitChapter] Insertando en spine después de {current_idref}")
            spine_position = spine.index(current_idref)

            # Reordenar spine para poner el nuevo archivo después del primero
            new_spine = spine[:spine_position + 1] + [new_idref] + spine[spine_position + 1:]

            # Si el nuevo idref ya estaba en el spine (al final), quitarlo de ahí
            if new_spine.count(new_idref) > 1:
                # Buscar la segunda ocurrencia y eliminarla
                first_index = new_spine.index(new_idref)
                second_index = new_spine.index(new_idref, first_index + 1)
                new_spine.pop(second_index)

            self.core.set_spine(new_spine)

            print(f"[SplitChapter] División completada exitosamente")

            # Actualizar interfaz
            self.main_window.sidebar_left.populate_tree()

            # Abrir el primer archivo
            self.main_window.set_current_resource(href1, name1)

            # Mostrar mensaje de éxito
            self._show_toast(f"Capítulo dividido en {name1} y {name2}")

            # Cerrar diálogo
            GLib.timeout_add(1500, self.close)

        except Exception as e:
            print(f"[SplitChapter] ERROR: {e}")
            import traceback
            traceback.print_exc()

            error_dialog = Adw.MessageDialog(transient_for=self, modal=True)
            error_dialog.set_heading("Error al Dividir")
            error_dialog.set_body(f"Ocurrió un error al dividir el capítulo:\n\n{str(e)}")
            error_dialog.add_response("ok", "OK")
            error_dialog.present()

    def _split_html_content(self) -> tuple[str, str]:
        """
        Divide el contenido HTML en dos partes, intentando mantener
        la estructura HTML válida en ambos archivos
        """
        import xml.etree.ElementTree as ET

        # Intentar parsear el HTML de forma más robusta
        # Buscar las partes principales del documento

        # 1. Extraer declaración XML si existe
        xml_declaration = ""
        xml_match = re.search(r'(<\?xml[^>]*\?>)', self.html_content, re.IGNORECASE)
        if xml_match:
            xml_declaration = xml_match.group(1) + "\n"

        # 2. Extraer DOCTYPE
        doctype = ""
        doctype_match = re.search(r'(<!DOCTYPE[^>]*>)', self.html_content, re.DOTALL | re.IGNORECASE)
        if doctype_match:
            doctype = doctype_match.group(1) + "\n"

        # 3. Extraer tag <html> de apertura con sus atributos
        html_open = "<html>"
        html_match = re.search(r'(<html[^>]*>)', self.html_content, re.IGNORECASE)
        if html_match:
            html_open = html_match.group(1) + "\n"

        # 4. Extraer todo el <head>
        head = ""
        head_match = re.search(r'(<head[^>]*>.*?</head>)', self.html_content, re.DOTALL | re.IGNORECASE)
        if head_match:
            head = head_match.group(1) + "\n"

        # 5. Extraer tag <body> de apertura
        body_open = "<body>"
        body_open_match = re.search(r'(<body[^>]*>)', self.html_content, re.IGNORECASE)
        if body_open_match:
            body_open = body_open_match.group(1) + "\n"

        # 6. Encontrar el contenido del body
        body_start_match = re.search(r'<body[^>]*>', self.html_content, re.IGNORECASE)
        body_end_match = re.search(r'</body>', self.html_content, re.IGNORECASE)

        if body_start_match and body_end_match:
            body_start = body_start_match.end()
            body_end = body_end_match.start()
            body_content = self.html_content[body_start:body_end]

            # Calcular offset relativo al contenido del body
            split_in_body = self.split_offset - body_start

            if 0 <= split_in_body <= len(body_content):
                # Dividir el contenido del body
                body_part1 = body_content[:split_in_body]
                body_part2 = body_content[split_in_body:]

                # Construir archivo 1
                file1_content = (
                    xml_declaration +
                    doctype +
                    html_open +
                    head +
                    body_open +
                    body_part1 +
                    "\n</body>\n</html>"
                )

                # Construir archivo 2
                file2_content = (
                    xml_declaration +
                    doctype +
                    html_open +
                    head +
                    body_open +
                    body_part2 +
                    "\n</body>\n</html>"
                )

                return file1_content, file2_content

        # Fallback: usar template básico
        print("[SplitChapter] WARNING: No se pudo parsear HTML, usando división simple")

        part1_body = self.html_content[:self.split_offset]
        part2_body = self.html_content[self.split_offset:]

        # Usar template mínimo similar al de create_document
        template = """<?xml version='1.0' encoding='UTF-8'?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="es" xml:lang="es">
<head>
  <title>{title}</title>
  <meta charset="utf-8"/>
</head>
<body>
{content}
</body>
</html>"""

        file1_content = template.format(title="Parte 1", content=part1_body)
        file2_content = template.format(title="Parte 2", content=part2_body)

        return file1_content, file2_content

    def _show_toast(self, message: str):
        """Muestra un mensaje toast"""
        toast = Adw.Toast()
        toast.set_title(message)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)


def show_split_chapter_dialog(main_window: 'GutenAIWindow'):
    """Muestra el diálogo de división de capítulo"""
    if not main_window.core:
        main_window.show_error("No hay ningún proyecto abierto")
        return

    if not main_window.current_resource:
        main_window.show_error("No hay ningún documento abierto")
        return

    # Verificar que el archivo actual es un documento HTML
    current_href = main_window.current_resource
    if not current_href.endswith('.html') and not current_href.endswith('.xhtml'):
        main_window.show_error("Solo se pueden dividir documentos HTML")
        return

    dialog = SplitChapterDialog(main_window)
    dialog.present()
