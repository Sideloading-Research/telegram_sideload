# Watch Video Plugin

## Description
This plugin handles video file uploads. It ensures that video content is only sent to multimodal LLMs that natively support video analysis.

## How it Works
1.  **Detection:** The plugin detects if a message contains a video file.
2.  **Provider Check:** It checks the currently active AI provider.
    - **Supported:** Gemini, OpenAI (GPT-4o).
    - **Unsupported:** Anthropic, Grok, Llama, etc.
3.  **Action:**
    - If supported, the video is passed to the model for analysis.
    - If unsupported, the video is blocked, and a warning message is returned to the user, advising them to switch to a supported provider.

## Requirements
- None (uses Telegram Bot API for file handling).

## Compatibility
- **Gemini:** Supported (Native video analysis).
- **OpenAI (GPT-4o):** Supported.
- **Others:** Not supported (Video will be blocked).
