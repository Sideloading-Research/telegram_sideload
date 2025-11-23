# Generate Picture Plugin

## Description
This plugin detects user requests to generate images (e.g., "create an image of...", "draw a cat"). It ensures that such requests are only processed by AI providers that support image generation.

## How it Works
1.  **Detection:** The plugin scans user messages for keywords indicating an intent to generate images (e.g., "generate image", "create picture", "draw", "dibuja", "crea una imagen").
2.  **Provider Check:** It checks the currently active AI provider.
    - **Supported:** Gemini (via Imagen), OpenAI (via DALL-E).
    - **Unsupported:** Anthropic (Claude 3.5), Grok, Llama 3.2 (Text-only or Vision-input only).
3.  **Action:**
    - If supported, the request is passed to the model.
    - If unsupported, the request is blocked with a warning.

## Requirements
- None.

## Compatibility
- **Gemini:** Supported.
- **OpenAI:** Supported.
- **Others:** Not supported (Request will be blocked).
