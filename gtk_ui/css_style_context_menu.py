"""
ui/css_style_context_menu.py
Sistema de menú contextual dinámico basado en clases CSS disponibles
"""

import re
from gi.repository import Gtk, Gio, GLib, Gdk
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass

@dataclass
class CSSClass:
    """Representa una clase CSS extraída"""
    element: str  # 'p', 'h1', 'div', etc. o '*' para universal
    class_name: str  # nombre de la clase sin el punto
    full_selector: str  # selector completo original
    description: str = ""  # descripción opcional

class CSSStyleManager:
    """Maneja la extracción y organización de estilos CSS"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.cached_styles: Dict[str, List[CSSClass]] = {}
        self.last_cache_time: Dict[str, float] = {}
    
    def get_available_styles_for_document(self, document_href: str) -> Dict[str, List[CSSClass]]:
        """Obtiene estilos disponibles para un documento específico"""
        
        if not self.main_window.core:
            return {}
        
        try:
            # Obtener CSS vinculados al documento
            linked_css = self._get_linked_css_files(document_href)
            
            # Extraer clases de cada CSS
            all_styles = {}
            
            for css_href in linked_css:
                styles = self._extract_css_classes(css_href)
                
                # Organizar por elemento
                for style in styles:
                    if style.element not in all_styles:
                        all_styles[style.element] = []
                    all_styles[style.element].append(style)
            
            return all_styles
            
        except Exception as e:
            print(f"Error extracting CSS styles: {e}")
            return {}
    
    def _get_linked_css_files(self, document_href: str) -> List[str]:
        """Extrae archivos CSS vinculados a un documento HTML"""
        
        try:
            content = self.main_window.core.read_text(document_href)
            
            # Buscar <link rel="stylesheet"> 
            css_links = []
            pattern = r'<link[^>]+rel=[\'"]*stylesheet[\'"]*[^>]+href=[\'"]*([^"\']+)[\'"]*[^>]*>'
            
            matches = re.finditer(pattern, content, re.IGNORECASE)
            
            for match in matches:
                css_path = match.group(1)
                
                # Resolver ruta relativa
                doc_dir = Path(document_href).parent
                if css_path.startswith('../'):
                    # Ruta relativa hacia arriba
                    resolved_path = (doc_dir / css_path).as_posix()
                    css_links.append(resolved_path)
                else:
                    css_links.append(css_path)
            
            return css_links
            
        except Exception as e:
            print(f"Error finding linked CSS: {e}")
            return []
    
    def _extract_css_classes(self, css_href: str) -> List[CSSClass]:
        """Extrae clases CSS de un archivo"""
        
        # Verificar cache
        if css_href in self.cached_styles:
            css_file_path = self.main_window.core.opf_dir / css_href
            if css_file_path.exists():
                file_time = css_file_path.stat().st_mtime
                if css_href in self.last_cache_time and file_time <= self.last_cache_time[css_href]:
                    return self.cached_styles[css_href]
        
        try:
            css_content = self.main_window.core.read_text(css_href)
            classes = self._parse_css_content(css_content)
            
            # Actualizar cache
            self.cached_styles[css_href] = classes
            css_file_path = self.main_window.core.opf_dir / css_href
            if css_file_path.exists():
                self.last_cache_time[css_href] = css_file_path.stat().st_mtime
            
            return classes
            
        except Exception as e:
            print(f"Error reading CSS file {css_href}: {e}")
            return []
    
    def _parse_css_content(self, css_content: str) -> List[CSSClass]:
        """Parsea contenido CSS y extrae selectores con clases"""
        
        classes = []
        
        # Remover comentarios
        css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
        
        # Buscar selectores con clases
        # Patrones: p.clase, .clase, h1.clase, div.clase:hover, etc.
        patterns = [
            # Elemento con clase: p.clase, h1.titulo, etc.
            (r'([a-zA-Z][a-zA-Z0-9]*)\s*\.\s*([a-zA-Z][a-zA-Z0-9_-]*)', 'element_class'),
            # Clase universal: .clase
            (r'^\s*\.\s*([a-zA-Z][a-zA-Z0-9_-]*)', 'universal_class')
        ]
        
        # Extraer selectores (antes de las llaves)
        selector_blocks = re.findall(r'([^{}]+)\s*\{[^}]*\}', css_content, re.MULTILINE)
        
        for selector_block in selector_blocks:
            selectors = [s.strip() for s in selector_block.split(',')]
            
            for selector in selectors:
                selector = selector.strip()
                
                # Elemento con clase: p.destacado, h2.titulo
                element_class_match = re.search(r'^([a-zA-Z][a-zA-Z0-9]*)\s*\.\s*([a-zA-Z][a-zA-Z0-9_-]*)', selector)
                if element_class_match:
                    element = element_class_match.group(1)
                    class_name = element_class_match.group(2)
                    
                    classes.append(CSSClass(
                        element=element,
                        class_name=class_name,
                        full_selector=selector,
                        description=self._generate_class_description(element, class_name)
                    ))
                    continue
                
                # Clase universal: .destacado
                universal_class_match = re.search(r'^\s*\.\s*([a-zA-Z][a-zA-Z0-9_-]*)', selector)
                if universal_class_match:
                    class_name = universal_class_match.group(1)
                    
                    classes.append(CSSClass(
                        element='*',
                        class_name=class_name,
                        full_selector=selector,
                        description=self._generate_class_description('*', class_name)
                    ))
        
        # Eliminar duplicados
        unique_classes = {}
        for cls in classes:
            key = f"{cls.element}.{cls.class_name}"
            if key not in unique_classes:
                unique_classes[key] = cls
        
        return list(unique_classes.values())
    
    def _generate_class_description(self, element: str, class_name: str) -> str:
        """Genera descripción legible para una clase"""
        
        # Mapeo de nombres comunes
        descriptions = {
            'destacado': 'Texto destacado',
            'titulo': 'Título',
            'subtitulo': 'Subtítulo', 
            'centrado': 'Texto centrado',
            'derecha': 'Alineado a la derecha',
            'izquierda': 'Alineado a la izquierda',
            'negrita': 'Texto en negrita',
            'cursiva': 'Texto en cursiva',
            'subrayado': 'Texto subrayado',
            'pequeño': 'Texto pequeño',
            'grande': 'Texto grande',
            'codigo': 'Código',
            'cita': 'Cita o referencia',
            'nota': 'Nota al pie',
            'introduccion': 'Introducción',
            'conclusion': 'Conclusión'
        }
        
        desc = descriptions.get(class_name.lower(), class_name.replace('-', ' ').replace('_', ' ').title())
        
        if element != '*':
            return f"{element.upper()}: {desc}"
        else:
            return desc

class DynamicStyleContextMenu:
    """Menú contextual dinámico para aplicar estilos CSS"""
    
    def __init__(self, main_window, central_editor):
        self.main_window = main_window
        self.central_editor = central_editor
        self.style_manager = CSSStyleManager(main_window)
    
    def setup_context_menu(self):
        """Configura el menú contextual dinámico"""
        
        # Interceptar click derecho
        right_click = Gtk.GestureClick()
        right_click.set_button(3)
        right_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        
        def on_right_click(gesture, n_press, x, y):
            if n_press == 1:
                gesture.set_state(Gtk.EventSequenceState.CLAIMED)
                self._show_dynamic_context_menu(x, y)
                return True
            return False
        
        right_click.connect('pressed', on_right_click)
        self.central_editor.source_view.add_controller(right_click)
    
    def _show_dynamic_context_menu(self, x: float, y: float):
        """Muestra menú contextual con estilos CSS disponibles"""
        
        if not self.main_window.current_resource:
            return
        
        buffer = self.central_editor.source_buffer
        
        # Verificar si hay texto seleccionado
        has_selection = buffer.get_has_selection()
        selected_text = ""
        
        if has_selection:
            start, end = buffer.get_selection_bounds()
            selected_text = buffer.get_text(start, end, False)
        
        # Crear menú
        menu = Gio.Menu()

        # *** SECCIÓN DE FORMATO HTML (incluye listas) ***
        if has_selection:
            format_section = Gio.Menu()
            format_section.append("Párrafo <p>", "win.wrap_paragraph")
            format_section.append("Encabezado H1", "win.wrap_h1")
            format_section.append("Encabezado H2", "win.wrap_h2")
            format_section.append("Encabezado H3", "win.wrap_h3")
            format_section.append("Cita <blockquote>", "win.wrap_blockquote")
            format_section.append("Lista con viñetas <ul>", "win.wrap_unordered_list")
            format_section.append("Lista numerada <ol>", "win.wrap_ordered_list")
            format_section.append("Elemento de lista <li>", "win.wrap_list_item")
            menu.append_section("📝 Formato HTML", format_section)

        # Sección de edición básica
        if has_selection:
            edit_section = Gio.Menu()
            edit_section.append("Cortar", "text.cut")
            edit_section.append("Copiar", "text.copy")
            menu.append_section("Edición", edit_section)
        else:
            edit_section = Gio.Menu()
            edit_section.append("Pegar", "text.paste")
            edit_section.append("Seleccionar todo", "text.select-all")
            menu.append_section("Edición", edit_section)
        
        # Sección de estilos CSS dinámicos
        if has_selection:
            css_styles = self.style_manager.get_available_styles_for_document(
                self.main_window.current_resource
            )
            
            if css_styles:
                self._add_css_styles_to_menu(menu, css_styles, selected_text)
            else:
                # Fallback: elementos HTML básicos
                self._add_basic_html_elements(menu)
        
        # Mostrar popover con tamaño controlado
        popover = Gtk.PopoverMenu()
        popover.set_menu_model(menu)
        popover.set_parent(self.central_editor.source_view)

        # Configurar tamaño para evitar scrolls en GTK4
        popover.set_size_request(280, -1)  # Ancho fijo, alto automático
        popover.set_has_arrow(True)

        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        popover.set_pointing_to(rect)
        popover.popup()
    
    def _add_css_styles_to_menu(self, menu: Gio.Menu, css_styles: Dict[str, List[CSSClass]], selected_text: str):
        """Agrega estilos CSS organizados jerárquicamente al menú"""

        # *** ELEMENTOS HTML SIEMPRE DISPONIBLES ***
        # Mapeo de elementos a nombres de acciones correctos
        element_actions = {
            'p': 'wrap_paragraph',
            'h1': 'wrap_h1',
            'h2': 'wrap_h2',
            'h3': 'wrap_h3',
            'h4': 'wrap_h4',
            'h5': 'wrap_h5',
            'h6': 'wrap_h6',
            'blockquote': 'wrap_blockquote',
            'em': 'wrap_emphasis',
            'strong': 'wrap_strong',
            'code': 'wrap_code',
            'span': 'wrap_span'
        }

        all_basic_elements = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'em', 'strong', 'code', 'span']

        for element in all_basic_elements:
            element_name = self._get_element_display_name(element)
            action_name = element_actions.get(element, f'wrap_{element}')

            # Verificar si tiene variantes CSS
            variants = css_styles.get(element, [])

            if variants:
                # *** CREAR SUBMENÚ CON VARIANTES ***
                element_submenu = Gio.Menu()

                # SIEMPRE incluir opción normal primero
                element_submenu.append("Normal", f"win.{action_name}")

                # Agregar variantes con clases CSS
                for css_class in variants:
                    css_action_name = f"apply_css_class_{css_class.element}_{css_class.class_name}"
                    self._register_css_action(css_action_name, css_class, selected_text)

                    # Título descriptivo más corto
                    variant_title = css_class.description or css_class.class_name.replace('-', ' ').title()
                    element_submenu.append(variant_title, f"win.{css_action_name}")

                # Agregar submenú al menú principal con icono
                menu.append_submenu(f"📝 {element_name}", element_submenu)
            else:
                # *** ELEMENTO SIN VARIANTES - DIRECTO ***
                # Solo agregar a sección básica al final
                pass

        # *** ELEMENTOS BÁSICOS SIN VARIANTES ***
        elements_with_variants = set(css_styles.keys()) - {'*'}
        basic_elements_only = [elem for elem in all_basic_elements if elem not in elements_with_variants]

        if basic_elements_only:
            basic_section = Gio.Menu()
            for element in basic_elements_only:
                element_name = self._get_element_display_name(element)
                action_name = element_actions.get(element, f'wrap_{element}')
                basic_section.append(element_name, f"win.{action_name}")
            menu.append_section("📄 Básicos", basic_section)

        # *** CLASES UNIVERSALES (si existen) ***
        if '*' in css_styles and css_styles['*']:
            universal_section = Gio.Menu()
            for css_class in css_styles['*']:
                action_name = f"apply_css_class_{css_class.element}_{css_class.class_name}"
                self._register_css_action(action_name, css_class, selected_text)

                variant_title = css_class.description or css_class.class_name.replace('-', ' ').title()
                universal_section.append(variant_title, f"win.{action_name}")

            menu.append_section("🎨 Universales", universal_section)

        # *** SECCIÓN DE INSERTAR CONTENIDO ***
        content_section = Gio.Menu()
        content_section.append("📷 Insertar imagen(es)", "win.insert_images")
        menu.append_section("➕ Insertar", content_section)

    def _organize_html_elements_with_variants(self, css_styles: Dict[str, List[CSSClass]]) -> Dict[str, List[CSSClass]]:
        """Organiza elementos HTML agrupando sus variantes"""
        # Ya viene organizado por elemento, solo filtrar elementos válidos
        valid_elements = {}
        for element, classes in css_styles.items():
            if element != '*' and classes:  # Excluir clases universales
                valid_elements[element] = classes
        return valid_elements

    def _get_element_display_name(self, element: str) -> str:
        """Obtiene nombre legible para mostrar del elemento HTML"""
        display_names = {
            'p': 'Párrafo',
            'h1': 'Encabezado H1',
            'h2': 'Encabezado H2',
            'h3': 'Encabezado H3',
            'h4': 'Encabezado H4',
            'h5': 'Encabezado H5',
            'h6': 'Encabezado H6',
            'blockquote': 'Cita',
            'div': 'División',
            'span': 'Span',
            'em': 'Énfasis',
            'strong': 'Fuerte',
            'code': 'Código',
            'ul': 'Lista desordenada',
            'ol': 'Lista ordenada',
            'li': 'Elemento de lista'
        }
        return display_names.get(element, element.upper())

    def _get_basic_html_elements_without_variants(self, html_elements: Dict[str, List[CSSClass]]) -> List[str]:
        """Obtiene elementos HTML básicos que no tienen variantes CSS"""
        all_basic_elements = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'em', 'strong', 'code', 'span']
        elements_with_variants = set(html_elements.keys())
        return [elem for elem in all_basic_elements if elem not in elements_with_variants]
    
    def _add_basic_html_elements(self, menu: Gio.Menu):
        """Agrega elementos HTML básicos cuando no hay CSS disponible"""
        self._add_standard_html_elements(menu)
    
    def _add_standard_html_elements(self, menu: Gio.Menu):
        """Agrega elementos HTML estándar SIEMPRE disponibles"""
        
        # Elementos estructurales básicos
        structure_section = Gio.Menu()
        structure_section.append("Párrafo <p>", "win.wrap_paragraph")
        structure_section.append("Encabezado H1", "win.wrap_h1")
        structure_section.append("Encabezado H2", "win.wrap_h2") 
        structure_section.append("Encabezado H3", "win.wrap_h3")
        structure_section.append("Encabezado H4", "win.wrap_h4")
        structure_section.append("Cita <blockquote>", "win.wrap_blockquote")
        
        menu.append_section("Estructura HTML", structure_section)
        
        # Elementos de formato inline
        inline_section = Gio.Menu()
        inline_section.append("Énfasis <em>", "win.wrap_emphasis")
        inline_section.append("Fuerte <strong>", "win.wrap_strong")
        inline_section.append("Código <code>", "win.wrap_code")
        inline_section.append("Span genérico <span>", "win.wrap_span")
        
        menu.append_section("Formato inline", inline_section)
        
        # Registrar acciones estándar si no existen
        self._ensure_standard_actions_registered()
    
    def _ensure_standard_actions_registered(self):
        """Asegura que las acciones HTML estándar estén registradas"""
        
        standard_actions = {
            'wrap_h4': ('h4', 'Encabezado H4'),
            'wrap_emphasis': ('em', 'Énfasis'),
            'wrap_strong': ('strong', 'Fuerte'), 
            'wrap_code': ('code', 'Código'),
            'wrap_span': ('span', 'Span genérico')
        }
        
        for action_name, (tag, description) in standard_actions.items():
            if not self.main_window.lookup_action(action_name):
                action = Gio.SimpleAction.new(action_name, None)
                action.connect("activate", self._on_wrap_standard_element, tag, description)
                self.main_window.add_action(action)
    
    def _on_wrap_standard_element(self, action, param, tag: str, description: str):
        """Aplica elemento HTML estándar al texto seleccionado"""
        
        buffer = self.central_editor.source_buffer
        
        if not buffer.get_has_selection():
            self.main_window.show_error("Selecciona texto para aplicar formato")
            return
        
        # Obtener selección
        start, end = buffer.get_selection_bounds()
        selected_text = buffer.get_text(start, end, False)
        
        if not selected_text.strip():
            return
        
        # Crear texto envuelto
        wrapped_text = f"<{tag}>{selected_text}</{tag}>"
        
        # Reemplazar selección
        buffer.delete(start, end)
        buffer.insert(start, wrapped_text)
        
        # Mostrar confirmación
        self.main_window.show_info(f"Aplicado formato: {description}")
        
        # Actualizar preview
        self._update_preview_after_edit()
    
    def _register_css_action(self, action_name: str, css_class: CSSClass, selected_text: str):
        """Registra acción temporal para aplicar clase CSS"""
        
        # Evitar registros duplicados
        if self.main_window.lookup_action(action_name):
            return
        
        action = Gio.SimpleAction.new(action_name, None)
        action.connect("activate", self._on_apply_css_class, css_class, selected_text)
        self.main_window.add_action(action)
        
        # Programar limpieza de la acción después de un tiempo
        GLib.timeout_add_seconds(30, lambda: self._cleanup_action(action_name))
    
    def _on_apply_css_class(self, action, param, css_class: CSSClass, original_selected_text: str):
        """Aplica clase CSS al texto seleccionado"""
        
        buffer = self.central_editor.source_buffer
        
        if not buffer.get_has_selection():
            self.main_window.show_error("No hay texto seleccionado")
            return
        
        # Obtener selección actual (por si cambió)
        start, end = buffer.get_selection_bounds()
        selected_text = buffer.get_text(start, end, False)
        
        # Determinar elemento HTML a usar
        if css_class.element == '*':
            # Clase universal - usar span por defecto
            wrapped_text = f'<span class="{css_class.class_name}">{selected_text}</span>'
        else:
            # Elemento específico
            wrapped_text = f'<{css_class.element} class="{css_class.class_name}">{selected_text}</{css_class.element}>'
        
        # Reemplazar selección
        buffer.delete(start, end)
        buffer.insert(start, wrapped_text)
        
        # Mostrar confirmación
        self.main_window.show_info(f"Aplicado estilo: {css_class.element}.{css_class.class_name}")
        
        # Actualizar preview
        self._update_preview_after_edit()
    
    def _cleanup_action(self, action_name: str):
        """Limpia acción temporal"""
        try:
            action = self.main_window.lookup_action(action_name)
            if action:
                self.main_window.remove_action(action_name)
        except:
            pass
        return False  # No repetir timeout
    
    def _update_preview_after_edit(self):
        """Actualiza preview después de aplicar estilo"""
        if hasattr(self.central_editor, '_update_preview_after_edit'):
            self.central_editor._update_preview_after_edit()

# *** INTEGRACIÓN CON CENTRAL_EDITOR ***
def integrate_dynamic_css_menu(central_editor_instance):
    """Integra el sistema de menú dinámico CSS con el editor central"""
    
    # Crear instancia del menú dinámico
    dynamic_menu = DynamicStyleContextMenu(
        central_editor_instance.main_window,
        central_editor_instance
    )
    
    # Configurar menú contextual
    dynamic_menu.setup_context_menu()
    
    # Guardar referencia en el editor
    central_editor_instance.dynamic_css_menu = dynamic_menu
    
    return dynamic_menu

# *** MODIFICACIÓN PARA CENTRAL_EDITOR ***
"""
En central_editor.py, en el método _setup_widget():

# Reemplazar la línea de _setup_context_menu() con:
from .css_style_context_menu import integrate_dynamic_css_menu
integrate_dynamic_css_menu(self)
"""