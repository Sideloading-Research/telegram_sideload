# Listen Audio Plugin

## Description
This plugin handles audio and voice message uploads. It ensures that audio content is only sent to multimodal LLMs that natively support audio analysis.

## How it Works
1.  **Detection:** The plugin detects if a message contains an audio file or a voice note.
2.  **Provider Check:** It checks the currently active AI provider.
    - **Supported:** Gemini, OpenAI (GPT-4o).
    - **Unsupported:** Anthropic (Claude 3.5), Grok, Llama 3.2.
3.  **Action:**
    - If supported, the audio is passed to the model.
    - If unsupported, the audio is blocked with a warning.

## Requirements
- None.

## Compatibility
- **Gemini:** Supported (Native audio).
- **OpenAI (GPT-4o):** Supported (Native audio).
- **Others:** Not supported (Audio will be blocked).
