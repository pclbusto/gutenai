"""
ui/__init__.py
Configuración común de versiones de gi para todos los módulos UI
"""

import gi

# Establecer versiones requeridas ANTES de cualquier import
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('GtkSource', '5')
gi.require_version('WebKit', '6.0')