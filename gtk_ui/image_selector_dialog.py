"""
ui/image_selector_dialog.py
Diálogo para seleccionar e insertar imágenes del EPUB - COMPLETAMENTE CORREGIDO
"""

from gi.repository import Gtk, Adw, GdkPixbuf, GLib, Gio, Pango, GObject
from pathlib import Path
from typing import List, Set, Optional, TYPE_CHECKING
import mimetypes
from dataclasses import dataclass

from core.guten_core import KIND_IMAGE

if TYPE_CHECKING:
    from .main_window import GutenAIWindow

@dataclass
class ImageInfo:
    """Información de una imagen del EPUB"""
    href: str
    name: str
    full_path: Path
    size_bytes: int
    mime_type: str
    selected: bool = False
    thumbnail: Optional[GdkPixbuf.Pixbuf] = None

# *** WRAPPER CLASS CORREGIDA ***
class ImageWrapper(GObject.Object):
    """Wrapper GObject para ImageInfo"""
    
    def __init__(self, image_info: ImageInfo):
        super().__init__()
        self.image_info = image_info
        # Guardar referencia a checkbox para poder actualizarla
        self.checkbox_ref = None

class ImageSelectorDialog:
    """Diálogo para seleccionar imágenes del EPUB"""
    
    def __init__(self, main_window: 'GutenAIWindow'):
        self.main_window = main_window
        self.images: List[ImageInfo] = []
        self.selected_images: Set[str] = set()
        
        # Configuración de thumbnails
        self.THUMBNAIL_SIZE = 120
        self.THUMBNAIL_CACHE = {}
        
        # Referencias de widgets
        self.dialog: Optional[Adw.Window] = None
        self.grid_view: Optional[Gtk.GridView] = None
        self.status_label: Optional[Gtk.Label] = None
        self.accept_button: Optional[Gtk.Button] = None
        
        # *** REFERENCIAS PARA ACTUALIZACIÓN ***
        self.checkbox_refs: List[Gtk.CheckButton] = []
        self.wrappers: List[ImageWrapper] = []
    
    def show_dialog(self):
        """Muestra el diálogo selector de imágenes"""
        
        if not self.main_window.core:
            self.main_window.show_error("No hay proyecto EPUB abierto")
            return
        
        # Cargar imágenes del proyecto
        if not self._load_images():
            self.main_window.show_error("No hay imágenes en el proyecto EPUB")
            return
        
        # Crear y mostrar diálogo
        self._create_dialog()
        self._populate_grid()
        self.dialog.present()
    
    def _load_images(self) -> bool:
        """Carga la lista de imágenes del EPUB"""
        
        try:
            image_items = self.main_window.core.list_items(kind=KIND_IMAGE)
            
            if not image_items:
                return False
            
            self.images.clear()
            
            for item in image_items:
                try:
                    full_path = (self.main_window.core.opf_dir / item.href).resolve()
                    
                    if not full_path.exists():
                        continue
                    
                    # Información del archivo
                    stat_info = full_path.stat()
                    
                    image_info = ImageInfo(
                        href=item.href,
                        name=Path(item.href).name,
                        full_path=full_path,
                        size_bytes=stat_info.st_size,
                        mime_type=item.media_type or mimetypes.guess_type(str(full_path))[0] or "image/*"
                    )
                    
                    self.images.append(image_info)
                    
                except Exception as e:
                    print(f"Error loading image info for {item.href}: {e}")
                    continue
            
            return len(self.images) > 0
            
        except Exception as e:
            print(f"Error loading images: {e}")
            return False
    
    def _create_dialog(self):
        """Crea el diálogo principal"""
        
        self.dialog = Adw.Window()
        self.dialog.set_title("Seleccionar imágenes")
        self.dialog.set_default_size(800, 600)
        self.dialog.set_transient_for(self.main_window)
        self.dialog.set_modal(True)
        
        # Header bar
        header_bar = Adw.HeaderBar()
        
        # Botón cancelar
        cancel_button = Gtk.Button()
        cancel_button.set_label("Cancelar")
        cancel_button.connect('clicked', self._on_cancel_clicked)
        header_bar.pack_start(cancel_button)
        
        # Botón aceptar
        self.accept_button = Gtk.Button()
        self.accept_button.set_label("Insertar seleccionadas")
        self.accept_button.add_css_class("suggested-action")
        self.accept_button.set_sensitive(False)
        self.accept_button.connect('clicked', self._on_accept_clicked)
        header_bar.pack_end(self.accept_button)
        
        # Toolbar view
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header_bar)
        
        # Contenido principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.set_spacing(12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        
        # Status bar superior
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        status_box.set_spacing(12)
        
        self.status_label = Gtk.Label()
        self._update_status_label()
        status_box.append(self.status_label)
        
        # Botones de selección rápida
        select_all_btn = Gtk.Button()
        select_all_btn.set_label("Seleccionar todas")
        select_all_btn.add_css_class("flat")
        select_all_btn.connect('clicked', self._on_select_all)
        status_box.append(select_all_btn)
        
        select_none_btn = Gtk.Button()
        select_none_btn.set_label("Deseleccionar todas")
        select_none_btn.add_css_class("flat")
        select_none_btn.connect('clicked', self._on_select_none)
        status_box.append(select_none_btn)
        
        main_box.append(status_box)
        
        # Grid de imágenes con scroll
        self._create_images_grid()
        main_box.append(self.grid_scroll)
        
        toolbar_view.set_content(main_box)
        self.dialog.set_content(toolbar_view)
    
    def _create_images_grid(self):
        """Crea el grid view para las imágenes - CORREGIDO"""
        
        # ScrolledWindow para el grid
        self.grid_scroll = Gtk.ScrolledWindow()
        self.grid_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.grid_scroll.set_vexpand(True)
        
        # *** USAR LISTSTORE CON IMAGEWRAPPER PERSONALIZADO ***
        self.list_store = Gio.ListStore(item_type=ImageWrapper)
        
        # Selection model
        self.selection_model = Gtk.NoSelection.new(self.list_store)
        
        # Factory para crear elementos
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)
        
        # GridView
        self.grid_view = Gtk.GridView()
        self.grid_view.set_model(self.selection_model)
        self.grid_view.set_factory(factory)
        self.grid_view.set_min_columns(2)
        self.grid_view.set_max_columns(5)
        
        self.grid_scroll.set_child(self.grid_view)
    
    def _populate_grid(self):
        """Puebla el grid con las imágenes"""
        
        # Limpiar modelo y referencias
        self.list_store.remove_all()
        self.checkbox_refs.clear()
        self.wrappers.clear()
        
        # Crear wrappers para las imágenes
        for image_info in self.images:
            wrapper = ImageWrapper(image_info)
            self.wrappers.append(wrapper)
            self.list_store.append(wrapper)
        
        # *** INICIAR GENERACIÓN DE THUMBNAILS DESPUÉS DE QUE EL GRID ESTÉ POBLADO ***
        GLib.timeout_add(100, self._start_thumbnail_generation)
    
    def _on_factory_setup(self, factory, list_item):
        """Configura cada elemento del grid"""
        
        # Contenedor principal
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        card.set_spacing(6)
        card.set_size_request(140, 180)
        card.add_css_class("card")
        card.set_margin_top(6)
        card.set_margin_bottom(6)
        card.set_margin_start(6)
        card.set_margin_end(6)
        
        # Checkbox para selección
        checkbox = Gtk.CheckButton()
        checkbox.set_halign(Gtk.Align.START)
        checkbox.set_margin_top(6)
        checkbox.set_margin_start(6)
        card.append(checkbox)
        
        # Imagen thumbnail
        image = Gtk.Image()
        image.set_size_request(self.THUMBNAIL_SIZE, self.THUMBNAIL_SIZE)
        image.set_halign(Gtk.Align.CENTER)
        image.set_valign(Gtk.Align.CENTER)
        card.append(image)
        
        # Información de la imagen
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        info_box.set_spacing(2)
        info_box.set_margin_start(6)
        info_box.set_margin_end(6)
        info_box.set_margin_bottom(6)
        
        # Nombre del archivo
        name_label = Gtk.Label()
        name_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        name_label.set_max_width_chars(15)
        name_label.add_css_class("caption-heading")
        info_box.append(name_label)
        
        # Información adicional (tamaño)
        size_label = Gtk.Label()
        size_label.add_css_class("caption")
        size_label.add_css_class("dim-label")
        info_box.append(size_label)
        
        card.append(info_box)
        
        # Guardar referencias en el widget
        card.checkbox = checkbox
        card.image = image
        card.name_label = name_label
        card.size_label = size_label
        
        list_item.set_child(card)
    
    def _on_factory_bind(self, factory, list_item):
        """Vincula datos a cada elemento del grid - CORREGIDO SIN DISCONNECT"""
        
        wrapper = list_item.get_item()
        image_info = wrapper.image_info
        card = list_item.get_child()
        
        # *** GUARDAR REFERENCIA DEL CHECKBOX Y WIDGET DE IMAGEN ***
        wrapper.checkbox_ref = card.checkbox
        wrapper.image_widget_ref = card.image  # Para actualizar thumbnails después
        
        if card.checkbox not in self.checkbox_refs:
            self.checkbox_refs.append(card.checkbox)
        
        # *** CONFIGURAR CHECKBOX SIN DESCONECTAR (ya que puede no tener conexiones) ***
        card.checkbox.set_active(image_info.selected)
        
        # *** CONECTAR SOLO UNA VEZ - USAR CONNECT CON USER DATA ÚNICO ***
        # Esto evita conexiones duplicadas porque cada bind es con un wrapper diferente
        card.checkbox.connect('toggled', self._on_image_toggled, image_info)
        
        # *** CONFIGURAR THUMBNAIL O PLACEHOLDER ***
        if image_info.thumbnail:
            card.image.set_from_pixbuf(image_info.thumbnail)
        else:
            # Imagen placeholder mientras se genera el thumbnail
            card.image.set_from_icon_name("image-x-generic")
            card.image.set_pixel_size(64)
        
        # Configurar labels
        card.name_label.set_text(image_info.name)
        card.size_label.set_text(self._format_file_size(image_info.size_bytes))

    def _generate_thumbnails_sequential(self, index: int):
        """Genera thumbnails de manera secuencial - MÉTODO CORREGIDO"""
        
        if index >= len(self.images):
            print(f"[DEBUG] Thumbnail generation completed for {len(self.images)} images")
            return False
        
        image_info = self.images[index]
        wrapper = self.wrappers[index]
        
        # Generar thumbnail si no existe
        if image_info.thumbnail is None:
            try:
                print(f"[DEBUG] Generating thumbnail for {image_info.name}")
                thumbnail = self._create_thumbnail(image_info.full_path)
                
                if thumbnail:
                    image_info.thumbnail = thumbnail
                    
                    # *** ACTUALIZAR EL WIDGET DE IMAGEN DIRECTAMENTE ***
                    if hasattr(wrapper, 'image_widget_ref') and wrapper.image_widget_ref and wrapper.image_widget_ref.get_parent():
                        GLib.idle_add(lambda: self._update_image_widget(wrapper.image_widget_ref, thumbnail))
                    
                    print(f"[DEBUG] Thumbnail generated successfully for {image_info.name}")
                else:
                    print(f"[DEBUG] Failed to generate thumbnail for {image_info.name}")
                    
            except Exception as e:
                print(f"[ERROR] Error creating thumbnail for {image_info.name}: {e}")
        
        # *** CONTINUAR CON LA SIGUIENTE IMAGEN EN EL SIGUIENTE IDLE ***
        GLib.timeout_add(50, lambda: self._generate_thumbnails_sequential(index + 1))
        return False
    
    def _update_image_widget(self, image_widget, thumbnail):
        """Actualiza el widget de imagen con el thumbnail"""
        try:
            if image_widget and image_widget.get_parent():  # Verificar que aún existe
                image_widget.set_from_pixbuf(thumbnail)
                return False
        except Exception as e:
            print(f"[ERROR] Error updating image widget: {e}")
            return False
    
    def _start_thumbnail_generation(self):
        """Inicia la generación de thumbnails de manera asíncrona"""
        # Generar thumbnails de forma secuencial para evitar problemas de concurrencia
        self._generate_thumbnails_sequential(0)
        return False  # Solo ejecutar una vez
    
    

    def _on_image_toggled(self, checkbox, image_info: ImageInfo):
        """Maneja el toggle de selección de imagen"""
        
        image_info.selected = checkbox.get_active()
        
        if image_info.selected:
            self.selected_images.add(image_info.href)
        else:
            self.selected_images.discard(image_info.href)
        
        self._update_status_label()
        self.accept_button.set_sensitive(len(self.selected_images) > 0)
    
    def _generate_thumbnails(self):
        """Genera thumbnails para las imágenes de forma asíncrona - MEJORADO"""
        
        # Procesar imágenes una por una
        current_index = 0
        
        def process_next_image():
            nonlocal current_index
            
            if current_index >= len(self.images):
                return False  # Terminar
            
            image_info = self.images[current_index]
            
            if image_info.thumbnail is None:
                try:
                    # Generar thumbnail
                    thumbnail = self._create_thumbnail(image_info.full_path)
                    if thumbnail:
                        image_info.thumbnail = thumbnail
                        
                        # *** ACTUALIZAR UI DE MANERA MÁS EFICIENTE ***
                        # Notificar cambio en el modelo
                        self.list_store.items_changed(current_index, 1, 1)
                        
                except Exception as e:
                    print(f"Error creating thumbnail for {image_info.name}: {e}")
            
            current_index += 1
            
            # Continuar con la siguiente imagen en el próximo idle
            GLib.idle_add(process_next_image)
            return False
        
        # Iniciar procesamiento
        return process_next_image()
    
    def _create_thumbnail(self, image_path: Path) -> Optional[GdkPixbuf.Pixbuf]:
        """Crea un thumbnail de una imagen - MEJORADO"""
        
        try:
            # *** VERIFICAR QUE EL ARCHIVO EXISTE ***
            if not image_path.exists():
                print(f"[ERROR] Image file not found: {image_path}")
                return None
            
            # *** VERIFICAR TAMAÑO DEL ARCHIVO ***
            file_size = image_path.stat().st_size
            if file_size == 0:
                print(f"[ERROR] Empty image file: {image_path}")
                return None
            
            # *** CARGAR CON MANEJO DE ERRORES MÁS ESPECÍFICO ***
            try:
                # Intentar cargar con un tamaño máximo para evitar problemas de memoria
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(image_path), 
                    self.THUMBNAIL_SIZE * 2,  # Cargar a resolución mayor para mejor calidad
                    self.THUMBNAIL_SIZE * 2, 
                    True  # Mantener aspecto
                )
            except Exception as pixbuf_error:
                print(f"[ERROR] Cannot load image {image_path}: {pixbuf_error}")
                try:
                    # Fallback: intentar carga normal
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(image_path))
                except Exception as fallback_error:
                    print(f"[ERROR] Fallback load also failed for {image_path}: {fallback_error}")
                    return None
            
            if not pixbuf:
                print(f"[ERROR] Pixbuf is None for {image_path}")
                return None
            
            # Verificar dimensiones válidas
            original_width = pixbuf.get_width()
            original_height = pixbuf.get_height()
            
            if original_width <= 0 or original_height <= 0:
                print(f"[ERROR] Invalid dimensions for {image_path}: {original_width}x{original_height}")
                return None
            
            # *** REDIMENSIONAR SOLO SI ES NECESARIO ***
            if original_width <= self.THUMBNAIL_SIZE and original_height <= self.THUMBNAIL_SIZE:
                # La imagen ya es pequeña, no redimensionar
                return pixbuf
            
            # *** MEJORAR CÁLCULO DE DIMENSIONES ***
            if original_width > original_height:
                new_width = self.THUMBNAIL_SIZE
                new_height = max(1, int((original_height * self.THUMBNAIL_SIZE) / original_width))
            else:
                new_height = self.THUMBNAIL_SIZE
                new_width = max(1, int((original_width * self.THUMBNAIL_SIZE) / original_height))
            
            # Redimensionar manteniendo aspecto con mejor interpolación
            thumbnail = pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)
            
            print(f"[DEBUG] Thumbnail created: {original_width}x{original_height} -> {new_width}x{new_height}")
            return thumbnail
            
        except Exception as e:
            print(f"[ERROR] Unexpected error creating thumbnail for {image_path}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _update_grid_item(self, index: int):
        """Actualiza un item específico del grid"""
        if 0 <= index < self.list_store.get_n_items():
            self.list_store.items_changed(index, 1, 1)
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Formatea el tamaño del archivo"""
        
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def _update_status_label(self):
        """Actualiza el label de status"""
        
        if self.status_label:
            total_images = len(self.images)
            selected_count = len(self.selected_images)
            self.status_label.set_text(f"{total_images} imágenes disponibles - {selected_count} seleccionadas")
    
    def _on_select_all(self, button):
        """Selecciona todas las imágenes - CORREGIDO"""
        
        print("[DEBUG] Select all clicked")
        
        # *** ACTUALIZAR DATOS ***
        for image_info in self.images:
            image_info.selected = True
            self.selected_images.add(image_info.href)
        
        # *** ACTUALIZAR CHECKBOXES VISIBLES ***
        for checkbox in self.checkbox_refs:
            if checkbox and checkbox.get_parent():  # Verificar que sigue existiendo
                checkbox.set_active(True)
        
        # *** ACTUALIZAR STATUS Y BOTÓN ***
        self._update_status_label()
        self.accept_button.set_sensitive(True)
        
        print(f"[DEBUG] Selected images: {len(self.selected_images)}")
    
    def _on_select_none(self, button):
        """Deselecciona todas las imágenes - CORREGIDO"""
        
        print("[DEBUG] Select none clicked")
        
        # *** ACTUALIZAR DATOS ***
        for image_info in self.images:
            image_info.selected = False
        
        self.selected_images.clear()
        
        # *** ACTUALIZAR CHECKBOXES VISIBLES ***
        for checkbox in self.checkbox_refs:
            if checkbox and checkbox.get_parent():  # Verificar que sigue existiendo
                checkbox.set_active(False)
        
        # *** ACTUALIZAR STATUS Y BOTÓN ***
        self._update_status_label()
        self.accept_button.set_sensitive(False)
        
        print(f"[DEBUG] Selected images: {len(self.selected_images)}")
    
    def _on_cancel_clicked(self, button):
        """Maneja el clic del botón cancelar"""
        self.dialog.destroy()
    
    def _on_accept_clicked(self, button):
        """Maneja el clic del botón aceptar e inserta las imágenes"""
        
        if not self.selected_images:
            self.main_window.show_error("No hay imágenes seleccionadas")
            return
        
        try:
            # Insertar etiquetas <img> en el editor
            self._insert_image_tags()
            
            # Mostrar confirmación
            count = len(self.selected_images)
            self.main_window.show_info(f"{count} imagen{'es' if count != 1 else ''} insertada{'s' if count != 1 else ''}")
            
            # Cerrar diálogo
            self.dialog.destroy()
            
        except Exception as e:
            self.main_window.show_error(f"Error insertando imágenes: {e}")
    
    def _insert_image_tags(self):
        """Inserta las etiquetas <img> en el editor"""
        
        if not self.main_window.current_resource:
            raise Exception("No hay documento abierto en el editor")
        
        # Obtener editor
        editor = self.main_window.central_editor
        buffer = editor.source_buffer
        
        # Obtener posición del cursor
        cursor_mark = buffer.get_insert()
        cursor_iter = buffer.get_iter_at_mark(cursor_mark)
        
        # Generar etiquetas HTML para imágenes seleccionadas
        html_tags = []
        
        for image_info in self.images:
            if image_info.href in self.selected_images:
                # Calcular ruta relativa desde el documento actual a la imagen
                relative_path = self._calculate_relative_path(
                    self.main_window.current_resource,
                    image_info.href
                )
                
                # Crear etiqueta img
                alt_text = Path(image_info.name).stem.replace('_', ' ').replace('-', ' ').title()
                img_tag = f'<img src="{relative_path}" alt="{alt_text}"/>'
                html_tags.append(img_tag)
        
        # Insertar todas las etiquetas
        if html_tags:
            combined_html = '\n'.join(html_tags)
            buffer.insert(cursor_iter, combined_html)
            
            # Actualizar preview si es necesario
            if hasattr(editor, '_update_preview_after_edit'):
                editor._update_preview_after_edit()
    
    def _calculate_relative_path(self, from_href: str, to_href: str) -> str:
        """Calcula la ruta relativa desde un documento a una imagen"""
        
        try:
            from_path = Path(from_href)
            to_path = Path(to_href)
            
            # Usar posixpath para mantener separadores web
            from posixpath import relpath
            relative = relpath(to_path.as_posix(), start=from_path.parent.as_posix())
            
            return relative
            
        except Exception as e:
            print(f"Error calculating relative path: {e}")
            # Fallback: usar ruta original
            return to_href


# *** INTEGRACIÓN CON EL MENÚ CONTEXTUAL ***

def add_insert_image_option(dynamic_menu_instance):
    """Agrega opción de insertar imagen al menú contextual existente"""
    
    # Modificar el método _add_standard_html_elements para incluir insertar imagen
    original_method = dynamic_menu_instance._add_standard_html_elements
    
    def enhanced_add_standard_html_elements(menu):
        # Llamar al método original
        original_method(menu)
        
        # Agregar sección de inserción de contenido
        content_section = Gio.Menu()
        content_section.append("Insertar imagen(es)", "win.insert_images")
        menu.append_section("Insertar contenido", content_section)
        
        # Registrar acción si no existe
        if not dynamic_menu_instance.main_window.lookup_action("insert_images"):
            insert_action = Gio.SimpleAction.new("insert_images", None)
            insert_action.connect("activate", _on_insert_images_clicked, dynamic_menu_instance.main_window)
            dynamic_menu_instance.main_window.add_action(insert_action)
    
    # Reemplazar el método
    dynamic_menu_instance._add_standard_html_elements = enhanced_add_standard_html_elements

def _on_insert_images_clicked(action, param, main_window):
    """Maneja el clic en 'Insertar imagen(es)'"""
    
    dialog = ImageSelectorDialog(main_window)
    dialog.show_dialog()


# *** ALTERNATIVA: INTEGRACIÓN DIRECTA EN CENTRAL_EDITOR ***

def integrate_image_selector_with_editor(central_editor_instance):
    """Integra el selector de imágenes con el editor central"""
    
    # Agregar al menú contextual existente
    if hasattr(central_editor_instance, 'dynamic_css_menu'):
        add_insert_image_option(central_editor_instance.dynamic_css_menu)
    else:
        # Registrar acción directamente en el editor
        if not central_editor_instance.main_window.lookup_action("insert_images"):
            insert_action = Gio.SimpleAction.new("insert_images", None)
            insert_action.connect("activate", lambda a, p: ImageSelectorDialog(central_editor_instance.main_window).show_dialog())
            central_editor_instance.main_window.add_action(insert_action)