"""
ui/sidebar_left.py
Sidebar izquierdo - Estructura del EPUB y navegación de recursos
"""

from gi.repository import Gtk, Adw, Gio, GLib, Gdk
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from core.guten_core import KIND_DOCUMENT, KIND_STYLE, KIND_IMAGE, KIND_FONT, KIND_AUDIO, KIND_VIDEO

if TYPE_CHECKING:
    from .main_window import GutenAIWindow


class SidebarLeft:
    """Maneja el sidebar izquierdo con la estructura del EPUB"""
    
    def __init__(self, main_window: 'GutenAIWindow'):
        self.main_window = main_window
        
        # Estado de selección por categoría
        self.selected_items = {
            KIND_DOCUMENT: set(),
            KIND_STYLE: set(), 
            KIND_IMAGE: set(),
            KIND_FONT: set(),
            KIND_AUDIO: set(),
            KIND_VIDEO: set()
        }
        
        # *** AGREGAR: Estado de expansión y drag & drop ***
        self.expanded_categories = set()  # Qué categorías están expandidas
        self.drag_source_href = None

        self._setup_widget()
        self._setup_styling()
        
        # Estado para drag & drop
        self.drag_source_href = None
        self.drag_target_position = -1
    
    def _setup_widget(self):
        """Configura el widget principal del sidebar"""
        
        self.sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.sidebar_box.set_size_request(280, -1)
        
        # Header del sidebar
        self._setup_header()
        
        # Lista de recursos
        self._setup_resource_list()
        
        # Conectar señales
        self.resource_listbox.connect('selected-rows-changed', self._on_selection_changed)
    
    def _setup_header(self):
        """Configura el header del sidebar"""
        
        sidebar_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        sidebar_header.set_margin_top(12)
        sidebar_header.set_margin_bottom(12)
        sidebar_header.set_margin_start(12)
        sidebar_header.set_margin_end(12)
        
        sidebar_title = Gtk.Label()
        sidebar_title.set_text("Estructura EPUB")
        sidebar_title.add_css_class("heading")
        sidebar_header.append(sidebar_title)
        
        # Contador de selección
        self.selection_counter = Gtk.Label()
        self.selection_counter.set_text("")
        self.selection_counter.add_css_class("caption")
        sidebar_header.append(self.selection_counter)
        
        self.sidebar_box.append(sidebar_header)
    
    def _setup_resource_list(self):
        """Configura la lista de recursos"""
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        
        self.resource_listbox = Gtk.ListBox()
        self.resource_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.resource_listbox.add_css_class("navigation-sidebar")
        
        scrolled.set_child(self.resource_listbox)
        self.sidebar_box.append(scrolled)
    
    def _setup_styling(self):
        """Configura CSS personalizado para mejorar la visualización"""
        css_provider = Gtk.CssProvider()
        css_data = """
        /* Mejorar la visualización de elementos seleccionados */
        listbox row:selected {
            background-color: @accent_color;
            color: @accent_fg_color;
            border-left: 4px solid @accent_bg_color;
        }
        
        /* Hacer más visible el hover */
        listbox row:hover {
            background-color: alpha(@accent_color, 0.1);
        }
        
        /* Selección múltiple más visible */
        listbox.navigation-sidebar row:selected {
            background: linear-gradient(90deg, @accent_color, alpha(@accent_color, 0.8));
            border-radius: 6px;
            margin: 2px;
            font-weight: bold;
        }
        
        /* Iconos en elementos seleccionados */
        listbox row:selected image {
            color: @accent_fg_color;
        }
        
        /* Categorías vacías con estilo diferente */
        .empty-category {
            opacity: 0.7;
        }
        
        .empty-category .title {
            font-style: italic;
        }
        """
        
        css_provider.load_from_data(css_data.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def get_widget(self) -> Gtk.Widget:
        """Retorna el widget principal del sidebar"""
        return self.sidebar_box
    
    def populate_tree(self):
        """Puebla el ListBox preservando el estado de expansión"""
        if not self.main_window.core:
            return
        
        # *** GUARDAR estado actual de expansión ***
        self._save_expansion_state()
        
        # Limpiar listbox
        self._clear_listbox()
        
        # Categorías principales
        categories = [
            ("📄 Texto", KIND_DOCUMENT),
            ("🎨 Estilos", KIND_STYLE), 
            ("🖼️ Imágenes", KIND_IMAGE),
            ("🔤 Fuentes", KIND_FONT),
            ("🎵 Audio", KIND_AUDIO),
            ("🎥 Video", KIND_VIDEO),
        ]
        
        for category_name, kind in categories:
            items = self.main_window.core.list_items(kind=kind)
            
            if items:
                category_row = self._create_category_row(category_name, len(items), kind)
                self.resource_listbox.append(category_row)
                
                # *** RESTAURAR estado de expansión ***
                if kind in self.expanded_categories:
                    category_row.set_expanded(True)
                
                # Agregar los recursos EN ORDEN DEL SPINE para documentos
                if kind == KIND_DOCUMENT:
                    ordered_items = self._get_documents_in_spine_order(items)
                else:
                    ordered_items = items
                
                for item in ordered_items:
                    resource_row = self._create_resource_row(
                        Path(item.href).name,
                        item.href,
                        kind
                    )
                    category_row.add_row(resource_row)
            else:
                self._create_empty_category(category_name, kind)
    
    def _get_documents_in_spine_order(self, items):
        """Ordena los documentos según el spine del EPUB"""
        try:
            spine = self.main_window.core.get_spine()
            spine_items = []
            non_spine_items = []
            
            # Crear diccionario por ID para búsqueda rápida
            items_by_id = {item.id: item for item in items}
            
            # Agregar items del spine en orden
            for spine_id in spine:
                if spine_id in items_by_id:
                    spine_items.append(items_by_id[spine_id])
            
            # Agregar items que no están en el spine
            spine_ids = set(spine)
            for item in items:
                if item.id not in spine_ids:
                    non_spine_items.append(item)
            
            return spine_items + non_spine_items
            
        except Exception as e:
            print(f"Error ordering documents: {e}")
            return items
    

    def _save_expansion_state(self):
        """Guarda qué categorías están expandidas antes de reconstruir"""
        self.expanded_categories.clear()
        
        # Iterar sobre las filas actuales del listbox
        child = self.resource_listbox.get_first_child()
        while child:
            if isinstance(child, Adw.ExpanderRow):
                # Determinar qué tipo de categoría es basado en el título
                title = child.get_title()
                if child.get_expanded():
                    if "Texto" in title:
                        self.expanded_categories.add(KIND_DOCUMENT)
                    elif "Estilos" in title:
                        self.expanded_categories.add(KIND_STYLE)
                    elif "Imágenes" in title:
                        self.expanded_categories.add(KIND_IMAGE)
                    elif "Fuentes" in title:
                        self.expanded_categories.add(KIND_FONT)
                    elif "Audio" in title:
                        self.expanded_categories.add(KIND_AUDIO)
                    elif "Video" in title:
                        self.expanded_categories.add(KIND_VIDEO)
            
            child = child.get_next_sibling()

    def _clear_listbox(self):
        """Limpia todo el contenido del listbox"""
        child = self.resource_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.resource_listbox.remove(child)
            child = next_child
    
    def _create_category_row(self, name: str, count: int, category_type: str) -> Adw.ExpanderRow:
        """Crea una fila expandible para una categoría con elementos"""
        expander = Adw.ExpanderRow()
        expander.set_title(name)
        expander.set_subtitle("Categoría de recursos")
        
        # Box para botones (crear/importar + menú)
        buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        buttons_box.set_spacing(4)
        
        # Botón de acción según el tipo de categoría (crear/importar)
        if category_type in [KIND_DOCUMENT, KIND_STYLE]:
            add_btn = Gtk.Button()
            add_btn.set_icon_name("list-add-symbolic")
            add_btn.set_tooltip_text(f"Crear nuevo {name.split()[1].lower() if ' ' in name else 'recurso'}")
            add_btn.add_css_class("flat")
            add_btn.connect('clicked', self._on_create_new_resource, category_type)
            buttons_box.append(add_btn)

            # Para documentos, agregar también botón de importar HTML
            if category_type == KIND_DOCUMENT:
                import_btn = Gtk.Button()
                import_btn.set_icon_name("folder-open-symbolic")
                import_btn.set_tooltip_text("Importar archivos HTML existentes")
                import_btn.add_css_class("flat")
                import_btn.connect('clicked', self._on_import_html_files)
                buttons_box.append(import_btn)
            
        elif category_type in [KIND_IMAGE, KIND_FONT, KIND_AUDIO, KIND_VIDEO]:
            import_btn = Gtk.Button()
            import_btn.set_icon_name("folder-open-symbolic")
            import_btn.set_tooltip_text(f"Importar {name.split()[1].lower() if ' ' in name else 'archivo'}")
            import_btn.add_css_class("flat")
            import_btn.connect('clicked', self._on_import_resource, category_type)
            buttons_box.append(import_btn)
        
        # Menú botón para acciones en lote
        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("view-more-symbolic")
        menu_btn.set_tooltip_text(f"Acciones para {name.lower()} seleccionados")
        menu_btn.add_css_class("flat")
        menu_btn.set_menu_model(self._create_category_menu(category_type))
        buttons_box.append(menu_btn)
        
        expander.add_suffix(buttons_box)
        return expander
    
    def _create_empty_category(self, category_name: str, kind: str):
        """Crea una categoría vacía con información para el usuario"""
        empty_title = f"{category_name} (vacía)"
        category_row = self._create_category_row(empty_title, 0, kind)
        category_row.add_css_class("empty-category")
        category_row.set_subtitle("Categoría vacía - usa los botones para agregar contenido")
        
        self.resource_listbox.append(category_row)
        
        # Agregar fila informativa
        info_row = Adw.ActionRow()
        info_row.set_title("Sin elementos")

        if kind == KIND_DOCUMENT:
            info_row.set_subtitle("Haz clic en + para crear un nuevo documento o en 📁 para importar HTML existente")
        elif kind == KIND_STYLE:
            info_row.set_subtitle(f"Haz clic en + para crear un nuevo {category_name.split()[1].lower()}")
        elif kind in [KIND_IMAGE, KIND_FONT, KIND_AUDIO, KIND_VIDEO]:
            info_row.set_subtitle(f"Haz clic en 📁 para importar {category_name.split()[1].lower()}")

        info_row.set_sensitive(False)
        category_row.add_row(info_row)
    
    def _create_resource_row(self, name: str, href: str, resource_type: str) -> Adw.ActionRow:
        """Crea una fila con menú contextual para renombrar"""
        row = Adw.ActionRow()
        row.set_title(name)
        row.set_subtitle(href)
        
        # Checkbox para selección múltiple
        checkbox = Gtk.CheckButton()
        checkbox.connect('toggled', self._on_checkbox_toggled, href, resource_type)
        row.add_prefix(checkbox)
        
        # Icono según el tipo
        icon_name = {
            KIND_DOCUMENT: "text-x-generic-symbolic",
            KIND_STYLE: "text-css-symbolic", 
            KIND_IMAGE: "image-x-generic-symbolic",
            KIND_FONT: "font-x-generic-symbolic",
            KIND_AUDIO: "audio-x-generic-symbolic",
            KIND_VIDEO: "video-x-generic-symbolic"
        }.get(resource_type, "text-x-generic-symbolic")
        
        icon = Gtk.Image.new_from_icon_name(icon_name)
        row.add_prefix(icon)
        
        # *** DRAG & DROP SOLO PARA DOCUMENTOS ***
        if resource_type == KIND_DOCUMENT:
            self._setup_drag_drop(row, href, name)
        
        # Hacer la fila activable
        row.set_activatable(True)
        row.connect('activated', self._on_resource_row_activated, href, resource_type, name)
        
        # *** MENÚ CONTEXTUAL PARA CADA RECURSO ***
        self._setup_resource_context_menu(row, href, name, resource_type)
        return row

    def _on_selection_changed(self, listbox):
        """Maneja cambios en la selección"""
        selected_rows = listbox.get_selected_rows()
        count = len(selected_rows)
        
        # Actualizar contador visual
        if count == 0:
            self.selection_counter.set_text("")
        elif count == 1:
            self.selection_counter.set_text("1 seleccionado")
        else:
            self.selection_counter.set_text(f"{count} seleccionados")
        
        # Cambiar estilo del contador
        if count > 0:
            self.selection_counter.add_css_class("accent")
        else:
            self.selection_counter.remove_css_class("accent")
        
        # Actualizar título en la ventana principal
        if count > 1:
            self.main_window.resource_title.set_text(f"{count} recursos seleccionados")
        elif count == 0:
            self.main_window.resource_title.set_text("Ningún recurso seleccionado")
    
    def _on_resource_row_activated(self, row, href, resource_type, name):
        """Maneja la activación de una fila de recurso"""
        print(f"Recurso activado: {href} (Tipo: {resource_type})")
        self.main_window.set_current_resource(href, name)
    
    def _on_create_new_resource(self, button, resource_type):
        """Maneja la creación de un nuevo recurso"""
        if not self.main_window.core:
            self.main_window.show_error("No hay proyecto abierto")
            return
        
        # Delegar al dialog manager
        self.main_window.dialog_manager.show_create_resource_dialog(resource_type)
    
    def _on_import_resource(self, button, resource_type):
        """Maneja la importación de recursos desde archivo"""
        if not self.main_window.core:
            self.main_window.show_error("No hay proyecto abierto")
            return

        # Delegar al dialog manager
        self.main_window.dialog_manager.show_import_resource_dialog(resource_type)

    def _on_import_html_files(self, button):
        """Maneja la importación de archivos HTML existentes"""
        if not self.main_window.core:
            self.main_window.show_error("No hay proyecto abierto")
            return

        dialog = Gtk.FileDialog()
        dialog.set_title("Importar archivos HTML")

        # Filtro para archivos HTML
        filter_html = Gtk.FileFilter()
        filter_html.set_name("Archivos HTML/XHTML")
        filter_html.add_pattern("*.html")
        filter_html.add_pattern("*.htm")
        filter_html.add_pattern("*.xhtml")

        filters = Gio.ListStore()
        filters.append(filter_html)
        dialog.set_filters(filters)

        # Permitir selección múltiple
        dialog.open_multiple(self.main_window, None, self._on_import_html_response)

    def _on_import_html_response(self, dialog, result):
        """Maneja la respuesta del diálogo de importación HTML"""
        try:
            files = dialog.open_multiple_finish(result)
            if not files:
                return

            imported_count = 0
            errors = []
            imported_ids = []  # Para tracking de documentos importados

            for i in range(files.get_n_items()):
                file = files.get_item(i)
                source_path = Path(file.get_path())

                try:
                    # Leer contenido del archivo
                    content = source_path.read_text(encoding='utf-8')

                    # Generar un nombre único para el archivo en el proyecto
                    base_name = source_path.stem
                    extension = '.xhtml'  # Normalizar a XHTML
                    counter = 1
                    filename = f"{base_name}{extension}"

                    # Verificar si ya existe y generar nombre único
                    text_dir = self.main_window.core.layout["TEXT"]
                    while (self.main_window.core.opf_dir / text_dir / filename).exists():
                        filename = f"{base_name}_{counter}{extension}"
                        counter += 1

                    # Convertir HTML a XHTML válido si es necesario
                    content = self._convert_to_valid_xhtml(content, source_path.name)

                    # Agregar al proyecto
                    href = f"{Path(text_dir).name}/{filename}"
                    doc_id = filename.replace('.xhtml', '')

                    # Escribir archivo
                    self.main_window.core.write_text(href, content)

                    # Agregar al manifest
                    self.main_window.core.add_to_manifest(
                        doc_id,
                        href,
                        media_type="application/xhtml+xml"
                    )

                    # Agregar al spine
                    self.main_window.core.spine_insert(doc_id)
                    imported_ids.append(doc_id)

                    imported_count += 1
                    print(f"[IMPORT] Added {filename} to manifest and spine with ID: {doc_id}")

                except Exception as e:
                    errors.append(f"{source_path.name}: {str(e)}")

            # Actualizar UI
            self.main_window.refresh_structure()

            # Regenerar navegación si se importaron documentos
            if imported_count > 0:
                try:
                    self.main_window.core.generate_nav_basic(overwrite=True)
                    print(f"[IMPORT] Regenerated navigation after importing {imported_count} documents")
                except Exception as e:
                    print(f"[WARNING] Could not regenerate navigation: {e}")

            # Mostrar resultados
            if imported_count > 0:
                message = f"Se importaron {imported_count} archivo(s) HTML exitosamente"
                if len(imported_ids) > 1:
                    message += f"\nSe actualizó la navegación automáticamente"
                if errors:
                    message += f"\n\nErrores en {len(errors)} archivo(s):\n" + "\n".join(errors[:5])
                    if len(errors) > 5:
                        message += f"\n... y {len(errors) - 5} error(es) más"
                self.main_window.show_info(message)
            else:
                error_msg = "No se pudo importar ningún archivo"
                if errors:
                    error_msg += ":\n" + "\n".join(errors[:3])
                self.main_window.show_error(error_msg)

        except Exception as e:
            self.main_window.show_error(f"Error importando archivos HTML: {e}")

    def _convert_to_valid_xhtml(self, content: str, filename: str) -> str:
        """Convierte contenido HTML a XHTML válido"""
        # Si ya tiene declaración XML, dejarlo como está
        if content.strip().startswith('<?xml'):
            return content

        # Si es HTML completo, convertir a XHTML
        if '<html' in content.lower():
            # Básico: agregar namespace XHTML si no lo tiene
            if 'xmlns=' not in content:
                content = content.replace('<html', '<html xmlns="http://www.w3.org/1999/xhtml"')

            # Agregar declaración XML si no la tiene
            if not content.strip().startswith('<?xml'):
                content = '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE html>\n' + content
        else:
            # Es un fragmento, crear documento XHTML completo
            title = Path(filename).stem.replace('_', ' ').title()
            content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="es" xml:lang="es">
<head>
    <title>{title}</title>
    <meta charset="utf-8"/>
</head>
<body>
{content}
</body>
</html>'''

        return content
    
    def _on_checkbox_toggled(self, checkbox, href, resource_type):
        """Maneja el toggle de checkboxes individuales"""
        if checkbox.get_active():
            self.selected_items[resource_type].add(href)
        else:
            self.selected_items[resource_type].discard(href)
        
        # Actualizar contador visual (opcional)
        count = sum(len(items) for items in self.selected_items.values())
        if count > 0:
            self.selection_counter.set_text(f"{count} marcados")
            self.selection_counter.add_css_class("accent")
        else:
            self.selection_counter.set_text("")
            self.selection_counter.remove_css_class("accent")
    
    def _setup_resource_context_menu(self, row: Adw.ActionRow, href: str, name: str, resource_type: str):
        """Configura menú contextual click-derecho en cada recurso"""
        
        # Gesture para click derecho
        right_click = Gtk.GestureClick()
        right_click.set_button(3)  # Botón derecho
        
        def on_right_click(gesture, n_press, x, y):
            if n_press == 1:  # Single click
                self._show_resource_context_menu(row, href, name, resource_type, x, y)
        
        right_click.connect('pressed', on_right_click)
        row.add_controller(right_click)


    def _show_resource_context_menu(self, row: Adw.ActionRow, href: str, name: str, resource_type: str, x: float, y: float):
        """Muestra menú contextual para el recurso"""

        menu = Gio.Menu()

        # *** USAR ID SANITIZADO CONSISTENTE ***
        safe_href = self._sanitize_href_for_action(href)

        # Sección de edición
        edit_section = Gio.Menu()
        edit_section.append("Renombrar", f"win.rename_resource_{safe_href}")

        # Opciones específicas por tipo
        if resource_type == KIND_DOCUMENT:
            edit_section.append("Abrir en editor externo", f"win.open_external_{safe_href}")
        elif resource_type == KIND_IMAGE:
            edit_section.append("Establecer como portada", f"win.set_cover_{safe_href}")
            edit_section.append("Ver en galería", f"win.view_gallery_{safe_href}")
        elif resource_type == KIND_STYLE:
            edit_section.append("Aplicar a todos los documentos", f"win.apply_style_all_{safe_href}")

        menu.append_section(None, edit_section)

        # Sección de gestión
        manage_section = Gio.Menu()

        if resource_type == KIND_DOCUMENT:
            manage_section.append("Eliminar del spine", f"win.remove_spine_{safe_href}")

        manage_section.append("Copiar ruta", f"win.copy_path_{safe_href}")
        manage_section.append("Eliminar", f"win.delete_resource_{safe_href}")

        menu.append_section(None, manage_section)
        
        # Crear popover
        popover = Gtk.PopoverMenu()
        popover.set_menu_model(menu)
        popover.set_parent(row)
        
        # *** REGISTRAR ACCIONES ANTES DE MOSTRAR ***
        self._register_resource_actions(href, name, resource_type, safe_href)
        
        # Mostrar popover
        rect = Gdk.Rectangle()
        rect.x = x
        rect.y = y
        popover.set_pointing_to(rect)
        popover.popup()
    
    def _sanitize_href_for_action(self, href: str) -> str:
        """Sanitiza href para usar como ID de acción de manera consistente"""
        # Reemplazar caracteres problemáticos con guiones bajos
        safe = href.replace('/', '_').replace('.', '_').replace('-', '_').replace(' ', '_')
        # Remover caracteres especiales adicionales
        import re
        safe = re.sub(r'[^a-zA-Z0-9_]', '_', safe)
        # Evitar múltiples guiones bajos seguidos
        safe = re.sub(r'_+', '_', safe).strip('_')
        return safe

    def _register_resource_actions(self, href: str, name: str, resource_type: str, safe_href: str = None):
        """Registra acciones específicas para un recurso"""

        if not safe_href:
            safe_href = self._sanitize_href_for_action(href)

        # *** VERIFICAR SI LA ACCIÓN YA ESTÁ REGISTRADA ***
        action_name = f"rename_resource_{safe_href}"

        # Evitar registros duplicados
        if self.main_window.lookup_action(action_name):
            print(f"[DEBUG] Action {action_name} already exists, skipping")
            return

        try:
            # Acción renombrar
            rename_action = Gio.SimpleAction.new(action_name, None)
            rename_action.connect("activate", self._on_rename_resource, href, name, resource_type)
            self.main_window.add_action(rename_action)

            # Acción eliminar
            delete_action_name = f"delete_resource_{safe_href}"
            if not self.main_window.lookup_action(delete_action_name):
                delete_action = Gio.SimpleAction.new(delete_action_name, None)
                delete_action.connect("activate", self._on_delete_single_resource, href, name)
                self.main_window.add_action(delete_action)

            # Acción "Set as Cover" para imágenes
            if resource_type == KIND_IMAGE:
                cover_action_name = f"set_cover_{safe_href}"
                if not self.main_window.lookup_action(cover_action_name):
                    cover_action = Gio.SimpleAction.new(cover_action_name, None)
                    cover_action.connect("activate", self._on_set_single_as_cover, href, name)
                    self.main_window.add_action(cover_action)

            print(f"[DEBUG] Actions registered for {href} -> {safe_href}")

        except Exception as e:
            print(f"[ERROR] Failed to register actions for {href}: {e}")
    
    def _on_rename_resource(self, action, param, href: str, current_name: str, resource_type: str):
        """Maneja la acción de renombrar recurso"""
        print(f"[DEBUG] Rename action triggered for: {href}")
        try:
            self.main_window.dialog_manager.show_rename_dialog(href, current_name, resource_type)
        except Exception as e:
            print(f"[ERROR] Error showing rename dialog: {e}")
            self.main_window.show_error(f"Error abriendo diálogo de renombre: {e}")

    def _on_delete_single_resource(self, action, param, href: str, name: str):
        """Elimina un solo recurso"""
        self.main_window.dialog_manager.show_confirmation_dialog(
            "Confirmar eliminación",
            f"¿Eliminar '{name}'? Esta acción no se puede deshacer.",
            lambda: self._do_delete_single_resource(href)
        )

    def _do_delete_single_resource(self, href: str):
        """Ejecuta eliminación de recurso individual"""
        try:
            self.main_window.core.remove_from_manifest(href)
            self.main_window.refresh_structure()
            self.main_window.show_info(f"'{Path(href).name}' eliminado")
        except Exception as e:
            self.main_window.show_error(f"Error eliminando: {e}")

    def _on_set_single_as_cover(self, action, param, href: str, name: str):
        """Maneja la acción de establecer una imagen como portada"""
        print(f"[DEBUG] Set as cover action triggered for: {href}")
        try:
            self._set_image_as_cover(href, name)
        except Exception as e:
            print(f"[ERROR] Error setting cover: {e}")
            self.main_window.show_error(f"Error estableciendo portada: {e}")

    def _set_image_as_cover(self, image_href: str, image_name: str):
        """Establece una imagen como portada del EPUB"""
        if not self.main_window.core:
            self.main_window.show_error("No hay proyecto abierto")
            return

        try:
            # 1. Actualizar propiedades en el manifest - quitar cover-image de otras imágenes
            for item in self.main_window.core.list_items(KIND_IMAGE):
                if item.href != image_href and item.properties and "cover-image" in item.properties:
                    # Remover propiedad cover-image de otras imágenes
                    new_props = item.properties.replace("cover-image", "").strip()
                    self.main_window.core._update_item_properties(item.href, new_props)

            # 2. Establecer cover-image en la imagen seleccionada
            self.main_window.core._update_item_properties(image_href, "cover-image")

            # 3. Crear/actualizar cover.xhtml
            cover_html_path = self._create_cover_html(image_href, image_name)

            # 4. Agregar cover.xhtml al manifest si no existe
            self._ensure_cover_in_manifest(cover_html_path, image_href)

            # 5. Mover cover.xhtml al inicio del spine
            self._move_cover_to_spine_start(cover_html_path)

            # 6. Actualizar metadatos
            self._update_cover_metadata(image_href)

            # Refrescar UI
            self.main_window.refresh_structure()
            self.main_window.show_info(f"'{image_name}' establecida como portada")

        except Exception as e:
            raise Exception(f"Error configurando portada: {e}")

    def _create_cover_html(self, image_href: str, image_name: str) -> str:
        """Crea el archivo cover.xhtml según las especificaciones EPUB 3.3"""
        if not self.main_window.core.workdir:
            raise Exception("No hay directorio de trabajo")

        # Calcular ruta relativa de la imagen usando el mismo método que funciona en insertar imágenes
        cover_html_href = "Text/cover.xhtml"  # Ruta relativa al opf_dir (no incluir OEBPS)
        relative_image_path = self._calculate_relative_path_for_cover(cover_html_href, image_href)

        # Contenido HTML para la portada según EPUB 3.3 spec
        cover_html_content = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>Portada</title>
    <style type="text/css">
        body {{
            margin: 0;
            padding: 0;
            text-align: center;
            background-color: white;
        }}
        .cover {{
            display: block;
            text-align: center;
            height: 100vh;
            width: 100vw;
        }}
        .cover img {{
            height: 100vh;
            width: auto;
            max-width: 100vw;
            object-fit: contain;
        }}
    </style>
</head>
<body>
    <section class="cover" epub:type="cover">
        <img src="{relative_image_path}" alt="Portada del libro" />
    </section>
</body>
</html>'''

        # Determinar ruta para cover.xhtml usando el layout del core
        text_layout_path = self.main_window.core.layout.get("TEXT", "OEBPS/Text")

        # DEBUG: Imprimir rutas para diagnosticar el problema
        print(f"[DEBUG] workdir: {self.main_window.core.workdir}")
        print(f"[DEBUG] text_layout_path: {text_layout_path}")

        text_dir = Path(self.main_window.core.workdir) / text_layout_path
        text_dir.mkdir(parents=True, exist_ok=True)

        cover_file_path = text_dir / "cover.xhtml"

        print(f"[DEBUG] cover_file_path: {cover_file_path}")

        # Escribir el archivo
        with open(cover_file_path, 'w', encoding='utf-8') as f:
            f.write(cover_html_content)

        # Calcular href relativo al opf_dir (OEBPS), no al workdir
        relative_path = str(cover_file_path.relative_to(self.main_window.core.opf_dir))
        print(f"[DEBUG] relative_path for manifest: {relative_path}")

        return relative_path

    def _ensure_cover_in_manifest(self, cover_html_path: str, image_href: str):
        """Asegura que cover.xhtml esté en el manifest"""
        # Verificar si ya existe en el manifest
        try:
            existing_item = self.main_window.core._get_item(cover_html_path)
            print(f"[DEBUG] Cover HTML ya existe en manifest: {existing_item.id}")
        except:
            # No existe, agregarlo
            print(f"[DEBUG] Agregando cover.xhtml al manifest: {cover_html_path}")
            self.main_window.core.add_to_manifest(
                id_="cover",
                href=cover_html_path,
                media_type="application/xhtml+xml",
                properties=""  # No se necesita svg property para epub:type="cover"
            )

    def _move_cover_to_spine_start(self, cover_html_path: str):
        """Mueve el cover.xhtml al inicio del spine"""
        try:
            # Obtener el item del manifest
            cover_item = self.main_window.core._get_item(cover_html_path)
            cover_id = cover_item.id

            # Remover del spine si ya está
            current_spine = self.main_window.core.get_spine()
            if cover_id in current_spine:
                self.main_window.core.spine_remove(cover_id)

            # Insertar al inicio del spine
            self.main_window.core.spine_insert(cover_id, index=0)

        except Exception as e:
            print(f"[DEBUG] Error moviendo cover al inicio del spine: {e}")

    def _update_cover_metadata(self, image_href: str):
        """Actualiza los metadatos del EPUB para referenciar la portada"""
        try:
            # Esto sería ideal pero el core actual no tiene método para metadatos
            # self.main_window.core.set_metadata("cover", image_href)
            print(f"[DEBUG] Cover metadata would be updated for: {image_href}")
        except Exception as e:
            print(f"[DEBUG] Error updating cover metadata: {e}")

    def _calculate_relative_path_for_cover(self, cover_href: str, image_href: str) -> str:
        """Calcula la ruta relativa desde cover.xhtml hacia la imagen (mismo método que funciona en insertar imágenes)"""

        try:
            from pathlib import Path
            from posixpath import relpath

            cover_path = Path(cover_href)
            image_path = Path(image_href)

            # Usar posixpath para mantener separadores web
            relative = relpath(image_path.as_posix(), start=cover_path.parent.as_posix())

            print(f"[DEBUG] Cover relative path calculation:")
            print(f"[DEBUG]   From: {cover_href} -> {cover_path.parent}")
            print(f"[DEBUG]   To: {image_href}")
            print(f"[DEBUG]   Result: {relative}")

            return relative

        except Exception as e:
            print(f"[DEBUG] Error calculating relative path for cover: {e}")
            # Fallback: usar ruta original
            return image_href

    def _setup_drag_drop(self, row: Adw.ActionRow, href: str, name: str):
        """Configura drag & drop con mejor debug"""
        
        # *** DRAG SOURCE ***
        drag_source = Gtk.DragSource()
        drag_source.set_actions(Gdk.DragAction.MOVE)
        
        def on_drag_prepare(source, x, y):
            print(f"[DRAG] Preparing to drag: {name}")
            self.drag_source_href = href
            
            # Crear contenido simple
            content = Gdk.ContentProvider.new_for_value(href)
            return content
        
        def on_drag_begin(source, drag):
            print(f"[DRAG] Started dragging: {name}")
            row.add_css_class("dragging")
        
        def on_drag_end(source, drag, delete_data):
            print(f"[DRAG] Ended dragging: {name}")
            row.remove_css_class("dragging")
            self.drag_source_href = None
        
        drag_source.connect("prepare", on_drag_prepare)
        drag_source.connect("drag-begin", on_drag_begin)
        drag_source.connect("drag-end", on_drag_end)
        
        row.add_controller(drag_source)
        
        # *** DROP TARGET ***
        drop_target = Gtk.DropTarget.new(str, Gdk.DragAction.MOVE)
        
        def on_drop_enter(target, x, y):
            print(f"[DROP] Enter: {name}")
            if self.drag_source_href and self.drag_source_href != href:
                row.add_css_class("drop-target")
                return Gdk.DragAction.MOVE
            return 0
        
        def on_drop_leave(target):
            print(f"[DROP] Leave: {name}")
            row.remove_css_class("drop-target")
        
        def on_drop(target, value, x, y):
            print(f"[DROP] Dropping on: {name}")
            
            if not self.drag_source_href or self.drag_source_href == href:
                print("[DROP] Invalid drop")
                return False
            
            # Limpiar estilos inmediatamente
            row.remove_css_class("drop-target")
            
            print(f"[DROP] Executing reorder: {self.drag_source_href} -> {href}")
            
            # Reordenar
            success = self._reorder_documents(self.drag_source_href, href)
            
            if success:
                # Delay más corto para refresh
                GLib.timeout_add(50, self._refresh_after_reorder)
            
            return success
        
        drop_target.connect("enter", on_drop_enter)
        drop_target.connect("leave", on_drop_leave)
        drop_target.connect("drop", on_drop)
        
        row.add_controller(drop_target)
    
    def _refresh_after_reorder(self) -> bool:
        """Refresca SOLO la categoría de documentos sin colapsar"""
        print("[DEBUG] Refreshing after reorder")
        
        try:
            # Marcar Texto como expandido
            self.expanded_categories.add(KIND_DOCUMENT)
            
            # Refrescar toda la estructura (manteniendo expansión)
            self.populate_tree()
            
            return False  # No repetir
            
        except Exception as e:
            print(f"[DEBUG] Error refreshing: {e}")
            return False
        
    
    def _setup_styling(self):
        """Configura CSS personalizado incluyendo estilos de drag & drop"""
        css_provider = Gtk.CssProvider()
        css_data = """
        /* Estilos existentes... */
        listbox row:selected {
            background-color: @accent_color;
            color: @accent_fg_color;
            border-left: 4px solid @accent_bg_color;
        }
        
        listbox row:hover {
            background-color: alpha(@accent_color, 0.1);
        }
        
        /* *** ESTILOS DRAG & DROP *** */
        .dragging {
            opacity: 0.5;
            background: alpha(@accent_color, 0.2);
            border: 2px dashed @accent_color;
        }
        
        .drop-target {
            background: alpha(@success_color, 0.2);
            border: 2px solid @success_color;
            border-radius: 8px;
        }
        
        .drop-target.dragging {
            background: alpha(@warning_color, 0.2);
            border-color: @warning_color;
        }
        
        /* Indicador visual durante drag */
        .navigation-sidebar row.dragging {
            transform: rotate(2deg);
            box-shadow: 0 4px 12px alpha(@accent_color, 0.3);
        }
        
        /* Animación suave para drop */
        .navigation-sidebar row {
            transition: all 200ms ease-in-out;
        }
        """
        
        css_provider.load_from_data(css_data.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
    def _reorder_documents(self, source_href: str, target_href: str) -> bool:
        """Reordena documentos con debug detallado"""
        
        if not self.main_window.core:
            print("[DEBUG] No core available")
            return False
        
        try:
            print(f"[DEBUG] Starting reorder: {source_href} -> {target_href}")
            
            # Obtener IDs de manifest
            source_item = self.main_window.core._get_item(source_href)
            target_item = self.main_window.core._get_item(target_href)
            
            source_id = source_item.id
            target_id = target_item.id
            
            print(f"[DEBUG] Source ID: {source_id}, Target ID: {target_id}")
            
            # Obtener spine actual
            current_spine = self.main_window.core.get_spine()
            print(f"[DEBUG] Current spine: {current_spine}")
            
            if source_id not in current_spine:
                print(f"[DEBUG] Adding {source_id} to spine first")
                self.main_window.core.spine_insert(source_id)
                current_spine = self.main_window.core.get_spine()
            
            if target_id not in current_spine:
                print(f"[DEBUG] Adding {target_id} to spine first")
                self.main_window.core.spine_insert(target_id)
                current_spine = self.main_window.core.get_spine()
            
            # Encontrar posiciones
            source_pos = current_spine.index(source_id)
            target_pos = current_spine.index(target_id)
            
            print(f"[DEBUG] Source pos: {source_pos}, Target pos: {target_pos}")
            
            if source_pos == target_pos:
                print("[DEBUG] Same position, no change needed")
                return True
            
            # Usar el método spine_move del core
            self.main_window.core.spine_move(source_id, target_pos)
            
            new_spine = self.main_window.core.get_spine()
            print(f"[DEBUG] New spine: {new_spine}")
            
            self.main_window.show_info(f"Capítulo reordenado: {Path(source_href).name}")
            return True
            
        except Exception as e:
            print(f"[DEBUG] Reordering failed: {e}")
            import traceback
            traceback.print_exc()
            self.main_window.show_error(f"Error reordenando: {e}")
            return False
        
    def _create_category_menu(self, category_type: str):
        """Crea el menú contextual para cada categoría"""
        menu = Gio.Menu()
        
        if category_type in [KIND_DOCUMENT, KIND_STYLE]:
            # Acciones para recursos de texto
            menu.append("Seleccionar todos", f"win.select_all_{category_type}")
            menu.append("Deseleccionar todos", f"win.deselect_all_{category_type}")
            
            if category_type == KIND_DOCUMENT:
                menu.append("Agregar al spine", f"win.add_to_spine_{category_type}")
                menu.append("Quitar del spine", f"win.remove_from_spine_{category_type}")
                menu.append("Vincular estilos", f"win.batch_link_styles_{category_type}")
            
            menu.append("Eliminar seleccionados", f"win.delete_selected_{category_type}")
            
        elif category_type in [KIND_IMAGE, KIND_FONT, KIND_AUDIO, KIND_VIDEO]:
            # Acciones para recursos binarios
            menu.append("Seleccionar todos", f"win.select_all_{category_type}")
            menu.append("Deseleccionar todos", f"win.deselect_all_{category_type}")
            menu.append("Eliminar seleccionados", f"win.delete_selected_{category_type}")
            menu.append("Exportar seleccionados", f"win.export_selected_{category_type}")
            
            if category_type == KIND_IMAGE:
                menu.append("Establecer como portada", f"win.set_as_cover_{category_type}")
        
        # Registrar acciones dinámicamente
        self._register_batch_actions(category_type)
        
        return menu
    
    def _register_batch_actions(self, category_type: str):
        """Registra las acciones de lote para una categoría"""
        
        # Seleccionar/deseleccionar todos
        select_all_action = Gio.SimpleAction.new(f"select_all_{category_type}", None)
        select_all_action.connect("activate", self._on_select_all, category_type)
        self.main_window.add_action(select_all_action)
        
        deselect_all_action = Gio.SimpleAction.new(f"deselect_all_{category_type}", None)
        deselect_all_action.connect("activate", self._on_deselect_all, category_type)
        self.main_window.add_action(deselect_all_action)
        
        # Eliminar seleccionados
        delete_action = Gio.SimpleAction.new(f"delete_selected_{category_type}", None)
        delete_action.connect("activate", self._on_delete_selected, category_type)
        self.main_window.add_action(delete_action)
        
        # Acciones específicas por tipo
        if category_type == KIND_DOCUMENT:
            add_spine_action = Gio.SimpleAction.new(f"add_to_spine_{category_type}", None)
            add_spine_action.connect("activate", self._on_add_to_spine, category_type)
            self.main_window.add_action(add_spine_action)
            
            remove_spine_action = Gio.SimpleAction.new(f"remove_from_spine_{category_type}", None)
            remove_spine_action.connect("activate", self._on_remove_from_spine, category_type)
            self.main_window.add_action(remove_spine_action)
            
            batch_styles_action = Gio.SimpleAction.new(f"batch_link_styles_{category_type}", None)
            batch_styles_action.connect("activate", self._on_batch_link_styles, category_type)
            self.main_window.add_action(batch_styles_action)
            
        elif category_type == KIND_IMAGE:
            cover_action = Gio.SimpleAction.new(f"set_as_cover_{category_type}", None)
            cover_action.connect("activate", self._on_set_as_cover, category_type)
            self.main_window.add_action(cover_action)
            
        # Exportar seleccionados (para recursos binarios)
        if category_type in [KIND_IMAGE, KIND_FONT, KIND_AUDIO, KIND_VIDEO]:
            export_action = Gio.SimpleAction.new(f"export_selected_{category_type}", None)
            export_action.connect("activate", self._on_export_selected, category_type)
            self.main_window.add_action(export_action)
    
    # Acciones de lote
    def _on_select_all(self, action, param, category_type):
        """Selecciona todos los elementos de una categoría"""
        if not self.main_window.core:
            return
        
        items = self.main_window.core.list_items(kind=category_type)
        for item in items:
            self.selected_items[category_type].add(item.href)
        
        # Actualizar checkboxes visualmente
        self._update_checkboxes_visual_state(category_type, True)
        self._update_selection_counter()
    
    def _on_deselect_all(self, action, param, category_type):
        """Deselecciona todos los elementos de una categoría"""
        self.selected_items[category_type].clear()
        self._update_checkboxes_visual_state(category_type, False)
        self._update_selection_counter()
    
    def _on_delete_selected(self, action, param, category_type):
        """Elimina los elementos seleccionados de una categoría"""
        selected = self.selected_items[category_type].copy()
        
        if not selected:
            self.main_window.show_error(f"No hay elementos seleccionados en {category_type}")
            return
        
        # Diálogo de confirmación
        count = len(selected)
        message = f"¿Eliminar {count} elemento(s) seleccionado(s)? Esta acción no se puede deshacer."
        
        self.main_window.dialog_manager.show_confirmation_dialog(
            "Confirmar eliminación",
            message,
            lambda: self._do_delete_selected(selected, category_type)
        )
    
    def _do_delete_selected(self, selected_hrefs, category_type):
        """Realiza la eliminación de elementos seleccionados"""
        deleted_count = 0
        
        for href in selected_hrefs:
            try:
                self.main_window.core.remove_from_manifest(href)
                deleted_count += 1
            except Exception as e:
                print(f"Error eliminando {href}: {e}")
        
        # Limpiar selección
        self.selected_items[category_type].clear()
        self._update_selection_counter()
        
        # Actualizar UI
        self.main_window.refresh_structure()
        self.main_window.show_info(f"Eliminados {deleted_count} elementos")
    
    def _on_add_to_spine(self, action, param, category_type):
        """Agrega documentos seleccionados al spine"""
        if category_type != KIND_DOCUMENT:
            return
            
        selected = self.selected_items[category_type].copy()
        if not selected:
            self.main_window.show_error("No hay documentos seleccionados")
            return
        
        added_count = 0
        for href in selected:
            try:
                mi = self.main_window.core._get_item(href)
                self.main_window.core.spine_insert(mi.id)
                added_count += 1
            except Exception as e:
                print(f"Error agregando al spine {href}: {e}")
        
        self.main_window.show_info(f"Agregados {added_count} documentos al spine")
    
    def _on_remove_from_spine(self, action, param, category_type):
        """Quita documentos seleccionados del spine"""
        if category_type != KIND_DOCUMENT:
            return
            
        selected = self.selected_items[category_type].copy()
        if not selected:
            self.main_window.show_error("No hay documentos seleccionados")
            return
        
        removed_count = 0
        for href in selected:
            try:
                mi = self.main_window.core._get_item(href)
                self.main_window.core.spine_remove(mi.id)
                removed_count += 1
            except Exception as e:
                print(f"Error quitando del spine {href}: {e}")
        
        self.main_window.show_info(f"Quitados {removed_count} documentos del spine")
    
    def _on_batch_link_styles(self, action, param, category_type):
        """Vincula estilos a múltiples documentos seleccionados"""
        if category_type != KIND_DOCUMENT:
            return
            
        selected = self.selected_items[category_type].copy()
        if not selected:
            self.main_window.show_error("No hay documentos seleccionados")
            return
        
        # Usar el diálogo de estilos pero para múltiples documentos
        self.main_window.dialog_manager.show_batch_style_linking_dialog(selected)
    
    def _on_set_as_cover(self, action, param, category_type):
        """Establece una imagen seleccionada como portada"""
        if category_type != KIND_IMAGE:
            return
            
        selected = self.selected_items[category_type].copy()
        if len(selected) != 1:
            self.main_window.show_error("Selecciona exactamente una imagen para establecer como portada")
            return
        
        href = next(iter(selected))
        try:
            # Quitar propiedad cover-image de otras imágenes
            for item in self.main_window.core.list_items(KIND_IMAGE):
                if "cover-image" in (item.properties or ""):
                    # Actualizar en el manifest removiendo la propiedad
                    pass  # TODO: implementar método para actualizar propiedades
            
            # Establecer nueva portada
            mi = self.main_window.core._get_item(href)
            # TODO: implementar método para establecer propiedades
            
            self.main_window.show_info(f"'{Path(href).name}' establecida como portada")
            
        except Exception as e:
            self.main_window.show_error(f"Error estableciendo portada: {e}")
    
    def _on_export_selected(self, action, param, category_type):
        """Exporta recursos seleccionados a una carpeta"""
        selected = self.selected_items[category_type].copy()
        if not selected:
            self.main_window.show_error(f"No hay elementos seleccionados en {category_type}")
            return
        
        # TODO: Implementar diálogo de exportación
        self.main_window.show_info("Función de exportación - Por implementar")
    
    def _update_checkboxes_visual_state(self, category_type: str, checked: bool):
        """Actualiza visualmente el estado de los checkboxes de una categoría"""
        # Esta función requeriría iterar sobre los widgets visibles
        # Por simplicidad, se actualiza el contador y se refresca en el próximo populate_tree()
        self.main_window.refresh_structure()
    
    def _update_selection_counter(self):
        """Actualiza el contador de elementos seleccionados"""
        total_count = sum(len(items) for items in self.selected_items.values())
        
        if total_count > 0:
            self.selection_counter.set_text(f"{total_count} marcados")
            self.selection_counter.add_css_class("accent")
        else:
            self.selection_counter.set_text("")
            self.selection_counter.remove_css_class("accent")
    
    def get_selected_items(self, category_type: str = None):
        """Obtiene los elementos seleccionados de una categoría o todas"""
        if category_type:
            return self.selected_items[category_type].copy()
        return {k: v.copy() for k, v in self.selected_items.items()}
    
    def clear_selection(self, category_type: str = None):
        """Limpia la selección de una categoría o todas"""
        if category_type:
            self.selected_items[category_type].clear()
        else:
            for items in self.selected_items.values():
                items.clear()
        self._update_selection_counter()