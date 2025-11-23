"""
Listen Audio Plugin

This plugin validates that audio/voice uploads are only sent to AI providers
that support native audio analysis. This prevents API errors for providers
that only support text or vision.

Supported Providers:
- Gemini (Google): Native audio understanding
- OpenAI (GPT-4o): Native audio understanding

Unsupported Providers:
- Anthropic (Claude): Vision only, no audio
- Others: Typically text/vision only
"""

# List of providers that support native audio input
SUPPORTED_PROVIDERS = ["gemini", "openai"]

def is_plugin_applicable(messages, provider):
    """
    Determines if this plugin should process the current message.
    
    Returns True if the last user message contains audio or voice content.
    This allows the plugin to intercept audio uploads and validate
    provider compatibility before sending to the API.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        provider: Active AI provider (e.g., 'openai', 'anthropic')
    
    Returns:
        bool: True if message contains audio/voice content
    """
    if not messages:
        return False
    
    last_message = messages[-1]
    if last_message.get("role") != "user":
        return False
    
    content = last_message.get("content", "")
    
    # Check if content contains audio or voice (content can be a list of parts for multimodal)
    has_audio = False
    if isinstance(content, list):
        for part in content:
            if part.get("type") == "audio" or part.get("type") == "voice":
                has_audio = True
                break
    
    if has_audio:
        return True
            
    return False

def process_messages(messages, provider):
    """
    Validates provider compatibility with audio content.
    
    If the provider supports audio, the message passes through unchanged.
    If not, the audio content is replaced with a user-friendly error message
    explaining that they need to switch to a compatible provider.
    
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
        print(f"Plugin listen_audio: Provider {provider} supports audio. Proceeding.")
        # Audio content passes through unchanged - the provider wrapper will handle it
        return messages
    else:
        print(f"Plugin listen_audio: Provider {provider} does NOT support audio. Blocking.")
        # Replace audio content with helpful error message
        messages[-1]["content"] = f"Sorry, the current AI provider ({provider}) does not support audio analysis."
        return messages

