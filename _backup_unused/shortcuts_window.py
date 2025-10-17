#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
import sys

def create_shortcuts_window(self):
    """Crear ventana de atajos de teclado"""
    builder = Gtk.Builder()
    
    # Definir XML para la ventana de atajos
    shortcuts_xml = """<?xml version="1.0" encoding="UTF-8"?>
<interface>
<object class="GtkShortcutsWindow" id="shortcuts_window">
<property name="modal">1</property>
<child>
    <object class="GtkShortcutsSection">
    <property name="visible">1</property>
    <property name="section-name">general</property>
    <property name="title" translatable="yes">General</property>
    <child>
        <object class="GtkShortcutsGroup">
        <property name="visible">1</property>
        <property name="title" translatable="yes">Archivo</property>
        <child>
            <object class="GtkShortcutsShortcut">
            <property name="visible">1</property>
            <property name="title" translatable="yes">Abrir EPUB</property>
            <property name="accelerator">&lt;Ctrl&gt;o</property>
            </object>
        </child>
        <child>
            <object class="GtkShortcutsShortcut">
            <property name="visible">1</property>
            <property name="title" translatable="yes">Guardar cambios</property>
            <property name="accelerator">&lt;Ctrl&gt;s</property>
            </object>
        </child>
        <child>
            <object class="GtkShortcutsShortcut">
            <property name="visible">1</property>
            <property name="title" translatable="yes">Salir</property>
            <property name="accelerator">&lt;Ctrl&gt;q</property>
            </object>
        </child>
        </object>
    </child>
    <child>
        <object class="GtkShortcutsGroup">
        <property name="visible">1</property>
        <property name="title" translatable="yes">Vista</property>
        <child>
            <object class="GtkShortcutsShortcut">
            <property name="visible">1</property>
            <property name="title" translatable="yes">Mostrar/Ocultar sidebar izquierdo</property>
            <property name="accelerator">F9</property>
            </object>
        </child>
        <child>
            <object class="GtkShortcutsShortcut">
            <property name="visible">1</property>
            <property name="title" translatable="yes">Mostrar/Ocultar previsualización</property>
            <property name="accelerator">&lt;Ctrl&gt;p</property>
            </object>
        </child>
        <child>
            <object class="GtkShortcutsShortcut">
            <property name="visible">1</property>
            <property name="title" translatable="yes">Previsualización en ventana separada</property>
            <property name="accelerator">&lt;Ctrl&gt;&lt;Shift&gt;p</property>
            </object>
        </child>
        </object>
    </child>
    <child>
        <object class="GtkShortcutsGroup">
        <property name="visible">1</property>
        <property name="title" translatable="yes">Edición</property>
        <child>
            <object class="GtkShortcutsShortcut">
            <property name="visible">1</property>
            <property name="title" translatable="yes">Deshacer</property>
            <property name="accelerator">&lt;Ctrl&gt;z</property>
            </object>
        </child>
        <child>
            <object class="GtkShortcutsShortcut">
            <property name="visible">1</property>
            <property name="title" translatable="yes">Rehacer</property>
            <property name="accelerator">&lt;Ctrl&gt;&lt;Shift&gt;z</property>
            </object>
        </child>
        <child>
            <object class="GtkShortcutsShortcut">
            <property name="visible">1</property>
            <property name="title" translatable="yes">Buscar</property>
            <property name="accelerator">&lt;Ctrl&gt;f</property>
            </object>
        </child>
        <child>
            <object class="GtkShortcutsShortcut">
            <property name="visible">1</property>
            <property name="title" translatable="yes">Buscar y reemplazar</property>
            <property name="accelerator">&lt;Ctrl&gt;h</property>
            </object>
        </child>
        </object>
    </child>
    <child>
        <object class="GtkShortcutsGroup">
        <property name="visible">1</property>
        <property name="title" translatable="yes">Ayuda</property>
        <child>
            <object class="GtkShortcutsShortcut">
            <property name="visible">1</property>
            <property name="title" translatable="yes">Atajos de teclado</property>
            <property name="accelerator">&lt;Ctrl&gt;question</property>
            </object>
        </child>
        </object>
    </child>
    </object>
</child>
</object>
</interface>"""
    
    builder.add_from_string(shortcuts_xml)
    shortcuts_window = builder.get_object("shortcuts_window")
    
    return shortcuts_window

if __name__ == "__main__":

    class Dummy:
        pass

    dummy = Dummy()
    window = create_shortcuts_window(dummy)
    window.set_title("Atajos de teclado")
    window.set_default_size(600, 400)
    window.connect("close-request", Gtk.main_quit)
    window.show()

    Gtk.main()