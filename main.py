import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

# Refactored imports
import bot_config
from utils.mind_data_manager import MindDataManager
from conversation_manager import ConversationManager
from app_logic import AppLogic

# Initialize managers and services
# These are global instances for the bot's lifecycle.
MIND_MANAGER = MindDataManager.get_instance()
CONVERSATION_MANAGER = ConversationManager(mind_manager=MIND_MANAGER)

# Token and allowed IDs are now fetched via bot_config functions
TOKEN = bot_config.get_token()
ALLOWED_USER_IDS = bot_config.get_allowed_user_ids()
ALLOWED_GROUP_IDS = bot_config.get_allowed_group_ids()

APPLICATION_LOGIC = AppLogic(
    conversation_manager=CONVERSATION_MANAGER,
    allowed_user_ids=ALLOWED_USER_IDS,
    allowed_group_ids=ALLOWED_GROUP_IDS
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("In the start function...")
    user = update.effective_user
    # The 'if True:' condition seems to be a placeholder for potential future logic.
    # Keeping it as is for now.
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
    if update.message: # Can be triggered by a command
        await update.message.reply_text(text)
    elif update.callback_query: # Can be triggered by a button press
        await update.callback_query.edit_message_text(text)


async def start_game_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    # Forwards to start_new_game to send the actual "Wie kann ich dir helfen?" message
    await start_new_game(update, context)


async def restrict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if update.effective_chat.type == 'private':
        text = f"Keine Berechtigung für user_id {user_id}."
    else: # group/supergroup
        text = f"This group (ID: {chat_id}) is not authorized to use this bot."
    
    print(text)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
    )


def is_allowed(update: Update) -> bool:
    """Check if the user/chat is allowed by delegating to AppLogic."""
    chat_type = update.effective_chat.type
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    return APPLICATION_LOGIC.check_authorization(chat_type, user_id, chat_id)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("\nDEBUG MESSAGE INFO:")
    if update.message is not None:
        print(f"Message text: {update.message.text}")
        print(f"Chat type: {update.message.chat.type}")
        print(f"Entities: {update.message.entities}")
        user_message_text = update.message.text if update.message.text else "<unsupported message type>"
    else:
        print("Message is None (e.g. an image)")
        user_message_text = "<unsupported message type>" # Or handle differently if needed

    print(f"Chat ID: {update.effective_chat.id}")
    
    if is_allowed(update):
        user_id = update.effective_user.id
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name

        answer, provider_report = APPLICATION_LOGIC.process_user_request(
            user_id=user_id,
            raw_user_message=user_message_text,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        
        if provider_report and update.message: # Send provider switch report if any
            await update.message.reply_text(provider_report)

        if update.message: # Ensure there's a message to reply to
            await update.message.reply_text(answer)
        elif update.effective_chat.id: # Fallback if no direct message (e.g. channel post bot is part of)
             await context.bot.send_message(chat_id=update.effective_chat.id, text=answer)

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

        username = update.effective_user.username
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name

        answer, provider_report = APPLICATION_LOGIC.process_user_request(
            user_id=user_id,
            raw_user_message=user_input, # Use the command argument as the message
            username=username,
            first_name=first_name,
            last_name=last_name
        )

        if provider_report: # Send provider switch report if any
            await update.message.reply_text(provider_report)
            
        await update.message.reply_text(answer)
    else:
        await restrict(update, context)


def main():
    app = Application.builder().token(TOKEN).build()

    # Define combined filter for private chats not in ALLOWED_USER_IDS
    private_chat_filter_restricted = filters.ChatType.PRIVATE & ~filters.User(user_id=ALLOWED_USER_IDS)
    
    # Define combined filter for group chats not in ALLOWED_GROUP_IDS
    if ALLOWED_GROUP_IDS:
        group_chat_filter_restricted = filters.ChatType.GROUPS & ~filters.Chat(chat_id=ALLOWED_GROUP_IDS)
    else: 
        group_chat_filter_restricted = filters.ChatType.GROUPS 

    restrict_handler = MessageHandler(
        private_chat_filter_restricted | group_chat_filter_restricted,
        restrict
    )
    app.add_handler(restrict_handler, group=-1) 

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", handle_group_command)) 
    app.add_handler(CallbackQueryHandler(start_game_callback, pattern="^start_game$"))
    
    allowed_private_messages_filter = filters.ChatType.PRIVATE & filters.User(user_id=ALLOWED_USER_IDS) & filters.TEXT & ~filters.COMMAND
    
    if ALLOWED_GROUP_IDS:
        allowed_group_messages_filter = filters.ChatType.GROUPS & filters.Chat(chat_id=ALLOWED_GROUP_IDS) & filters.TEXT
    else: 
        allowed_group_messages_filter = filters.NONE 

    app.add_handler(MessageHandler(
        allowed_private_messages_filter | allowed_group_messages_filter,
        handle_message
    ))
    
    print("Bot polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
