#!/usr/bin/env python3
"""
Diálogo de validación EPUB con epubcheck para GutenAI
Interfaz GTK4 para mostrar resultados de validación
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GObject, Gio, Pango
import threading
from pathlib import Path
from typing import Optional

from utils.epubcheck_wrapper import (
    EpubCheckWrapper, EpubCheckResult, MessageLevel,
    ValidationProfile, quick_validate
)


class EpubCheckDialog(Adw.Window):
    """Diálogo para validación EPUB con epubcheck"""

    def __init__(self, parent_window: Optional[Gtk.Window] = None):
        super().__init__()

        self.set_title("Validación EPUB")
        self.set_default_size(800, 600)
        self.set_modal(True)

        if parent_window:
            self.set_transient_for(parent_window)

        self._wrapper = EpubCheckWrapper()
        self._current_result: Optional[EpubCheckResult] = None

        self._setup_ui()
        self._check_epubcheck_installation()

    def _setup_ui(self):
        """Configura la interfaz de usuario"""
        # Header bar
        header = Adw.HeaderBar()

        # Botón de cerrar
        close_btn = Gtk.Button(label="Cerrar")
        close_btn.connect("clicked", self._on_close_clicked)
        header.pack_end(close_btn)

        # Container principal con ToolbarView para libadwaita
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header)
        self.set_content(toolbar_view)

        # Container de contenido
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        toolbar_view.set_content(main_box)

        # Toolbar
        toolbar = self._create_toolbar()
        main_box.append(toolbar)

        # Content stack
        self._stack = Adw.ViewStack()
        self._stack_sidebar = Adw.ViewSwitcherBar()
        self._stack_sidebar.set_stack(self._stack)

        main_box.append(self._stack_sidebar)
        main_box.append(self._stack)

        # Páginas del stack
        self._create_file_selection_page()
        self._create_results_page()
        self._create_details_page()

    def _create_toolbar(self) -> Gtk.Widget:
        """Crea la toolbar"""
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        toolbar.add_css_class("toolbar")
        toolbar.set_margin_start(12)
        toolbar.set_margin_end(12)
        toolbar.set_margin_top(6)
        toolbar.set_margin_bottom(6)

        # Selector de archivo
        self._file_button = Gtk.Button(label="Seleccionar EPUB")
        self._file_button.connect("clicked", self._on_select_file)
        toolbar.append(self._file_button)

        # Separador
        toolbar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # Perfil de validación
        profile_label = Gtk.Label(label="Perfil:")
        toolbar.append(profile_label)

        self._profile_dropdown = Gtk.DropDown()
        profiles = ["Por defecto", "Diccionarios", "EDUPUB", "Índices", "Vista previa"]
        string_list = Gtk.StringList()
        for profile in profiles:
            string_list.append(profile)
        self._profile_dropdown.set_model(string_list)
        self._profile_dropdown.set_selected(0)
        toolbar.append(self._profile_dropdown)

        # Opciones
        self._usage_check = Gtk.CheckButton(label="Incluir uso")
        toolbar.append(self._usage_check)

        self._warnings_check = Gtk.CheckButton(label="Fallar en advertencias")
        toolbar.append(self._warnings_check)

        # Botón de validar
        self._validate_button = Gtk.Button(label="Validar")
        self._validate_button.add_css_class("suggested-action")
        self._validate_button.set_sensitive(False)
        self._validate_button.connect("clicked", self._on_validate_clicked)
        toolbar.append(self._validate_button)

        return toolbar

    def _create_file_selection_page(self):
        """Crea la página de selección de archivo"""
        page = Adw.StatusPage()
        page.set_title("Selecciona un archivo EPUB")
        page.set_description("Utiliza el botón 'Seleccionar EPUB' para elegir un archivo a validar")
        page.set_icon_name("document-open-symbolic")

        select_btn = Gtk.Button(label="Seleccionar archivo")
        select_btn.add_css_class("pill")
        select_btn.add_css_class("suggested-action")
        select_btn.connect("clicked", self._on_select_file)
        page.set_child(select_btn)

        self._stack.add_titled(page, "selection", "Selección")

    def _create_results_page(self):
        """Crea la página de resultados"""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._results_box.set_margin_start(12)
        self._results_box.set_margin_end(12)
        self._results_box.set_margin_top(12)
        self._results_box.set_margin_bottom(12)

        scrolled.set_child(self._results_box)
        self._stack.add_titled(scrolled, "results", "Resultados")

    def _create_details_page(self):
        """Crea la página de detalles"""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._details_box.set_margin_start(12)
        self._details_box.set_margin_end(12)
        self._details_box.set_margin_top(12)
        self._details_box.set_margin_bottom(12)

        scrolled.set_child(self._details_box)
        self._stack.add_titled(scrolled, "details", "Detalles")

    def _check_epubcheck_installation(self):
        """Verifica la instalación de epubcheck"""
        def check_thread():
            installed, version = self._wrapper.check_installation()

            def update_ui():
                if not installed:
                    self._show_error_status(f"epubcheck no disponible: {version}")
                    self._file_button.set_sensitive(False)
                else:
                    self._show_info_status(f"epubcheck disponible: {version}")

            GObject.idle_add(update_ui)

        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()

    def _show_error_status(self, message: str):
        """Muestra un mensaje de error"""
        page = Adw.StatusPage()
        page.set_title("Error")
        page.set_description(message)
        page.set_icon_name("dialog-error-symbolic")

        # Reemplazar página de selección
        self._stack.remove(self._stack.get_child_by_name("selection"))
        self._stack.add_titled(page, "selection", "Error")

    def _show_info_status(self, message: str):
        """Muestra un mensaje informativo"""
        pass  # Por ahora no hacer nada especial

    def _on_select_file(self, button: Gtk.Button):
        """Manejador para selección de archivo"""
        dialog = Gtk.FileChooserDialog(
            title="Seleccionar archivo EPUB",
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            "Cancelar", Gtk.ResponseType.CANCEL,
            "Abrir", Gtk.ResponseType.ACCEPT
        )

        # Filtro para archivos EPUB
        filter_epub = Gtk.FileFilter()
        filter_epub.set_name("Archivos EPUB")
        filter_epub.add_pattern("*.epub")
        dialog.add_filter(filter_epub)

        filter_all = Gtk.FileFilter()
        filter_all.set_name("Todos los archivos")
        filter_all.add_pattern("*")
        dialog.add_filter(filter_all)

        dialog.connect("response", self._on_file_dialog_response)
        dialog.present()

    def _on_file_dialog_response(self, dialog: Gtk.FileChooserDialog, response: int):
        """Manejador de respuesta del diálogo de archivo"""
        if response == Gtk.ResponseType.ACCEPT:
            file = dialog.get_file()
            if file:
                self._selected_file = Path(file.get_path())
                self._file_button.set_label(self._selected_file.name)
                self._validate_button.set_sensitive(True)

        dialog.destroy()

    def _on_validate_clicked(self, button: Gtk.Button):
        """Manejador para validación"""
        if not hasattr(self, '_selected_file'):
            return

        # Mostrar progreso
        self._show_progress()

        # Ejecutar validación en hilo separado
        def validate_thread():
            try:
                profile_map = {
                    0: ValidationProfile.DEFAULT,
                    1: ValidationProfile.DICT,
                    2: ValidationProfile.EDUPUB,
                    3: ValidationProfile.IDX,
                    4: ValidationProfile.PREVIEW
                }

                profile = profile_map.get(self._profile_dropdown.get_selected(), ValidationProfile.DEFAULT)
                include_usage = self._usage_check.get_active()
                fail_on_warnings = self._warnings_check.get_active()

                result = self._wrapper.validate_epub(
                    self._selected_file,
                    profile=profile,
                    include_usage=include_usage,
                    fail_on_warnings=fail_on_warnings
                )

                def update_ui():
                    self._current_result = result
                    self._show_results(result)
                    self._stack.set_visible_child_name("results")

                GObject.idle_add(update_ui)

            except Exception as e:
                def show_error():
                    self._show_validation_error(str(e))

                GObject.idle_add(show_error)

        thread = threading.Thread(target=validate_thread, daemon=True)
        thread.start()

    def _show_progress(self):
        """Muestra indicador de progreso"""
        page = Adw.StatusPage()
        page.set_title("Validando...")
        page.set_description("Por favor espera mientras se valida el archivo EPUB")

        spinner = Gtk.Spinner()
        spinner.set_spinning(True)
        spinner.set_size_request(32, 32)
        page.set_child(spinner)

        # Reemplazar página de resultados temporalmente
        old_page = self._stack.get_child_by_name("results")
        if old_page:
            self._stack.remove(old_page)

        self._stack.add_titled(page, "results", "Validando...")
        self._stack.set_visible_child_name("results")

    def _show_validation_error(self, error: str):
        """Muestra error de validación"""
        page = Adw.StatusPage()
        page.set_title("Error de validación")
        page.set_description(error)
        page.set_icon_name("dialog-error-symbolic")

        # Reemplazar página de resultados
        old_page = self._stack.get_child_by_name("results")
        if old_page:
            self._stack.remove(old_page)

        self._stack.add_titled(page, "results", "Error")

    def _show_results(self, result: EpubCheckResult):
        """Muestra los resultados de la validación"""
        # Limpiar contenido anterior
        while self._results_box.get_first_child():
            self._results_box.remove(self._results_box.get_first_child())

        while self._details_box.get_first_child():
            self._details_box.remove(self._details_box.get_first_child())

        # Recrear página de resultados
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self._results_box)

        old_page = self._stack.get_child_by_name("results")
        if old_page:
            self._stack.remove(old_page)

        self._stack.add_titled(scrolled, "results", "Resultados")

        # Título y estado general
        self._add_results_header(result)

        # Estadísticas de validación
        self._add_validation_stats(result)

        # Mensajes de validación
        if result.messages:
            self._add_messages_section(result.messages)

        # Información de la publicación
        self._add_publication_info(result.publication)

        # Detalles de items (en página separada)
        self._add_items_details(result.items)

    def _add_results_header(self, result: EpubCheckResult):
        """Añade el encabezado de resultados"""
        group = Adw.PreferencesGroup()
        group.set_title("Estado de validación")

        # Status row
        status_row = Adw.ActionRow()
        status_row.set_title(result.checker.filename)

        if result.is_valid:
            status_row.set_subtitle("✓ EPUB válido")
            status_icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
            status_icon.add_css_class("success")
        else:
            status_row.set_subtitle("✗ EPUB inválido")
            status_icon = Gtk.Image.new_from_icon_name("dialog-error-symbolic")
            status_icon.add_css_class("error")

        status_row.add_suffix(status_icon)
        group.add(status_row)

        self._results_box.append(group)

    def _add_validation_stats(self, result: EpubCheckResult):
        """Añade estadísticas de validación"""
        group = Adw.PreferencesGroup()
        group.set_title("Estadísticas")

        # Errores fatales
        if result.checker.nFatal > 0:
            fatal_row = Adw.ActionRow()
            fatal_row.set_title("Errores fatales")
            fatal_row.set_subtitle(str(result.checker.nFatal))
            fatal_icon = Gtk.Image.new_from_icon_name("dialog-error-symbolic")
            fatal_row.add_suffix(fatal_icon)
            group.add(fatal_row)

        # Errores
        if result.checker.nError > 0:
            error_row = Adw.ActionRow()
            error_row.set_title("Errores")
            error_row.set_subtitle(str(result.checker.nError))
            error_icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
            error_row.add_suffix(error_icon)
            group.add(error_row)

        # Advertencias
        if result.checker.nWarning > 0:
            warning_row = Adw.ActionRow()
            warning_row.set_title("Advertencias")
            warning_row.set_subtitle(str(result.checker.nWarning))
            warning_icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic")
            warning_row.add_suffix(warning_icon)
            group.add(warning_row)

        # Tiempo de validación
        time_row = Adw.ActionRow()
        time_row.set_title("Tiempo de validación")
        time_row.set_subtitle(f"{result.checker.elapsedTime}ms")
        group.add(time_row)

        self._results_box.append(group)

    def _add_messages_section(self, messages):
        """Añade sección de mensajes"""
        group = Adw.PreferencesGroup()
        group.set_title(f"Mensajes ({len(messages)})")

        for message in messages[:10]:  # Limitar a 10 mensajes
            # Usar ExpanderRow para mostrar detalles
            msg_row = Adw.ExpanderRow()
            msg_row.set_title(message.message)

            # Subtitle con ID y número de ubicaciones
            locations_count = len(message.locations)
            subtitle_parts = [f"ID: {message.id}"]
            if locations_count > 0:
                subtitle_parts.append(f"{locations_count} ubicación(es)")
            if message.additional_locations > 0:
                subtitle_parts.append(f"+ {message.additional_locations} más")
            msg_row.set_subtitle(" • ".join(subtitle_parts))

            # Icono según severidad
            if message.severity == MessageLevel.FATAL:
                icon = Gtk.Image.new_from_icon_name("dialog-error-symbolic")
                icon.add_css_class("error")
            elif message.severity == MessageLevel.ERROR:
                icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
                icon.add_css_class("warning")
            elif message.severity == MessageLevel.WARNING:
                icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic")
                icon.add_css_class("accent")
            else:
                icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic")

            msg_row.add_prefix(icon)

            # Añadir ubicaciones como filas expandibles
            for i, location in enumerate(message.locations[:5]):  # Mostrar hasta 5 ubicaciones
                loc_row = Adw.ActionRow()
                loc_row.set_title(f"📁 {location.path}")

                location_info = []
                if location.line is not None:
                    location_info.append(f"Línea {location.line}")
                if location.column is not None:
                    location_info.append(f"Columna {location.column}")

                if location_info:
                    loc_row.set_subtitle(" • ".join(location_info))

                msg_row.add_row(loc_row)

            # Si hay más ubicaciones de las que mostramos
            if len(message.locations) > 5:
                more_locations_row = Adw.ActionRow()
                more_locations_row.set_title(f"... y {len(message.locations) - 5} ubicaciones más")
                more_locations_row.add_css_class("dim-label")
                msg_row.add_row(more_locations_row)

            # Añadir sugerencia si existe
            if message.suggestion:
                suggestion_row = Adw.ActionRow()
                suggestion_row.set_title("💡 Sugerencia")
                suggestion_row.set_subtitle(message.suggestion)
                msg_row.add_row(suggestion_row)

            group.add(msg_row)

        if len(messages) > 10:
            more_row = Adw.ActionRow()
            more_row.set_title(f"... y {len(messages) - 10} mensajes más")
            group.add(more_row)

        self._results_box.append(group)

    def _add_publication_info(self, publication):
        """Añade información de la publicación"""
        group = Adw.PreferencesGroup()
        group.set_title("Información de la publicación")

        if publication.title:
            title_row = Adw.ActionRow()
            title_row.set_title("Título")
            title_row.set_subtitle(publication.title)
            group.add(title_row)

        if publication.creator:
            author_row = Adw.ActionRow()
            author_row.set_title("Autor(es)")
            author_row.set_subtitle(", ".join(publication.creator))
            group.add(author_row)

        if publication.language:
            lang_row = Adw.ActionRow()
            lang_row.set_title("Idioma")
            lang_row.set_subtitle(publication.language)
            group.add(lang_row)

        if publication.ePubVersion:
            version_row = Adw.ActionRow()
            version_row.set_title("Versión EPUB")
            version_row.set_subtitle(publication.ePubVersion)
            group.add(version_row)

        chars_row = Adw.ActionRow()
        chars_row.set_title("Caracteres")
        chars_row.set_subtitle(f"{publication.charsCount:,}")
        group.add(chars_row)

        spine_row = Adw.ActionRow()
        spine_row.set_title("Elementos en spine")
        spine_row.set_subtitle(str(publication.nSpines))
        group.add(spine_row)

        self._results_box.append(group)

    def _add_items_details(self, items):
        """Añade detalles de items a la página de detalles"""
        group = Adw.PreferencesGroup()
        group.set_title(f"Archivos del EPUB ({len(items)})")

        for item in items:
            item_row = Adw.ExpanderRow()
            item_row.set_title(item.fileName)
            item_row.set_subtitle(f"{item.media_type or 'Tipo desconocido'} - {item.uncompressedSize:,} bytes")

            # Detalles expandibles
            if item.isSpineItem:
                spine_label = Gtk.Label(label=f"Índice en spine: {item.spineIndex}")
                spine_label.set_halign(Gtk.Align.START)
                item_row.add_row(spine_label)

            if item.referencedItems:
                refs_label = Gtk.Label(label=f"Referencias: {len(item.referencedItems)}")
                refs_label.set_halign(Gtk.Align.START)
                item_row.add_row(refs_label)

            group.add(item_row)

        self._details_box.append(group)

    def _on_close_clicked(self, button: Gtk.Button):
        """Manejador del botón cerrar"""
        self.close()

    def validate_file(self, file_path: Path):
        """Valida un archivo específico (API pública)"""
        self._selected_file = file_path
        self._file_button.set_label(file_path.name)
        self._validate_button.set_sensitive(True)
        self._on_validate_clicked(self._validate_button)


# Función de conveniencia para mostrar el diálogo
def show_epubcheck_dialog(parent_window: Optional[Gtk.Window] = None,
                         epub_file: Optional[Path] = None) -> EpubCheckDialog:
    """
    Muestra el diálogo de validación EPUB

    Args:
        parent_window: Ventana padre
        epub_file: Archivo EPUB a validar automáticamente

    Returns:
        EpubCheckDialog: Instancia del diálogo
    """
    dialog = EpubCheckDialog(parent_window)

    if epub_file:
        dialog.validate_file(epub_file)

    dialog.present()
    return dialog


if __name__ == "__main__":
    # Test independiente
    import sys

    class TestApp(Adw.Application):
        def __init__(self):
            super().__init__(application_id="gutenai.com")

        def do_activate(self):
            dialog = EpubCheckDialog()

            if len(sys.argv) > 1:
                dialog.validate_file(Path(sys.argv[1]))

            dialog.present()

    app = TestApp()
    app.run(sys.argv)