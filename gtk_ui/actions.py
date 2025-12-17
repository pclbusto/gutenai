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

        # Acerca de
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.main_window.add_action(about_action)
        
        # Acción para generar NAV
        gen_nav_action = Gio.SimpleAction.new("generate_nav", None)
        gen_nav_action.connect("activate", self._on_generate_nav)
        self.main_window.add_action(gen_nav_action)
        
        # Mostrar atajos - Eliminado (se usa set_help_overlay nativo)
        # shortcuts_action = Gio.SimpleAction.new("show_shortcuts", None)
        # shortcuts_action.connect("activate", self._on_show_shortcuts)
        # self.main_window.add_action(shortcuts_action)

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

        # Validación EPUB con epubcheck
        validate_epub_action = Gio.SimpleAction.new("validate_epub", None)
        validate_epub_action.connect("activate", self._on_validate_epub)
        self.main_window.add_action(validate_epub_action)

        # Recargar WebView
        reload_webkit_action = Gio.SimpleAction.new("reload_webkit", None)
        reload_webkit_action.connect("activate", self._on_reload_webkit)
        self.main_window.add_action(reload_webkit_action)

        # Acciones de búsqueda en documento
        search_action = Gio.SimpleAction.new("search_in_document", None)
        search_action.connect("activate", self._on_search_in_document)
        self.main_window.add_action(search_action)

        search_replace_action = Gio.SimpleAction.new("search_and_replace", None)
        search_replace_action.connect("activate", self._on_search_and_replace)
        self.main_window.add_action(search_replace_action)

        global_search_replace_action = Gio.SimpleAction.new("global_search_replace", None)
        global_search_replace_action.connect("activate", self._on_global_search_replace)
        self.main_window.add_action(global_search_replace_action)

        search_next_action = Gio.SimpleAction.new("search_next", None)
        search_next_action.connect("activate", self._on_search_next)
        self.main_window.add_action(search_next_action)

        search_prev_action = Gio.SimpleAction.new("search_prev", None)
        search_prev_action.connect("activate", self._on_search_prev)
        self.main_window.add_action(search_prev_action)

        # Estadísticas del libro
        statistics_action = Gio.SimpleAction.new("show_statistics", None)
        statistics_action.connect("activate", self._on_show_statistics)
        self.main_window.add_action(statistics_action)

        # Estadísticas del capítulo actual
        current_chapter_stats_action = Gio.SimpleAction.new("show_current_chapter_statistics", None)
        current_chapter_stats_action.connect("activate", self._on_show_current_chapter_statistics)
        self.main_window.add_action(current_chapter_stats_action)

        # Renombrado en lote
        batch_rename_action = Gio.SimpleAction.new("batch_rename", None)
        batch_rename_action.connect("activate", self._on_batch_rename)
        self.main_window.add_action(batch_rename_action)

        # Dividir capítulo
        split_chapter_action = Gio.SimpleAction.new("split_chapter", None)
        split_chapter_action.connect("activate", self._on_split_chapter)
        self.main_window.add_action(split_chapter_action)

        # Acciones de formato HTML (delegadas al editor)
        wrap_paragraph_action = Gio.SimpleAction.new("wrap_paragraph", None)
        wrap_paragraph_action.connect("activate", self._on_wrap_paragraph)
        self.main_window.add_action(wrap_paragraph_action)

        wrap_h1_action = Gio.SimpleAction.new("wrap_h1", None)
        wrap_h1_action.connect("activate", self._on_wrap_h1)
        self.main_window.add_action(wrap_h1_action)

        wrap_h2_action = Gio.SimpleAction.new("wrap_h2", None)
        wrap_h2_action.connect("activate", self._on_wrap_h2)
        self.main_window.add_action(wrap_h2_action)

        wrap_h3_action = Gio.SimpleAction.new("wrap_h3", None)
        wrap_h3_action.connect("activate", self._on_wrap_h3)
        self.main_window.add_action(wrap_h3_action)

        wrap_blockquote_action = Gio.SimpleAction.new("wrap_blockquote", None)
        wrap_blockquote_action.connect("activate", self._on_wrap_blockquote)
        self.main_window.add_action(wrap_blockquote_action)

        link_styles_action = Gio.SimpleAction.new("link_styles", None)
        link_styles_action.connect("activate", self._on_link_styles)
        self.main_window.add_action(link_styles_action)

        # Acción de guardado manual
        save_action = Gio.SimpleAction.new("save_current", None)
        save_action.connect("activate", self._on_save_current)
        self.main_window.add_action(save_action)

        # Acciones para toggles de sidebar
        left_toggle_action = Gio.SimpleAction.new("toggle_left_sidebar", None)
        left_toggle_action.connect("activate", self._on_toggle_left_sidebar)
        self.main_window.add_action(left_toggle_action)

        right_toggle_action = Gio.SimpleAction.new("toggle_right_sidebar", None)
        right_toggle_action.connect("activate", self._on_toggle_right_sidebar)
        self.main_window.add_action(right_toggle_action)

        # Acción para fullscreen preview
        fullscreen_action = Gio.SimpleAction.new("fullscreen_preview", None)
        fullscreen_action.connect("activate", self._on_fullscreen_preview)
        self.main_window.add_action(fullscreen_action)

        # *** CONFIGURAR ATAJOS DE TECLADO ***
        self._setup_keyboard_shortcuts()
    
    def _setup_keyboard_shortcuts(self):
        """Configura los atajos de teclado"""
        app = self.main_window.get_application()
        
        # Atajos de archivo
        app.set_accels_for_action("win.open_epub", ["<Ctrl>o"])
        app.set_accels_for_action("win.open_folder", ["<Ctrl><Shift>o"])
        app.set_accels_for_action("win.new_project", ["<Ctrl>n"])
        app.set_accels_for_action("win.save_current", ["<Ctrl>s"])
        app.set_accels_for_action("win.export_epub", ["<Ctrl><Shift>e"])
        app.set_accels_for_action("app.quit", ["<Ctrl>q"])
        
        # Atajos de formato HTML
        app.set_accels_for_action("win.wrap_paragraph", ["<Ctrl>p"])
        app.set_accels_for_action("win.wrap_h1", ["<Ctrl>1"])
        app.set_accels_for_action("win.wrap_h2", ["<Ctrl>2"])
        app.set_accels_for_action("win.wrap_h3", ["<Ctrl>3"])
        app.set_accels_for_action("win.wrap_blockquote", ["<Ctrl><Shift>q"])
        app.set_accels_for_action("win.wrap_unordered_list", ["<Ctrl><Alt>u"])
        app.set_accels_for_action("win.wrap_ordered_list", ["<Ctrl><Alt>o"])
        app.set_accels_for_action("win.wrap_list_item", ["<Ctrl><Shift>i"])
        app.set_accels_for_action("win.link_styles", ["<Ctrl>l"])
        
        # Atajos de navegación
        app.set_accels_for_action("win.toggle_left_sidebar", ["F9"])
        app.set_accels_for_action("win.toggle_right_sidebar", ["F10"])
        app.set_accels_for_action("win.fullscreen_preview", ["F11"])
        app.set_accels_for_action("win.generate_nav", ["<Ctrl>g"])
        
        # Atajos de ayuda
        app.set_accels_for_action("win.show-help-overlay", ["F1"])  # Mapear explícitamente F1 al help overlay estándar
        app.set_accels_for_action("win.preferences", ["<Ctrl><Shift>p"])
        app.set_accels_for_action("win.validate_epub", ["<Ctrl><Shift>v"])
        app.set_accels_for_action("win.reload_webkit", ["F5"])  # Recargar previsualización

        # Atajos de IA (cambiado para evitar conflicto)
        app.set_accels_for_action("win.ai_correction", ["<Ctrl><Shift>F7"])

        # Atajos de recursos (sin conflictos)
        app.set_accels_for_action("win.create_document", ["<Ctrl><Shift>n"])
        app.set_accels_for_action("win.create_css", ["<Ctrl><Shift>s"])  # Cambiado de C a S
        app.set_accels_for_action("win.import_image", ["<Ctrl><Shift>m"])  # Cambiado de I a M
        app.set_accels_for_action("win.import_font", ["<Ctrl><Shift>t"])  # Cambiado de F a T
        app.set_accels_for_action("win.rename_resource", ["F2"])  # Renombrar recurso seleccionado
        app.set_accels_for_action("win.delete_resource", ["<Ctrl>Delete"])  # Eliminar recurso seleccionado
        app.set_accels_for_action("win.batch_rename", ["<Ctrl><Shift>r"])  # Renombrado en lote

        # Atajos de búsqueda
        app.set_accels_for_action("win.search_in_document", ["<Ctrl>f"])
        app.set_accels_for_action("win.search_and_replace", ["<Ctrl>h"])
        app.set_accels_for_action("win.search_next", ["F3"])
        app.set_accels_for_action("win.search_prev", ["<Shift>F3"])
        app.set_accels_for_action("win.global_search_replace", ["<Ctrl><Shift>h"])

        # Atajos de estadísticas
        app.set_accels_for_action("win.show_current_chapter_statistics", ["F6"])
        app.set_accels_for_action("win.show_statistics", ["<Ctrl>F6"])
    
    # def _on_show_shortcuts(self, action, param):
    #     """Muestra la ventana de atajos"""
    #     self.main_window.dialog_manager.show_shortcuts_window()
    
    def _on_open_epub(self, action, param):
        """Abre un archivo EPUB existente"""
        from .settings_manager import get_settings

        dialog = Gtk.FileDialog()
        dialog.set_title("Abrir EPUB")

        # Establecer carpeta inicial desde las preferencias
        settings = get_settings()
        workspace_dir = settings.get_workspace_directory()
        initial_folder = Gio.File.new_for_path(str(workspace_dir))
        dialog.set_initial_folder(initial_folder)

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
        import shutil
        import tempfile

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

                # Limpiar proyecto anterior si existe
                self._cleanup_previous_project()

                # Crear carpeta temporal única
                temp_dir = Path(tempfile.mkdtemp(prefix=f"gutenai_{epub_path.stem}_"))
                print(f"[Open EPUB] Usando carpeta temporal: {temp_dir}")

                # Descomprimir el EPUB en la carpeta temporal
                self.main_window.core = GutenCore.open_epub(epub_path, temp_dir)

                # Guardar estado
                self.main_window.original_epub_path = epub_path
                self.main_window.temp_workdir = temp_dir
                self.main_window.is_new_project = False

                # Actualizar UI
                self._update_ui_after_open()
                self.main_window.show_info(f"EPUB '{epub_path.name}' abierto")

        except Exception as e:
            self.main_window.show_error(f"Error abriendo EPUB: {e}")
    
    def _cleanup_previous_project(self):
        """Limpia el proyecto anterior si existe"""
        import shutil

        # Si hay una carpeta temporal, eliminarla
        if self.main_window.temp_workdir and self.main_window.temp_workdir.exists():
            try:
                print(f"[Cleanup] Eliminando carpeta temporal: {self.main_window.temp_workdir}")
                shutil.rmtree(self.main_window.temp_workdir)
                self.main_window.temp_workdir = None
            except Exception as e:
                print(f"[Cleanup] Error eliminando carpeta temporal: {e}")

        # Resetear estado
        self.main_window.core = None
        self.main_window.current_resource = None
        self.main_window.original_epub_path = None

    def _on_open_folder(self, action, param):
        """Abre una carpeta de proyecto EPUB existente"""
        from .settings_manager import get_settings

        dialog = Gtk.FileDialog()
        dialog.set_title("Abrir carpeta proyecto EPUB")

        # Establecer carpeta inicial desde las preferencias
        settings = get_settings()
        workspace_dir = settings.get_workspace_directory()
        initial_folder = Gio.File.new_for_path(str(workspace_dir))
        dialog.set_initial_folder(initial_folder)

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

                # Limpiar proyecto anterior si existe
                self._cleanup_previous_project()

                # Abrir proyecto usando el core
                self.main_window.core = GutenCore.open_folder(project_dir)

                # Marcar como proyecto persistente (NO temporal)
                self.main_window.is_new_project = True
                self.main_window.temp_workdir = None
                self.main_window.original_epub_path = None

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
        from .settings_manager import get_settings

        dialog = Gtk.FileDialog()
        dialog.set_title("Crear nuevo proyecto EPUB - Selecciona carpeta del proyecto")

        # Establecer carpeta inicial desde las preferencias
        settings = get_settings()
        workspace_dir = settings.get_workspace_directory()
        initial_folder = Gio.File.new_for_path(str(workspace_dir))
        dialog.set_initial_folder(initial_folder)

        dialog.select_folder(self.main_window, None, self._on_new_project_response)
    
    def _on_new_project_response(self, dialog, result):
        """Maneja la respuesta del diálogo de nuevo proyecto"""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                project_dir = Path(folder.get_path())

                # Verificar que la carpeta esté vacía o solo tenga archivos ocultos
                existing_files = [f for f in project_dir.iterdir() if not f.name.startswith('.')]
                if existing_files:
                    self.main_window.show_error(
                        f"La carpeta '{project_dir.name}' no está vacía. "
                        "Selecciona una carpeta vacía para crear el proyecto EPUB."
                    )
                    return

                # Limpiar proyecto anterior si existe
                self._cleanup_previous_project()

                # Crear proyecto usando el core directamente en la carpeta seleccionada
                self.main_window.core = GutenCore.new_project(
                    project_dir,
                    title="Nuevo Libro",
                    lang="es"
                )

                # Marcar como proyecto nuevo (NO es temporal)
                self.main_window.is_new_project = True
                self.main_window.temp_workdir = None
                self.main_window.original_epub_path = None

                # Actualizar UI
                self._update_ui_after_open()
                self.main_window.show_info(f"Nuevo proyecto creado en '{project_dir}'")

        except Exception as e:
            self.main_window.show_error(f"Error creando proyecto: {e}")
    
    def _update_ui_after_open(self):
        """Actualiza la UI después de abrir un proyecto"""
        if not self.main_window.core:
            return

        # Configurar settings para el proyecto actual
        from .settings_manager import get_settings
        settings = get_settings()
        project_path = str(self.main_window.core.workdir)
        settings.set_current_project(project_path)

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

        # Actualizar configuración del editor con la específica del proyecto
        self.main_window.central_editor.update_editor_settings()

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

    def _on_about(self, action, param):
        """Muestra el diálogo About"""
        self.main_window.about_dialog.show()

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
                # La importación de imágenes se maneja desde el sidebar
                self.main_window.show_info(f"Use el sidebar para importar imágenes: {file_path}")
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

        # La eliminación de recursos se maneja desde el sidebar con confirmación
        resource_name = self.main_window.current_resource
        self.main_window.show_info(f"Use el menú contextual del sidebar para eliminar: {resource_name}")

    def _on_export_text(self, action, param):
        """Muestra el diálogo de exportación a texto"""
        if not self.main_window.core:
            self.main_window.show_error("No hay ningún proyecto abierto")
            return

        # Delegar al dialog manager
        self.main_window.dialog_manager.show_export_text_dialog()

    def _on_reload_webkit(self, action, param):
        """Recarga el proceso de WebKit (útil cuando se cuelga)"""
        if hasattr(self.main_window, 'sidebar_right'):
            self.main_window.sidebar_right.reload_webview()
            self.main_window.show_info("WebKit recargado")
        else:
            self.main_window.show_error("No hay preview disponible")

    def _on_validate_epub(self, action, param):
        """Muestra el diálogo de validación EPUB"""
        if not self.main_window.core:
            # Si no hay proyecto abierto, permitir validar archivo externo
            from .epubcheck_dialog import show_epubcheck_dialog
            show_epubcheck_dialog(self.main_window)
            return

        # Si hay proyecto abierto, validar el EPUB exportado
        try:
            # Crear EPUB temporal para validar
            import tempfile
            from pathlib import Path

            with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
                temp_path = Path(temp_file.name)

            # Exportar temporalmente
            self.main_window.core.export_epub(temp_path, include_unreferenced=False)

            # Mostrar diálogo con el archivo temporal
            from .epubcheck_dialog import show_epubcheck_dialog
            dialog = show_epubcheck_dialog(self.main_window, temp_path)

            # Limpiar archivo temporal cuando se cierre el diálogo
            def cleanup_temp_file():
                try:
                    temp_path.unlink(missing_ok=True)
                except:
                    pass

            dialog.connect("destroy", lambda w: cleanup_temp_file())

        except Exception as e:
            self.main_window.show_error(f"Error validando EPUB: {e}")
            # En caso de error, mostrar diálogo normal
            from .epubcheck_dialog import show_epubcheck_dialog
            show_epubcheck_dialog(self.main_window)

    def _on_search_in_document(self, action, param):
        """Maneja la acción de búsqueda en documento (solo búsqueda, sin reemplazo)"""
        if hasattr(self.main_window, 'central_editor'):
            self.main_window.central_editor.show_search_panel(show_replace=False)
        else:
            self.main_window.show_info("No hay editor activo")

    def _on_search_and_replace(self, action, param):
        """Maneja la acción de búsqueda y reemplazo"""
        if hasattr(self.main_window, 'central_editor'):
            self.main_window.central_editor.show_search_replace_panel()
        else:
            self.main_window.show_info("No hay editor activo")

    def _on_search_next(self, action, param):
        """Maneja la acción de siguiente resultado de búsqueda"""
        if hasattr(self.main_window, 'central_editor'):
            self.main_window.central_editor._on_search_next()

    def _on_search_prev(self, action, param):
        """Maneja la acción de resultado anterior de búsqueda"""
        if hasattr(self.main_window, 'central_editor'):
            self.main_window.central_editor._on_search_prev()

    def _on_save_current(self, action, param):
        """Guarda el archivo actual"""
        if hasattr(self.main_window, 'central_editor') and self.main_window.central_editor:
            self.main_window.central_editor.force_save()
        else:
            self.main_window.show_info("No hay archivo para guardar")

    def _on_wrap_paragraph(self, action, param):
        """Convierte la selección en párrafo HTML"""
        if hasattr(self.main_window, 'central_editor') and self.main_window.central_editor:
            self.main_window.central_editor._on_wrap_paragraph(action, param)

    def _on_wrap_h1(self, action, param):
        """Convierte la selección en encabezado H1"""
        if hasattr(self.main_window, 'central_editor') and self.main_window.central_editor:
            self.main_window.central_editor._on_wrap_heading(action, param, 1)

    def _on_wrap_h2(self, action, param):
        """Convierte la selección en encabezado H2"""
        if hasattr(self.main_window, 'central_editor') and self.main_window.central_editor:
            self.main_window.central_editor._on_wrap_heading(action, param, 2)

    def _on_wrap_h3(self, action, param):
        """Convierte la selección en encabezado H3"""
        if hasattr(self.main_window, 'central_editor') and self.main_window.central_editor:
            self.main_window.central_editor._on_wrap_heading(action, param, 3)

    def _on_wrap_blockquote(self, action, param):
        """Convierte la selección en cita HTML"""
        if hasattr(self.main_window, 'central_editor') and self.main_window.central_editor:
            self.main_window.central_editor._on_wrap_blockquote(action, param)

    def _on_link_styles(self, action, param):
        """Abre el diálogo para vincular estilos CSS"""
        if hasattr(self.main_window, 'central_editor') and self.main_window.central_editor:
            self.main_window.central_editor._on_link_styles(action, param)

    def _on_show_statistics(self, action, param):
        """Muestra el diálogo de estadísticas del libro completo"""
        from .statistics_dialog import show_statistics_dialog
        show_statistics_dialog(self.main_window, current_chapter_only=False)

    def _on_show_current_chapter_statistics(self, action, param):
        """Muestra las estadísticas solo del capítulo actual"""
        from .statistics_dialog import show_statistics_dialog
        show_statistics_dialog(self.main_window, current_chapter_only=True)

    def _on_batch_rename(self, action, param):
        """Muestra el diálogo de renombrado en lote"""
        from .batch_rename_dialog import show_batch_rename_dialog
        show_batch_rename_dialog(self.main_window)

    def _on_split_chapter(self, action, param):
        """Divide el capítulo actual en dos archivos"""
        from .split_chapter_dialog import show_split_chapter_dialog
        show_split_chapter_dialog(self.main_window)

    def _on_global_search_replace(self, action, param):
        """Muestra el diálogo de búsqueda/reemplazo global"""
        from .global_search_replace_dialog import show_global_search_replace_dialog
        show_global_search_replace_dialog(self.main_window)

    def _on_toggle_left_sidebar(self, action, param):
        """Alterna la visibilidad del panel lateral izquierdo"""
        if hasattr(self.main_window, 'left_sidebar_btn'):
            self.main_window.left_sidebar_btn.set_active(
                not self.main_window.left_sidebar_btn.get_active())

    def _on_toggle_right_sidebar(self, action, param):
        """Alterna la visibilidad del panel lateral derecho"""
        if hasattr(self.main_window, 'right_sidebar_btn'):
            self.main_window.right_sidebar_btn.set_active(
                not self.main_window.right_sidebar_btn.get_active())

    def _on_fullscreen_preview(self, action, param):
        """Abre la previsualización en pantalla completa"""
        if hasattr(self.main_window, 'sidebar_right') and self.main_window.sidebar_right:
            self.main_window.sidebar_right._on_fullscreen_preview(None)