import os
import tempfile
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkSource', '4')
gi.require_version('WebKit2', '4.1')

from gi.repository import Gtk, GObject, GLib, Gdk, GtkSource
from gi.repository import WebKit2
from lxml import html
from ebooklib import epub

from .gutenia_factory import GuteniaFactory

class EditorTab:
    def __init__(self, parent_window, settings, file_path):
        self.parent_window = parent_window
        self.current_path = file_path
        self.current_book = None
        self.book_loaded = False
        
        self.is_active = False
        self.dirty_items = set()
        self.current_item_id = None
        self.tab_label = None
        self.buffer_changed_handler_id = None

        self.widgets = GuteniaFactory.build(settings)
        self.main_paned = self.widgets["main_paned"]
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_box.pack_start(self.widgets["search_bar"], False, True, 0)
        self.main_box.pack_start(self.main_paned, True, True, 0)

        self.category_notebook = self.widgets["category_notebook"]
        self.category_treeviews = self.widgets["category_treeviews"]
        
        self.category_models = {
            "Texto": Gtk.ListStore(str, str),
            "Estilos": Gtk.ListStore(str, str),
            "Imágenes": Gtk.ListStore(str, str),
            "Fuentes": Gtk.ListStore(str, str),
            "Otros": Gtk.ListStore(str, str)
        }

        for name, model in self.category_models.items():
            if name in self.category_treeviews:
                self.category_treeviews[name].set_model(model)
        
        self.text_buffer = self.widgets["text_buffer"]
        self.content_textview = self.widgets["content_textview"]
        self.search_bar = self.widgets["search_bar"]
        self.search_entry = self.widgets["search_entry"]
        self.search_results_panel = self.widgets["search_results_panel"]
        self.search_results_treeview = self.widgets["search_results_treeview"]
        self.search_results_model = Gtk.ListStore(str, str, int)
        self.search_results_treeview.set_model(self.search_results_model)

        self.book_content_map = {}
        self.search_settings = None
        self.search_context = None

        self.load_epub()
        
        if self.book_loaded:
            self.setup_event_handlers()
            self.populate_category_lists()
            self.setup_search()
            self.update_window_title()
            
            for model_name in ["Texto", "Estilos", "Imágenes", "Fuentes", "Otros"]:
                if len(self.category_models[model_name]) > 0:
                    self.category_treeviews[model_name].get_selection().select_path(Gtk.TreePath.new_first())
                    break

    def _update_label_style(self):
        if not self.tab_label: return
        is_dirty = bool(self.dirty_items)
        base_name = os.path.basename(self.current_path)
        display_text = f"*{base_name}" if is_dirty else base_name
        if self.is_active:
            self.tab_label.set_markup(f"<b>{GLib.markup_escape_text(display_text)}</b>")
        else:
            self.tab_label.set_text(display_text)

    def destroy(self):
        self.current_book = None
        self.book_content_map.clear()
        self.dirty_items.clear()
        for model in self.category_models.values():
            model.clear()
        self.search_results_model.clear()

    def is_book_loaded(self):
        return self.book_loaded

    def get_current_path(self):
        return self.current_path

    def is_dirty(self):
        self._commit_buffer_changes()
        return bool(self.dirty_items)

    def set_active_style(self, is_active):
        self.is_active = is_active
        self._update_label_style()

    def get_tab_label_box(self):
        self.tab_label = Gtk.Label(label=os.path.basename(self.current_path))
        self.tab_label.set_tooltip_text(self.current_path)
        close_image = Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.BUTTON)
        close_button = Gtk.Button(image=close_image)
        close_button.set_relief(Gtk.ReliefStyle.NONE)
        close_button.connect("clicked", self.on_close_tab_clicked)
        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        tab_box.pack_start(self.tab_label, True, True, 0)
        tab_box.pack_start(close_button, False, False, 0)
        tab_box.show_all()
        return tab_box

    def on_close_tab_clicked(self, button):
        self.parent_window.close_tab(self)

    def on_buffer_changed(self, text_buffer):
        if self.current_item_id:
            self.dirty_items.add(self.current_item_id)
            self._update_label_style()

    def setup_event_handlers(self):
        for treeview in self.category_treeviews.values():
            treeview.get_selection().connect("changed", self.on_item_selection_changed)
        self.buffer_changed_handler_id = self.text_buffer.connect("changed", self.on_buffer_changed)
        self.search_entry.connect("search-changed", self.on_search_text_changed)
        self.search_entry.connect("activate", self.on_find_all_activated)
        self.widgets["btn_prev"].connect("clicked", self.on_search_previous)
        self.widgets["btn_next"].connect("clicked", self.on_search_next)
        self.search_results_treeview.get_selection().connect("changed", self.on_search_result_selected)
        self.search_bar.connect("key-press-event", self.on_search_bar_escape)

    def update_window_title(self):
        header_bar = self.parent_window.get_titlebar()
        book_title = os.path.basename(self.current_path)
        if self.current_book:
            titles = self.current_book.get_metadata('DC', 'title')
            if titles: book_title = titles[0][0]
        header_bar.props.title = book_title
        header_bar.props.subtitle = os.path.basename(self.current_path)

    def load_epub(self):
        try:
            self.current_book = epub.read_epub(self.current_path)
            self.book_loaded = True
        except Exception as e:
            self.book_loaded = False
            self.parent_window.show_error_dialog(f"Error al cargar EPUB: {self.current_path}", str(e))

    def _commit_buffer_changes(self):
        if not self.current_item_id: return
        item_mem = self.book_content_map.get(self.current_item_id)
        if not item_mem: return
        start, end = self.text_buffer.get_bounds()
        contenido_buf = self.text_buffer.get_text(start, end, False)
        item_mem.content = contenido_buf.encode('utf-8')

    def populate_category_lists(self):
        if not self.current_book: return
        for model in self.category_models.values():
            model.clear()
        self.book_content_map.clear()

        for item in self.current_book.get_items():
            self.book_content_map[item.get_id()] = item
            media_type = item.media_type if hasattr(item, 'media_type') else ''
            data_to_append = [item.get_name(), item.get_id()]

            if 'xhtml' in media_type or 'html' in media_type:
                self.category_models["Texto"].append(data_to_append)
            elif 'css' in media_type:
                self.category_models["Estilos"].append(data_to_append)
            elif 'jpeg' in media_type or 'jpg' in media_type or 'png' in media_type or 'gif' in media_type or 'svg' in media_type:
                self.category_models["Imágenes"].append(data_to_append)
            elif 'font' in media_type or 'opentype' in media_type:
                self.category_models["Fuentes"].append(data_to_append)
            else:
                self.category_models["Otros"].append(data_to_append)

    # --- MÉTODO CORREGIDO ---
    def on_item_selection_changed(self, selection):
        model, treeiter = selection.get_selected()
        if not treeiter: return
        
        for name, treeview in self.category_treeviews.items():
            if treeview.get_selection() != selection:
                treeview.get_selection().unselect_all()

        nuevo_item_id = model.get_value(treeiter, 1)
        if nuevo_item_id == self.current_item_id: return
        
        self._commit_buffer_changes()
        
        self.current_item_id = nuevo_item_id
        item = self.book_content_map.get(self.current_item_id)
        if not item: return

        item_media_type = item.media_type if hasattr(item, 'media_type') else ''
        text_types = ['xhtml', 'html', 'xml', 'css', 'javascript', 'text']
        is_text_item = any(tt in item_media_type for tt in text_types)

        # Bloqueamos el manejador de la señal 'changed' ANTES de modificar el buffer
        if self.buffer_changed_handler_id:
            self.text_buffer.handler_block(self.buffer_changed_handler_id)
        
        # Escribimos el contenido nuevo (sea texto o un mensaje)
        if is_text_item:
            try:
                content = item.content.decode('utf-8')
            except UnicodeDecodeError:
                content = item.content.decode('latin-1', 'ignore')
            self.text_buffer.set_text(content)
        else:
            self.text_buffer.set_text(f"Item no textual: {item.get_name()}\nTipo: {item_media_type}")
        
        # Marcamos el buffer como NO modificado, ya que el cambio fue programático
        self.text_buffer.set_modified(False)
        
        # Desbloqueamos el manejador
        if self.buffer_changed_handler_id:
            self.text_buffer.handler_unblock(self.buffer_changed_handler_id)

    def on_save_clicked(self, button):
        if not self.current_book: return
        self._commit_buffer_changes()
        if not self.dirty_items: return

        for item_id in self.dirty_items:
            item_mod = self.book_content_map.get(item_id)
            item_orig = self.current_book.get_item_with_id(item_id)
            if item_mod and item_orig:
                item_orig.content = item_mod.content
        try:
            epub.write_epub(self.current_path, self.current_book, {})
            self.dirty_items.clear()
            self.text_buffer.set_modified(False)
            self._update_label_style()
        except Exception as e:
            self.parent_window.show_error_dialog("Error al guardar el EPUB.", str(e))

    def on_preview_clicked(self, button):
        selection = self.category_treeviews["Texto"].get_selection()
        model, treeiter = selection.get_selected()
        if not self.current_book or not treeiter: return
        item_id = model.get_value(treeiter, 1)
        current_item = self.book_content_map.get(item_id)
        if not current_item or not isinstance(current_item, epub.EpubHtml): return
        with tempfile.TemporaryDirectory() as temp_dir:
            for item in self.current_book.get_items():
                if not item.get_name(): continue
                item_path = os.path.join(temp_dir, item.get_name())
                os.makedirs(os.path.dirname(item_path), exist_ok=True)
                try:
                    with open(item_path, 'wb') as f:
                        item_from_map = self.book_content_map.get(item.get_id())
                        if item_from_map: f.write(item_from_map.content)
                        else: f.write(item.content)
                except Exception as e:
                    print(f"Error al escribir archivo temporal {item.get_name()}: {e}")
            preview_dialog = Gtk.Dialog(title="Vista Previa", transient_for=self.parent_window, modal=True, flags=0)
            preview_dialog.add_button("_Cerrar", Gtk.ResponseType.CLOSE)
            preview_dialog.set_default_size(800, 600)
            scrolled_window = Gtk.ScrolledWindow()
            preview_dialog.get_content_area().pack_start(scrolled_window, True, True, 0)
            settings = WebKit2.Settings()
            settings.set_property('enable-developer-extras', True)
            settings.set_property('allow-file-access-from-file-urls', True)
            webview = WebKit2.WebView.new_with_settings(settings)
            scrolled_window.add(webview)
            chapter_file_path = os.path.join(temp_dir, current_item.get_name())
            uri = GLib.filename_to_uri(chapter_file_path, None)
            webview.load_uri(uri)
            preview_dialog.show_all()
            preview_dialog.run()
            preview_dialog.destroy()

    def on_export_to_text_clicked(self, button):
        if not self.current_book: return
        file_dialog = Gtk.FileChooserDialog(title="Exportar como Texto", parent=self.parent_window, action=Gtk.FileChooserAction.SAVE)
        file_dialog.add_buttons("_Cancelar", Gtk.ResponseType.CANCEL, "_Exportar", Gtk.ResponseType.OK)
        book_title = os.path.splitext(os.path.basename(self.current_path))[0]
        file_dialog.set_current_name(f"{book_title}.txt")
        response = file_dialog.run()
        if response == Gtk.ResponseType.OK:
            filepath = file_dialog.get_filename()
            if not filepath.endswith(".txt"): filepath += ".txt"
            try:
                all_text = []
                for item_id, linear in self.current_book.spine:
                    item = self.current_book.get_item_with_id(item_id)
                    if item and isinstance(item, epub.EpubHtml):
                        tree = html.fromstring(item.content)
                        clean_text = tree.text_content()
                        all_text.append(clean_text)
                full_text = "\n\n----------\n\n".join(all_text)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(full_text)
            except Exception as e:
                self.parent_window.show_error_dialog("Ocurrió un error al exportar.", str(e))
        file_dialog.destroy()
        
    def setup_search(self):
        self.search_settings = GtkSource.SearchSettings.new()
        self.search_context = GtkSource.SearchContext.new(buffer=self.text_buffer, settings=self.search_settings)
        self.search_bar.connect_entry(self.search_entry)

    def toggle_search_bar(self):
        self.search_bar.set_search_mode(not self.search_bar.get_search_mode())

    def on_search_bar_escape(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.search_bar.set_search_mode(False)
            self.search_results_panel.hide()
            return True
        return False

    def on_search_text_changed(self, search_entry):
        if not self.search_settings: return
        self.search_settings.set_search_text(search_entry.get_text())

    def on_search_next(self, button):
        if not self.search_context: return
        start_iter = self.text_buffer.get_iter_at_mark(self.text_buffer.get_insert())
        self.search_context.forward_async(start_iter, None, self.on_forward_find_finished)

    def on_search_previous(self, button):
        if not self.search_context: return
        start_iter = self.text_buffer.get_iter_at_mark(self.text_buffer.get_insert())
        self.search_context.backward_async(start_iter, None, self.on_backward_find_finished)

    def on_forward_find_finished(self, context, result):
        try:
            found, match_start, match_end, wrapped = self.search_context.forward_finish(result)
            if found: self._show_find_result(match_start, match_end)
        except GLib.Error as e: print(f"Error en búsqueda: {e.message}")

    def on_backward_find_finished(self, context, result):
        try:
            found, match_start, match_end, wrapped = self.search_context.backward_finish(result)
            if found: self._show_find_result(match_start, match_end)
        except GLib.Error as e: print(f"Error en búsqueda: {e.message}")

    def _show_find_result(self, match_start, match_end):
        self.text_buffer.select_range(match_start, match_end)
        self.content_textview.scroll_to_iter(match_start, 0.0, True, 0.5, 0.5)

    def on_find_all_activated(self, search_entry):
        if not self.search_context: return
        self.search_results_model.clear()
        search_text = search_entry.get_text()
        if not search_text:
            self.search_results_panel.hide()
            return
        
        start_iter = self.text_buffer.get_start_iter()
        found_any = False
        while True:
            found, match_start, match_end = self.search_context.forward(start_iter)
            if not found: break
            
            found_any = True
            line_num = match_start.get_line() + 1
            line_start_iter = self.text_buffer.get_iter_at_line(match_start.get_line())
            line_end_iter = line_start_iter.copy()
            if not line_end_iter.ends_line():
                line_end_iter.forward_to_line_end()
            line_text = self.text_buffer.get_text(line_start_iter, line_end_iter, False).strip()
            self.search_results_model.append([str(line_num), line_text, match_start.get_offset()])
            start_iter = match_end
            
        self.search_results_panel.set_visible(found_any)

    def on_search_result_selected(self, selection):
        model, treeiter = selection.get_selected()
        if treeiter:
            match_offset = model.get_value(treeiter, 2)
            match_start = self.text_buffer.get_iter_at_offset(match_offset)
            search_text_len = len(self.search_settings.get_search_text() or "")
            match_end = self.text_buffer.get_iter_at_offset(match_offset + search_text_len)
            self._show_find_result(match_start, match_end)