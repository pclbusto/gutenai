#!/usr/bin/env python3
"""
Guten.AI - EPUB Editor
Punto de entrada principal de la aplicación
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw
import sys
from pathlib import Path

# Agregar el directorio de la aplicación al path para imports
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

# Importar la ventana principal
from gtk_ui.main_window import GutenAIApplication 

def main():
    """Función principal de la aplicación"""
    app = GutenAIApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)