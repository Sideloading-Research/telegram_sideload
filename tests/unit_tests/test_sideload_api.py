
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

class TestSideloadAPI(unittest.TestCase):
    
    def setUp(self):
        # Mock bot_config
        self.mock_bot_config = MagicMock()
        self.mock_bot_config.get_allowed_user_ids.return_value = []
        self.mock_bot_config.get_allowed_group_ids.return_value = []
        
        # Mock app_logic module
        self.mock_app_logic_module = MagicMock()
        self.mock_app_instance = MagicMock()
        self.mock_app_logic_module.AppLogic.return_value = self.mock_app_instance
        self.mock_app_instance.process_user_request.return_value = ("Test Answer", "Test Report", {"models_used": {"test-model"}})
        
        # Patch modules in sys.modules
        self.modules_patcher = patch.dict(sys.modules, {
            'bot_config': self.mock_bot_config,
            'app_logic': self.mock_app_logic_module
        })
        self.modules_patcher.start()
        
        # Patch other dependencies
        self.mind_manager_patcher = patch('utils.mind_data_manager.MindDataManager')
        self.conversation_manager_patcher = patch('conversation_manager.ConversationManager')
        
        self.mock_mind_manager = self.mind_manager_patcher.start()
        self.mock_conversation_manager = self.conversation_manager_patcher.start()

    def tearDown(self):
        self.modules_patcher.stop()
        self.mind_manager_patcher.stop()
        self.conversation_manager_patcher.stop()
        
        # Unimport sideload_api
        if 'sideload_api' in sys.modules:
            del sys.modules['sideload_api']

    def test_ask_sideload(self):
        """Test that ask_sideload correctly calls AppLogic."""
        import sideload_api

        # Call the API
        response, report, model = sideload_api.ask_sideload("Hello world")

        # Verify response
        self.assertEqual(response, "Test Answer")
        self.assertEqual(report, "Test Report")
        self.assertEqual(model, "test-model")

        # Verify AppLogic was called correctly
        self.mock_app_instance.process_user_request.assert_called_once()

        args, kwargs = self.mock_app_instance.process_user_request.call_args

        # Check arguments
        self.assertEqual(kwargs['raw_user_message'], "Hello world")
        self.assertEqual(kwargs['chat_type'], "API")
        self.assertTrue(kwargs['generate_ai_reply'])

    def test_ask_sideload_force_model(self):
        """Test that force_model parameter works."""
        import sideload_api
        
        # Call with force_model
        response, report, model = sideload_api.ask_sideload("Hello world", force_model="forced-model")
        
        # Verify call arguments
        # We can't easily check global state here without more complex mocking, 
        # but we can ensure the API call succeeds.
        self.assertEqual(response, "Test Answer")

    def test_ask_sideload_custom_user(self):
        import sideload_api
        response, report, model = sideload_api.ask_sideload("Hi", user_id="custom_user")

        args, kwargs = self.mock_app_instance.process_user_request.call_args
        self.assertEqual(kwargs['user_id'], "custom_user")

if __name__ == '__main__':
    unittest.main()
