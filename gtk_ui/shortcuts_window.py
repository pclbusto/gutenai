"""
gtk_ui/shortcuts_window.py
Ventana nativa de atajos de teclado usando XML y GtkBuilder
"""
from . import *
from gi.repository import Gtk, Adw, Gio
from typing import TYPE_CHECKING
import os
from pathlib import Path

if TYPE_CHECKING:
    from .main_window import GutenAIWindow


def create_shortcuts_window(parent_window: 'GutenAIWindow') -> Gtk.ShortcutsWindow:
    """Crea y devuelve la ventana de atajos usando el archivo XML de recursos"""
    builder = Gtk.Builder()

    # Ruta al archivo XML de atajos
    current_dir = Path(__file__).parent
    shortcuts_xml_path = current_dir / "resources" / "shortcuts.xml"
    
    print(f"[DEBUG] Buscando shortcuts.xml en: {shortcuts_xml_path}")
    
    if not shortcuts_xml_path.exists():
        print(f"Error: No se encuentra el archivo de atajos: {shortcuts_xml_path}")
        return None

    try:
        builder.add_from_file(str(shortcuts_xml_path))
        shortcuts_window = builder.get_object("shortcuts_window")
        
        print(f"[DEBUG] shortcuts_window obtenido: {shortcuts_window}")

        if shortcuts_window:
            shortcuts_window.set_transient_for(parent_window)
            return shortcuts_window
        else:
            print("Error: No se pudo obtener shortcuts_window del builder")
            return None

    except Exception as e:
        print(f"Error creando ventana de atajos XML: {e}")
        return None