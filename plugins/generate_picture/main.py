"""
Generate Picture Plugin

This plugin validates that image generation requests are only sent to AI providers
that support image generation capabilities. It detects user intent through keywords
in multiple languages and blocks requests to providers without generation support.

Supported Providers:
- Gemini (Google): Image generation via Imagen
- OpenAI: Image generation via DALL-E

Unsupported Providers:
- Anthropic (Claude): Vision input only, no generation
- Others: Typically no generation support
"""

import re

# List of providers that support image generation
SUPPORTED_PROVIDERS = ["gemini", "openai"]

# Keywords in English and Spanish indicating image generation intent
KEYWORDS = [
    "generate image", "create image", "draw", "paint", "picture of",
    "generar imagen", "crear imagen", "dibuja", "pinta", "foto de",
    "generate a picture", "create a picture", "haz un dibujo", "haz una imagen"
]

def is_plugin_applicable(messages, provider):
    """
    Determines if this plugin should process the current message.
    
    Returns True if the user's message contains keywords indicating
    an intent to generate an image. Uses a multilingual keyword list
    to detect requests in English and Spanish.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        provider: Active AI provider (e.g., 'openai', 'anthropic')
    
    Returns:
        bool: True if message contains image generation keywords
    """
    if not messages:
        return False
    
    last_message = messages[-1]
    if last_message.get("role") != "user":
        return False
    
    content = last_message.get("content", "")
    
    # Extract text content (handle both string and multimodal list formats)
    text_content = ""
    if isinstance(content, list):
        for part in content:
            if part.get("type") == "text":
                text_content += part.get("text", "") + " "
    elif isinstance(content, str):
        text_content = content
    
    # Case-insensitive keyword matching
    text_content = text_content.lower()
    
    for keyword in KEYWORDS:
        if keyword in text_content:
            return True
            
    return False

def process_messages(messages, provider):
    """
    Validates provider compatibility with image generation.
    
    If the provider supports image generation, the request passes through unchanged.
    If not, the request is replaced with an error message explaining that the
    user needs to switch to a compatible provider.
    
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
        print(f"Plugin generate_picture: Provider {provider} supports image generation. Proceeding.")
        # Request passes through unchanged - provider will handle generation
        return messages
    else:
        print(f"Plugin generate_picture: Provider {provider} does NOT support image generation. Blocking.")
        # Replace request with helpful error message
        messages[-1]["content"] = f"Sorry, the current AI provider ({provider}) does not support image generation. Please switch to Gemini or OpenAI."
        return messages

