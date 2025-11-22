# Watch Picture Plugin

## Description
This plugin handles image uploads. It ensures that image content is sent to multimodal LLMs that support vision capabilities.

## How it Works
1.  **Detection:** The plugin detects if a message contains an image (photo or image document).
2.  **Provider Check:** It checks the currently active AI provider.
    - **Supported:** Gemini, OpenAI (GPT-4o), Anthropic (Claude 3.5), Grok, Llama 3.2.
    - **Unsupported:** Text-only models (if any).
3.  **Action:**
    - If supported, the image is passed to the model.
    - If unsupported, the image is blocked with a warning.

## Requirements
- None.

## Compatibility
- **Gemini:** Supported.
- **OpenAI:** Supported.
- **Anthropic:** Supported.
