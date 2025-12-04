"""
ui/global_search_replace_dialog.py
Diálogo para buscar y reemplazar en todo el libro
"""
from . import *
from gi.repository import Gtk, Adw, GLib
from pathlib import Path
from typing import TYPE_CHECKING, List, Tuple
import re

if TYPE_CHECKING:
    from .main_window import GutenAIWindow


class GlobalSearchReplaceDialog(Adw.Window):
    """Diálogo para buscar y reemplazar texto en todos los documentos del libro"""

    def __init__(self, main_window: 'GutenAIWindow'):
        super().__init__()

        self.main_window = main_window
        self.core = main_window.core

        if not self.core:
            return

        # Configuración de ventana
        self.set_title("Buscar y Reemplazar en Todo el Libro")
        self.set_default_size(800, 600)
        self.set_modal(True)
        self.set_transient_for(main_window)

        # Variables
        self.search_results = []  # Lista de (href, line_num, line_text, match_start, match_end)
        self.use_regex = False
        self.case_sensitive = False

        # Crear interfaz
        self._setup_ui()

    def _setup_ui(self):
        """Configura la interfaz del diálogo"""

        # HeaderBar
        header_bar = Adw.HeaderBar()

        # Botón cerrar
        close_btn = Gtk.Button(label="Cerrar")
        close_btn.connect('clicked', lambda b: self.close())
        header_bar.pack_start(close_btn)

        # Box principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Toast overlay
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(main_box)

        # === SECCIÓN DE BÚSQUEDA ===
        search_group = Adw.PreferencesGroup()
        search_group.set_title("Buscar y Reemplazar")
        search_group.set_margin_start(12)
        search_group.set_margin_end(12)
        search_group.set_margin_top(12)

        # Campo de búsqueda
        self.search_entry = Adw.EntryRow()
        self.search_entry.set_title("Buscar")
        search_group.add(self.search_entry)

        # Campo de reemplazo
        self.replace_entry = Adw.EntryRow()
        self.replace_entry.set_title("Reemplazar con")
        search_group.add(self.replace_entry)

        # Opciones
        options_row = Adw.ActionRow()
        options_row.set_title("Opciones")

        options_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        options_box.set_margin_top(6)
        options_box.set_margin_bottom(6)

        # Checkbox sensible a mayúsculas
        self.case_check = Gtk.CheckButton(label="Sensible a mayúsculas")
        self.case_check.connect('toggled', lambda cb: setattr(self, 'case_sensitive', cb.get_active()))
        options_box.append(self.case_check)

        # Checkbox regex
        self.regex_check = Gtk.CheckButton(label="Usar expresiones regulares")
        self.regex_check.connect('toggled', lambda cb: setattr(self, 'use_regex', cb.get_active()))
        options_box.append(self.regex_check)

        options_row.add_suffix(options_box)
        search_group.add(options_row)

        # Botones de acción
        buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        buttons_box.set_margin_start(12)
        buttons_box.set_margin_end(12)
        buttons_box.set_margin_top(6)
        buttons_box.set_margin_bottom(6)
        buttons_box.set_halign(Gtk.Align.END)

        # Botón buscar
        search_btn = Gtk.Button(label="Buscar")
        search_btn.add_css_class("suggested-action")
        search_btn.connect('clicked', self._on_search)
        buttons_box.append(search_btn)

        # Botón reemplazar todo
        self.replace_all_btn = Gtk.Button(label="Reemplazar Todo")
        self.replace_all_btn.set_sensitive(False)
        self.replace_all_btn.connect('clicked', self._on_replace_all)
        buttons_box.append(self.replace_all_btn)

        search_group.add(Adw.PreferencesRow(child=buttons_box))
        main_box.append(search_group)

        # === RESULTADOS ===
        results_group = Adw.PreferencesGroup()
        results_group.set_title("Resultados")
        results_group.set_margin_start(12)
        results_group.set_margin_end(12)
        results_group.set_margin_top(12)
        results_group.set_margin_bottom(12)

        # Label de contador
        self.results_label = Gtk.Label(label="")
        self.results_label.set_halign(Gtk.Align.START)
        self.results_label.add_css_class("dim-label")
        self.results_label.set_margin_start(12)
        self.results_label.set_margin_bottom(6)
        results_group.add(Adw.PreferencesRow(child=self.results_label))

        # ScrolledWindow para resultados
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_min_content_height(300)

        # ListBox para resultados
        self.results_listbox = Gtk.ListBox()
        self.results_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.results_listbox.add_css_class("boxed-list")
        self.results_listbox.connect('row-activated', self._on_result_activated)
        scrolled.set_child(self.results_listbox)

        results_group.add(Adw.PreferencesRow(child=scrolled))
        main_box.append(results_group)

        # ToolbarView
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header_bar)
        toolbar_view.set_content(self.toast_overlay)
        self.set_content(toolbar_view)

    def _on_search(self, button):
        """Busca en todos los documentos del libro"""
        search_text = self.search_entry.get_text()

        if not search_text:
            self._show_toast("Ingresa un texto para buscar")
            return

        # Limpiar resultados anteriores
        self.search_results = []
        while True:
            row = self.results_listbox.get_row_at_index(0)
            if row is None:
                break
            self.results_listbox.remove(row)

        # Buscar en todos los documentos del spine
        spine = self.core.get_spine()
        total_matches = 0

        for idref in spine:
            item = self.core._get_item(idref)
            href = item.href

            # Solo buscar en documentos HTML
            if not href.endswith(('.html', '.xhtml', '.htm')):
                continue

            try:
                content = self.core.read_text(href)
                matches = self._find_matches(content, search_text)

                if matches:
                    total_matches += len(matches)
                    for line_num, line_text, match_start, match_end in matches:
                        self.search_results.append((href, line_num, line_text, match_start, match_end))
                        self._add_result_row(href, line_num, line_text, match_start, match_end, search_text)

            except Exception as e:
                print(f"[GlobalSearch] Error buscando en {href}: {e}")

        # Actualizar label de resultados
        if total_matches == 0:
            self.results_label.set_text("No se encontraron coincidencias")
            self.replace_all_btn.set_sensitive(False)
        elif total_matches == 1:
            self.results_label.set_text("1 coincidencia encontrada")
            self.replace_all_btn.set_sensitive(True)
        else:
            self.results_label.set_text(f"{total_matches} coincidencias encontradas")
            self.replace_all_btn.set_sensitive(True)

    def _find_matches(self, content: str, search_text: str) -> List[Tuple[int, str, int, int]]:
        """Encuentra todas las coincidencias en el contenido"""
        matches = []
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            if self.use_regex:
                # Usar expresiones regulares
                try:
                    flags = 0 if self.case_sensitive else re.IGNORECASE
                    pattern = re.compile(search_text, flags)
                    for match in pattern.finditer(line):
                        matches.append((line_num, line, match.start(), match.end()))
                except re.error as e:
                    self._show_toast(f"Error en expresión regular: {e}")
                    return []
            else:
                # Búsqueda simple
                search_in = line if self.case_sensitive else line.lower()
                search_for = search_text if self.case_sensitive else search_text.lower()

                start = 0
                while True:
                    pos = search_in.find(search_for, start)
                    if pos == -1:
                        break
                    matches.append((line_num, line, pos, pos + len(search_text)))
                    start = pos + 1

        return matches

    def _add_result_row(self, href: str, line_num: int, line_text: str, match_start: int, match_end: int, search_text: str):
        """Agrega una fila de resultado"""
        row = Gtk.ListBoxRow()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        # Archivo y línea
        file_label = Gtk.Label()
        file_label.set_markup(f"<b>{Path(href).name}</b> — Línea {line_num}")
        file_label.set_halign(Gtk.Align.START)
        file_label.add_css_class("caption")
        box.append(file_label)

        # Contexto con el match resaltado
        # Mostrar hasta 100 caracteres alrededor del match
        context_start = max(0, match_start - 50)
        context_end = min(len(line_text), match_end + 50)
        context = line_text[context_start:context_end].strip()

        # Ajustar posiciones del match en el contexto
        adjusted_start = match_start - context_start
        adjusted_end = match_end - context_start

        # Crear label con markup
        before = GLib.markup_escape_text(context[:adjusted_start])
        match = GLib.markup_escape_text(context[adjusted_start:adjusted_end])
        after = GLib.markup_escape_text(context[adjusted_end:])

        context_label = Gtk.Label()
        context_label.set_markup(f"{before}<span background='yellow' foreground='black'><b>{match}</b></span>{after}")
        context_label.set_halign(Gtk.Align.START)
        context_label.set_ellipsize(3)  # ELLIPSIZE_END
        context_label.set_max_width_chars(80)
        context_label.add_css_class("monospace")
        box.append(context_label)

        row.set_child(box)

        # Guardar datos en la fila
        row.href = href
        row.line_num = line_num

        self.results_listbox.append(row)

    def _on_result_activated(self, listbox, row):
        """Abre el archivo y va a la línea del resultado"""
        if hasattr(row, 'href'):
            # Abrir el archivo
            self.main_window.set_current_resource(row.href, Path(row.href).name)

            # TODO: Ir a la línea específica (requiere implementar scroll a línea en el editor)
            self._show_toast(f"Abriendo {Path(row.href).name}")

    def _on_replace_all(self, button):
        """Reemplaza todas las coincidencias"""
        search_text = self.search_entry.get_text()
        replace_text = self.replace_entry.get_text()

        if not search_text:
            self._show_toast("Ingresa un texto para buscar")
            return

        if not self.search_results:
            self._show_toast("Primero realiza una búsqueda")
            return

        # Confirmar con el usuario
        total_matches = len(self.search_results)

        dialog = Adw.MessageDialog(transient_for=self, modal=True)
        dialog.set_heading("Confirmar reemplazo")
        dialog.set_body(f"¿Reemplazar {total_matches} coincidencia(s) en todo el libro?\n\n"
                       f"Buscar: {search_text}\n"
                       f"Reemplazar con: {replace_text}")

        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("replace", "Reemplazar Todo")
        dialog.set_response_appearance("replace", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def on_response(dlg, response):
            if response == "replace":
                self._perform_replace_all(search_text, replace_text)

        dialog.connect("response", on_response)
        dialog.present()

    def _perform_replace_all(self, search_text: str, replace_text: str):
        """Realiza el reemplazo en todos los archivos"""
        try:
            # Agrupar por archivo
            files_to_modify = {}
            for href, line_num, line_text, match_start, match_end in self.search_results:
                if href not in files_to_modify:
                    files_to_modify[href] = []
                files_to_modify[href].append((line_num, line_text, match_start, match_end))

            total_replacements = 0

            # Procesar cada archivo
            for href, matches in files_to_modify.items():
                try:
                    content = self.core.read_text(href)

                    # Realizar reemplazos
                    if self.use_regex:
                        flags = 0 if self.case_sensitive else re.IGNORECASE
                        pattern = re.compile(search_text, flags)
                        new_content = pattern.sub(replace_text, content)
                        replacements = len(pattern.findall(content))
                    else:
                        if self.case_sensitive:
                            replacements = content.count(search_text)
                            new_content = content.replace(search_text, replace_text)
                        else:
                            # Reemplazo case-insensitive sin regex
                            pattern = re.compile(re.escape(search_text), re.IGNORECASE)
                            replacements = len(pattern.findall(content))
                            new_content = pattern.sub(replace_text, content)

                    # Guardar si hubo cambios
                    if new_content != content:
                        self.core.write_text(href, new_content)
                        total_replacements += replacements
                        print(f"[GlobalReplace] {href}: {replacements} reemplazos")

                except Exception as e:
                    print(f"[GlobalReplace] Error procesando {href}: {e}")

            # Recargar el archivo actual si fue modificado
            if self.main_window.current_resource in files_to_modify:
                self.main_window.central_editor.load_resource(self.main_window.current_resource)

            # Mostrar resultado
            self._show_toast(f"Se reemplazaron {total_replacements} coincidencia(s)")

            # Limpiar resultados
            self.search_results = []
            while True:
                row = self.results_listbox.get_row_at_index(0)
                if row is None:
                    break
                self.results_listbox.remove(row)

            self.results_label.set_text("")
            self.replace_all_btn.set_sensitive(False)

        except Exception as e:
            print(f"[GlobalReplace] Error: {e}")
            import traceback
            traceback.print_exc()

            error_dialog = Adw.MessageDialog(transient_for=self, modal=True)
            error_dialog.set_heading("Error al reemplazar")
            error_dialog.set_body(f"Ocurrió un error:\n\n{str(e)}")
            error_dialog.add_response("ok", "OK")
            error_dialog.present()

    def _show_toast(self, message: str):
        """Muestra un mensaje toast"""
        toast = Adw.Toast()
        toast.set_title(message)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)


def show_global_search_replace_dialog(main_window: 'GutenAIWindow'):
    """Muestra el diálogo de búsqueda/reemplazo global"""
    if not main_window.core:
        main_window.show_error("No hay ningún proyecto abierto")
        return

    dialog = GlobalSearchReplaceDialog(main_window)
    dialog.present()
