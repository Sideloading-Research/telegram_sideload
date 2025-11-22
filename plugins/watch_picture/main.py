"""
Watch Picture Plugin

This plugin validates that image uploads are only sent to AI providers
that support vision capabilities. Most modern LLMs support images, but
this plugin provides a safety check and helpful error messages.

Supported Providers:
- Gemini (Google): Vision support
- OpenAI (GPT-4o, GPT-4 Vision): Vision support
- Anthropic (Claude 3.5): Vision support

Unsupported Providers:
- Text-only models (if any)
"""

# List of providers that support image/vision input
SUPPORTED_PROVIDERS = ["gemini", "openai", "anthropic"]

def is_plugin_applicable(messages, provider):
    """
    Determines if this plugin should process the current message.
    
    Returns True if the last user message contains image content.
    This allows the plugin to intercept image uploads and validate
    provider compatibility.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        provider: Active AI provider (e.g., 'openai', 'anthropic')
    
    Returns:
        bool: True if message contains image content
    """
    if not messages:
        return False
    
    last_message = messages[-1]
    if last_message.get("role") != "user":
        return False
    
    content = last_message.get("content", "")
    
    # Check if content contains images (content can be a list of parts for multimodal)
    has_image = False
    if isinstance(content, list):
        for part in content:
            if part.get("type") == "image_url" or part.get("type") == "image":
                has_image = True
                break
    
    if has_image:
        return True
            
    return False

def process_messages(messages, provider):
    """
    Validates provider compatibility with image content.
    
    If the provider supports images, the message passes through unchanged.
    If not, the image content is replaced with an error message.
    
    Args:
        messages: List of message dicts
        provider: Active AI provider
    
    Returns:
        list: Modified messages (either unchanged or with error message)
    """
    if not messages:
        return messages
        
    # Check if provider is supported (partial string matching)
    is_supported = False
    if provider:
        provider_lower = provider.lower()
        for supported in SUPPORTED_PROVIDERS:
            if supported in provider_lower:
                is_supported = True
                break
    
    if is_supported:
        print(f"Plugin watch_picture: Provider {provider} supports images. Proceeding.")
        # Image content passes through unchanged
        return messages
    else:
        print(f"Plugin watch_picture: Provider {provider} does NOT support images. Blocking.")
        # Replace image content with error message
        messages[-1]["content"] = f"Sorry, the current AI provider ({provider}) does not support image analysis."
        return messages

