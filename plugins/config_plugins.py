"""
Plugin Configuration Manager

This file controls which plugins are active.
Set a plugin to False to deactivate it and save on API costs.
"""

# Plugin activation status
PLUGIN_STATUS = {
    "summarize_youtube_video": True,
    "web_reader": True,
    "watch_video": True,
    "watch_picture": True,
    "listen_audio": True,
    "generate_picture": True,
    "reaction_tracker": True,  # Tracks message reactions for learning from user feedback
}

def is_plugin_enabled(plugin_name):
    """
    Check if a plugin is enabled.
    
    Args:
        plugin_name: Name of the plugin (e.g., 'summarize_youtube_video')
    
    Returns:
        bool: True if enabled, False otherwise
    """
    return PLUGIN_STATUS.get(plugin_name, False)

def enable_plugin(plugin_name):
    """Enable a specific plugin."""
    if plugin_name in PLUGIN_STATUS:
        PLUGIN_STATUS[plugin_name] = True
        return True
    return False

def disable_plugin(plugin_name):
    """Disable a specific plugin."""
    if plugin_name in PLUGIN_STATUS:
        PLUGIN_STATUS[plugin_name] = False
        return True
    return False

def enable_all_plugins():
    """Enable all plugins."""
    for plugin_name in PLUGIN_STATUS:
        PLUGIN_STATUS[plugin_name] = True

def disable_all_plugins():
    """Disable all plugins."""
    for plugin_name in PLUGIN_STATUS:
        PLUGIN_STATUS[plugin_name] = False

def get_plugin_status():
    """Get the current status of all plugins."""
    return PLUGIN_STATUS.copy()
