import os
import re
from dataclasses import dataclass

GROUPS_SETTINGS_DIR = "groups_settings"

@dataclass
class GroupSettings:
    group_id: int
    group_description: str | None = None
    group_rules: str | None = None
    max_autotrigger_messages_per_day: int | None = None
    max_requested_messages_per_day: int | None = None

def parse_settings_file(file_path):
    settings = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple parsing for key = value
        # We need to handle potentially quoted strings
        lines = content.splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Handle integers
                if value.lstrip('-').isdigit():
                    settings[key] = int(value)
                # Handle quoted strings
                elif value.startswith('"') and value.endswith('"'):
                    settings[key] = value[1:-1].replace('\\n', '\n')
                else:
                    settings[key] = value
                    
        return settings
    except Exception as e:
        print(f"Error parsing group settings file {file_path}: {e}")
        return None

def load_all_group_settings() -> dict[int, GroupSettings]:
    """
    Scans the groups_settings directory and returns a dictionary
    mapping group_id to their GroupSettings objects.
    """
    all_settings = {}
    
    if not os.path.exists(GROUPS_SETTINGS_DIR):
        print(f"Directory {GROUPS_SETTINGS_DIR} does not exist.")
        return all_settings

    for filename in os.listdir(GROUPS_SETTINGS_DIR):
        if filename.endswith(".txt"):
            file_path = os.path.join(GROUPS_SETTINGS_DIR, filename)
            raw_settings = parse_settings_file(file_path)
            
            if raw_settings and 'group_id' in raw_settings:
                try:
                    group_id = raw_settings['group_id']
                    # Create GroupSettings object with data from file
                    # Filter out keys that don't belong to the dataclass to avoid TypeError
                    valid_keys = GroupSettings.__annotations__.keys()
                    filtered_settings = {k: v for k, v in raw_settings.items() if k in valid_keys}
                    
                    settings_obj = GroupSettings(**filtered_settings)
                    all_settings[group_id] = settings_obj
                except Exception as e:
                    print(f"Error creating GroupSettings for file {filename}: {e}")
                
    return all_settings

_cached_settings: dict[int, GroupSettings] | None = None

def get_group_settings(group_id: int) -> GroupSettings | None:
    global _cached_settings
    if _cached_settings is None:
        _cached_settings = load_all_group_settings()
    
    return _cached_settings.get(group_id)

def reload_group_settings():
    global _cached_settings
    _cached_settings = load_all_group_settings()
