#!/usr/bin/env python3
"""
Guten.AI - EPUB Editor
Punto de entrada principal de la aplicación
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gdk', '4.0')

from gi.repository import Adw, Gtk, Gdk
import os
import sys
from pathlib import Path
    
# Agregar el directorio de la aplicación al path para imports
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

# Importar la ventana principal
from gtk_ui.main_window import GutenAIApplication 


def _check_display() -> bool:
    """
    Verifica que exista un backend gráfico disponible antes de arrancar Adwaita.
    Retorna True si hay display válido; en caso contrario imprime una advertencia.
    """
    # Gtk.init_check devuelve (bool, argv) en PyGObject >= 3.46 — mantenemos compatibilidad.
    init_ok = False
    try:
        init_result = Gtk.init_check()
        if isinstance(init_result, tuple):
            init_ok = bool(init_result[0])
        else:
            init_ok = bool(init_result)
    except Exception:
        init_ok = False

    display = Gdk.Display.get_default()
    has_display = init_ok and display is not None

    if not has_display:
        display = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
        msg_lines = [
            "No se pudo inicializar GTK: no hay servidor gráfico disponible.",
            "Asegúrate de ejecutar GutenAI dentro de una sesión con soporte para GTK4 (X11/Wayland).",
        ]
        if not display:
            msg_lines.append("Variables esperadas: DISPLAY (X11) o WAYLAND_DISPLAY (Wayland).")
        if not os.environ.get("XDG_RUNTIME_DIR"):
            msg_lines.append("También se espera XDG_RUNTIME_DIR apuntando al runtime de usuario.")
        print("\n".join(msg_lines), file=sys.stderr)
    return has_display


def main():
    """Función principal de la aplicación"""
    if not _check_display():
        return 1
    
    app = GutenAIApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
