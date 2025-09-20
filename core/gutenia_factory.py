import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkSource', '4')

from gi.repository import Gtk, GtkSource

class GuteniaFactory:
    """
    Construye la interfaz de usuario para una pestaña de Gutenia, 
    incluyendo el nuevo panel de navegación por categorías.
    """
    @staticmethod
    def build(settings):
        # --- ESTRUCTURA DE NAVEGACIÓN POR CATEGORÍAS ---

        # 1. Creamos el Notebook principal para la navegación izquierda.
        category_notebook = Gtk.Notebook()
        category_notebook.set_tab_pos(Gtk.PositionType.LEFT)

        # 2. Creamos un diccionario para guardar las referencias a los TreeView de cada categoría.
        treeviews = {}

        # 3. Definimos las categorías y creamos una pestaña para cada una.
        categories = ["Texto", "Estilos", "Imágenes", "Fuentes", "Otros"]
        for category_name in categories:
            # Cada pestaña contiene un ScrolledWindow con un TreeView dentro.
            scrolled_window = Gtk.ScrolledWindow()
            scrolled_window.set_hexpand(True)
            scrolled_window.set_vexpand(True)
            
            treeview = Gtk.TreeView()
            
            # Añadimos las columnas al TreeView
            renderer_text = Gtk.CellRendererText()
            column_text = Gtk.TreeViewColumn("Archivo", renderer_text, text=0)
            treeview.append_column(column_text)

            scrolled_window.add(treeview)
            
            # Guardamos la referencia al treeview para poder llenarlo después.
            treeviews[category_name] = treeview

            # Añadimos la página al notebook.
            label = Gtk.Label(label=category_name)
            category_notebook.append_page(scrolled_window, label)

        # --- UI PRINCIPAL (PANELES Y EDITOR) ---
        
        search_bar = Gtk.SearchBar()
        search_bar.set_search_mode(False)
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        search_box.set_border_width(6)
        search_bar.add(search_box)
        search_entry = Gtk.SearchEntry()
        search_box.pack_start(search_entry, True, True, 0)
        btn_prev = Gtk.Button(image=Gtk.Image.new_from_icon_name("go-up-symbolic", Gtk.IconSize.BUTTON))
        btn_prev.set_tooltip_text("Buscar anterior")
        search_box.pack_start(btn_prev, False, False, 0)
        btn_next = Gtk.Button(image=Gtk.Image.new_from_icon_name("go-down-symbolic", Gtk.IconSize.BUTTON))
        btn_next.set_tooltip_text("Buscar siguiente")
        search_box.pack_start(btn_next, False, False, 0)

        main_paned_h = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        main_paned_h.set_position(settings.get('paned_position', 250))
        
        # El panel izquierdo ahora contiene nuestro Notebook de categorías
        main_paned_h.add1(category_notebook)

        right_paned_v = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        right_paned_v.set_position(settings.get('v_paned_position', 500))
        main_paned_h.add2(right_paned_v)

        content_scrolled = Gtk.ScrolledWindow()
        right_paned_v.add1(content_scrolled)
        
        text_buffer = GtkSource.Buffer()
        lang_manager = GtkSource.LanguageManager.get_default()
        language = lang_manager.get_language('xml')
        if language: text_buffer.set_language(language)
        
        content_textview = GtkSource.View.new_with_buffer(text_buffer)
        content_textview.set_show_line_numbers(True)
        content_textview.set_highlight_current_line(True)
        content_textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        content_textview.set_monospace(True)
        content_textview.set_auto_indent(True)
        content_textview.set_indent_on_tab(True)
        content_textview.set_tab_width(2)
        content_scrolled.add(content_textview)

        search_results_panel = Gtk.ScrolledWindow()
        search_results_panel.set_no_show_all(True) 
        search_results_panel.hide()
        right_paned_v.add2(search_results_panel)
        search_results_treeview = Gtk.TreeView()
        search_results_panel.add(search_results_treeview)
        
        # Devolvemos todos los widgets necesarios.
        return {
            "main_paned": main_paned_h,
            "category_notebook": category_notebook,
            "category_treeviews": treeviews,
            "content_textview": content_textview,
            "text_buffer": text_buffer,
            "search_bar": search_bar,
            "search_entry": search_entry,
            "btn_prev": btn_prev,
            "btn_next": btn_next,
            "search_results_panel": search_results_panel,
            "search_results_treeview": search_results_treeview,
        }