# Intro

Chat with your sideload in Telegram. 

The mindfile for the sideload is automatically pulled from a specified GitHub repository, and it regularly updated, to keep your sideload up-to-date.

The bot supports both private chats and group chats (when group IDs are authorized)

# Prerequisites

## API keys

- You have a Telegram account
- You got an API key for Google AI: https://aistudio.google.com/apikey
- You got a Telegram bot token: https://t.me/botfather

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

## 0. Get the telegram IDs of the allowed users 

For example, of your friends in telegram. You can also add group IDs if you want your bot to work in group chats.

## 1. Create a VM, and do SSH into it

For example, in Digital Ocean, Azure, etc.

You can also run the script locally. Useful for testing.

The script was tested on Ubuntu VM.

## 2. Clone this repository into the VM

## 3. Create a tmux session

```
tmux new -s session_name
```

## 4. Install the dependencies with pip

cd to the dir where you cloned this and run in a terminal:

```
pip install -r requirements.txt
```

## 5. Specify the API keys and allowed users like this:

```
echo "export GOOGLE_API_KEY='<your_google_api_key>'" >> ~/.bashrc

echo "export GOOGLE_MODEL_NAME='gemini-2.5-pro-exp-03-25'" >> ~/.bashrc

echo "export ALLOWED_USER_IDS='some_id1,some_id2,some_id3'" >> ~/.bashrc

echo "export TELEGRAM_LLM_BOT_TOKEN='<your_telegram_bot_token>'" >> ~/.bashrc

# Optional: If you want the bot to work in group chats, do:
echo "export ALLOWED_GROUP_IDS='group_id1,group_id2'" >> ~/.bashrc

source ~/.bashrc
```

## 6. Run the main script

```
python3 main.py
```

To leave the script running even after you log out, press `Ctrl+b`, and then quicly after that press `d`.

To return to the tmux session in the future, run `tmux attach -t session_name`.

## Configuration

The bot's behavior is controlled by settings in `config.py`. The main settings include:
- `REPO_URL`: The GitHub repository containing the mindfile data. By default, the bot pulls the mindfile from https://github.com/RomanPlusPlus/open-source-human-mind.git.
- `REFRESH_EVERY_N_REQUESTS`: How often the mindfile data is refreshed (default: 10)
- `REMOVE_CHAIN_OF_THOUGHT_FROM_ANSWER7`: Whether to remove chain-of-thought reasoning from responses. Removed only from the answer visible to the user. Both will still be used internally.
- `REMOVE_INTERNAL_DIALOG_FROM_ANSWER7`: Same.

You can modify these settings in the `config.py` file to customize the bot's behavior.

