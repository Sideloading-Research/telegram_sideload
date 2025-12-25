import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from telegram import Update, Message, User, Chat, MessageEntity
from telegram.constants import ChatType, MessageEntityType
from telegram.ext import ContextTypes
import sys
import os

# Adjust path to import main
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import main
from main import handle_message
import config

class TestHandleMessage(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.update = MagicMock(spec=Update)
        self.context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        self.update.effective_user = MagicMock(spec=User)
        self.update.effective_chat = MagicMock(spec=Chat)
        self.update.message = MagicMock(spec=Message)
        
        # Default mock values
        self.update.effective_user.id = 12345
        self.update.effective_user.username = "testuser"
        self.update.effective_user.first_name = "Test"
        self.update.effective_user.last_name = "User"
        self.update.effective_chat.id = 67890
        self.update.effective_chat.type = ChatType.PRIVATE
        self.update.message.text = "Hello bot"
        self.update.message.caption = None
        self.update.message.entities = []
        self.update.message.caption_entities = []
        self.update.message.reply_to_message = None
        
        self.context.bot.id = 999
        self.context.bot.username = "mybot"
        
        # Patch dependencies
        self.is_allowed_patcher = patch('main.is_allowed')
        self.mock_is_allowed = self.is_allowed_patcher.start()
        
        self.is_global_rate_limited_patcher = patch('main.is_global_rate_limited')
        self.mock_rate_limiter = self.is_global_rate_limited_patcher.start()
        
        self.app_logic_patcher = patch('main.APPLICATION_LOGIC')
        self.mock_app_logic = self.app_logic_patcher.start()
        # process_user_request is not async in AppLogic, but it's called via asyncio.to_thread
        # When mocked, asyncio.to_thread just runs the mock.
        # So we should mock it as a regular function returning the tuple, NOT AsyncMock
        self.mock_app_logic.process_user_request = MagicMock(return_value=("AI Answer", None, {}))
        
        self.reply_text_wrapper_patcher = patch('main.reply_text_wrapper', new_callable=AsyncMock)
        self.mock_reply = self.reply_text_wrapper_patcher.start()
        
        self.typing_patcher = patch('main.send_typing_periodically', new_callable=AsyncMock)
        self.mock_typing = self.typing_patcher.start()
        
        # Default behavior: allowed, not rate limited
        self.mock_is_allowed.return_value = True
        self.mock_rate_limiter.return_value = (False, False)

    async def asyncTearDown(self):
        self.is_allowed_patcher.stop()
        self.is_global_rate_limited_patcher.stop()
        self.app_logic_patcher.stop()
        self.reply_text_wrapper_patcher.stop()
        self.typing_patcher.stop()

    async def test_private_chat_normal_flow(self):
        """Test a normal message in private chat generates reply."""
        await handle_message(self.update, self.context)
        
        self.mock_rate_limiter.assert_called_once()
        self.mock_app_logic.process_user_request.assert_called_once()
        args, kwargs = self.mock_app_logic.process_user_request.call_args
        self.assertTrue(kwargs['generate_ai_reply'])
        self.mock_reply.assert_called_with(self.update, self.context, "AI Answer")

    async def test_private_chat_rate_limited_silent(self):
        """Test rate limit blocking silently in private chat."""
        self.mock_rate_limiter.return_value = (True, False)
        
        await handle_message(self.update, self.context)
        
        self.mock_app_logic.process_user_request.assert_not_called()
        self.mock_reply.assert_not_called()

    async def test_private_chat_rate_limited_warning(self):
        """Test rate limit blocking with warning in private chat."""
        self.mock_rate_limiter.return_value = (True, True)
        
        await handle_message(self.update, self.context)
        
        self.mock_app_logic.process_user_request.assert_not_called()
        self.mock_reply.assert_called_once() # Should reply with warning

    async def test_group_chat_no_mention_monitoring(self):
        """Test group message without mention (passive monitoring)."""
        self.update.effective_chat.type = ChatType.GROUP
        self.update.message.chat.type = ChatType.GROUP # Fix: Ensure message.chat.type is set
        # Config: BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7 = True (default assumption in code logic)
        with patch('main.BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7', True):
            await handle_message(self.update, self.context)
            
            # Should NOT check rate limit
            self.mock_rate_limiter.assert_not_called()
            
            # Should process request but NOT generate AI reply
            self.mock_app_logic.process_user_request.assert_called_once()
            args, kwargs = self.mock_app_logic.process_user_request.call_args
            self.assertFalse(kwargs['generate_ai_reply'])
            
            # Should NOT reply
            self.mock_reply.assert_not_called()

    async def test_group_chat_with_mention(self):
        """Test group message with @mention."""
        self.update.effective_chat.type = ChatType.GROUP
        self.update.message.chat.type = ChatType.GROUP # Fix: Ensure message.chat.type is set
        self.update.message.text = "@mybot hello"
        entity = MessageEntity(type=MessageEntityType.MENTION, offset=0, length=6)
        self.update.message.entities = [entity]
        
        with patch('main.BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7', True):
            await handle_message(self.update, self.context)
            
            # Should check rate limit
            self.mock_rate_limiter.assert_called_once()
            
            # Should generate AI reply
            self.mock_app_logic.process_user_request.assert_called_once()
            args, kwargs = self.mock_app_logic.process_user_request.call_args
            self.assertTrue(kwargs['generate_ai_reply'])
            
            # Should reply
            self.mock_reply.assert_called()

    async def test_group_chat_reply_to_bot(self):
        """Test group message replying to bot."""
        self.update.effective_chat.type = ChatType.GROUP
        self.update.message.chat.type = ChatType.GROUP # Fix: Ensure message.chat.type is set
        reply_msg = MagicMock(spec=Message)
        reply_msg.from_user = MagicMock(spec=User)
        reply_msg.from_user.id = 999 # Bot ID
        self.update.message.reply_to_message = reply_msg
        
        with patch('main.BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7', True):
            await handle_message(self.update, self.context)
            
            self.mock_rate_limiter.assert_called_once()
            self.assertTrue(self.mock_app_logic.process_user_request.call_args[1]['generate_ai_reply'])
            self.mock_reply.assert_called()

    async def test_group_chat_trigger_word(self):
        """Test group message with trigger word."""
        self.update.effective_chat.type = ChatType.GROUP
        self.update.message.chat.type = ChatType.GROUP # Fix: Ensure message.chat.type is set
        self.update.message.text = "hey computer help me"
        
        with patch('main.BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7', True), \
             patch('main.TRIGGER_WORDS_LIST', ['computer']):
            await handle_message(self.update, self.context)
            
            self.mock_rate_limiter.assert_called_once()
            self.assertTrue(self.mock_app_logic.process_user_request.call_args[1]['generate_ai_reply'])
            self.mock_reply.assert_called()

    async def test_group_chat_always_reply_mode(self):
        """Test group chat when BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7 is False."""
        self.update.effective_chat.type = ChatType.GROUP
        self.update.message.chat.type = ChatType.GROUP # Fix: Ensure message.chat.type is set
        
        with patch('main.BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7', False):
            await handle_message(self.update, self.context)
            
            # Should check rate limit even without mention
            self.mock_rate_limiter.assert_called_once()
            
            # Should generate AI reply
            self.assertTrue(self.mock_app_logic.process_user_request.call_args[1]['generate_ai_reply'])
            
            # Should reply
            self.mock_reply.assert_called()

    async def test_not_allowed(self):
        """Test when user/chat is not allowed."""
        self.mock_is_allowed.return_value = False
        # We need to mock restrict function which is called when not allowed
        with patch('main.restrict', new_callable=AsyncMock) as mock_restrict:
            await handle_message(self.update, self.context)
            mock_restrict.assert_called_once()
            self.mock_app_logic.process_user_request.assert_not_called()

if __name__ == '__main__':
    unittest.main()

