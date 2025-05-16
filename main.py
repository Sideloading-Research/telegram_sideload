import os
from ai_providers.rate_limited_ai_wrapper import (
    PROVIDER_FROM_ENV,
    ask_gpt_multi_message,
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
from config import ENABLE_USER_DEFINED_AI_PROVIDERS7, MAX_TELEGRAM_MESSAGE_LEN, PLATFORM_SPECIFIC_PROMPT_ADDITION
from utils.answer_modifications import modify_answer_before_sending_to_telegram
from utils.mind_data_manager import MindDataManager
from utils.creds_handler import CREDS
from utils.constants import c

# Parse USERS_INFO from environment variables
USER_DESCRIPTIONS_FROM_ENV = {}
raw_users_info = CREDS.get("USERS_INFO", "")
if raw_users_info:
    try:
        user_entries = raw_users_info.split(';')
        for entry in user_entries:
            if entry.strip(): # Ensure entry is not just whitespace
                parts = entry.split(':', 1)
                if len(parts) == 2:
                    user_id = parts[0].strip()
                    description = parts[1].strip()
                    if user_id and description: # Ensure both user_id and description are non-empty
                        USER_DESCRIPTIONS_FROM_ENV[user_id] = description
                else:
                    print(f"Warning: Malformed entry in USERS_INFO: '{entry}'")
    except Exception as e:
        print(f"Warning: Could not parse USERS_INFO environment variable: {e}")


"""
Note:
Currently, it's limiting the number of messages from the user by keeping only the last MAX_MESSAGES_NUM messages.
It was selected as the most user-friendly option, even if it's costlier.
Some possible alternative strategies:
- maybe detect a change of topic and reset the chat
- add the reset chat button
- reset after a night
--- save the ts of the latest msg
--- if the latest msg by the user was yesterday, and more than 5h elapsed, then reset

"""

PROVIDER_INDICATORS = {  # the indicators are case-insensitive
    "openai": ["o:", "о:"],  # Russian and Latin
    "anthropic": ["a:", "а:", "c:", "с:"],  # Russian and Latin
}  # if the user message starts with any of the indicators, use the provider

SELECTED_PROVIDER = None

# Retrieve token from CREDS
TOKEN = CREDS.get("TELEGRAM_LLM_BOT_TOKEN")
if not TOKEN:
    raise ValueError(
        "No token provided. Set the TELEGRAM_LLM_BOT_TOKEN environment variable."
    )


allowed_ids_str = CREDS.get("ALLOWED_USER_IDS")

# Convert the string of comma-separated integers to a list of integers
ALLOWED_USER_IDS = [int(user_id.strip()) for user_id in allowed_ids_str.split(",")]

# Add near the top with other constants
allowed_groups_str = CREDS.get("ALLOWED_GROUP_IDS", "")
ALLOWED_GROUP_IDS = [int(group_id.strip()) for group_id in allowed_groups_str.split(",") if group_id.strip()]

MAX_MESSAGES_NUM = 50
MESSAGES_BY_USER = {} # user_id -> messages_list
MIND_MANAGER = MindDataManager.get_instance() 


# Helper function to format user information
def format_user_info_prompt(user_descriptions_dict):
    if not user_descriptions_dict:
        return ""
    
    formatted_items = []
    for user_id, description in user_descriptions_dict.items():
        formatted_items.append(f"- {user_id}: {description}")
    
    return "Some known users:\n" + "\n".join(formatted_items)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("In the start function...")

    user = update.effective_user

    if True:
        keyboard = [[InlineKeyboardButton("Start", callback_data="start_game")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        welcome_message = f"Hello {user.first_name}, ich bin dein hilfreicher Assistent! Clicke 'Start'"
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_message,
            reply_markup=reply_markup,
        )


async def start_new_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "Wie kann ich dir helfen?"
    if update.message:
        await update.message.reply_text(text)
    else:
        await update.callback_query.edit_message_text(text)


async def start_game_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    await start_new_game(update, context)


def update_provider_from_user_input(user_input):
    if not ENABLE_USER_DEFINED_AI_PROVIDERS7:
        return False, ""
        
    switch7 = False
    report = ""
    for provider, indicators in PROVIDER_INDICATORS.items():
        for indicator in indicators:
            if user_input.lower().startswith(indicator):
                global SELECTED_PROVIDER
                if provider != SELECTED_PROVIDER:
                    switch7 = True
                    if SELECTED_PROVIDER is None:
                        SELECTED_PROVIDER = PROVIDER_FROM_ENV
                    report = f"{SELECTED_PROVIDER} -> {provider}"
                    print(report)
                SELECTED_PROVIDER = provider
                return switch7, report
    return switch7, report


def build_initial_assistant_messages():
    """Returns the initial messages that should be present in every conversation."""
    system_message, context = MIND_MANAGER.get_current_data()

    user_info_prompt_addition = format_user_info_prompt(USER_DESCRIPTIONS_FROM_ENV)
    print(f"User info prompt addition: {user_info_prompt_addition}")

    full_system_message = system_message
    if PLATFORM_SPECIFIC_PROMPT_ADDITION:
        full_system_message += "\n\n" + PLATFORM_SPECIFIC_PROMPT_ADDITION
    if user_info_prompt_addition:
        full_system_message += "\n\n" + user_info_prompt_addition
    
    # Debug print
    # print(f"Full system message being used:\n{full_system_message}")

    return [
        {"role": "system", "content": full_system_message},
        {"role": "assistant", "content": context}
    ]


async def restrict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if update.effective_chat.type == 'private':
        text = f"Keine Berechtigung für user_id {user_id}."
    else:
        text = f"This group (ID: {chat_id}) is not authorized to use this bot."
    
    print(text)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
    )


def is_allowed(update: Update) -> bool:
    """Check if the user/chat is allowed to use the bot"""
    chat_type = update.effective_chat.type
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if chat_type == 'private':
        return user_id in ALLOWED_USER_IDS
    else:  # group/supergroup
        return chat_id in ALLOWED_GROUP_IDS


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("\nDEBUG MESSAGE INFO:")
    print(f"Message text: {update.message.text}")
    print(f"Chat type: {update.message.chat.type}")
    print(f"Chat ID: {update.effective_chat.id}")
    print(f"Entities: {update.message.entities}")
    print(f"From user: {update.effective_user.username} (ID: {update.effective_user.id})")
    
    if is_allowed(update):
        user_id = update.effective_user.id
        user_message = update.message.text
        username = update.effective_user.username or update.effective_user.first_name or f"user_{user_id}"
        formatted_message = f"{username} wrote: {user_message}"
        
        # Check for reset dialog command
        if user_message.lower() == c.reset_dialog_command:
            if user_id in MESSAGES_BY_USER:
                MESSAGES_BY_USER[user_id] = build_initial_assistant_messages()
                await update.message.reply_text("Dialog has been reset.")
            else:
                await update.message.reply_text("No dialog history to reset.")
            return

        if user_id in MESSAGES_BY_USER:
            MESSAGES_BY_USER[user_id].append(
                {"role": "user", "content": formatted_message},
            )

        else:  # the user posted his first message
            MESSAGES_BY_USER[user_id] = build_initial_assistant_messages() + [
                {"role": "user", "content": formatted_message},
            ]

        answer = ask_gpt_multi_message(
            MESSAGES_BY_USER[user_id],
            max_length=500,
            user_defined_provider=SELECTED_PROVIDER,
        )

        MESSAGES_BY_USER[user_id].append(
            {"role": "assistant", "content": answer},
        )

        # remove the oldest messages. We keep only the last MAX_MESSAGES_NUM messages
        if len(MESSAGES_BY_USER[user_id]) > MAX_MESSAGES_NUM:
            MESSAGES_BY_USER[user_id] = MESSAGES_BY_USER[user_id][-MAX_MESSAGES_NUM:]

            # attach the initial messages to the beginning
            MESSAGES_BY_USER[user_id] = build_initial_assistant_messages() + MESSAGES_BY_USER[user_id]
        print(f"Messages length: {len(MESSAGES_BY_USER[user_id])}")

        answer = modify_answer_before_sending_to_telegram(answer)
        await update.message.reply_text(answer)
    else:
        await restrict(update, context)


async def handle_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if is_allowed(update):
        user_id = update.effective_user.id
        
        # Get the text after the command
        user_input = ' '.join(context.args)
        if not user_input:
            await update.message.reply_text("Please provide a message after the command, like: /ask How are you?")
            return

        username = update.effective_user.username or update.effective_user.first_name or f"user_{user_id}"
        formatted_message = f"{username} wrote: {user_input}"

        # Process the message similar to handle_message
        if user_id in MESSAGES_BY_USER:
            MESSAGES_BY_USER[user_id].append(
                {"role": "user", "content": formatted_message},
            )
        else:
            MESSAGES_BY_USER[user_id] = build_initial_assistant_messages() + [
                {"role": "user", "content": formatted_message},
            ]

        answer = ask_gpt_multi_message(
            MESSAGES_BY_USER[user_id],
            max_length=500,
            user_defined_provider=SELECTED_PROVIDER,
        )

        MESSAGES_BY_USER[user_id].append(
            {"role": "assistant", "content": answer},
        )

        # Manage message history
        if len(MESSAGES_BY_USER[user_id]) > MAX_MESSAGES_NUM:
            MESSAGES_BY_USER[user_id] = MESSAGES_BY_USER[user_id][-MAX_MESSAGES_NUM:]
            MESSAGES_BY_USER[user_id] = build_initial_assistant_messages() + MESSAGES_BY_USER[user_id]

        answer = modify_answer_before_sending_to_telegram(answer)
        await update.message.reply_text(answer)
    else:
        await restrict(update, context)


def main():
    app = Application.builder().token(TOKEN).build()

    # Update the restrict handler to use the new logic
    restrict_handler = MessageHandler(
        filters.ALL & ~filters.User(ALLOWED_USER_IDS) & filters.ChatType.PRIVATE |  # Private chat restrictions
        filters.ALL & ~filters.Chat(ALLOWED_GROUP_IDS) & filters.ChatType.GROUPS,   # Group restrictions
        restrict
    )
    app.add_handler(restrict_handler)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", handle_group_command))
    app.add_handler(CallbackQueryHandler(start_game_callback, pattern="^start_game$"))
    
    # Modified message handler to catch all messages in groups for debugging
    app.add_handler(MessageHandler(
        (filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE) |  # Private chats
        (filters.TEXT & filters.ChatType.GROUPS),  # All group messages for debugging
        handle_message
    ))
    
    app.run_polling()


if __name__ == "__main__":
    main()
