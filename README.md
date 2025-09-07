# Telegram Sideload Bot

Chat with your AI sideload in Telegram. This bot fetches a "mindfile" from a GitHub repository, allowing for a persistent and up-to-date personality for your AI. It supports private chats and group chats, and features a unique pseudo-infinite context mechanism to handle large mindfiles.

## Key Features

-   **Modular Worker Architecture**: The bot uses a pipeline of workers (`Data`, `Style`, `QualityChecks`) to process messages, ensuring high-quality, well-styled responses.
-   **Multi-Provider Support**: Seamlessly switch between different AI providers (e.g., Google, OpenAI, Anthropic) on-the-fly.
-   **Quality Control**: Responses are automatically checked for quality, with a built-in retry mechanism to meet desired standards.
-   **Dynamic Mindfile**: The bot automatically pulls and updates its mindfile from a specified GitHub repository.
-   **Pseudo-Infinite Context**: A unique "tip of the tongue" feature allows the use of mindfiles larger than the LLM's context window by randomly omitting parts of it in each interaction.

## Architecture Overview

The bot's architecture is designed around a series of workers that process incoming messages in a pipeline. This ensures that each response is generated, styled, and quality-checked before being sent to the user.

```
[IntegrationWorker]
    |
    ├──> 1. [DataWorker] -> [AI Provider] (gets initial answer)
    |
    ├──> 2. [StyleWorker] -> [AI Provider] (applies styling)
    |
    └──> 3. [QualityChecksWorker] -> [AI Provider] (evaluates quality)
```

## Prerequisites

### API Keys

You will need the following API keys, which should be set as environment variables:

-   **Telegram Bot Token**: Obtain this from [@BotFather](https://t.me/botfather) on Telegram.
-   **Google**: Get your API key from [Google AI Studio](https://aistudio.google.com/apikey).

### Mindfile Setup

Before using the bot, you need to create and publish your mindfile to a GitHub repository. Your repository must have the following structure:

```
your-repo/
└── full_dataset/
    ├── system_message.txt (required)
    ├── structured_self_facts.txt (required)
    ├── structured_memories.txt (required)
    ├── consumed_media_list.txt (optional)
    ├── dialogs.txt (optional)
    ├── dreams.txt (optional)
    ├── interviews_etc.txt (optional)
    ├── writings_fiction.txt (optional)
    ├── writings_non_fiction.txt (optional)
    └── [other optional context files].txt
```

-   `system_message.txt`: Required. Contains the system message for the sideload.
-   `structured_self_facts.txt`: Required. Contains a detailed self-description.
-   `structured_memories.txt`: Required. Contains written memories.
-   Other files like `dialogs.txt`, `dreams.txt`, etc.: Optional but recommended for richer context, as used by various workers.


## How to Deploy

### 1. Set up your environment

The bot can be deployed on a VM (e.g., Digital Ocean, Azure) or run locally. It has been tested on Ubuntu, Linux Mint, and macOS.

### 2. Clone the repository

```bash
git clone <repository_url>
cd <repository_name>
```

### 3. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Note: To avoid abuse, the bot only talks with authorized users and authorized groups.

The easiest way to get the IDs is to start talking with the bot. 
If he complains that the ID is not in the list of authorized IDs, you can add it to the list of authorized IDs.

Same for groups. 

Thus, if you don't already have the IDs, you can just skip adding them to env variables, for now. 

There are also third-party bots that can help you get the IDs of your users and groups. 
For example,  @getmyid_bot , @userinfobot .
But we don't know if they are safe to use. Use at your own risk.


**Required:**

```bash
# Telegram
TELEGRAM_LLM_BOT_TOKEN='<your_telegram_bot_token>'
ALLOWED_USER_IDS='<your_user_id>,<another_user_id>' # Comma-separated

# Google
GOOGLE_API_KEY='<your_google_api_key>'
GOOGLE_MODEL_NAME='<model_name>'

```

The 2.5 generation of Gemini models is the first one where we have noticed human-like quality of responses and a good understanding of the mindfile. Thus, we recommend using 2.5 or later generations.

The list of other models from Google can be found here:
https://cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions

Note: While the codebase includes files for other AI providers (like Anthropic and OpenAI in the `ai_providers` directory), the bot is currently optimized and tested for Google's models.

**Optional:**

```bash
# Group chats
ALLOWED_GROUP_IDS='<group_id_1>,<group_id_2>' # Comma-separated

# User descriptions so the bot can better understand with whom it is talking
USERS_INFO='<user_id_1>:Description of user 1;<user_id_2>:Description of user 2'

# Trigger words for the bot in group chats
TRIGGER_WORDS='sideload;bot name;question for bot' # Semicolon-separated
```



### 5. Run the bot

```bash
python3 main.py
```

For long-running sessions, it's recommended to use a terminal multiplexer like `tmux`.



## 6. Add the bot to your group

In telegram, find the official bot manager (@BotFather) and send him this:
/setjoingroups

In the menu, select your bot and click Enable. 

In telegram, in a chat with your bot, click "..." in the top right corner and select Info.

There, click "Add to group or channel" and select your group.

If the bot complains that he can't chat in this group with the such and such ID,
add the ID to the list of allowed IDs.

After that, do the /setjoingroups thing again, but this time click Disable, so no one could add the bot to other groups.


## Configuration

The bot's behavior can be further customized through `config.py`. 

## Usage

### Interacting with the Bot

-   **Private Chat**: Simply send a message to the bot.
-   **Group Chat**: Mention the bot, reply to one of its messages, or use a trigger word (if configured).
 

## The "tip of the tongue" pseudo-infinite context

The script uses a computationally cheap way to implement a form of infinite context. In each interaction, it randomly omits parts of the mindfile.

**Pros:**
- The entire mindfile is eventually used by the sideload.
- It introduces randomization, preventing identical answers to the same question.
- It emulates human-like memory recall, where not all information is available at once.

**Cons:**
- At any given time, the sideload only has a partial view of the mindfile. However, experiments show this is not a significant issue.