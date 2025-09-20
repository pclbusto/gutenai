# --- AÑADIR ESTAS IMPORTACIONES ---
import os
import json
from gi.repository import GLib
# -----------------------------------

class SettingsManager:
    """
    Gestiona la carga y guardado de la configuración de la aplicación (tamaño, posición, etc.).
    """
    def __init__(self, app_name='gutenia'):
        user_data_dir = GLib.get_user_data_dir()
        config_dir = os.path.join(user_data_dir, app_name)
        os.makedirs(config_dir, exist_ok=True)
        self.settings_path = os.path.join(config_dir, 'settings.json')

    def load(self):
        """Carga la configuración desde el archivo JSON."""
        try:
            with open(self.settings_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save(self, settings_dict):
        """Guarda el diccionario de configuración en el archivo JSON."""
        with open(self.settings_path, 'w') as f:
            json.dump(settings_dict, f, indent=4)