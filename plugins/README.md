# Telegram LLM Bot - Plugin System

**Author:** Marco Baturan

## Overview

This directory contains the plugin system for the Telegram LLM Bot. Plugins are modular extensions that enhance the bot's functionality by adding specialized capabilities such as content summarization, multimodal input validation, and web scraping.

## Architecture

The plugin system is designed with the following principles:

### Dynamic Loading
- Plugins are automatically discovered and loaded from subdirectories at startup
- Each plugin must be in its own directory with a `main.py` file
- Plugins can be enabled/disabled via configuration without code changes

### Plugin Interface
Each plugin must implement two functions in `main.py`:

1. **`is_plugin_applicable(messages, provider)`**
   - Determines if the plugin should process the current message
   - Receives the message history and the active AI provider
   - Returns `True` if the plugin should handle this message, `False` otherwise

2. **`process_messages(messages, provider)`**
   - Modifies the message content before sending to the LLM
   - Can replace user input with processed content (e.g., transcripts, summaries)
   - Returns the modified messages list

### Provider Awareness
Plugins receive the active AI provider (e.g., "openai", "anthropic", "gemini") and can:
- Check if the provider supports required capabilities (vision, audio, video)
- Block unsupported content with helpful error messages
- Adapt behavior based on provider features

## Available Plugins

### Content Processing

#### 📺 `summarize_youtube_video`
- **Purpose:** Automatically summarizes YouTube videos
- **Trigger:** Detects YouTube URLs in messages
- **Process:** Fetches transcript and generates executive summary
- **Requirements:** `youtube-transcript-api`
- **Compatibility:** All text-based providers

#### 🌐 `web_reader`
- **Purpose:** Summarizes web page content
- **Trigger:** Detects HTTP/HTTPS URLs (excluding YouTube)
- **Process:** Scrapes page text and generates summary
- **Requirements:** `requests`, `beautifulsoup4`
- **Compatibility:** All text-based providers

### Multimodal Input Validation

#### 🎬 `watch_video`
- **Purpose:** Validates video upload compatibility
- **Trigger:** User uploads a video file
- **Process:** Checks if provider supports native video analysis
- **Supported Providers:** Gemini, OpenAI (GPT-4o)
- **Action:** Blocks video if provider doesn't support it

#### 🖼️ `watch_picture`
- **Purpose:** Validates image upload compatibility
- **Trigger:** User uploads an image
- **Process:** Checks if provider supports vision
- **Supported Providers:** Gemini, OpenAI, Anthropic
- **Action:** Blocks image if provider doesn't support it

#### 🎵 `listen_audio`
- **Purpose:** Validates audio upload compatibility
- **Trigger:** User uploads audio or voice note
- **Process:** Checks if provider supports native audio
- **Supported Providers:** Gemini, OpenAI (GPT-4o)
- **Action:** Blocks audio if provider doesn't support it

### Content Generation

#### 🎨 `generate_picture`
- **Purpose:** Validates image generation requests
- **Trigger:** Keywords like "generate image", "draw", "dibuja"
- **Process:** Checks if provider supports image generation
- **Supported Providers:** Gemini, OpenAI
- **Action:** Blocks request if provider doesn't support generation

## Plugin Management

### Configuration File
`config_plugins.py` controls which plugins are active:

```python
PLUGIN_STATUS = {
    "summarize_youtube_video": True,
    "web_reader": True,
    "watch_video": True,
    "watch_picture": True,
    "listen_audio": True,
    "generate_picture": True,
}
```

### Telegram Commands

Manage plugins directly from Telegram:

- **`/plugins`** - Show status of all plugins
- **`/enable_plugin <name>`** - Enable a specific plugin
  - Example: `/enable_plugin summarize_youtube_video`
- **`/disable_plugin <name>`** - Disable a specific plugin
  - Example: `/disable_plugin web_reader`
- **`/enable_all_plugins`** - Enable all plugins
- **`/disable_all_plugins`** - Disable all plugins (useful for cost savings)

### Cost Management
Disable expensive plugins during low-budget periods:
```
/disable_plugin summarize_youtube_video
/disable_plugin web_reader
```

## Creating a New Plugin

### Directory Structure
```
plugins/
├── your_plugin_name/
│   ├── main.py           # Required: Plugin logic
│   ├── requirements.txt  # Required: Dependencies
│   ├── license.md        # Required: License (Public Domain)
│   └── README.md         # Required: Documentation
```

### Template (`main.py`)
```python
def is_plugin_applicable(messages, provider):
    """
    Check if this plugin should process the message.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        provider: Active AI provider (e.g., 'openai', 'anthropic')
    
    Returns:
        bool: True if plugin should handle this message
    """
    if not messages:
        return False
    
    last_message = messages[-1]
    if last_message.get("role") != "user":
        return False
    
    # Your detection logic here
    return False

def process_messages(messages, provider):
    """
    Process and modify the messages.
    
    Args:
        messages: List of message dicts
        provider: Active AI provider
    
    Returns:
        list: Modified messages
    """
    # Your processing logic here
    return messages
```

### Registration
1. Add plugin name to `config_plugins.py` `PLUGIN_STATUS`
2. Set to `True` to enable by default
3. Plugin will be auto-loaded on next bot restart

## Plugin Execution Order

Plugins are processed in directory listing order. The **first** plugin that returns `True` from `is_plugin_applicable()` will process the message. Subsequent plugins are skipped.

## Licensing

All plugins in this directory are released into the **Public Domain** under the Unlicense. See individual `license.md` files for details.

## Dependencies

Install all plugin dependencies:
```bash
pip install -r requirements.txt
```

Individual plugin requirements are listed in their respective `requirements.txt` files.
