"""
gtk_ui/smart_link_inserter.py
Sistema de inserción inteligente de enlaces a hooks existentes
"""

import os
from gi.repository import Gtk, GLib, Gio, GObject, Pango
from typing import Optional, List, Dict
from pathlib import Path

# Importar constantes si es necesario
from core.guten_core import KIND_DOCUMENT

class SmartLinkInserter:
    """
    Gestor de inserción de enlaces a hooks (anchors) en el editor HTML
    """

    def __init__(self, central_editor):
        """
        Inicializa el insertor de enlaces
        
        Args:
            central_editor: Instancia de CentralEditor
        """
        self.central_editor = central_editor
        self.main_window = central_editor.main_window
        
        # Diálogo de selección
        self.link_dialog: Optional[Gtk.Window] = None
        
        # Estado
        self._pending_selection = None
        self._hooks_model = None  # Gtk.ListStore
        self._filter_model = None # Gtk.TreeModelFilter (si se usa TreeView) o Gtk.FilterListModel
        
        # Cache de hooks
        self._cached_hooks = []

    # =====================================================
    # INTERFAZ DE USUARIO
    # =====================================================

    def show_link_insertion_dialog(self):
        """
        Muestra el diálogo para seleccionar un hook y crear un enlace
        """
        buffer = self.central_editor.source_buffer
        
        # Verificar que hay selección (opcional, si no hay se puede usar el texto del hook como link)
        start_iter, end_iter = buffer.get_selection_bounds()
        if start_iter.equal(end_iter):
            # No hay selección, se insertará el texto del contexto del hook
            self._pending_selection = (start_iter.get_offset(), start_iter.get_offset())
            has_selection = False
        else:
            self._pending_selection = (start_iter.get_offset(), end_iter.get_offset())
            has_selection = True
            
        # Verificar que tenemos acceso al índice de hooks
        if not self.main_window.core or not hasattr(self.main_window.core, 'hook_index'):
            self.main_window.show_error("El índice de hooks no está disponible")
            return
            
        # Refrescar índice si es necesario?
        # self.main_window.core.hook_index.update_dirty_files()
        
        # Obtener todos los hooks
        self._cached_hooks = self.main_window.core.hook_index.get_all_hooks()
        
        if not self._cached_hooks:
            self.main_window.show_info(
                "No se encontraron hooks (anclajes) en el libro.\n\n"
                "Para usar esta función, primero debes crear hooks en otros capítulos:\n"
                "1. Selecciona texto en un capítulo destino\n"
                "2. Clic derecho -> Hooks -> Crear Hook"
            )
            return
            
        # Crear diálogo
        self._create_dialog(has_selection)

    def _create_dialog(self, has_selection: bool):
        """Crea el diálogo de selección de hooks"""
        from gi.repository import Adw
        
        if self.link_dialog:
            self.link_dialog.destroy()
            
        self.link_dialog = Adw.Window()
        self.link_dialog.set_transient_for(self.main_window)
        self.link_dialog.set_modal(True)
        self.link_dialog.set_default_size(600, 500)
        self.link_dialog.set_title("Insertar Enlace a Hook")
        
        # Contenedor principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        # Header bar
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False) # Vamos a poner botones custom
        
        # Título custom
        title_label = Gtk.Label(label="Insertar Enlace")
        title_label.add_css_class("title")
        header.set_title_widget(title_label)
        
        # Botón Cancelar (Izquierda)
        cancel_btn = Gtk.Button(label="Cancelar")
        cancel_btn.connect('clicked', lambda w: self.link_dialog.close())
        header.pack_start(cancel_btn)
        
        # Botón Insertar (Derecha)
        self.insert_btn = Gtk.Button(label="Insertar Enlace")
        self.insert_btn.add_css_class("suggested-action")
        self.insert_btn.connect('clicked', self._on_insert_confirmed)
        self.insert_btn.set_sensitive(False) # Desactivado hasta que se seleccione algo
        header.pack_end(self.insert_btn)
        
        main_box.append(header)
        
        # Contenido
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_top(12)
        content_box.set_margin_bottom(12)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)
        content_box.set_vexpand(True)
        
        # Campo de búsqueda
        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text("Buscar por ID, texto o archivo...")
        search_entry.connect('search-changed', self._on_search_changed)
        content_box.append(search_entry)
        
        # Lista de hooks (TreeView para mejor soporte de columnas)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_min_content_height(300)
        
        # Crear modelo y vista
        self.tree_view = self._create_hooks_treeview()
        scrolled.set_child(self.tree_view)
        
        content_box.append(scrolled)
        
        # Texto de ayuda / Preview
        if has_selection:
            help_text = "Se creará un enlace sobre el texto seleccionado apuntando al hook elegido."
        else:
            help_text = "Se insertará el texto de contexto del hook como enlace."
            
        help_label = Gtk.Label(label=help_text)
        help_label.set_halign(Gtk.Align.START)
        help_label.add_css_class("dim-label")
        content_box.append(help_label)
        
        main_box.append(content_box)
        
        self.link_dialog.set_content(main_box)
        self.link_dialog.present()
        
        # Foco en búsqueda
        GLib.timeout_add(100, lambda: search_entry.grab_focus())

    def _create_hooks_treeview(self) -> Gtk.TreeView:
        """Crea el TreeView para listar hooks"""
        # Modelo: ID, Contexto, Archivo, Objeto Hook (invisible)
        self.store = Gtk.ListStore(str, str, str, object)
        
        # Poblar modelo inicial
        for hook in self._cached_hooks:
            # Simplificar nombre de archivo para mostrar
            pretty_file = Path(hook.file_href).name
            self.store.append([hook.hook_id, hook.context_text, pretty_file, hook])
            
        # Filtro
        self.filter_model = self.store.filter_new(None)
        self.filter_model.set_visible_func(self._filter_func)
        
        # Vista
        tree = Gtk.TreeView(model=self.filter_model)
        tree.set_headers_visible(True)
        
        # Columnas
        # 1. ID
        renderer_id = Gtk.CellRendererText()
        renderer_id.set_property("weight", Pango.Weight.BOLD)
        col_id = Gtk.TreeViewColumn("ID", renderer_id, text=0)
        col_id.set_sort_column_id(0)
        col_id.set_resizable(True)
        tree.append_column(col_id)
        
        # 2. Contexto
        renderer_ctx = Gtk.CellRendererText()
        renderer_ctx.set_property("ellipsize", Pango.EllipsizeMode.END)
        col_ctx = Gtk.TreeViewColumn("Contexto", renderer_ctx, text=1)
        col_ctx.set_expand(True)
        col_ctx.set_resizable(True)
        tree.append_column(col_ctx)
        
        renderer_file = Gtk.CellRendererText()
        renderer_file.set_property("sensitive", False)  # Efecto 'dim'
        col_file = Gtk.TreeViewColumn("Archivo", renderer_file, text=2)
        col_file.set_sort_column_id(2)
        tree.append_column(col_file)
        
        # Selección
        selection = tree.get_selection()
        selection.connect("changed", self._on_selection_changed)
        
        # Doble click para activar
        tree.connect("row-activated", lambda t, p, c: self._on_insert_confirmed(None))
        
        return tree

    def _filter_func(self, model, iter, data):
        """Función de filtrado para la búsqueda"""
        if not hasattr(self, '_current_search_query') or not self._current_search_query:
            return True
            
        query = self._current_search_query.lower()
        
        hook_id = model.get_value(iter, 0).lower()
        context = model.get_value(iter, 1).lower()
        filename = model.get_value(iter, 2).lower()
        
        return (query in hook_id or 
                query in context or 
                query in filename)

    def _on_search_changed(self, entry):
        """Callback al tippear en búsqueda"""
        self._current_search_query = entry.get_text()
        self.filter_model.refilter()
        
    def _on_selection_changed(self, selection):
        """Callback al cambiar selección en la lista"""
        model, iter = selection.get_selected()
        if iter:
            self.insert_btn.set_sensitive(True)
        else:
            self.insert_btn.set_sensitive(False)

    def _on_insert_confirmed(self, button):
        """Callback al confirmar inserción"""
        selection = self.tree_view.get_selection()
        model, iter = selection.get_selected()
        
        if not iter:
            return
            
        # Obtener objeto hook real
        hook = model.get_value(iter, 3)
        
        # Realizar inserción
        self._insert_link_to_hook(hook)
        
        # Cerrar
        self.link_dialog.close()

    # =====================================================
    # LÓGICA DE INSERCIÓN
    # =====================================================

    def _calculate_relative_href(self, source_href: str, target_href: str) -> str:
        """
        Calcula la ruta relativa desde el archivo fuente al destino
        
        Args:
            source_href: Ruta del archivo donde está el enlace (ej: Text/cap1.xhtml)
            target_href: Ruta del archivo destino (ej: Text/cap2.xhtml)
            
        Returns:
            Ruta relativa (ej: "cap2.xhtml" o "../Text/cap2.xhtml")
        """
        if source_href == target_href:
            return "" # Mismo archivo
            
        # Simular rutas absolutas para usar os.path.relpath
        # No importa la base mientras sea común
        base = "/epub_root"
        abs_source = os.path.join(base, source_href)
        abs_target = os.path.join(base, target_href)
        
        # Obtener directorio del fuente
        source_dir = os.path.dirname(abs_source)
        
        # Calcular relativo
        rel_path = os.path.relpath(abs_target, start=source_dir)
        
        return rel_path

    def _insert_link_to_hook(self, hook):
        """
        Inserta el tag <a> en el editor
        """
        if not self._pending_selection:
            return
            
        start_offset, end_offset = self._pending_selection
        buffer = self.central_editor.source_buffer
        current_file = self.main_window.current_resource
        
        # Calcular href
        rel_path = self._calculate_relative_href(current_file, hook.file_href)
        full_href = f"{rel_path}#{hook.hook_id}"
        
        # Texto del enlace
        if start_offset == end_offset:
            # Sin selección previa: usar texto del hook
            link_text = hook.context_text
            is_replace = False
        else:
            # Con selección: usar texto seleccionado
            start_iter = buffer.get_iter_at_offset(start_offset)
            end_iter = buffer.get_iter_at_offset(end_offset)
            link_text = buffer.get_text(start_iter, end_iter, False)
            is_replace = True
            
        # Construir tag
        link_tag = f'<a href="{full_href}">{link_text}</a>'
        
        # Ejecutar en buffer (con soporte Undo)
        buffer.begin_user_action()
        try:
            if is_replace:
                # Borrar selección
                start_iter = buffer.get_iter_at_offset(start_offset)
                end_iter = buffer.get_iter_at_offset(end_offset)
                buffer.delete(start_iter, end_iter)
                
            # Insertar
            insert_iter = buffer.get_iter_at_offset(start_offset)
            buffer.insert(insert_iter, link_tag)
            
            # Posicionar cursor al final
            # Nuevo offset = start + len(tag)
            new_offset = start_offset + len(link_tag)
            new_iter = buffer.get_iter_at_offset(new_offset)
            buffer.place_cursor(new_iter)
            
        finally:
            buffer.end_user_action()
            
        # Actualizar estado
        if hasattr(self.central_editor, '_needs_save'):
            self.central_editor._needs_save = True
            
        self.main_window.show_info(f"Enlace creado hacia '{hook.hook_id}'")


def integrate_smart_link_inserter(central_editor):
    """
    Integra el sistema de enlaces inteligentes con el editor
    """
    # Crear instancia
    link_inserter = SmartLinkInserter(central_editor)
    
    # Guardar referencia
    central_editor.smart_link_inserter = link_inserter
    
    # Registrar acción
    # Accion: win.insert_smart_link
    action = Gio.SimpleAction.new("insert_smart_link", None)
    action.connect("activate", lambda a, p: link_inserter.show_link_insertion_dialog())
    central_editor.main_window.add_action(action)
    
    return link_inserter
