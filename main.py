import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyParameters
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
import bot_config
from utils.mind_data_manager import MindDataManager
from conversation_manager import ConversationManager
from app_logic import AppLogic
from telegram.constants import ChatType, MessageEntityType, ChatAction
from telegram.error import TelegramError, BadRequest, TimedOut, NetworkError, RetryAfter

from config import BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7
from config_sanity_checks import run_sanity_checks
import config

# Initialize managers and services
# These are global instances for the bot's lifecycle.
MIND_MANAGER = MindDataManager.get_instance()
CONVERSATION_MANAGER = ConversationManager(mind_manager=MIND_MANAGER)

# Token and allowed IDs are now fetched via bot_config functions
TOKEN = bot_config.get_token()
ALLOWED_USER_IDS = bot_config.get_allowed_user_ids()
ALLOWED_GROUP_IDS = bot_config.get_allowed_group_ids()
TRIGGER_WORDS_LIST = bot_config.get_trigger_words() # Import trigger words

APPLICATION_LOGIC = AppLogic(
    conversation_manager=CONVERSATION_MANAGER,
    allowed_user_ids=ALLOWED_USER_IDS,
    allowed_group_ids=ALLOWED_GROUP_IDS
)


async def reply_text_wrapper(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    text: str,
    reply_markup=None,
    parse_mode=None,
    disable_web_page_preview=None,
    disable_notification=None,
    reply_to_message_id=None,
    allow_sending_without_reply=True,
    max_retries: int = 3,
    fallback_to_send_message: bool = True
) -> bool:
    """
    Wrapper for sending text messages with comprehensive error handling.
    
    Args:
        update: The update object
        context: The context object
        text: The text to send
        reply_markup: Optional inline keyboard markup
        parse_mode: Optional parse mode (e.g., 'HTML', 'Markdown')
        disable_web_page_preview: Optional boolean to disable link previews
        disable_notification: Optional boolean to send without notification
        reply_to_message_id: Optional message ID to reply to
        allow_sending_without_reply: If True, send even if reply_to_message_id is invalid
        max_retries: Maximum number of retry attempts for rate limits
        fallback_to_send_message: If True, fallback to context.bot.send_message if reply fails
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    if not text:
        print("Warning: Attempted to send empty message")
        return False
        
    # Truncate message if too long (Telegram limit is 4096 characters)
    if len(text) > 4096:
        print(f"Warning: Message too long ({len(text)} chars), truncating to 4096")
        text = text[:4093] + "..."
    
    for attempt in range(max_retries):
        try:
            common_args = {
                "text": text,
                "reply_markup": reply_markup,
                "parse_mode": parse_mode,
                "disable_web_page_preview": disable_web_page_preview,
                "disable_notification": disable_notification,
            }

            if update.message and hasattr(update.message, 'reply_text'):
                # Determine the actual message ID to reply to for update.message.reply_text
                # If caller provides reply_to_message_id, that takes precedence.
                # Otherwise, update.message.reply_text replies to update.message.message_id.
                effective_reply_to_msg_id = reply_to_message_id if reply_to_message_id is not None else update.message.message_id

                reply_params_obj = ReplyParameters(
                    message_id=effective_reply_to_msg_id,
                    allow_sending_without_reply=allow_sending_without_reply
                )
                await update.message.reply_text(
                    **common_args,
                    reply_parameters=reply_params_obj
                )
                return True
            elif fallback_to_send_message and update.effective_chat:
                send_args = {**common_args}
                if reply_to_message_id is not None:
                    # If caller wants to reply to a specific message via send_message
                    reply_params_obj = ReplyParameters(
                        message_id=reply_to_message_id,
                        allow_sending_without_reply=allow_sending_without_reply
                    )
                    send_args["reply_parameters"] = reply_params_obj
                else:
                    # Not replying to a specific message via send_message.
                    # Pass allow_sending_without_reply directly, as no ReplyParameters are involved.
                    send_args["allow_sending_without_reply"] = allow_sending_without_reply
                
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    **send_args
                )
                return True
            else:
                print("Error: No valid method to send message (no update.message or effective_chat)")
                return False
                
        except Exception as e:
            print(f"Error sending message (attempt {attempt + 1}/{max_retries}): {type(e).__name__}: {e}")
            
            # If this was the last attempt, give up
            if attempt == max_retries - 1:
                print(f"Failed to send message after {max_retries} attempts")
                return False
            
            # Exponential backoff: 2^attempt seconds (1s, 2s, 4s, 8s, etc.)
            wait_time = 2 ** attempt
            
            # Special handling for rate limit errors - use their suggested wait time
            if hasattr(e, 'retry_after'):
                wait_time = e.retry_after
                print(f"Rate limited. Waiting {wait_time} seconds as requested by Telegram")
            else:
                print(f"Waiting {wait_time} seconds before retry...")
            
            await asyncio.sleep(wait_time)
    
    return False


async def send_typing_periodically(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Sends typing action every 4 seconds."""
    try:
        while True:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        # This is expected when the task is cancelled.
        # You can add a print here for debugging if you want.
        pass
    except Exception as e:
        print(f"Error in send_typing_periodically: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("In the start function...")
    user = update.effective_user
    # The 'if True:' condition seems to be a placeholder for potential future logic.
    # Keeping it as is for now.
    if True:
        keyboard = [[InlineKeyboardButton("Start", callback_data="start_game")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        welcome_message = f"Hello {user.first_name}, ich bin dein hilfreicher Assistent! Clicke 'Start'"
        await reply_text_wrapper(
            update=update,
            context=context,
            text=welcome_message,
            reply_markup=reply_markup
        )


async def start_new_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "Wie kann ich dir helfen?"
    if update.message: # Can be triggered by a command
        await reply_text_wrapper(update, context, text)
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
    await reply_text_wrapper(update, context, text)


def is_allowed(update: Update) -> bool:
    """Check if the user/chat is allowed by delegating to AppLogic."""
    chat_type = update.effective_chat.type
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    return APPLICATION_LOGIC.check_authorization(chat_type, user_id, chat_id)


# Plugin Management Commands
async def plugins_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the status of all plugins."""
    if not is_allowed(update):
        await restrict(update, context)
        return
    
    status = APPLICATION_LOGIC.get_plugin_status()
    message = "**Plugin Status:**\n\n"
    for plugin_name, enabled in status.items():
        status_emoji = "✅" if enabled else "❌"
        message += f"{status_emoji} `{plugin_name}`: {'Enabled' if enabled else 'Disabled'}\n"
    
    await reply_text_wrapper(update, context, message, parse_mode="Markdown")


async def enable_plugin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enable a specific plugin."""
    if not is_allowed(update):
        await restrict(update, context)
        return
    
    if not context.args:
        await reply_text_wrapper(update, context, "Usage: /enable_plugin <plugin_name>")
        return
    
    plugin_name = context.args[0]
    if APPLICATION_LOGIC.enable_plugin(plugin_name):
        await reply_text_wrapper(update, context, f"✅ Plugin `{plugin_name}` enabled.", parse_mode="Markdown")
    else:
        await reply_text_wrapper(update, context, f"❌ Plugin `{plugin_name}` not found.", parse_mode="Markdown")


async def disable_plugin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disable a specific plugin."""
    if not is_allowed(update):
        await restrict(update, context)
        return
    
    if not context.args:
        await reply_text_wrapper(update, context, "Usage: /disable_plugin <plugin_name>")
        return
    
    plugin_name = context.args[0]
    if APPLICATION_LOGIC.disable_plugin(plugin_name):
        await reply_text_wrapper(update, context, f"❌ Plugin `{plugin_name}` disabled.", parse_mode="Markdown")
    else:
        await reply_text_wrapper(update, context, f"❌ Plugin `{plugin_name}` not found.", parse_mode="Markdown")


async def enable_all_plugins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enable all plugins."""
    if not is_allowed(update):
        await restrict(update, context)
        return
    
    APPLICATION_LOGIC.enable_all_plugins()
    await reply_text_wrapper(update, context, "✅ All plugins enabled.")


async def disable_all_plugins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disable all plugins."""
    if not is_allowed(update):
        await restrict(update, context)
        return
    
    APPLICATION_LOGIC.disable_all_plugins()
    await reply_text_wrapper(update, context, "❌ All plugins disabled.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("\nDEBUG MESSAGE INFO:")
    
    user_message_text = "<unsupported message type>" # Default
    message_text_content_for_mention_check = None # Text for mention scanning (text or caption)
    message_entities_for_mention_check = None   # Entities for mention scanning

    if update.message:
        print(f"Chat type: {update.message.chat.type}")
        # Prioritize message.text for user_message_text and mention checks
        if update.message.text:
            print(f"Message text: {update.message.text}")
            user_message_text = update.message.text
            message_text_content_for_mention_check = update.message.text
            message_entities_for_mention_check = update.message.entities
            if update.message.entities: print(f"Entities: {update.message.entities}")
        # Fallback to caption if message.text is empty but caption exists
        elif update.message.caption:
            print(f"Message caption: {update.message.caption}")
            user_message_text = update.message.caption # Use caption as the primary message content
            message_text_content_for_mention_check = update.message.caption
            message_entities_for_mention_check = update.message.caption_entities
            if update.message.caption_entities: print(f"Caption Entities: {update.message.caption_entities}")
        else:
            # Neither text nor caption (e.g. sticker, voice message without caption)
            print("Message has no text or caption.")
            # user_message_text remains "<unsupported message type>"
    else:
        # This case should ideally not be hit by a MessageHandler unless filters are very broad
        print("Update does not contain a message.")
        # user_message_text remains "<unsupported message type>"

    # admin commands
    if user_message_text == "admin:test":
        config.set_data_source_mode("QUICK_TEST")
        MIND_MANAGER.force_refresh()
        await reply_text_wrapper(update, context, "quick test mode activated")
        return
    if user_message_text == "admin:norm":
        config.set_data_source_mode("NORMAL")
        MIND_MANAGER.force_refresh()
        await reply_text_wrapper(update, context, "normal mode activated")
        return

    print(f"Chat ID: {update.effective_chat.id}")
    
    if is_allowed(update):
        typing_task = asyncio.create_task(
            send_typing_periodically(context, update.effective_chat.id)
        )
        try:
            bot_should_always_reply_in_group = False # Default for clarity, will be set by mention logic
            # Conditional group message handling for deciding IF WE REPLY
            if update.message and update.message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                if BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7:
                    bot_was_mentioned_or_replied_to = False
                    
                    if message_text_content_for_mention_check and context.bot.username:
                        bot_username_at = f"@{context.bot.username}"
                        if message_entities_for_mention_check:
                            for entity in message_entities_for_mention_check:
                                if entity.type == MessageEntityType.MENTION:
                                    mention_text = message_text_content_for_mention_check[entity.offset : entity.offset + entity.length]
                                    if mention_text == bot_username_at:
                                        bot_was_mentioned_or_replied_to = True
                                        print(f"Bot was mentioned by @username: {bot_username_at}")
                                        break
                                elif entity.type == MessageEntityType.TEXT_MENTION: 
                                    if entity.user and entity.user.id == context.bot.id:
                                        bot_was_mentioned_or_replied_to = True
                                        print(f"Bot was mentioned by text_mention (user ID: {context.bot.id})")
                                        break
                    elif not context.bot.username:
                         print("Warning: Bot username not available in context.bot.username. Mention check might be unreliable.")

                    if not bot_was_mentioned_or_replied_to and update.message.reply_to_message:
                        if update.message.reply_to_message.from_user and update.message.reply_to_message.from_user.id == context.bot.id:
                            bot_was_mentioned_or_replied_to = True
                            print("Message is a reply to the bot.")

                    # Check for trigger words if not already mentioned or replied to
                    if not bot_was_mentioned_or_replied_to and TRIGGER_WORDS_LIST and message_text_content_for_mention_check:
                        for word in TRIGGER_WORDS_LIST:
                            if word in message_text_content_for_mention_check.lower():
                                bot_was_mentioned_or_replied_to = True
                                print(f"Bot triggered by word: '{word}'")
                                break # Exit loop once a trigger word is found

                    # This variable now controls if we REPLY, not if we PROCESS
                    bot_should_always_reply_in_group = bot_was_mentioned_or_replied_to 
                    
                    if not bot_should_always_reply_in_group:
                        print(f"In group {update.effective_chat.id}, bot not mentioned/replied to. Message will be processed for history, but bot will not reply.")
                # Else (BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7 is False), bot_should_always_reply_in_group remains True

            # Message is processed for history regardless of mention status (if is_allowed)
            user_id = update.effective_user.id
            username = update.effective_user.username
            first_name = update.effective_user.first_name
            last_name = update.effective_user.last_name
            chat_id = update.effective_chat.id
            chat_type = update.effective_chat.type

            # Determine if AI reply should be generated by AppLogic
            generate_ai_reply_for_app_logic = False
            if chat_type == ChatType.PRIVATE:
                generate_ai_reply_for_app_logic = True
            elif chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                if not BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7:
                    generate_ai_reply_for_app_logic = True # Always generate if config is off
                else:
                    # Generate only if mentioned/replied to, this is the bot_should_always_reply_in_group variable
                    generate_ai_reply_for_app_logic = bot_should_always_reply_in_group 
            
            print(f"Decision for chat {chat_id} (type: {chat_type}): Generate AI reply in AppLogic? {generate_ai_reply_for_app_logic}. Bot should send reply if available? {bot_should_always_reply_in_group if chat_type != ChatType.PRIVATE else True}")

            answer, provider_report = await asyncio.to_thread(
                APPLICATION_LOGIC.process_user_request,
                user_id=user_id,
                raw_user_message=user_message_text,
                chat_id=chat_id,            
                chat_type=chat_type,  
                generate_ai_reply=generate_ai_reply_for_app_logic,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            
            # Conditional reply logic: only send if an answer was generated AND conditions met
            should_send_reply_based_on_mention_rules = False
            if chat_type == ChatType.PRIVATE:
                should_send_reply_based_on_mention_rules = True
            elif chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                if not BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7:
                    should_send_reply_based_on_mention_rules = True 
                else:
                    should_send_reply_based_on_mention_rules = bot_should_always_reply_in_group

            if answer and should_send_reply_based_on_mention_rules:
                if provider_report: 
                    await reply_text_wrapper(update, context, provider_report)
                await reply_text_wrapper(update, context, answer)
                print(f"Replied with generated answer in chat {chat_id}.")
            elif not answer and should_send_reply_based_on_mention_rules:
                 print(f"Logic indicated a reply should be sent in chat {chat_id}, but no answer was generated (generate_ai_reply was False). This is expected if not mentioned in group/mention-only mode.")
            else:
                print(f"Processed message for history in chat {chat_id}. No reply sent (either answer was None or mention rules not met).")
        finally:
            typing_task.cancel()

    else:
        await restrict(update, context)


async def handle_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if is_allowed(update):
        typing_task = asyncio.create_task(
            send_typing_periodically(context, update.effective_chat.id)
        )
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            chat_type = update.effective_chat.type
            
            # Get the text after the command
            user_input = ' '.join(context.args)
            if not user_input:
                await reply_text_wrapper(update, context, "Please provide a message after the command, like: /ask How are you?")
                return

            username = update.effective_user.username
            first_name = update.effective_user.first_name
            last_name = update.effective_user.last_name

            answer, provider_report = await asyncio.to_thread(
                APPLICATION_LOGIC.process_user_request,
                user_id=user_id,
                raw_user_message=user_input, 
                chat_id=chat_id,            
                chat_type=chat_type, 
                generate_ai_reply=True, # Commands should always generate a reply       
                username=username,
                first_name=first_name,
                last_name=last_name
            )

            if provider_report: # Send provider switch report if any
                await reply_text_wrapper(update, context, provider_report)
                
            await reply_text_wrapper(update, context, answer)
        finally:
            typing_task.cancel()
    else:
        await restrict(update, context)


def main():
    run_sanity_checks()
    
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
    
    # Plugin management commands
    app.add_handler(CommandHandler("plugins", plugins_status))
    app.add_handler(CommandHandler("enable_plugin", enable_plugin_cmd))
    app.add_handler(CommandHandler("disable_plugin", disable_plugin_cmd))
    app.add_handler(CommandHandler("enable_all_plugins", enable_all_plugins_cmd))
    app.add_handler(CommandHandler("disable_all_plugins", disable_all_plugins_cmd))
    
    app.add_handler(CallbackQueryHandler(start_game_callback, pattern="^start_game$"))
    
    allowed_message_content_filter = (filters.TEXT | filters.CAPTION) & ~filters.COMMAND

    allowed_private_messages_filter = filters.ChatType.PRIVATE & filters.User(user_id=ALLOWED_USER_IDS) & allowed_message_content_filter
    
    if ALLOWED_GROUP_IDS:
        allowed_group_messages_filter = filters.ChatType.GROUPS & filters.Chat(chat_id=ALLOWED_GROUP_IDS) & allowed_message_content_filter
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
