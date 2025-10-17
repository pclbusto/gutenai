"""
GutenAI - Diálogo de preferencias
Configuración de API keys, editor y otras opciones
"""

from gi.repository import Gtk, Adw
from typing import TYPE_CHECKING

from .settings_manager import get_settings

if TYPE_CHECKING:
    from .main_window import GutenAIWindow


class PreferencesDialog(Adw.PreferencesWindow):
    """Diálogo de preferencias de GutenAI"""

    def __init__(self, parent_window: 'GutenAIWindow'):
        super().__init__()

        self.parent_window = parent_window
        self.settings = get_settings()

        self.set_title("Preferencias de GutenAI")
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_default_size(600, 500)

        self._setup_pages()
        self._load_current_settings()

    def _setup_pages(self):
        """Configura las páginas de preferencias"""

        # Página de IA
        self._create_ai_page()

        # Página del Editor
        self._create_editor_page()

        # Página de Interfaz
        self._create_ui_page()

    def _create_ai_page(self):
        """Crea la página de configuración de IA"""

        ai_page = Adw.PreferencesPage()
        ai_page.set_title("Inteligencia Artificial")
        ai_page.set_icon_name("applications-science-symbolic")

        # Grupo de Gemini
        gemini_group = Adw.PreferencesGroup()
        gemini_group.set_title("Google Gemini 1.5")
        gemini_group.set_description("Configuración para corrección ortográfica y gramatical con IA")

        # Switch para habilitar/deshabilitar Gemini
        self.gemini_enabled_row = Adw.SwitchRow()
        self.gemini_enabled_row.set_title("Habilitar corrección con IA")
        self.gemini_enabled_row.set_subtitle("Usar Gemini 1.5 para corrección avanzada")
        self.gemini_enabled_row.connect('notify::active', self._on_gemini_enabled_changed)

        # Entry para API Key
        self.api_key_row = Adw.PasswordEntryRow()
        self.api_key_row.set_title("API Key de Gemini")
        self.api_key_row.set_text(self.settings.get_gemini_api_key() or "")
        self.api_key_row.connect('notify::text', self._on_api_key_changed)

        # Botón para obtener API Key
        get_key_btn = Gtk.Button()
        get_key_btn.set_icon_name("web-browser-symbolic")
        get_key_btn.set_tooltip_text("Obtener API Key")
        get_key_btn.set_valign(Gtk.Align.CENTER)
        get_key_btn.connect('clicked', self._on_get_api_key_clicked)
        self.api_key_row.add_suffix(get_key_btn)

        # Información de uso
        self.usage_info_row = Adw.ActionRow()
        self.usage_info_row.set_title("Límite de uso")
        self.usage_info_row.set_subtitle("15 consultas por hora (gratis)")

        # Idioma de corrección
        self.language_row = Adw.ComboRow()
        self.language_row.set_title("Idioma de corrección")

        language_model = Gtk.StringList()
        languages = [
            "Español (es)",
            "English (en)",
            "Français (fr)",
            "Deutsch (de)",
            "Italiano (it)",
            "Português (pt)"
        ]
        for lang in languages:
            language_model.append(lang)

        self.language_row.set_model(language_model)
        self.language_row.set_selected(0)  # Español por defecto
        self.language_row.connect('notify::selected', self._on_language_changed)

        gemini_group.add(self.gemini_enabled_row)
        gemini_group.add(self.api_key_row)
        gemini_group.add(self.usage_info_row)
        gemini_group.add(self.language_row)

        ai_page.add(gemini_group)
        self.add(ai_page)

    def _create_editor_page(self):
        """Crea la página de configuración del editor"""

        editor_page = Adw.PreferencesPage()
        editor_page.set_title("Editor")
        editor_page.set_icon_name("applications-utilities-symbolic")

        # Grupo de apariencia
        appearance_group = Adw.PreferencesGroup()
        appearance_group.set_title("Apariencia")

        # Tema del editor
        self.theme_row = Adw.ComboRow()
        self.theme_row.set_title("Tema del editor")

        theme_model = Gtk.StringList()
        themes = ["Adwaita", "Adwaita-dark", "Classic", "Cobalt", "Kate", "Oblivion"]
        for theme in themes:
            theme_model.append(theme)

        self.theme_row.set_model(theme_model)
        self.theme_row.connect('notify::selected', self._on_theme_changed)

        # Mostrar números de línea
        self.line_numbers_row = Adw.SwitchRow()
        self.line_numbers_row.set_title("Mostrar números de línea")
        self.line_numbers_row.connect('notify::active', self._on_line_numbers_changed)

        # Ajuste de línea
        self.word_wrap_row = Adw.SwitchRow()
        self.word_wrap_row.set_title("Ajuste de línea")
        self.word_wrap_row.set_subtitle("Ajustar líneas largas automáticamente")
        self.word_wrap_row.connect('notify::active', self._on_word_wrap_changed)

        appearance_group.add(self.theme_row)
        appearance_group.add(self.line_numbers_row)
        appearance_group.add(self.word_wrap_row)

        # Grupo de comportamiento
        behavior_group = Adw.PreferencesGroup()
        behavior_group.set_title("Comportamiento")

        # Auto-guardado
        self.auto_save_row = Adw.SwitchRow()
        self.auto_save_row.set_title("Auto-guardado")
        self.auto_save_row.set_subtitle("Guardar automáticamente los cambios")
        self.auto_save_row.connect('notify::active', self._on_auto_save_changed)

        # Delay de auto-guardado
        self.auto_save_delay_row = Adw.SpinRow()
        self.auto_save_delay_row.set_title("Retraso de auto-guardado")
        self.auto_save_delay_row.set_subtitle("Tiempo en milisegundos")

        adjustment = Gtk.Adjustment()
        adjustment.set_lower(500)
        adjustment.set_upper(5000)
        adjustment.set_step_increment(100)
        adjustment.set_page_increment(500)
        self.auto_save_delay_row.set_adjustment(adjustment)
        self.auto_save_delay_row.connect('notify::value', self._on_auto_save_delay_changed)

        behavior_group.add(self.auto_save_row)
        behavior_group.add(self.auto_save_delay_row)

        editor_page.add(appearance_group)
        editor_page.add(behavior_group)
        self.add(editor_page)

    def _create_ui_page(self):
        """Crea la página de configuración de interfaz"""

        ui_page = Adw.PreferencesPage()
        ui_page.set_title("Interfaz")
        ui_page.set_icon_name("preferences-desktop-symbolic")

        # Grupo de paneles
        panels_group = Adw.PreferencesGroup()
        panels_group.set_title("Paneles")

        # Sidebar izquierdo visible por defecto
        self.left_sidebar_row = Adw.SwitchRow()
        self.left_sidebar_row.set_title("Mostrar estructura por defecto")
        self.left_sidebar_row.set_subtitle("Panel izquierdo visible al abrir")
        self.left_sidebar_row.connect('notify::active', self._on_left_sidebar_changed)

        # Sidebar derecho visible por defecto
        self.right_sidebar_row = Adw.SwitchRow()
        self.right_sidebar_row.set_title("Mostrar previsualización por defecto")
        self.right_sidebar_row.set_subtitle("Panel derecho visible al abrir")
        self.right_sidebar_row.connect('notify::active', self._on_right_sidebar_changed)

        panels_group.add(self.left_sidebar_row)
        panels_group.add(self.right_sidebar_row)

        # Grupo de archivos recientes
        recent_group = Adw.PreferencesGroup()
        recent_group.set_title("Archivos Recientes")

        # Botón para limpiar archivos recientes
        clear_recent_row = Adw.ActionRow()
        clear_recent_row.set_title("Limpiar archivos recientes")
        clear_recent_row.set_subtitle("Borrar lista de archivos abiertos recientemente")

        clear_btn = Gtk.Button()
        clear_btn.set_label("Limpiar")
        clear_btn.set_valign(Gtk.Align.CENTER)
        clear_btn.set_css_classes(["destructive-action"])
        clear_btn.connect('clicked', self._on_clear_recent_clicked)
        clear_recent_row.add_suffix(clear_btn)

        recent_group.add(clear_recent_row)

        ui_page.add(panels_group)
        ui_page.add(recent_group)
        self.add(ui_page)

    def _load_current_settings(self):
        """Carga la configuración actual en los controles"""

        # Configuración de Gemini
        self.gemini_enabled_row.set_active(self.settings.get("gemini.enabled", True))

        # Configuración del editor
        editor_settings = self.settings.get_editor_settings()

        # Tema
        current_theme = editor_settings.get("theme", "Adwaita-dark")
        theme_names = ["Adwaita", "Adwaita-dark", "Classic", "Cobalt", "Kate", "Oblivion"]
        if current_theme in theme_names:
            self.theme_row.set_selected(theme_names.index(current_theme))

        # Otros ajustes del editor
        self.line_numbers_row.set_active(editor_settings.get("show_line_numbers", True))
        self.word_wrap_row.set_active(editor_settings.get("word_wrap", True))
        self.auto_save_row.set_active(editor_settings.get("auto_save", True))
        self.auto_save_delay_row.set_value(editor_settings.get("auto_save_delay", 1500))

        # Configuración de UI
        ui_settings = self.settings.get_ui_settings()
        self.left_sidebar_row.set_active(ui_settings.get("sidebar_left_visible", True))
        self.right_sidebar_row.set_active(ui_settings.get("sidebar_right_visible", True))

    # Callbacks de cambios
    def _on_gemini_enabled_changed(self, switch, param):
        """Callback cuando se habilita/deshabilita Gemini"""
        enabled = switch.get_active()
        self.settings.set("gemini.enabled", enabled)
        self.settings.save_settings()

    def _on_api_key_changed(self, entry, param):
        """Callback cuando cambia la API key"""
        api_key = entry.get_text()
        self.settings.set_gemini_api_key(api_key)

    def _on_get_api_key_clicked(self, button):
        """Abre la página para obtener API key"""
        import webbrowser
        webbrowser.open("https://aistudio.google.com/app/apikey")

    def _on_language_changed(self, combo, param):
        """Callback cuando cambia el idioma"""
        selected = combo.get_selected()
        languages = ["es", "en", "fr", "de", "it", "pt"]
        if selected < len(languages):
            self.settings.set("gemini.language", languages[selected])
            self.settings.save_settings()

    def _on_theme_changed(self, combo, param):
        """Callback cuando cambia el tema"""
        selected = combo.get_selected()
        themes = ["Adwaita", "Adwaita-dark", "Classic", "Cobalt", "Kate", "Oblivion"]
        if selected < len(themes):
            self.settings.set("editor.theme", themes[selected])
            self.settings.save_settings()

    def _on_line_numbers_changed(self, switch, param):
        """Callback para números de línea"""
        self.settings.set("editor.show_line_numbers", switch.get_active())
        self.settings.save_settings()

    def _on_word_wrap_changed(self, switch, param):
        """Callback para ajuste de línea"""
        self.settings.set("editor.word_wrap", switch.get_active())
        self.settings.save_settings()

    def _on_auto_save_changed(self, switch, param):
        """Callback para auto-guardado"""
        self.settings.set("editor.auto_save", switch.get_active())
        self.settings.save_settings()

    def _on_auto_save_delay_changed(self, spin, param):
        """Callback para delay de auto-guardado"""
        self.settings.set("editor.auto_save_delay", int(spin.get_value()))
        self.settings.save_settings()

    def _on_left_sidebar_changed(self, switch, param):
        """Callback para sidebar izquierdo"""
        self.settings.set("ui.sidebar_left_visible", switch.get_active())
        self.settings.save_settings()

    def _on_right_sidebar_changed(self, switch, param):
        """Callback para sidebar derecho"""
        self.settings.set("ui.sidebar_right_visible", switch.get_active())
        self.settings.save_settings()

    def _on_clear_recent_clicked(self, button):
        """Limpia la lista de archivos recientes"""
        self.settings.set("recent_files", [])
        self.settings.save_settings()

        # Mostrar confirmación
        toast = Adw.Toast()
        toast.set_title("Archivos recientes borrados")
        toast.set_timeout(2)
        # Note: Necesitarías un toast overlay en la ventana principal para esto


def show_preferences_dialog(parent_window: 'GutenAIWindow'):
    """Muestra el diálogo de preferencias"""
    dialog = PreferencesDialog(parent_window)
    dialog.present()