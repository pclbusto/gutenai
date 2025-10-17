"""
gtk_ui/shortcuts_window.py
Ventana nativa de atajos de teclado usando XML y GtkBuilder
"""
from . import *
from gi.repository import Gtk, Adw, Gio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .main_window import GutenAIWindow


def show_shortcuts_window(parent_window: 'GutenAIWindow'):
    """Muestra la ventana de atajos usando XML y GtkBuilder"""
    builder = Gtk.Builder()

    # XML para la ventana de atajos con todos los grupos actualizados
    shortcuts_xml = """<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <object class="GtkShortcutsWindow" id="shortcuts_window">
    <property name="modal">1</property>
    <child>
      <object class="GtkShortcutsSection">
        <property name="visible">1</property>
        <property name="section-name">shortcuts</property>
        <property name="title">Atajos de teclado</property>

        <!-- Grupo de Archivo -->
        <child>
          <object class="GtkShortcutsGroup">
            <property name="visible">1</property>
            <property name="title">Archivo</property>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;o</property>
                <property name="title">Abrir EPUB</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;&lt;Shift&gt;o</property>
                <property name="title">Abrir carpeta proyecto</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;n</property>
                <property name="title">Nuevo proyecto</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;s</property>
                <property name="title">Guardar cambios</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;&lt;Shift&gt;e</property>
                <property name="title">Exportar EPUB</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;q</property>
                <property name="title">Salir</property>
              </object>
            </child>

          </object>
        </child>

        <!-- Grupo de Edición -->
        <child>
          <object class="GtkShortcutsGroup">
            <property name="visible">1</property>
            <property name="title">Edición</property>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;z</property>
                <property name="title">Deshacer</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;y</property>
                <property name="title">Rehacer</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;x</property>
                <property name="title">Cortar</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;c</property>
                <property name="title">Copiar</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;v</property>
                <property name="title">Pegar</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;a</property>
                <property name="title">Seleccionar todo</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;f</property>
                <property name="title">Buscar</property>
              </object>
            </child>

          </object>
        </child>

        <!-- Grupo de Formato HTML -->
        <child>
          <object class="GtkShortcutsGroup">
            <property name="visible">1</property>
            <property name="title">Formato HTML</property>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;p</property>
                <property name="title">Convertir a párrafo</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;1</property>
                <property name="title">Encabezado H1</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;2</property>
                <property name="title">Encabezado H2</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;3</property>
                <property name="title">Encabezado H3</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;&lt;Shift&gt;q</property>
                <property name="title">Cita (blockquote)</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;l</property>
                <property name="title">Vincular estilos CSS</property>
              </object>
            </child>

          </object>
        </child>

        <!-- Grupo de Navegación -->
        <child>
          <object class="GtkShortcutsGroup">
            <property name="visible">1</property>
            <property name="title">Navegación</property>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;&lt;Shift&gt;1</property>
                <property name="title">Mostrar/ocultar estructura</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;&lt;Shift&gt;2</property>
                <property name="title">Mostrar/ocultar previsualización</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">F11</property>
                <property name="title">Previsualización pantalla completa</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;r</property>
                <property name="title">Recargar previsualización</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;g</property>
                <property name="title">Generar navegación (TOC)</property>
              </object>
            </child>

          </object>
        </child>

        <!-- Grupo de Recursos -->
        <child>
          <object class="GtkShortcutsGroup">
            <property name="visible">1</property>
            <property name="title">Recursos</property>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;&lt;Shift&gt;n</property>
                <property name="title">Crear nuevo documento</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;&lt;Shift&gt;s</property>
                <property name="title">Crear nuevo CSS</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;&lt;Shift&gt;m</property>
                <property name="title">Importar imagen</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;&lt;Shift&gt;t</property>
                <property name="title">Importar fuente</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">Delete</property>
                <property name="title">Eliminar recurso seleccionado</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">F2</property>
                <property name="title">Renombrar recurso</property>
              </object>
            </child>

          </object>
        </child>

        <!-- Grupo de IA y Corrección -->
        <child>
          <object class="GtkShortcutsGroup">
            <property name="visible">1</property>
            <property name="title">IA y Corrección</property>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;&lt;Shift&gt;f7</property>
                <property name="title">Corrector IA</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;&lt;Alt&gt;c</property>
                <property name="title">Corrección rápida (sin asignar)</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;&lt;Alt&gt;s</property>
                <property name="title">Sugerencias (sin asignar)</property>
              </object>
            </child>

          </object>
        </child>

        <!-- Grupo de Ayuda -->
        <child>
          <object class="GtkShortcutsGroup">
            <property name="visible">1</property>
            <property name="title">Ayuda</property>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">F1</property>
                <property name="title">Mostrar atajos de teclado</property>
              </object>
            </child>

            <child>
              <object class="GtkShortcutsShortcut">
                <property name="visible">1</property>
                <property name="accelerator">&lt;Ctrl&gt;&lt;Shift&gt;p</property>
                <property name="title">Preferencias</property>
              </object>
            </child>

          </object>
        </child>

      </object>
    </child>
  </object>
</interface>"""

    try:
        builder.add_from_string(shortcuts_xml)
        shortcuts_window = builder.get_object("shortcuts_window")

        if shortcuts_window:
            shortcuts_window.set_transient_for(parent_window)
            shortcuts_window.present()
            return shortcuts_window
        else:
            print("Error: No se pudo obtener shortcuts_window del builder")
            return None

    except Exception as e:
        print(f"Error creando ventana de atajos XML: {e}")
        return None