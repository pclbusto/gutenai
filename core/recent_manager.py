# --- AÑADIR ESTAS IMPORTACIONES ---
import os
import json
from gi.repository import GLib
# -----------------------------------

class RecentManager:
    def __init__(self, app_name='gutenia', max_recent=10):
        self.MAX_RECENT = max_recent
        user_data_dir = GLib.get_user_data_dir()
        self.config_path = os.path.join(user_data_dir, app_name)
        os.makedirs(self.config_path, exist_ok=True)
        self.recent_files_path = os.path.join(self.config_path, 'recent.json')
        self.files = self.load()
        
    def load(self):
        try:
            with open(self.recent_files_path, 'r') as f: return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): return []
        
    def save(self):
        with open(self.recent_files_path, 'w') as f: json.dump(self.files, f)
        
    def add(self, new_path):
        if new_path in self.files: self.files.remove(new_path)
        self.files.insert(0, new_path)
        self.files = self.files[:self.MAX_RECENT]
        self.save()
        
    def get_files(self):
        return self.files