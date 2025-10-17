"""
ui/dialogs.py
Gestor de diálogos - Todos los diálogos modales de la aplicación
"""
from . import *
from gi.repository import Gtk, Adw, Gio
from pathlib import Path
from typing import Optional, Dict, TYPE_CHECKING

from core.guten_core import KIND_DOCUMENT, KIND_STYLE, KIND_IMAGE, KIND_FONT, KIND_AUDIO, KIND_VIDEO

if TYPE_CHECKING:
    from .main_window import GutenAIWindow


class DialogManager:
    """Gestiona todos los diálogos de la aplicación"""
    
    def __init__(self, main_window: 'GutenAIWindow'):
        self.main_window = main_window
        
        # Referencias temporales para diálogos activos
        self._style_checkboxes: Optional[Dict[str, Gtk.CheckButton]] = None
        self._clear_existing_checkbox: Optional[Gtk.CheckButton] = None
    
    def show_create_resource_dialog(self, resource_type: str):
        """Muestra diálogo para crear un nuevo recurso"""
        
        dialog = Adw.AlertDialog()
        dialog.set_heading("Crear nuevo recurso")
        
        if resource_type == KIND_DOCUMENT:
            dialog.set_body("Nombre para el nuevo capítulo/documento HTML:")
            placeholder = "capitulo_nuevo"
        elif resource_type == KIND_STYLE:
            dialog.set_body("Nombre para el nuevo archivo CSS:")
            placeholder = "estilo_nuevo"
        else:
            dialog.set_body(f"Nombre para el nuevo {resource_type}:")
            placeholder = "recurso_nuevo"
        
        # Entry para el nombre
        entry = Gtk.Entry()
        entry.set_placeholder_text(placeholder)
        entry.set_text(placeholder)
        dialog.set_extra_child(entry)
        
        # Botones
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("create", "Crear")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        
        # Conectar respuesta
        dialog.connect("response", self._on_create_resource_response, resource_type, entry)
        dialog.present(self.main_window)
    
    def _on_create_resource_response(self, dialog, response, resource_type, entry):
        """Maneja la respuesta del diálogo de creación de recursos"""
        if response != "create":
            return
        
        filename = entry.get_text().strip()
        if not filename:
            self.main_window.show_error("El nombre no puede estar vacío")
            return
        
        try:
            if resource_type == KIND_DOCUMENT:
                self._create_document(filename)
            elif resource_type == KIND_STYLE:
                self._create_css_file(filename)
            else:
                self.main_window.show_error(f"Tipo de recurso no soportado: {resource_type}")
                return
            
            # Actualizar la UI
            self.main_window.refresh_structure()
            
        except Exception as e:
            self.main_window.show_error(f"Error creando recurso: {e}")
    
    def _create_document(self, filename: str):
        """Crea un documento HTML usando el core"""
        item = self.main_window.core.create_document(filename)
        self.main_window.show_info(f"Documento '{filename}' creado correctamente")
        return item
    
    def _create_css_file(self, filename: str):
        """Crea un archivo CSS con contenido básico"""
        if not filename.endswith('.css'):
            filename += '.css'
        
        styles_dir = Path(self.main_window.core.layout["STYLES"]).name
        href = f"{styles_dir}/{filename}"
        
        # Contenido CSS básico
        css_content = """/* Estilos para el EPUB */

body {
    font-family: serif;
    line-height: 1.4;
    margin: 1em;
}

h1, h2, h3, h4, h5, h6 {
    font-family: sans-serif;
    margin: 1em 0 0.5em 0;
}

p {
    margin: 0 0 0.5em 0;
    text-indent: 1em;
}

.center {
    text-align: center;
}

.bold {
    font-weight: bold;
}

.italic {
    font-style: italic;
}
"""
        
        self.main_window.core.write_text(href, css_content)
        
        # Generar ID único y agregar al manifest
        base_id = Path(filename).stem
        id_ = self.main_window.core._unique_id(base_id)
        
        item = self.main_window.core.add_to_manifest(id_, href, media_type="text/css")
        self.main_window.show_info(f"Archivo CSS '{filename}' creado correctamente")
        return item
    
    def show_import_resource_dialog(self, resource_type: str):
        """Muestra diálogo para importar recursos desde disco"""
        
        dialog = Gtk.FileDialog()
        
        if resource_type == KIND_IMAGE:
            dialog.set_title("Importar imagen")
            filters = self._create_image_filters()
        elif resource_type == KIND_FONT:
            dialog.set_title("Importar fuente")
            filters = self._create_font_filters()
        elif resource_type == KIND_AUDIO:
            dialog.set_title("Importar audio")
            filters = self._create_audio_filters()
        elif resource_type == KIND_VIDEO:
            dialog.set_title("Importar video")
            filters = self._create_video_filters()
        else:
            dialog.set_title("Importar archivo")
            filters = None
        
        if filters:
            dialog.set_filters(filters)
        
        dialog.open(self.main_window, None, self._on_import_resource_response, resource_type)
    
    def _create_image_filters(self):
        """Crea filtros para archivos de imagen"""
        filter_images = Gtk.FileFilter()
        filter_images.set_name("Imágenes")
        filter_images.add_pattern("*.png")
        filter_images.add_pattern("*.jpg")
        filter_images.add_pattern("*.jpeg")
        filter_images.add_pattern("*.gif")
        filter_images.add_pattern("*.svg")
        filter_images.add_pattern("*.webp")
        filter_images.add_pattern("*.avif")
        
        filters = Gio.ListStore()
        filters.append(filter_images)
        return filters
    
    def _create_font_filters(self):
        """Crea filtros para archivos de fuente"""
        filter_fonts = Gtk.FileFilter()
        filter_fonts.set_name("Fuentes")
        filter_fonts.add_pattern("*.ttf")
        filter_fonts.add_pattern("*.otf")
        filter_fonts.add_pattern("*.woff")
        filter_fonts.add_pattern("*.woff2")
        
        filters = Gio.ListStore()
        filters.append(filter_fonts)
        return filters
    
    def _create_audio_filters(self):
        """Crea filtros para archivos de audio"""
        filter_audio = Gtk.FileFilter()
        filter_audio.set_name("Audio")
        filter_audio.add_pattern("*.mp3")
        filter_audio.add_pattern("*.m4a")
        filter_audio.add_pattern("*.aac")
        filter_audio.add_pattern("*.ogg")
        filter_audio.add_pattern("*.opus")
        
        filters = Gio.ListStore()
        filters.append(filter_audio)
        return filters
    
    def _create_video_filters(self):
        """Crea filtros para archivos de video"""
        filter_video = Gtk.FileFilter()
        filter_video.set_name("Video")
        filter_video.add_pattern("*.mp4")
        filter_video.add_pattern("*.m4v")
        filter_video.add_pattern("*.webm")
        filter_video.add_pattern("*.ogg")
        
        filters = Gio.ListStore()
        filters.append(filter_video)
        return filters
    
    def _on_import_resource_response(self, dialog, result, resource_type):
        """Maneja la respuesta del diálogo de importación"""
        try:
            file = dialog.open_finish(result)
            if file:
                src_path = Path(file.get_path())
                
                # Importar usando el core
                item = self.main_window.core.create_asset_from_disk(
                    src_path,
                    resource_type,
                    dest_name=src_path.name,
                    set_as_cover=(False)
                )
                
                tipo_nombre = self._get_resource_type_name(resource_type)
                self.main_window.show_info(f"{tipo_nombre.title()} '{src_path.name}' importada correctamente")
                
                # Actualizar la estructura
                self.main_window.refresh_structure()
                
        except Exception as e:
            self.main_window.show_error(f"Error importando archivo: {e}")
    
    def _get_resource_type_name(self, resource_type: str) -> str:
        """Convierte el tipo de recurso a nombre legible"""
        names = {
            KIND_IMAGE: "imagen",
            KIND_FONT: "fuente", 
            KIND_AUDIO: "audio",
            KIND_VIDEO: "video"
        }
        return names.get(resource_type, "archivo")
    
    def show_style_linking_dialog(self):
        """Muestra diálogo para vincular estilos CSS"""
        
        # Obtener estilos disponibles
        css_items = self.main_window.core.list_items(kind=KIND_STYLE)
        
        if not css_items:
            self.main_window.show_error("No hay archivos CSS en el proyecto")
            return
        
        dialog = Adw.AlertDialog()
        dialog.set_heading("Vincular estilos CSS")
        dialog.set_body("Selecciona los archivos CSS que deseas vincular a este documento:")
        
        # Crear contenido del diálogo
        content_box = self._create_style_dialog_content(css_items)
        dialog.set_extra_child(content_box)
        
        # Botones
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("apply", "Aplicar estilos")
        dialog.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        
        # Conectar respuesta
        dialog.connect("response", self._on_style_dialog_response)
        dialog.present(self.main_window)
    
    def _create_style_dialog_content(self, css_items):
        """Crea el contenido del diálogo de estilos"""
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.set_spacing(8)
        content_box.set_margin_top(12)
        content_box.set_margin_bottom(12)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)
        
        # Inicializar diccionario de checkboxes
        self._style_checkboxes = {}
        
        # Lista scrolleable de estilos
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_max_content_height(300)
        scrolled.set_propagate_natural_height(True)
        
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        list_box.add_css_class("boxed-list")
        
        for css_item in css_items:
            row = Adw.ActionRow()
            row.set_title(Path(css_item.href).name)
            row.set_subtitle(css_item.href)
            
            # Checkbox para selección
            checkbox = Gtk.CheckButton()
            checkbox.set_active(True)  # Por defecto seleccionado
            row.add_prefix(checkbox)
            
            # Guardar referencia
            self._style_checkboxes[css_item.href] = checkbox
            list_box.append(row)
        
        scrolled.set_child(list_box)
        content_box.append(scrolled)
        
        # Opciones adicionales
        options_group = self._create_style_options_group()
        content_box.append(options_group)
        
        return content_box
    
    def _create_style_options_group(self):
        """Crea el grupo de opciones para el diálogo de estilos"""
        
        options_group = Adw.PreferencesGroup()
        options_group.set_title("Opciones")
        
        # Checkbox para limpiar estilos existentes
        clear_row = Adw.ActionRow()
        clear_row.set_title("Limpiar estilos existentes")
        clear_row.set_subtitle("Elimina todos los <link> de CSS antes de agregar los nuevos")
        
        self._clear_existing_checkbox = Gtk.CheckButton()
        self._clear_existing_checkbox.set_active(True)
        clear_row.add_prefix(self._clear_existing_checkbox)
        
        options_group.add(clear_row)
        return options_group
    
    def _on_style_dialog_response(self, dialog, response):
        """Maneja la respuesta del diálogo de estilos"""
        if response != "apply":
            self._cleanup_style_dialog_refs()
            return
        
        if not self.main_window.core or not self.main_window.current_resource:
            self._cleanup_style_dialog_refs()
            return
        
        try:
            # Obtener estilos seleccionados
            selected_styles = []
            if self._style_checkboxes:
                for href, checkbox in self._style_checkboxes.items():
                    if checkbox.get_active():
                        style_name = Path(href).name
                        selected_styles.append(style_name)
            
            if not selected_styles:
                self.main_window.show_error("Debes seleccionar al menos un archivo CSS")
                self._cleanup_style_dialog_refs()
                return
            
            # Aplicar estilos
            self._apply_styles_to_document(selected_styles)
            
        except Exception as e:
            self.main_window.show_error(f"Error vinculando estilos: {e}")
        finally:
            self._cleanup_style_dialog_refs()
    
    def _apply_styles_to_document(self, selected_styles):
        """Aplica los estilos seleccionados al documento actual"""
        
        # Obtener configuración
        clear_existing = (self._clear_existing_checkbox.get_active() 
                         if self._clear_existing_checkbox else True)
        
        # Obtener ID del documento actual
        mi = self.main_window.core._get_item(self.main_window.current_resource)
        doc_id = mi.id
        
        # Aplicar estilos usando el core
        results = self.main_window.core.set_styles_for_documents(
            docs=[doc_id],
            styles=selected_styles,
            clear_existing=clear_existing,
            add_to_manifest_if_missing=True
        )
        
        # Mostrar resultado
        applied_count = len(results.get(mi.href, []))
        self.main_window.show_info(f"Se vincularon {applied_count} archivos CSS al documento")
        
        # Recargar el contenido en el editor
        self.main_window.central_editor.load_resource(self.main_window.current_resource)
    
    def _cleanup_style_dialog_refs(self):
        """Limpia las referencias temporales del diálogo de estilos"""
        self._style_checkboxes = None
        self._clear_existing_checkbox = None
    
    def show_error_dialog(self, title: str, message: str):
        """Muestra un diálogo de error simple"""
        dialog = Adw.AlertDialog()
        dialog.set_heading(title)
        dialog.set_body(message)
        dialog.add_response("ok", "Aceptar")
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        dialog.present(self.main_window)
    
    def show_confirmation_dialog(self, title: str, message: str, callback=None):
        """Muestra un diálogo de confirmación"""
        dialog = Adw.AlertDialog()
        dialog.set_heading(title)
        dialog.set_body(message)
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("confirm", "Confirmar")
        dialog.set_response_appearance("confirm", Adw.ResponseAppearance.DESTRUCTIVE)
        
        if callback:
            dialog.connect("response", self._on_confirmation_response, callback)
        
        dialog.present(self.main_window)
    
    def _on_confirmation_response(self, dialog, response, callback):
        """Maneja la respuesta de diálogos de confirmación"""
        if response == "confirm" and callback:
            callback()
    
    def show_info_dialog(self, title: str, message: str):
        """Muestra un diálogo informativo"""
        dialog = Adw.AlertDialog()
        dialog.set_heading(title)
        dialog.set_body(message)
        dialog.add_response("ok", "Aceptar")
        dialog.present(self.main_window)

    def show_shortcuts_window(self):
        """Muestra la ventana moderna de atajos de teclado libadwaita"""
        try:
            from .shortcuts_window import show_shortcuts_window
            show_shortcuts_window(self.main_window)
        except Exception as e:
            print(f"Error cargando ventana de atajos libadwaita: {e}")
            self._show_shortcuts_fallback()
    
    def _show_shortcuts_fallback(self):
        """Fallback: muestra atajos básicos en un diálogo simple"""
        shortcuts_text = """Atajos de teclado principales:

    📁 ARCHIVO:
    • Ctrl+O: Abrir EPUB
    • Ctrl+Shift+O: Abrir carpeta proyecto  
    • Ctrl+N: Nuevo proyecto
    • Ctrl+S: Guardar cambios
    • Ctrl+Shift+E: Exportar EPUB

    ✏️ FORMATO HTML:
    • Ctrl+P: Convertir a párrafo
    • Ctrl+1/2/3: Encabezados H1/H2/H3
    • Ctrl+Shift+Q: Cita (blockquote)
    • Ctrl+L: Vincular estilos CSS

    🧭 NAVEGACIÓN:
    • Ctrl+Shift+1: Mostrar/ocultar estructura
    • Ctrl+Shift+2: Mostrar/ocultar previsualización
    • F11: Previsualización pantalla completa
    • Ctrl+G: Generar navegación (TOC)

    ❓ AYUDA:
    • Ctrl+?: Mostrar atajos
    • Ctrl+Shift+P: Preferencias"""

        dialog = Adw.AlertDialog()
        dialog.set_heading("Atajos de teclado")
        dialog.set_body(shortcuts_text)
        dialog.add_response("ok", "Cerrar")
        dialog.present(self.main_window)

    def show_batch_style_linking_dialog(self, selected_hrefs):
        """Muestra diálogo para vincular estilos a múltiples documentos"""
        
        # Obtener estilos disponibles
        css_items = self.main_window.core.list_items(kind=KIND_STYLE)
        
        if not css_items:
            self.main_window.show_error("No hay archivos CSS en el proyecto")
            return
        
        dialog = Adw.AlertDialog()
        dialog.set_heading("Vincular estilos CSS")
        dialog.set_body(f"Selecciona los archivos CSS que deseas vincular a {len(selected_hrefs)} documentos:")
        
        # Usar el mismo contenido que el diálogo individual
        content_box = self._create_style_dialog_content(css_items)
        dialog.set_extra_child(content_box)
        
        # Botones
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("apply", "Aplicar estilos")
        dialog.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        
        # Conectar respuesta pasando los hrefs seleccionados
        dialog.connect("response", self._on_batch_style_dialog_response, selected_hrefs)
        dialog.present(self.main_window)

    def _on_batch_style_dialog_response(self, dialog, response, selected_hrefs):
        """Maneja la respuesta del diálogo de estilos en lote"""
        if response != "apply":
            self._cleanup_style_dialog_refs()
            return
        
        try:
            # Obtener estilos seleccionados
            selected_styles = []
            if self._style_checkboxes:
                for href, checkbox in self._style_checkboxes.items():
                    if checkbox.get_active():
                        style_name = Path(href).name
                        selected_styles.append(style_name)
            
            if not selected_styles:
                self.main_window.show_error("Debes seleccionar al menos un archivo CSS")
                return
            
            clear_existing = (self._clear_existing_checkbox.get_active() 
                            if self._clear_existing_checkbox else True)
            
            # Obtener IDs de documentos
            doc_ids = []
            for href in selected_hrefs:
                try:
                    mi = self.main_window.core._get_item(href)
                    doc_ids.append(mi.id)
                except:
                    continue
            
            # Aplicar estilos en lote
            results = self.main_window.core.set_styles_for_documents(
                docs=doc_ids,
                styles=selected_styles,
                clear_existing=clear_existing,
                add_to_manifest_if_missing=True
            )
            
            # Mostrar resultado
            total_links = sum(len(links) for links in results.values())
            self.main_window.show_info(
                f"Se aplicaron {len(selected_styles)} estilos CSS a {len(doc_ids)} documentos "
                f"({total_links} vínculos totales)"
            )
            
        except Exception as e:
            self.main_window.show_error(f"Error vinculando estilos en lote: {e}")
        finally:
            self._cleanup_style_dialog_refs()

    def show_rename_dialog(self, href: str, current_name: str, resource_type: str):
        """Muestra diálogo para renombrar un recurso"""
        
        dialog = Adw.AlertDialog()
        dialog.set_heading("Renombrar recurso")
        dialog.set_body(f"Nuevo nombre para '{current_name}':")
        
        # Entry para el nuevo nombre
        entry = Gtk.Entry()
        entry.set_text(Path(current_name).stem)  # Sin extensión
        entry.select_region(0, -1)  # Seleccionar todo
        
        # Validación en tiempo real
        validation_label = Gtk.Label()
        validation_label.add_css_class("caption")
        
        def on_entry_changed(entry):
            new_name = entry.get_text().strip()
            is_valid, error_msg = self.main_window.core.validate_rename(href, new_name)
            
            if is_valid:
                validation_label.set_text("✓ Nombre válido")
                validation_label.remove_css_class("error")
                validation_label.add_css_class("success")
                dialog.set_response_enabled("rename", True)
            else:
                validation_label.set_text(f"✗ {error_msg}")
                validation_label.add_css_class("error")
                validation_label.remove_css_class("success")
                dialog.set_response_enabled("rename", False)
        
        entry.connect('changed', on_entry_changed)
        
        # Layout del diálogo
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.set_spacing(8)
        content_box.append(entry)
        content_box.append(validation_label)
        
        # Checkbox para actualizar referencias
        update_refs_check = Gtk.CheckButton()
        update_refs_check.set_label("Actualizar referencias en otros archivos")
        update_refs_check.set_active(True)
        content_box.append(update_refs_check)
        
        dialog.set_extra_child(content_box)
        
        # Botones
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("rename", "Renombrar")
        dialog.set_response_appearance("rename", Adw.ResponseAppearance.SUGGESTED)
        
        # Validación inicial
        on_entry_changed(entry)
        
        # Conectar respuesta
        dialog.connect("response", self._on_rename_response, 
                    href, entry, update_refs_check, current_name)
        
        dialog.present(self.main_window)

    def _on_rename_response(self, dialog, response, href: str, entry: Gtk.Entry, 
                        update_refs_check: Gtk.CheckButton, old_name: str):
        """Maneja la respuesta del diálogo de renombrado"""
        
        if response != "rename":
            return
        
        new_name = entry.get_text().strip()
        update_references = update_refs_check.get_active()
        
        if not new_name:
            return
        
        try:
            # Renombrar usando el core mejorado
            new_href = self.main_window.core.rename_item(
                href, 
                new_name, 
                update_references=update_references
            )
            
            # Actualizar UI
            self.main_window.refresh_structure()
            
            # Mensaje de éxito
            action_msg = "renombrado y referencias actualizadas" if update_references else "renombrado"
            self.main_window.show_info(f"'{old_name}' {action_msg} como '{Path(new_href).name}'")
            
            # Si era el recurso actual, actualizar referencia
            if self.main_window.current_resource == href:
                self.main_window.current_resource = new_href
                self.main_window.resource_title.set_text(f"Recurso: {Path(new_href).name}")
                
        except Exception as e:
            self.main_window.show_error(f"Error renombrando: {e}")

    def show_export_text_dialog(self):
        """Muestra diálogo para exportar capítulos a texto"""
        if not self.main_window.core:
            self.main_window.show_error("No hay proyecto abierto")
            return

        # Obtener documentos del EPUB
        documents = self.main_window.core.find_items(kind=KIND_DOCUMENT)
        if not documents:
            self.main_window.show_error("No hay documentos para exportar")
            return

        # Crear ventana de diálogo
        dialog = Adw.Window()
        dialog.set_title("Exportar a Texto")
        dialog.set_modal(True)
        dialog.set_transient_for(self.main_window)
        dialog.set_default_size(600, 500)

        # Contenido principal
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.set_spacing(12)
        content_box.set_margin_top(12)
        content_box.set_margin_bottom(12)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)

        # Header
        header_label = Gtk.Label()
        header_label.set_markup("<span size='large' weight='bold'>Exportar Capítulos a Texto</span>")
        header_label.set_halign(Gtk.Align.START)
        content_box.append(header_label)

        # Lista de capítulos con checkboxes
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_min_content_height(250)

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("boxed-list")

        # Agregar checkbox para cada documento
        document_checkboxes = {}

        # Checkbox "Seleccionar todos"
        select_all_row = Adw.ActionRow()
        select_all_row.set_title("Seleccionar todos los capítulos")
        select_all_checkbox = Gtk.CheckButton()
        select_all_checkbox.set_active(True)
        select_all_row.add_prefix(select_all_checkbox)
        select_all_row.set_activatable_widget(select_all_checkbox)
        listbox.append(select_all_row)

        # Separador
        separator = Gtk.Separator()
        listbox.append(separator)

        # Agregar cada documento
        for doc in documents:
            row = Adw.ActionRow()
            doc_name = Path(doc.href).stem.replace('_', ' ').replace('-', ' ').title()
            row.set_title(doc_name)
            row.set_subtitle(doc.href)

            checkbox = Gtk.CheckButton()
            checkbox.set_active(True)
            document_checkboxes[doc.href] = checkbox

            row.add_prefix(checkbox)
            row.set_activatable_widget(checkbox)
            listbox.append(row)

        scrolled.set_child(listbox)
        content_box.append(scrolled)

        # Opciones de exportación
        options_group = Adw.PreferencesGroup()
        options_group.set_title("Opciones de Exportación")

        # Opción: Archivo único vs archivos separados
        export_mode_row = Adw.ActionRow()
        export_mode_row.set_title("Modo de exportación")
        export_mode_row.set_subtitle("Cómo organizar el texto exportado")

        export_mode_combo = Gtk.ComboBoxText()
        export_mode_combo.append("single", "Un solo archivo")
        export_mode_combo.append("separate", "Archivos separados")
        export_mode_combo.set_active(0)
        export_mode_row.add_suffix(export_mode_combo)

        options_group.add(export_mode_row)

        # Selector de directorio destino
        destination_row = Adw.ActionRow()
        destination_row.set_title("Directorio de destino")
        destination_row.set_subtitle("Selecciona dónde guardar los archivos")

        destination_button = Gtk.Button()
        destination_button.set_label("Seleccionar carpeta...")
        destination_button.add_css_class("flat")
        destination_row.add_suffix(destination_button)

        options_group.add(destination_row)
        content_box.append(options_group)

        # Botones
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.set_spacing(6)
        button_box.set_halign(Gtk.Align.END)

        cancel_button = Gtk.Button()
        cancel_button.set_label("Cancelar")
        button_box.append(cancel_button)

        export_button = Gtk.Button()
        export_button.set_label("Exportar")
        export_button.add_css_class("suggested-action")
        button_box.append(export_button)

        content_box.append(button_box)
        dialog.set_content(content_box)

        # Variables para mantener referencias
        selected_destination = {"path": None}

        # Funcionalidad del checkbox "Seleccionar todos"
        def on_select_all_toggled(checkbox):
            state = checkbox.get_active()
            for doc_checkbox in document_checkboxes.values():
                doc_checkbox.set_active(state)

        select_all_checkbox.connect("toggled", on_select_all_toggled)

        # Funcionalidad del selector de directorio
        def on_select_destination(button):
            file_dialog = Gtk.FileDialog()
            file_dialog.set_title("Seleccionar directorio de destino")

            def on_folder_selected(dialog, result):
                try:
                    folder = dialog.select_folder_finish(result)
                    if folder:
                        selected_destination["path"] = folder.get_path()
                        destination_row.set_subtitle(f"📁 {selected_destination['path']}")
                        export_button.set_sensitive(True)
                except Exception as e:
                    print(f"Error selecting folder: {e}")

            file_dialog.select_folder(self.main_window, None, on_folder_selected)

        destination_button.connect("clicked", on_select_destination)

        # Funcionalidad del botón exportar
        def on_export_clicked(button):
            # Obtener capítulos seleccionados
            selected_docs = [href for href, checkbox in document_checkboxes.items()
                           if checkbox.get_active()]

            if not selected_docs:
                self.main_window.show_error("Selecciona al menos un capítulo")
                return

            if not selected_destination["path"]:
                self.main_window.show_error("Selecciona un directorio de destino")
                return

            # Obtener modo de exportación
            export_mode = export_mode_combo.get_active_id()

            # Ejecutar exportación
            try:
                self._execute_text_export(selected_docs, selected_destination["path"], export_mode)
                dialog.close()
                self.main_window.show_info(f"Texto exportado exitosamente a {selected_destination['path']}")
            except Exception as e:
                self.main_window.show_error(f"Error exportando: {e}")

        export_button.connect("clicked", on_export_clicked)
        export_button.set_sensitive(False)  # Deshabilitado hasta seleccionar destino

        # Funcionalidad del botón cancelar
        cancel_button.connect("clicked", lambda b: dialog.close())

        dialog.present()

    def _execute_text_export(self, selected_docs: list, destination_path: str, export_mode: str):
        """Ejecuta la exportación de documentos a texto"""
        import html
        import re
        from pathlib import Path

        destination = Path(destination_path)

        if export_mode == "single":
            # Exportar todo a un solo archivo
            output_file = destination / "libro_exportado.txt"

            with open(output_file, 'w', encoding='utf-8') as f:
                for i, href in enumerate(selected_docs):
                    # Obtener contenido HTML
                    html_content = self.main_window.core.read_text(href)

                    # Convertir a texto plano
                    plain_text = self._html_to_plain_text(html_content)

                    # Agregar separador entre capítulos
                    if i > 0:
                        f.write("\n\n" + "="*50 + "\n\n")

                    # Agregar título del capítulo
                    chapter_title = Path(href).stem.replace('_', ' ').replace('-', ' ').title()
                    f.write(f"{chapter_title}\n\n")

                    # Agregar contenido
                    f.write(plain_text)
                    f.write("\n")

        else:  # separate
            # Exportar cada capítulo a archivo separado
            for href in selected_docs:
                # Obtener contenido HTML
                html_content = self.main_window.core.read_text(href)

                # Convertir a texto plano
                plain_text = self._html_to_plain_text(html_content)

                # Nombre del archivo
                chapter_name = Path(href).stem
                output_file = destination / f"{chapter_name}.txt"

                # Escribir archivo
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(plain_text)

    def _html_to_plain_text(self, html_content: str) -> str:
        """Convierte contenido HTML a texto plano"""
        import re
        import html

        # Remover scripts y styles
        text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Convertir algunos elementos HTML a texto con formato
        text = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n\n\1\n\n', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<br[^>]*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</?em[^>]*>', '*', text, flags=re.IGNORECASE)
        text = re.sub(r'</?strong[^>]*>', '**', text, flags=re.IGNORECASE)
        text = re.sub(r'</?b[^>]*>', '**', text, flags=re.IGNORECASE)
        text = re.sub(r'</?i[^>]*>', '*', text, flags=re.IGNORECASE)

        # Remover todas las demás etiquetas HTML
        text = re.sub(r'<[^>]+>', '', text)

        # Decodificar entidades HTML
        text = html.unescape(text)

        # Limpiar espacios excesivos
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = text.strip()

        return text
