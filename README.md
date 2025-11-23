# Telegram Sideload Bot

Chat with your AI sideload in Telegram. This bot fetches a "mindfile" from a GitHub repository, allowing for a persistent and up-to-date personality for your AI. It supports private chats and group chats, and features a unique pseudo-infinite context mechanism to handle large mindfiles.

## Key Features

-   **Modular Worker Architecture**: The bot uses a pipeline of workers, starting with a `DoormanWorker` to classify requests. An `IntegrationWorker` then polls multiple `DataWorker` instances in parallel, synthesizes their answers, and passes the result through `Style` and `QualityChecks` workers.
-   **Plugin System**: Extensible plugin architecture for preprocessing messages, validating multimodal content, and transforming user input before it reaches the AI pipeline. See [Plugin Documentation](plugins/README.md) for details.
-   **Multi-Provider Support via OpenRouter**: The bot leverages OpenRouter to access a wide range of models from different providers (Google, Anthropic, OpenAI, etc.). It uses a cascading fallback mechanism to ensure high availability.
-   **Quality Control**: Responses are automatically checked for quality, with a built-in retry mechanism to meet desired standards.
-   **Dynamic Mindfile**: The bot automatically pulls and updates its mindfile from a specified GitHub repository.
-   **Pseudo-Infinite Context**: A unique "tip of the tongue" feature allows the use of mindfiles larger than the LLM's context window by randomly omitting parts of it in each interaction.


## Architecture Overview

The bot's architecture is designed around a series of workers that process incoming messages in a pipeline. This ensures that each response is generated, styled, and quality-checked before being sent to the user.

```
[User Message]
     |
     v
[DoormanWorker] (Classifies request: deep, shallow, jailbreak)
     |
     v
[IntegrationWorker]
     |
     ├──> 1. Polls multiple [DataWorkers] in parallel -> [OpenRouter]
     |         |
     |         └──> Merges answers via LLM synthesis
     |
     ├──> 2. [StyleWorker] -> [OpenRouter] (applies styling)
     |
     └──> 3. [QualityChecksWorker] -> [OpenRouter] (evaluates quality)
```

## Prerequisites

### API Keys

You will need the following API keys, which should be set as environment variables:

-   **Telegram Bot Token**: Obtain this from [@BotFather](https://t.me/botfather) on Telegram.
-   **OpenRouter**: Get your API key from [OpenRouter](https://openrouter.ai/keys). This is now the default provider.

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

# OpenRouter (Default Provider)
OPENROUTER_KEY='<your_openrouter_api_key>'
```

The bot uses OpenRouter by default to access a variety of models from different providers. The specific models and their fallback order are defined in the `MODELS_TO_ATTEMPT` list in `config.py`. This provides flexibility and resilience by automatically trying different models if one fails.

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

### Local Sideload Setup

For instructions on advanced local setups, such as using a local mindfile or a local AI provider, see the [local run guide](docs/local_run.md).

### Admin Commands

For details on available admin commands for development and testing, see the [admin commands guide](docs/admin_commands.md).


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

## Plugin System

The bot includes a powerful plugin system that preprocesses messages before they reach the AI pipeline. Plugins can validate content, transform messages, and enhance functionality.

### Available Plugins

- **📺 summarize_youtube_video**: Automatically fetches and summarizes YouTube video transcripts
- **🌐 web_reader**: Scrapes and summarizes web page content
- **🎬 watch_video**: Validates video upload compatibility with AI providers
- **🖼️ watch_picture**: Validates image upload compatibility with AI providers
- **🎵 listen_audio**: Validates audio upload compatibility with AI providers
- **🎨 generate_picture**: Validates image generation requests

### Plugin Management Commands

Control plugins directly from Telegram:

- `/plugins` - Show status of all plugins
- `/enable_plugin <name>` - Enable a specific plugin
- `/disable_plugin <name>` - Disable a specific plugin
- `/enable_all_plugins` - Enable all plugins
- `/disable_all_plugins` - Disable all plugins (useful for cost savings)

### Plugin Documentation

For detailed information about the plugin system, including how to create custom plugins, see the [Plugin System Documentation](plugins/README.md).
 
# Working with large mindfiles

The app uses 3 strategies to work with the corpus much larger than the context window of any single language model.

## 1. Leftover Preservation

When `structured_self_facts` exceeds the configured token limit (typically 30% of the context window), the excess content is automatically preserved and made available to data workers instead of being discarded.

**Key features:**
- **Zero data loss**: All truncated content is preserved
- **Automatic distribution**: Leftover is split across multiple data workers via compendiums
- **Smart routing**: System automatically uses deep mode when leftover exists to ensure all data is consulted

**Impact**: In typical scenarios, this prevents 60-70% of biographical data from being lost, dramatically improving answer accuracy.

For detailed information, see the [Leftover Preservation Documentation](docs/leftover_preservation.md).

## 2. The "tip of the tongue" pseudo-infinite context

The script uses a computationally cheap way to implement a form of infinite context. In each interaction, it randomly omits parts of the mindfile.

**Pros:**
- The entire mindfile is eventually used by the sideload.
- It introduces randomization, preventing identical answers to the same question.
- It emulates human-like memory recall, where not all information is available at once.

**Cons:**
- At any given time, the sideload only has a partial view of the mindfile. However, experiments show this is not a significant issue.

## 3. Specialized DataWorkers

We use a multi-step process that leverages splitting the corpus into smaller chunks and then synthesizing the answers from each chunk into one answer:

1.  **Mindfile Segmentation**: The entire mindfile is first broken down into smaller, semantically coherent entries based on its internal structure (e.g., date markers).

2.  **Optimal Packing**: These entries are then intelligently packed into larger "compendiums" using a bin packing algorithm. Each compendium is sized to fit just within the LLM's context window, ensuring maximum data density without truncation.

3.  **Chunks Processing**: For "deep dive" questions, each compendium is assigned to a dedicated `DataWorker`.

4.  **Answer Synthesis**: The `IntegrationWorker` collects these partial answers and uses a final LLM call to synthesize them into a single, comprehensive, and coherent response.

This architecture allows the bot to have a complete and structured understanding of the entire mindfile for complex queries.