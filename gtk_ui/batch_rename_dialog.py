"""
ui/batch_rename_dialog.py
Diálogo para renombrado en lote de archivos HTML del spine
"""
from . import *
from gi.repository import Gtk, Adw, GLib
from pathlib import Path
from typing import TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from .main_window import GutenAIWindow


class BatchRenameDialog(Adw.Window):
    """Diálogo para renombrar múltiples archivos del spine con un patrón"""

    def __init__(self, main_window: 'GutenAIWindow', preselected_hrefs: List[str] = None):
        super().__init__()

        self.main_window = main_window
        self.core = main_window.core
        self.preselected_hrefs = preselected_hrefs or []

        if not self.core:
            return

        # Configuración de ventana
        self.set_title("Renombrado en Lote")
        self.set_default_size(900, 700)
        self.set_modal(True)
        self.set_transient_for(main_window)

        # Variables
        self.spine_items = []  # Lista de (idref, href, item)
        self.preview_items = []  # Lista de (old_name, new_name, idref)

        # Crear interfaz
        self._setup_ui()

        # Cargar archivos del spine
        self._load_spine_files()

    def _setup_ui(self):
        """Configura la interfaz del diálogo"""

        # HeaderBar
        header_bar = Adw.HeaderBar()

        # Botón cerrar
        close_btn = Gtk.Button(label="Cancelar")
        close_btn.connect('clicked', lambda b: self.close())
        header_bar.pack_start(close_btn)

        # Botón renombrar
        self.rename_btn = Gtk.Button(label="Aplicar Renombrado")
        self.rename_btn.add_css_class("suggested-action")
        self.rename_btn.connect('clicked', self._on_apply_rename)
        self.rename_btn.set_sensitive(False)
        header_bar.pack_end(self.rename_btn)

        # Box principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Toast overlay
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(main_box)

        # === SECCIÓN DE CONFIGURACIÓN ===
        config_group = Adw.PreferencesGroup()
        config_group.set_title("Configuración de Renombrado")
        config_group.set_description("Define el patrón para renombrar los archivos")
        config_group.set_margin_start(12)
        config_group.set_margin_end(12)
        config_group.set_margin_top(12)

        # Prefijo fijo
        prefix_row = Adw.EntryRow()
        prefix_row.set_title("Prefijo fijo")
        prefix_row.set_text("capitulo")
        prefix_row.connect('changed', self._on_pattern_changed)
        self.prefix_entry = prefix_row
        config_group.add(prefix_row)

        # Número inicial
        start_row = Adw.SpinRow()
        start_row.set_title("Número inicial")
        start_row.set_subtitle("Primer número de la secuencia")
        adjustment = Gtk.Adjustment(value=1, lower=0, upper=9999, step_increment=1)
        start_row.set_adjustment(adjustment)
        start_row.connect('changed', self._on_pattern_changed)
        self.start_spin = start_row
        config_group.add(start_row)

        # Dígitos (padding)
        digits_row = Adw.SpinRow()
        digits_row.set_title("Número de dígitos")
        digits_row.set_subtitle("Cantidad de dígitos para el número (con ceros a la izquierda)")
        adjustment2 = Gtk.Adjustment(value=2, lower=1, upper=5, step_increment=1)
        digits_row.set_adjustment(adjustment2)
        digits_row.connect('changed', self._on_pattern_changed)
        self.digits_spin = digits_row
        config_group.add(digits_row)

        # Ejemplo del patrón
        self.pattern_example = Adw.ActionRow()
        self.pattern_example.set_title("Ejemplo de nombre")
        example_label = Gtk.Label(label="capitulo01.html, capitulo02.html, ...")
        example_label.add_css_class("monospace")
        example_label.add_css_class("dim-label")
        self.pattern_example.add_suffix(example_label)
        self.pattern_example_label = example_label
        config_group.add(self.pattern_example)

        main_box.append(config_group)

        # === SECCIÓN DE SELECCIÓN ===
        selection_group = Adw.PreferencesGroup()
        selection_group.set_title("Archivos a Renombrar")
        selection_group.set_description("Selecciona los archivos que deseas renombrar")
        selection_group.set_margin_start(12)
        selection_group.set_margin_end(12)
        selection_group.set_margin_top(12)

        # Botones de selección
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_margin_start(12)
        button_box.set_margin_end(12)
        button_box.set_margin_top(6)
        button_box.set_margin_bottom(6)

        select_all_btn = Gtk.Button(label="Seleccionar Todos")
        select_all_btn.connect('clicked', self._on_select_all)
        button_box.append(select_all_btn)

        deselect_all_btn = Gtk.Button(label="Deseleccionar Todos")
        deselect_all_btn.connect('clicked', self._on_deselect_all)
        button_box.append(deselect_all_btn)

        from_current_btn = Gtk.Button(label="Desde Actual")
        from_current_btn.set_tooltip_text("Selecciona desde el archivo actual hasta el final")
        from_current_btn.connect('clicked', self._on_select_from_current)
        button_box.append(from_current_btn)

        selection_group.add(Adw.PreferencesRow(child=button_box))

        main_box.append(selection_group)

        # === LISTA DE ARCHIVOS ===
        preview_group = Adw.PreferencesGroup()
        preview_group.set_title("Vista Previa")
        preview_group.set_description("Revisa cómo quedarán los archivos renombrados")
        preview_group.set_margin_start(12)
        preview_group.set_margin_end(12)
        preview_group.set_margin_top(12)
        preview_group.set_margin_bottom(12)

        # ScrolledWindow para la lista
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_min_content_height(300)

        # ListBox para los archivos
        self.files_listbox = Gtk.ListBox()
        self.files_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.files_listbox.add_css_class("boxed-list")
        scrolled.set_child(self.files_listbox)

        preview_group.add(Adw.PreferencesRow(child=scrolled))
        main_box.append(preview_group)

        # ToolbarView
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header_bar)
        toolbar_view.set_content(self.toast_overlay)
        self.set_content(toolbar_view)

    def _load_spine_files(self):
        """Carga los archivos del spine"""
        spine = self.core.get_spine()

        for idref in spine:
            item = self.core._get_item(idref)
            self.spine_items.append((idref, item.href, item))

        # Crear filas para cada archivo
        self._populate_files_list()

        # Generar preview inicial
        self._on_pattern_changed()

    def _populate_files_list(self):
        """Puebla la lista de archivos con checkboxes"""
        # Limpiar lista
        while True:
            row = self.files_listbox.get_row_at_index(0)
            if row is None:
                break
            self.files_listbox.remove(row)

        # Agregar cada archivo
        for i, (idref, href, item) in enumerate(self.spine_items):
            row = self._create_file_row(i, idref, href)
            self.files_listbox.append(row)

    def _create_file_row(self, index: int, idref: str, href: str) -> Gtk.ListBoxRow:
        """Crea una fila para un archivo"""
        row = Gtk.ListBoxRow()
        row.set_activatable(False)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)

        # Checkbox - preseleccionar si está en la lista
        checkbox = Gtk.CheckButton()
        is_preselected = href in self.preselected_hrefs
        checkbox.set_active(is_preselected)
        checkbox.connect('toggled', lambda cb: self._on_selection_changed())
        box.append(checkbox)

        # Número de orden
        order_label = Gtk.Label(label=f"{index + 1}.")
        order_label.set_width_chars(4)
        order_label.add_css_class("dim-label")
        box.append(order_label)

        # Contenedor vertical para nombres
        names_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        names_box.set_hexpand(True)

        # Nombre actual
        current_name = Path(href).name
        current_label = Gtk.Label(label=current_name)
        current_label.set_halign(Gtk.Align.START)
        current_label.add_css_class("monospace")
        names_box.append(current_label)

        # Flecha y nuevo nombre
        arrow_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        arrow_label = Gtk.Label(label="→")
        arrow_label.add_css_class("dim-label")
        arrow_box.append(arrow_label)

        new_label = Gtk.Label(label="")
        new_label.set_halign(Gtk.Align.START)
        new_label.add_css_class("monospace")
        new_label.add_css_class("success")
        arrow_box.append(new_label)

        names_box.append(arrow_box)
        box.append(names_box)

        # Indicador si es el archivo actual
        if self.main_window.current_resource == href:
            badge = Gtk.Label(label="● ACTUAL")
            badge.add_css_class("dim-label")
            badge.add_css_class("caption")
            badge.set_valign(Gtk.Align.CENTER)
            box.append(badge)

        row.set_child(box)

        # Guardar referencias
        row.checkbox = checkbox
        row.new_label = new_label
        row.idref = idref
        row.href = href
        row.index = index

        return row

    def _on_pattern_changed(self, *args):
        """Se llama cuando cambia el patrón de renombrado"""
        prefix = self.prefix_entry.get_text()
        start_num = int(self.start_spin.get_value())
        digits = int(self.digits_spin.get_value())

        # Actualizar ejemplo
        example1 = f"{prefix}{str(start_num).zfill(digits)}.html"
        example2 = f"{prefix}{str(start_num + 1).zfill(digits)}.html"
        self.pattern_example_label.set_text(f"{example1}, {example2}, ...")

        # Actualizar preview de nombres
        self._update_preview()

    def _update_preview(self):
        """Actualiza la vista previa de nombres nuevos"""
        prefix = self.prefix_entry.get_text()
        start_num = int(self.start_spin.get_value())
        digits = int(self.digits_spin.get_value())

        # Contador para archivos seleccionados
        counter = start_num

        # Recorrer todas las filas
        for i in range(len(self.spine_items)):
            row = self.files_listbox.get_row_at_index(i)
            if row and hasattr(row, 'checkbox'):
                if row.checkbox.get_active():
                    # Generar nuevo nombre
                    new_name = f"{prefix}{str(counter).zfill(digits)}.html"
                    row.new_label.set_text(new_name)
                    row.new_label.set_visible(True)
                    counter += 1
                else:
                    row.new_label.set_text("")
                    row.new_label.set_visible(False)

    def _on_selection_changed(self):
        """Se llama cuando cambia la selección de archivos"""
        self._update_preview()

        # Habilitar/deshabilitar botón de renombrar
        has_selection = False
        for i in range(len(self.spine_items)):
            row = self.files_listbox.get_row_at_index(i)
            if row and hasattr(row, 'checkbox') and row.checkbox.get_active():
                has_selection = True
                break

        self.rename_btn.set_sensitive(has_selection)

    def _on_select_all(self, button):
        """Selecciona todos los archivos"""
        for i in range(len(self.spine_items)):
            row = self.files_listbox.get_row_at_index(i)
            if row and hasattr(row, 'checkbox'):
                row.checkbox.set_active(True)

    def _on_deselect_all(self, button):
        """Deselecciona todos los archivos"""
        for i in range(len(self.spine_items)):
            row = self.files_listbox.get_row_at_index(i)
            if row and hasattr(row, 'checkbox'):
                row.checkbox.set_active(False)

    def _on_select_from_current(self, button):
        """Selecciona desde el archivo actual hasta el final"""
        current_resource = self.main_window.current_resource
        if not current_resource:
            return

        found_current = False
        for i in range(len(self.spine_items)):
            row = self.files_listbox.get_row_at_index(i)
            if row and hasattr(row, 'checkbox'):
                if row.href == current_resource:
                    found_current = True

                if found_current:
                    row.checkbox.set_active(True)

    def _on_apply_rename(self, button):
        """Aplica el renombrado a los archivos seleccionados"""
        prefix = self.prefix_entry.get_text()
        start_num = int(self.start_spin.get_value())
        digits = int(self.digits_spin.get_value())

        if not prefix.strip():
            self._show_toast("El prefijo no puede estar vacío")
            return

        # Recopilar cambios
        rename_list = []  # (old_href, new_href, idref)
        counter = start_num

        for i in range(len(self.spine_items)):
            row = self.files_listbox.get_row_at_index(i)
            if row and hasattr(row, 'checkbox') and row.checkbox.get_active():
                old_href = row.href
                old_path = Path(old_href)
                new_name = f"{prefix}{str(counter).zfill(digits)}.html"
                new_href = str(old_path.parent / new_name)

                rename_list.append((old_href, new_href, row.idref))
                counter += 1

        if not rename_list:
            self._show_toast("No hay archivos seleccionados")
            return

        # Validar que no hay conflictos
        new_names = [new_href for _, new_href, _ in rename_list]
        if len(new_names) != len(set(new_names)):
            self._show_toast("Error: Hay nombres duplicados en el resultado")
            return

        # Confirmar con el usuario
        self._confirm_and_rename(rename_list)

    def _confirm_and_rename(self, rename_list: List[Tuple[str, str, str]]):
        """Muestra confirmación y realiza el renombrado"""
        # Crear diálogo de confirmación
        dialog = Adw.MessageDialog(transient_for=self, modal=True)
        dialog.set_heading("Confirmar Renombrado")
        dialog.set_body(f"¿Estás seguro de que deseas renombrar {len(rename_list)} archivo(s)?\n\n"
                       "Esta operación actualizará el OPF y moverá los archivos.")

        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("rename", "Renombrar")
        dialog.set_response_appearance("rename", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def on_response(dlg, response):
            if response == "rename":
                self._perform_rename(rename_list)

        dialog.connect("response", on_response)
        dialog.present()

    def _perform_rename(self, rename_list: List[Tuple[str, str, str]]):
        """Realiza el renombrado de archivos"""
        try:
            print(f"\n[BatchRename] Iniciando renombrado de {len(rename_list)} archivos...")

            # Renombrar cada archivo
            for old_href, new_href, idref in rename_list:
                print(f"[BatchRename] Renombrando: {old_href} -> {new_href}")

                # Extraer solo el nombre del archivo del nuevo href
                new_name = Path(new_href).name

                # Usar la función de GutenCore para renombrar
                # Esto actualiza el OPF, mueve el archivo y mantiene todo sincronizado
                self.core.rename_item(old_href, new_name, update_references=False)

            print("[BatchRename] Renombrado completado exitosamente")

            # Actualizar interfaz principal
            self.main_window.sidebar_left.populate_tree()

            # Si el archivo actual fue renombrado, actualizar referencia
            for old_href, new_href, _ in rename_list:
                if self.main_window.current_resource == old_href:
                    # El nuevo href real lo devuelve rename_item
                    new_name = Path(new_href).name
                    old_path = Path(old_href)
                    actual_new_href = str(old_path.parent / new_name)
                    self.main_window.current_resource = actual_new_href
                    break

            # Mostrar mensaje de éxito
            self._show_toast(f"Se renombraron {len(rename_list)} archivo(s) exitosamente")

            # Cerrar diálogo
            GLib.timeout_add(1000, self.close)

        except Exception as e:
            print(f"[BatchRename] ERROR: {e}")
            import traceback
            traceback.print_exc()

            error_dialog = Adw.MessageDialog(transient_for=self, modal=True)
            error_dialog.set_heading("Error al Renombrar")
            error_dialog.set_body(f"Ocurrió un error durante el renombrado:\n\n{str(e)}")
            error_dialog.add_response("ok", "OK")
            error_dialog.present()

    def _show_toast(self, message: str):
        """Muestra un mensaje toast"""
        toast = Adw.Toast()
        toast.set_title(message)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)


def show_batch_rename_dialog(main_window: 'GutenAIWindow', preselected_hrefs: List[str] = None):
    """Muestra el diálogo de renombrado en lote"""
    if not main_window.core:
        main_window.show_error("No hay ningún proyecto abierto")
        return

    dialog = BatchRenameDialog(main_window, preselected_hrefs=preselected_hrefs)
    dialog.present()
