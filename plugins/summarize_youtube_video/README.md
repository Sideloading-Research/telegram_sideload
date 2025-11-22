# Summarize YouTube Video Plugin

## Description
This plugin automatically detects YouTube links in the chat, fetches the video transcript using `youtube-transcript-api`, and generates a concise executive summary using the active LLM.

## How it Works
1.  **Detection:** The plugin scans user messages for "youtube.com" or "youtu.be" links.
2.  **Transcript Fetching:** It attempts to download the transcript (preferring Spanish or English).
3.  **Prompt Generation:** It replaces the original message with a structured prompt containing the transcript and specific instructions for an objective summary.
4.  **Processing:** The LLM processes the prompt and returns the summary.

## Requirements
- `youtube-transcript-api`

## Compatibility
- Works with all text-based LLM providers (OpenAI, Anthropic, Gemini, etc.).
