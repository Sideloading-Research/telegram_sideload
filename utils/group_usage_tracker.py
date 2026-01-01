import json
import os
from datetime import date
from telegram import Update
from telegram.constants import ChatType, MessageEntityType
from telegram.ext import ContextTypes

from utils.group_settings import get_group_settings
from config import (
    BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7,
    DEFAULT_MAX_AUTOTRIGGER_MESSAGES_PER_DAY,
    DEFAULT_MAX_REQUESTED_MESSAGES_PER_DAY
)
import bot_config

USAGE_FILE_PATH = "TEMP_DATA/group_daily_usage.json"
TRIGGER_WORDS_LIST = bot_config.get_trigger_words()

def _load_usage_data():
    if not os.path.exists(USAGE_FILE_PATH):
        return {}
    try:
        with open(USAGE_FILE_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        print("Warning: Could not read group usage file. Starting fresh.")
        return {}

def _save_usage_data(data):
    # Ensure directory exists
    os.makedirs(os.path.dirname(USAGE_FILE_PATH), exist_ok=True)
    try:
        with open(USAGE_FILE_PATH, 'w') as f:
            json.dump(data, f)
    except IOError as e:
        print(f"Error saving group usage data: {e}")

def _get_today_str():
    return date.today().isoformat()

def get_message_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str | None:
    """
    Determines the type of the message for quota purposes.
    
    Returns:
        "requested": Mention, Reply to bot, or explicit invocation.
        "autotrigger": Trigger word match.
        None: Neither (or not a group, or not text).
    """
    if not update.message:
        return None
    
    # Only applies to groups
    if update.message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return None
        
    message_text = update.message.text or update.message.caption
    message_entities = update.message.entities or update.message.caption_entities
    
    # 1. Check for "requested" (Mentions & Replies)
    is_requested = False
    
    # Check mentions in entities
    if message_text and context.bot.username:
        bot_username_at = f"@{context.bot.username}"
        if message_entities:
            for entity in message_entities:
                if entity.type == MessageEntityType.MENTION:
                    mention_text = message_text[entity.offset : entity.offset + entity.length]
                    # Case-insensitive check for username
                    if mention_text.lower() == bot_username_at.lower():
                        is_requested = True
                        break
                elif entity.type == MessageEntityType.TEXT_MENTION:
                    if entity.user and entity.user.id == context.bot.id:
                        is_requested = True
                        break
    
    # Check reply to bot
    if not is_requested and update.message.reply_to_message:
        if update.message.reply_to_message.from_user and update.message.reply_to_message.from_user.id == context.bot.id:
            is_requested = True
            
    if is_requested:
        return "requested"

    # 2. Check for "autotrigger" (Trigger Words)
    if TRIGGER_WORDS_LIST and message_text:
        message_text_lower = message_text.lower()
        for word in TRIGGER_WORDS_LIST:
            if word in message_text_lower:
                return "autotrigger"
    
    # If explicitly in "Answer Everything" mode (and it wasn't a specific trigger),
    # we usually consider it valid for answering.
    # However, if we want to limit "chatty mode" too, we might call this "autotrigger" or a new type.
    # The requirement says: "if BOT_ANSWERS... is False, we ignore group limits".
    # So we don't need to classify "general chatter" here because it won't be checked against limits.
    
    return None

def check_group_limits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Checks if the group has quota left to answer this message.
    Does NOT increment the counter.
    
    Returns:
        True: Allowed to answer (or limits ignored/not applicable).
        False: Quota exceeded or type forbidden (limit=0).
    """
    # 1. Global Override: If bot is in "Chatty Mode", ignore limits.
    if not BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7:
        return True

    chat_id = update.effective_chat.id
    settings = get_group_settings(chat_id)
    
    # If no settings file exists for this group, we assume unlimited?
    # Or default to 0? Existing logic elsewhere implies we might be lenient if no file.
    # BUT if a file DOES exist, limits apply.
    # UPDATE: Now we have generic defaults in config.py.
    # So if settings are missing, we just use defaults (handled below).
    # if not settings:
    #    return True

    msg_type = get_message_type(update, context)
    
    if not msg_type:
        # It's not a mention, reply, or trigger word. 
        # In "Respectful Mode" (BOT_ANSWERS...=True), we wouldn't answer anyway.
        # So quota check is irrelevant (pass).
        return True

    # Get the relevant limit
    # Logic:
    # 1. Start with generic defaults from config.py
    # 2. If group settings file exists AND defines a limit (not None), override.
    
    limit = 0
    
    if msg_type == "requested":
        limit = DEFAULT_MAX_REQUESTED_MESSAGES_PER_DAY
        if settings and settings.max_requested_messages_per_day is not None:
             limit = settings.max_requested_messages_per_day
             
    elif msg_type == "autotrigger":
        limit = DEFAULT_MAX_AUTOTRIGGER_MESSAGES_PER_DAY
        if settings and settings.max_autotrigger_messages_per_day is not None:
             limit = settings.max_autotrigger_messages_per_day
        
    # Check usage
    data = _load_usage_data()
    today_str = _get_today_str()
    group_str = str(chat_id)
    
    # Retrieve current count
    current_count = 0
    if group_str in data and data[group_str].get("date") == today_str:
        current_count = data[group_str].get(msg_type, 0)
        
    if current_count >= limit:
        print(f"Group {chat_id} limit reached for '{msg_type}': {current_count}/{limit}. Ignoring message.")
        return False
        
    return True

def increment_group_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Increments the usage counter for the message type.
    Should be called ONLY after a successful reply is sent.
    """
    # 1. Global Override Check
    if not BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7:
        return

    chat_id = update.effective_chat.id
    msg_type = get_message_type(update, context)
    
    if not msg_type:
        return

    data = _load_usage_data()
    today_str = _get_today_str()
    group_str = str(chat_id)

    # Initialize structure if needed
    if group_str not in data:
        data[group_str] = {}
    
    # Check if we need to reset for a new day
    if data[group_str].get("date") != today_str:
        data[group_str] = {
            "date": today_str,
            "autotrigger": 0,
            "requested": 0
        }

    # Increment
    current_count = data[group_str].get(msg_type, 0)
    data[group_str][msg_type] = current_count + 1
    
    _save_usage_data(data)
    print(f"Group {chat_id} usage incremented for '{msg_type}': {current_count + 1}")
