# Environment Variables Setup

This guide explains how to set up environment variables for the Telegram Sideload Bot.

## Quick Setup

1. **Copy the template:**
   ```bash
   cp docs/env_template.txt .env
   ```

2. **Edit the .env file:**
   ```bash
   # Open .env in your editor and fill in the values
   nano .env
   # or
   code .env
   ```

3. **Install dependencies:**
   ```bash
   pip install python-dotenv
   ```

## Required Credentials

The following credentials **must** be provided either in environment variables or in the `.env` file:

### Telegram Configuration
- **`TELEGRAM_LLM_BOT_TOKEN`**: Your Telegram bot token from [@BotFather](https://t.me/botfather)
- **`ALLOWED_USER_IDS`**: Comma-separated list of Telegram user IDs allowed to use the bot
- **`ALLOWED_GROUP_IDS`**: Comma-separated list of Telegram group IDs (use negative numbers)

### AI Provider
You must choose one AI provider and provide its credentials:

#### Option 1: OpenRouter (Recommended)
- Set `AI_PROVIDER=openrouter`
- Provide `OPENROUTER_KEY` from [openrouter.ai](https://openrouter.ai/)

#### Option 2: OpenAI
- Set `AI_PROVIDER=openai`
- Provide `OPENAI_API_KEY` from [platform.openai.com](https://platform.openai.com/api-keys)
- Optionally set `OPENAI_MODEL` (defaults to gpt-4)

#### Option 3: Anthropic
- Set `AI_PROVIDER=anthropic`
- Provide `ANTHROPIC_API_KEY` from [console.anthropic.com](https://console.anthropic.com/)
- Optionally set `ANTHROPIC_MODEL` (defaults to claude-3-sonnet-20240229)

#### Option 4: Google AI
- Set `AI_PROVIDER=google`
- Provide `GOOGLE_API_KEY` from [makersuite.google.com](https://makersuite.google.com/app/apikey)
- Optionally set `GOOGLE_MODEL_NAME` (defaults to gemini-pro)

#### Option 5: Ollama (Local)
- Set `AI_PROVIDER=ollama`
- No API key required (uses local Ollama instance)

## Optional Configuration

- **`USERS_INFO`**: Descriptive information about users (for personalization)
- **`TRIGGER_WORDS`**: Words that trigger bot responses (comma-separated)


## Security Notes

- Never commit `.env` files to version control
- Keep your API keys secure
- Use environment variables on production servers instead of `.env` files when possible


## Troubleshooting

- **"Required keys not found"**: Make sure all required credentials are filled in
- **"Invalid bot token"**: Double-check your bot token from @BotFather
- **"User not allowed"**: Verify the user ID is in `ALLOWED_USER_IDS`
- **API errors**: Check your API key and provider-specific settings
