"""
ui/actions.py
Gestor de acciones principales - Abrir, guardar, exportar, preferencias
"""

from gi.repository import Gtk, Gio, Adw
from pathlib import Path
from typing import TYPE_CHECKING

from core.guten_core import GutenCore

if TYPE_CHECKING:
    from .main_window import GutenAIWindow


class ActionManager:
    """Gestiona las acciones principales de la aplicación"""
    
    def __init__(self, main_window: 'GutenAIWindow'):
        self.main_window = main_window
    
    def setup_actions(self):
        """Configura todas las acciones de la aplicación"""
        
        # Abrir EPUB
        open_action = Gio.SimpleAction.new("open_epub", None)
        open_action.connect("activate", self._on_open_epub)
        self.main_window.add_action(open_action)
        
        # Abrir carpeta proyecto
        open_folder_action = Gio.SimpleAction.new("open_folder", None)
        open_folder_action.connect("activate", self._on_open_folder)
        self.main_window.add_action(open_folder_action)
        
        # Nuevo proyecto
        new_action = Gio.SimpleAction.new("new_project", None)
        new_action.connect("activate", self._on_new_project)
        self.main_window.add_action(new_action)
        
        # Exportar EPUB
        export_action = Gio.SimpleAction.new("export_epub", None)
        export_action.connect("activate", self._on_export_epub)
        self.main_window.add_action(export_action)

        # Exportar a texto
        export_text_action = Gio.SimpleAction.new("export_text", None)
        export_text_action.connect("activate", self._on_export_text)
        self.main_window.add_action(export_text_action)

        # Preferencias
        prefs_action = Gio.SimpleAction.new("preferences", None)
        prefs_action.connect("activate", self._on_preferences)
        self.main_window.add_action(prefs_action)
        
        # Acción para generar NAV
        gen_nav_action = Gio.SimpleAction.new("generate_nav", None)
        gen_nav_action.connect("activate", self._on_generate_nav)
        self.main_window.add_action(gen_nav_action)
        
        # Mostrar atajos
        shortcuts_action = Gio.SimpleAction.new("show_shortcuts", None)
        shortcuts_action.connect("activate", self._on_show_shortcuts)
        self.main_window.add_action(shortcuts_action)

        # Acciones de recursos
        create_doc_action = Gio.SimpleAction.new("create_document", None)
        create_doc_action.connect("activate", self._on_create_document)
        self.main_window.add_action(create_doc_action)

        create_css_action = Gio.SimpleAction.new("create_css", None)
        create_css_action.connect("activate", self._on_create_css)
        self.main_window.add_action(create_css_action)

        import_image_action = Gio.SimpleAction.new("import_image", None)
        import_image_action.connect("activate", self._on_import_image)
        self.main_window.add_action(import_image_action)

        import_font_action = Gio.SimpleAction.new("import_font", None)
        import_font_action.connect("activate", self._on_import_font)
        self.main_window.add_action(import_font_action)

        rename_action = Gio.SimpleAction.new("rename_resource", None)
        rename_action.connect("activate", self._on_rename_resource)
        self.main_window.add_action(rename_action)

        delete_action = Gio.SimpleAction.new("delete_resource", None)
        delete_action.connect("activate", self._on_delete_resource)
        self.main_window.add_action(delete_action)
        
        # *** CONFIGURAR ATAJOS DE TECLADO ***
        self._setup_keyboard_shortcuts()
    
    def _setup_keyboard_shortcuts(self):
        """Configura los atajos de teclado"""
        app = self.main_window.get_application()
        
        # Atajos de archivo
        app.set_accels_for_action("win.open_epub", ["<Ctrl>o"])
        app.set_accels_for_action("win.open_folder", ["<Ctrl><Shift>o"])
        app.set_accels_for_action("win.new_project", ["<Ctrl>n"])
        app.set_accels_for_action("win.export_epub", ["<Ctrl><Shift>e"])
        app.set_accels_for_action("app.quit", ["<Ctrl>q"])
        
        # Atajos de formato HTML
        app.set_accels_for_action("win.wrap_paragraph", ["<Ctrl>p"])
        app.set_accels_for_action("win.wrap_h1", ["<Ctrl>1"])
        app.set_accels_for_action("win.wrap_h2", ["<Ctrl>2"])
        app.set_accels_for_action("win.wrap_h3", ["<Ctrl>3"])
        app.set_accels_for_action("win.wrap_blockquote", ["<Ctrl><Shift>q"])
        app.set_accels_for_action("win.link_styles", ["<Ctrl>l"])
        
        # Atajos de navegación
        app.set_accels_for_action("win.toggle_left_sidebar", ["<Ctrl><Shift>1"])
        app.set_accels_for_action("win.toggle_right_sidebar", ["<Ctrl><Shift>2"])
        app.set_accels_for_action("win.fullscreen_preview", ["F11"])
        app.set_accels_for_action("win.generate_nav", ["<Ctrl>g"])
        
        # Atajos de ayuda
        app.set_accels_for_action("win.show_shortcuts", ["F1"])  # Solo F1 por ahora
        app.set_accels_for_action("win.preferences", ["<Ctrl><Shift>p"])

        # Atajos de IA (cambiado para evitar conflicto)
        app.set_accels_for_action("win.ai_correction", ["<Ctrl><Shift>f7"])

        # Atajos de recursos (sin conflictos)
        app.set_accels_for_action("win.create_document", ["<Ctrl><Shift>n"])
        app.set_accels_for_action("win.create_css", ["<Ctrl><Shift>s"])  # Cambiado de C a S
        app.set_accels_for_action("win.import_image", ["<Ctrl><Shift>m"])  # Cambiado de I a M
        app.set_accels_for_action("win.import_font", ["<Ctrl><Shift>t"])  # Cambiado de F a T
        app.set_accels_for_action("win.rename_resource", ["F2"])  # Renombrar recurso seleccionado
        app.set_accels_for_action("win.delete_resource", ["<Ctrl>Delete"])  # Eliminar recurso seleccionado

        # Crear acciones para toggles de sidebar
        left_toggle_action = Gio.SimpleAction.new("toggle_left_sidebar", None)
        left_toggle_action.connect("activate", lambda a, p: self.main_window.left_sidebar_btn.set_active(
            not self.main_window.left_sidebar_btn.get_active()))
        self.main_window.add_action(left_toggle_action)
        
        right_toggle_action = Gio.SimpleAction.new("toggle_right_sidebar", None)
        right_toggle_action.connect("activate", lambda a, p: self.main_window.right_sidebar_btn.set_active(
            not self.main_window.right_sidebar_btn.get_active()))
        self.main_window.add_action(right_toggle_action)
        
        # Acción para fullscreen preview
        fullscreen_action = Gio.SimpleAction.new("fullscreen_preview", None)
        fullscreen_action.connect("activate", lambda a, p: self.main_window.sidebar_right._on_fullscreen_preview(None))
        self.main_window.add_action(fullscreen_action)
    
    def _on_show_shortcuts(self, action, param):
        """Muestra la ventana de atajos"""
        self.main_window.dialog_manager.show_shortcuts_window()
    
    def _on_open_epub(self, action, param):
        """Abre un archivo EPUB existente"""
        
        dialog = Gtk.FileDialog()
        dialog.set_title("Abrir EPUB")
        
        # Filtro para archivos EPUB
        filter_epub = Gtk.FileFilter()
        filter_epub.set_name("Archivos EPUB")
        filter_epub.add_pattern("*.epub")
        
        filters = Gio.ListStore()
        filters.append(filter_epub)
        dialog.set_filters(filters)
        
        dialog.open(self.main_window, None, self._on_open_epub_response)
    
    def _on_open_epub_response(self, dialog, result):
        """Maneja la respuesta del diálogo de apertura de EPUB"""
        try:
            file = dialog.open_finish(result)
            if file:
                epub_path = Path(file.get_path())
                
                # Verificar que el archivo existe y es legible
                if not epub_path.exists():
                    self.main_window.show_error("El archivo EPUB no existe")
                    return
                
                if not epub_path.is_file():
                    self.main_window.show_error("La ruta seleccionada no es un archivo")
                    return
                
                # Directorio temporal para descomprimir
                workdir = Path.home() / "GutenAI" / "temp"
                workdir.mkdir(parents=True, exist_ok=True)
                
                # Abrir EPUB usando el core
                self.main_window.core = GutenCore.open_epub(epub_path, workdir)
                
                # Actualizar UI
                self._update_ui_after_open()
                self.main_window.show_info(f"EPUB '{epub_path.name}' abierto correctamente")
                
        except Exception as e:
            self.main_window.show_error(f"Error abriendo EPUB: {e}")
    
    def _on_open_folder(self, action, param):
        """Abre una carpeta de proyecto EPUB existente"""
        
        dialog = Gtk.FileDialog()
        dialog.set_title("Abrir carpeta proyecto EPUB")
        dialog.select_folder(self.main_window, None, self._on_open_folder_response)
    
    def _on_open_folder_response(self, dialog, result):
        """Maneja la respuesta del diálogo de apertura de carpeta"""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                project_dir = Path(folder.get_path())
                
                # Verificar estructura válida de proyecto EPUB
                if not self._validate_epub_project(project_dir):
                    return
                
                # Abrir proyecto usando el core
                self.main_window.core = GutenCore.open_folder(project_dir)
                
                # Actualizar UI
                self._update_ui_after_open()
                
                # Mensaje de éxito
                metadata = self.main_window.core.get_metadata()
                project_name = metadata.get("title", project_dir.name)
                self.main_window.show_info(f"Proyecto '{project_name}' abierto correctamente")
                
        except Exception as e:
            self.main_window.show_error(f"Error abriendo carpeta proyecto: {e}")
    
    def _validate_epub_project(self, project_dir: Path) -> bool:
        """Valida que una carpeta contenga un proyecto EPUB válido"""
        
        # Verificar container.xml
        container_path = project_dir / "META-INF" / "container.xml"
        if not container_path.exists():
            self.main_window.show_error(
                "La carpeta seleccionada no contiene un proyecto EPUB válido "
                "(falta META-INF/container.xml)"
            )
            return False
        
        # Verificar que sea un directorio
        if not project_dir.is_dir():
            self.main_window.show_error("La ruta seleccionada no es un directorio")
            return False
        
        return True
    
    def _on_new_project(self, action, param):
        """Crea un nuevo proyecto EPUB"""
        
        dialog = Gtk.FileDialog()
        dialog.set_title("Crear nuevo proyecto EPUB - Selecciona carpeta contenedora")
        dialog.select_folder(self.main_window, None, self._on_new_project_response)
    
    def _on_new_project_response(self, dialog, result):
        """Maneja la respuesta del diálogo de nuevo proyecto"""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                parent_dir = Path(folder.get_path())
                project_dir = parent_dir / "NuevoEPUB"
                
                # Verificar que el directorio de destino no exista
                if project_dir.exists():
                    self.main_window.show_error(
                        f"Ya existe una carpeta '{project_dir.name}' en la ubicación seleccionada"
                    )
                    return
                
                # Crear proyecto usando el core
                self.main_window.core = GutenCore.new_project(
                    project_dir,
                    title="Nuevo Libro",
                    lang="es"
                )
                
                # Actualizar UI
                self._update_ui_after_open()
                self.main_window.show_info(f"Nuevo proyecto creado en '{project_dir}'")
                
        except Exception as e:
            self.main_window.show_error(f"Error creando proyecto: {e}")
    
    def _update_ui_after_open(self):
        """Actualiza la UI después de abrir un proyecto"""
        if not self.main_window.core:
            return
        
        # Actualizar título del libro
        metadata = self.main_window.core.get_metadata()
        book_title = metadata.get("title", "EPUB sin título")
        if not book_title or book_title == "EPUB sin título":
            book_title = self.main_window.core.workdir.name
        
        self.main_window.update_book_title(book_title)
        
        # Refrescar estructura en sidebar izquierdo
        self.main_window.refresh_structure()
        
        # Limpiar editor y previsualización
        self.main_window.central_editor.set_text("")
        self.main_window.sidebar_right.web_view.load_html("", None)
        
        # Resetear recurso actual
        self.main_window.current_resource = None
        self.main_window.resource_title.set_text("Ningún recurso seleccionado")
    
    def _on_export_epub(self, action, param):
        """Exporta el EPUB actual"""
        
        if not self.main_window.core:
            self.main_window.show_error("No hay ningún proyecto abierto")
            return
        
        # Verificar que hay contenido para exportar
        spine = self.main_window.core.get_spine()
        if not spine:
            self.main_window.show_error(
                "El proyecto no tiene documentos en el spine. "
                "Agrega al menos un capítulo antes de exportar."
            )
            return
        
        dialog = Gtk.FileDialog()
        dialog.set_title("Exportar EPUB")
        
        # Nombre sugerido basado en el título del libro
        metadata = self.main_window.core.get_metadata()
        suggested_name = metadata.get("title", "libro")
        # Limpiar caracteres no válidos para nombre de archivo
        suggested_name = "".join(c for c in suggested_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not suggested_name:
            suggested_name = "libro"
        
        dialog.set_initial_name(f"{suggested_name}.epub")
        dialog.save(self.main_window, None, self._on_export_epub_response)
    
    def _on_export_epub_response(self, dialog, result):
        """Maneja la respuesta del diálogo de exportación"""
        try:
            file = dialog.save_finish(result)
            if file:
                output_path = Path(file.get_path())
                
                # Asegurar extensión .epub
                if not output_path.suffix.lower() == '.epub':
                    output_path = output_path.with_suffix('.epub')
                
                # Verificar permisos de escritura
                try:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    # Test de escritura
                    test_file = output_path.with_suffix('.tmp')
                    test_file.write_text("test")
                    test_file.unlink()
                except Exception as e:
                    self.main_window.show_error(f"No se puede escribir en la ubicación seleccionada: {e}")
                    return
                
                # Exportar usando el core
                self.main_window.core.export_epub(output_path, include_unreferenced=False)
                
                self.main_window.show_info(f"EPUB exportado correctamente a '{output_path.name}'")
                
        except Exception as e:
            self.main_window.show_error(f"Error exportando: {e}")
    
    def _on_generate_nav(self, action, param):
        """Genera el archivo de navegación (TOC)"""
        
        if not self.main_window.core:
            self.main_window.show_error("No hay proyecto abierto")
            return
        
        try:
            # Generar NAV desde headings
            nav_href = self.main_window.core.generate_nav_from_headings(
                levels=(1, 2, 3),
                overwrite=True,
                add_missing_ids=True
            )
            
            self.main_window.show_info("Navegación (TOC) generada automáticamente")
            
            # Refrescar estructura para mostrar el nav actualizado
            self.main_window.refresh_structure()
            
        except Exception as e:
            self.main_window.show_error(f"Error generando navegación: {e}")
    
    def _on_preferences(self, action, param):
        """Abre la ventana de preferencias"""
        self._show_preferences_dialog()
    
    def _show_preferences_dialog(self):
        """Muestra el diálogo de preferencias"""
        from .preferences_dialog import show_preferences_dialog
        show_preferences_dialog(self.main_window)
    
    def close_current_project(self):
        """Cierra el proyecto actual"""
        if self.main_window.core:
            # Limpiar referencias
            self.main_window.core = None
            self.main_window.current_resource = None
            
            # Resetear UI
            self.main_window.update_book_title("Sin libro abierto")
            self.main_window.resource_title.set_text("Ningún recurso seleccionado")
            self.main_window.central_editor.set_text("")
            self.main_window.sidebar_right.web_view.load_html("", None)
            
            # Limpiar estructura
            self.main_window.refresh_structure()
    
    def has_unsaved_changes(self) -> bool:
        """Verifica si hay cambios sin guardar"""
        if not self.main_window.core:
            return False
        
        # Verificar si el editor tiene cambios sin guardar
        return self.main_window.central_editor.has_unsaved_changes()
    
    def get_project_info(self) -> dict:
        """Obtiene información del proyecto actual"""
        if not self.main_window.core:
            return {}
        
        metadata = self.main_window.core.get_metadata()
        spine = self.main_window.core.get_spine()
        
        items_count = {
            "documents": len(self.main_window.core.list_items("document")),
            "styles": len(self.main_window.core.list_items("style")),
            "images": len(self.main_window.core.list_items("image")),
            "fonts": len(self.main_window.core.list_items("font")),
            "audio": len(self.main_window.core.list_items("audio")),
            "video": len(self.main_window.core.list_items("video")),
        }
        
        return {
            "title": metadata.get("title", "Sin título"),
            "language": metadata.get("language", "No especificado"),
            "identifier": metadata.get("identifier", "No especificado"),
            "spine_items": len(spine),
            "total_resources": len(self.main_window.core.list_items()),
            "items_by_type": items_count,
            "project_path": str(self.main_window.core.workdir),
        }

    def _on_create_document(self, action, param):
        """Crea un nuevo documento HTML"""
        from core.guten_core import KIND_DOCUMENT
        self.main_window.dialog_manager.show_create_resource_dialog(KIND_DOCUMENT)

    def _on_create_css(self, action, param):
        """Crea un nuevo archivo CSS"""
        from core.guten_core import KIND_STYLE
        self.main_window.dialog_manager.show_create_resource_dialog(KIND_STYLE)

    def _on_import_image(self, action, param):
        """Importa una imagen desde archivo"""
        if not self.main_window.core:
            self.main_window.show_error("No hay proyecto abierto")
            return

        dialog = Gtk.FileDialog()
        dialog.set_title("Seleccionar imagen para importar")

        # Filtros para imágenes
        filters = Gio.ListStore.new(Gtk.FileFilter)

        # Filtro para imágenes
        image_filter = Gtk.FileFilter()
        image_filter.set_name("Imágenes")
        image_filter.add_mime_type("image/jpeg")
        image_filter.add_mime_type("image/png")
        image_filter.add_mime_type("image/gif")
        image_filter.add_mime_type("image/webp")
        image_filter.add_mime_type("image/svg+xml")
        filters.append(image_filter)

        # Filtro para todos los archivos
        all_filter = Gtk.FileFilter()
        all_filter.set_name("Todos los archivos")
        all_filter.add_pattern("*")
        filters.append(all_filter)

        dialog.set_filters(filters)
        dialog.open(self.main_window, None, self._on_import_image_response)

    def _on_import_image_response(self, dialog, result):
        """Maneja la respuesta del selector de imagen"""
        try:
            file = dialog.open_finish(result)
            if file:
                file_path = file.get_path()
                # TODO: Implementar importación de imagen al proyecto
                self.main_window.show_info(f"Importar imagen: {file_path}")
        except Exception as e:
            if "dismissed" not in str(e).lower():
                print(f"Error seleccionando imagen: {e}")

    def _on_import_font(self, action, param):
        """Importa una fuente"""
        from core.guten_core import KIND_FONT
        self.main_window.dialog_manager.show_create_resource_dialog(KIND_FONT)

    def _on_rename_resource(self, action, param):
        """Renombra el recurso seleccionado usando el diálogo existente"""
        if not self.main_window.core or not self.main_window.current_resource:
            self.main_window.show_error("No hay recurso seleccionado")
            return

        # Obtener información del recurso actual
        current_href = self.main_window.current_resource
        current_name = current_href.split('/')[-1] if '/' in current_href else current_href

        # Determinar tipo de recurso
        resource_type = "document"  # Por defecto
        if current_name.endswith(('.css',)):
            resource_type = "style"
        elif current_name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp')):
            resource_type = "image"
        elif current_name.endswith(('.ttf', '.otf', '.woff', '.woff2')):
            resource_type = "font"

        # Usar el diálogo existente que ya está implementado
        self.main_window.dialog_manager.show_rename_dialog(current_href, current_name, resource_type)

    def _on_delete_resource(self, action, param):
        """Elimina el recurso seleccionado"""
        if not self.main_window.core or not self.main_window.current_resource:
            self.main_window.show_error("No hay recurso seleccionado")
            return

        # TODO: Implementar eliminación de recurso con confirmación
        # Por ahora solo mostramos mensaje
        resource_name = self.main_window.current_resource
        self.main_window.show_info(f"Eliminar recurso: {resource_name}")

    def _on_export_text(self, action, param):
        """Muestra el diálogo de exportación a texto"""
        if not self.main_window.core:
            self.main_window.show_error("No hay ningún proyecto abierto")
            return

        # Delegar al dialog manager
        self.main_window.dialog_manager.show_export_text_dialog()