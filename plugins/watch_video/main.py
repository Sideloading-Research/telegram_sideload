"""
Watch Video Plugin

This plugin validates that video uploads are only sent to AI providers
that support native video analysis. This prevents API errors and provides
helpful feedback to users when they try to send videos to text-only models.

Supported Providers:
- Gemini (Google): Native video understanding
- OpenAI (GPT-4o): Native video understanding

Unsupported Providers:
- Anthropic (Claude): Vision only, no video
- Others: Typically text-only
"""

# List of providers that support native video input
SUPPORTED_PROVIDERS = ["gemini", "openai"]

def is_plugin_applicable(messages, provider):
    """
    Determines if this plugin should process the current message.
    
    Returns True if the last user message contains video content.
    This allows the plugin to intercept video uploads and validate
    provider compatibility before sending to the API.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        provider: Active AI provider (e.g., 'openai', 'anthropic')
    
    Returns:
        bool: True if message contains video content
    """
    if not messages:
        return False
    
    last_message = messages[-1]
    if last_message.get("role") != "user":
        return False
    
    content = last_message.get("content", "")
    
    # Check if content contains video (content can be a list of parts for multimodal)
    has_video = False
    if isinstance(content, list):
        for part in content:
            if part.get("type") == "video" or part.get("type") == "video_url":
                has_video = True
                break
    
    if has_video:
        return True
            
    return False

def process_messages(messages, provider):
    """
    Validates provider compatibility with video content.
    
    If the provider supports video, the message passes through unchanged.
    If not, the video content is replaced with a user-friendly error message
    explaining that they need to switch to a compatible provider.
    
    Args:
        messages: List of message dicts
        provider: Active AI provider
    
    Returns:
        list: Modified messages (either unchanged or with error message)
    """
    if not messages:
        return messages
        
    # Check if provider is supported
    # We use partial matching because provider string might be "openai" or "openai:gpt-4o" etc.
    is_supported = False
    if provider:
        provider_lower = provider.lower()
        for supported in SUPPORTED_PROVIDERS:
            if supported in provider_lower:
                is_supported = True
                break
    
    if is_supported:
        print(f"Plugin watch_video: Provider {provider} supports video. Proceeding.")
        # Video content passes through unchanged - the provider wrapper will handle it
        return messages
    else:
        print(f"Plugin watch_video: Provider {provider} does NOT support video. Blocking.")
        # Replace video content with helpful error message
        messages[-1]["content"] = f"Sorry, the current AI provider ({provider}) does not support video analysis. Please switch to Gemini or GPT-4o."
        return messages

