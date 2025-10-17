"""
GutenAI - Gestor de configuración y preferencias
Maneja configuración persistente incluyendo API keys
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
import os

class SettingsManager:
    """Gestor de configuración persistente para GutenAI"""

    def __init__(self, app_name: str = "gutenai"):
        self.app_name = app_name
        self.config_dir = self._get_config_directory()
        self.config_file = self.config_dir / "config.json"
        self.settings = self._load_settings()

    def _get_config_directory(self) -> Path:
        """Obtiene el directorio de configuración según el sistema"""

        # Linux/Unix: ~/.config/gutenai
        if os.name == 'posix':
            config_home = os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))
            config_dir = Path(config_home) / self.app_name

        # Windows: %APPDATA%/gutenai
        elif os.name == 'nt':
            config_dir = Path(os.environ['APPDATA']) / self.app_name

        # Fallback
        else:
            config_dir = Path.home() / f'.{self.app_name}'

        # Crear directorio si no existe
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def _load_settings(self) -> Dict[str, Any]:
        """Carga configuración desde disco"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[SETTINGS] Error cargando configuración: {e}")
                return self._get_default_settings()
        else:
            return self._get_default_settings()

    def _get_default_settings(self) -> Dict[str, Any]:
        """Configuración por defecto"""
        return {
            "version": "1.0",
            "gemini": {
                "api_key": "",
                "enabled": True,
                "language": "es",
                "max_requests_per_hour": 15
            },
            "editor": {
                "theme": "Adwaita-dark",
                "show_line_numbers": True,
                "word_wrap": True,
                "auto_save": True,
                "auto_save_delay": 1500
            },
            "ui": {
                "sidebar_left_visible": True,
                "sidebar_right_visible": True,
                "window_width": 1400,
                "window_height": 900
            },
            "recent_files": [],
            "cache": {
                "corrections_cache_enabled": True,
                "max_cache_size_mb": 50
            }
        }

    def save_settings(self):
        """Guarda configuración a disco"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[SETTINGS] Error guardando configuración: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Obtiene valor de configuración usando notación de punto
        Ej: get("gemini.api_key") o get("editor.theme")
        """
        keys = key_path.split('.')
        value = self.settings

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key_path: str, value: Any):
        """
        Establece valor de configuración usando notación de punto
        Ej: set("gemini.api_key", "tu_api_key")
        """
        keys = key_path.split('.')
        current = self.settings

        # Navegar hasta el penúltimo nivel
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        # Establecer el valor final
        current[keys[-1]] = value

    def get_gemini_api_key(self) -> Optional[str]:
        """Obtiene la API key de Gemini"""
        api_key = self.get("gemini.api_key", "")
        return api_key if api_key and api_key.strip() else None

    def set_gemini_api_key(self, api_key: str):
        """Establece la API key de Gemini"""
        self.set("gemini.api_key", api_key.strip())
        self.save_settings()

    def is_gemini_enabled(self) -> bool:
        """Verifica si Gemini está habilitado"""
        return self.get("gemini.enabled", True) and self.get_gemini_api_key() is not None

    def get_recent_files(self) -> list:
        """Obtiene lista de archivos recientes"""
        return self.get("recent_files", [])

    def add_recent_file(self, file_path: str):
        """Agrega archivo a la lista de recientes"""
        recent = self.get_recent_files()

        # Remover si ya existe
        if file_path in recent:
            recent.remove(file_path)

        # Agregar al inicio
        recent.insert(0, file_path)

        # Limitar a 10 archivos recientes
        recent = recent[:10]

        self.set("recent_files", recent)
        self.save_settings()

    def get_editor_settings(self) -> Dict[str, Any]:
        """Obtiene configuración del editor"""
        return self.get("editor", {})

    def get_ui_settings(self) -> Dict[str, Any]:
        """Obtiene configuración de UI"""
        return self.get("ui", {})

    def update_ui_settings(self, **kwargs):
        """Actualiza configuración de UI"""
        for key, value in kwargs.items():
            self.set(f"ui.{key}", value)
        self.save_settings()


# Singleton global
_settings_manager = None

def get_settings() -> SettingsManager:
    """Obtiene la instancia global del gestor de configuración"""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager