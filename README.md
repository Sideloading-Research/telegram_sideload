# Intro

Chat with your sideload in Telegram. 

The mindfile for the sideload is automatically pulled from a specified GitHub repository, and it regularly updated, to keep your sideload up-to-date.

The bot supports both private chats and group chats.

A unique feature of the bot is that the mindfile can exceed the context window of the LLM, thanks to the pseudo-infinite context (see a section about about it below).

# Prerequisites

## API keys

- You have a Telegram account
- You got an API key for Google AI: https://aistudio.google.com/apikey
- You got a Telegram bot token: https://t.me/botfather
- You got a Google Gemini model ID (see the "Choose the LLM model to use" section below)

## Mindfile Setup

Before using the bot, you need to create and publish your mindfile to a GitHub repository. 

Your mindfile repository must have the following structure:

```
your-repo/
└── full_dataset/
    ├── system_message.txt
    ├── structured_self_facts.txt
    ├── structured_memories.txt
    └── [other optional context files].txt
```

Required files:
- `system_message.txt`: Contains the system message for the sideload. You can [this one as a template](https://github.com/RomanPlusPlus/open-source-human-mind/blob/main/full_dataset/system_message.txt).
- `structured_self_facts.txt`: Contains your detailed self-description. 
- `structured_memories.txt`: Contains your written memories. 

The two files will be placed at the start and at the end of the context, respectively. 
The rest of the files will be placed in the middle of the context.

# How to deploy:

## 1. Create a VM, and do SSH into it

For example, in Digital Ocean, Azure, etc. 
From experience, the script needs at least 1 GB of RAM.

You can also run the script locally. Useful for testing.

The script was tested on Ubuntu, Linux Mint, and MacOS. Not sure if it works on Windows.

## 2. Clone this repository into the VM

## 3. Create a tmux session

```
tmux new -s session_name
```

## 4. Install the dependencies with pip

cd to the dir where you cloned this and run in a terminal:

```
python3 -m venv venv
```
```
source venv/bin/activate
```
```
pip install -r requirements.txt
```

## 5. Choose the LLM model to use:

The script was extensively tested with these models:
- gemini-2.5-pro-preview-03-25
- gemini-2.5-flash-preview-04-17

The pro version is noticeably better, but it's also x10 more expensive.

The flash version still delivers good results. 

If you want to try other models, for best results make sure they have at least 1M context.

The 2.5 generation of Gemini models is the first one where we have noticed human-like quality of responses and a good understanding of the mindfile. Thus, we recommend using 2.5 or later generations.

The list of other models from Google can be found here:
https://cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions

Note: While the codebase includes files for other AI providers (like Anthropic and OpenAI in the `ai_providers` directory), the bot is currently optimized and tested for Google's models.

## 6. Obtain telegram user IDs and group IDs 

To avoid abuse, the bot only talks with authorized users and authorized groups.

The easiest way to get the IDs is to start talking with the bot. 
If he complains that the ID is not in the list of authorized IDs, you can add it to the list of authorized IDs.

Same for groups. 

Thus, if you don't already have the IDs, you can just skip adding them to env variables, for now. 

There are also third-party bots that can help you get the IDs of your users and groups. 
For example,  @getmyid_bot , @userinfobot .
But we don't know if they are safe to use. Use at your own risk.

## 7. Specify the API keys and allowed users like this:

```
echo "export GOOGLE_API_KEY='<your_google_api_key>'" >> ~/.bashrc

echo "export GOOGLE_MODEL_NAME='your_preferred_model'" >> ~/.bashrc

echo "export ALLOWED_USER_IDS='some_id1,some_id2,some_id3'" >> ~/.bashrc

echo "export TELEGRAM_LLM_BOT_TOKEN='<your_telegram_bot_token>'" >> ~/.bashrc

# Optional: If you want the bot to work in group chats, do:
echo "export ALLOWED_GROUP_IDS='group_id1,group_id2'" >> ~/.bashrc

# Optional: Provide descriptions for known users.
# This helps the bot understand who it's talking to.
# Format: 'id1:description1;id2:description2'
echo "export USERS_INFO='user_id1:Short description of user 1;user_id2:Notes about user 2'" >> ~/.bashrc

# Optional: Specify trigger words for group chats.
# If set, the bot will automatically respond in group chats to the messages that contais one of these words (case-insensitive).
# Format: 'word1;word2;word3'
echo "export TRIGGER_WORDS='sideload;bot name;question for bot'" >> ~/.bashrc

source ~/.bashrc
```

## 8. Run the main script

```
python3 main.py
```

To leave the script running even after you log out, press `Ctrl+b`, and then quicly after that press `d`.

To return to the tmux session in the future, run `tmux attach -t session_name`.

## 9. Additional configuration

The bot's behavior is controlled by settings in `config.py`. The main settings include:
- `REPO_URL`: The GitHub repository containing the mindfile data. By default, the bot pulls the mindfile from https://github.com/RomanPlusPlus/open-source-human-mind.git.
- `REFRESH_EVERY_N_REQUESTS`: How often the mindfile data is refreshed (default: 10)
- `REMOVE_CHAIN_OF_THOUGHT_FROM_ANSWER7`: Whether to remove chain-of-thought reasoning from responses. Removed only from the answer visible to the user. Both will still be used internally.
- `REMOVE_INTERNAL_DIALOG_FROM_ANSWER7`: Same.

See `config.py` for these and other settings.

## 10. Add the bot to your group

In telegram, find the official bot manager (@BotFather) and send him this:
/setjoingroups

In the menu, select your bot and click Enable. 

In telegram, in a chat with your bot, click "..." in the top right corner and select Info.

There, click "Add to group or channel" and select your group.

If the bot complains that he can't chat in this group with the such and such ID,
add the ID to the list of allowed IDs.

After that, do the /setjoingroups thing again, but this time click Disable, so no one could add the bot to other groups.

# The "tip of the tongue" pseudo-infinite context

The scrip uses a computationally cheap way to implement (kinda) infinite context:
every interaction, it randomly omits some parts of the huge mindfile. 

Pros:
- the entire huge midnfile is (eventually) used by the sideload
- one can run huge sideloads locally, even with today's open-source models and hardware
- the sideload's answers are additionally randomized, preventing identical answers to the same question
- the approach emulates presque vu / jamais vu - the human tendency to temporarily forget many things, with the ability to recall them later.

Cons:
- the resulting sideload at any given time contains only a part of the mindfile. Judging by our experiments, it does not seem to be a problem.