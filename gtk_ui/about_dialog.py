"""
ui/about_dialog.py
Diálogo About para mostrar información de la aplicación
"""
from . import *
from gi.repository import Gtk, Adw, GdkPixbuf, Gio
from pathlib import Path


class AboutDialog:
    """Maneja el diálogo About de la aplicación"""

    def __init__(self, main_window):
        self.main_window = main_window
        self._setup_dialog()

    def _setup_dialog(self):
        """Configura el diálogo About"""
        self.dialog = Adw.AboutWindow()
        self.dialog.set_transient_for(self.main_window)
        self.dialog.set_modal(True)

        # Información básica
        self.dialog.set_application_name("GutenAI")
        self.dialog.set_version("1.0.0")
        self.dialog.set_developer_name("GutenAI Team")

        # Intentar usar el icono instalado por setup.py
        self._setup_application_icon()

        # Descripción
        description = """Editor modular de EPUB con interfaz moderna.

GutenAI es un editor EPUB construido con Python, GTK4 y libadwaita. Proporciona una interfaz moderna para editar archivos de libros electrónicos con capacidades de vista previa en tiempo real y funciones de corrección de texto potenciadas por IA."""

        self.dialog.set_comments(description)

        # Información del proyecto
        self.dialog.set_website("https://github.com/gutenai/gutenai")

        # Licencia
        self.dialog.set_license_type(Gtk.License.GPL_3_0)

        # Copyright
        self.dialog.set_copyright("© 2024 GutenAI Team")

        # Desarrolladores
        developers = [
            "GutenAI Team",
            "Contribuidores de la comunidad"
        ]
        self.dialog.set_developers(developers)

        # Créditos adicionales (si el método existe)
        try:
            self.dialog.set_translator_credits("Traducido por la comunidad")
        except AttributeError:
            pass

        # Enlaces de soporte (si los métodos existen)
        try:
            self.dialog.add_link("Documentación", "https://docs.gutenai.org")
            self.dialog.add_link("Reportar errores", "https://github.com/gutenai/gutenai/issues")
            self.dialog.add_link("Discusiones", "https://github.com/gutenai/gutenai/discussions")
        except AttributeError:
            pass


    def _setup_application_icon(self):
        """Configura el icono de la aplicación con fallback"""
        try:
            # Verificar si el icono personalizado está instalado
            icon_theme = Gtk.IconTheme.get_for_display(self.main_window.get_display())

            if icon_theme.has_icon("gutenai"):
                self.dialog.set_application_icon("gutenai")
            else:
                # Fallback a icono del sistema
                self.dialog.set_application_icon("text-editor")

                # Mostrar aviso en consola
                print("⚠️  AVISO: Icono 'gutenai' no encontrado en el tema del sistema.")
                print("   Ejecute 'python setup.py install' para instalar los iconos.")

                # Mostrar toast en la interfaz
                self._show_icon_warning_toast()

        except Exception as e:
            print(f"Error configurando icono: {e}")
            self.dialog.set_application_icon("text-editor")

    def _show_icon_warning_toast(self):
        """Muestra un toast avisando sobre la falta del icono"""
        try:
            toast = Adw.Toast.new("Icono no instalado. Ejecute 'python setup.py install'")
            toast.set_timeout(5)  # 5 segundos

            # Intentar mostrar el toast en la ventana principal
            if hasattr(self.main_window, 'add_toast'):
                self.main_window.add_toast(toast)
            elif hasattr(self.main_window, 'get_content') and hasattr(self.main_window.get_content(), 'add_toast'):
                self.main_window.get_content().add_toast(toast)
            else:
                print("No se pudo mostrar el toast - método no disponible")

        except Exception as e:
            print(f"Error mostrando toast: {e}")

    def show(self):
        """Muestra el diálogo About"""
        self.dialog.present()

    def destroy(self):
        """Destruye el diálogo"""
        if hasattr(self, 'dialog'):
            self.dialog.destroy()