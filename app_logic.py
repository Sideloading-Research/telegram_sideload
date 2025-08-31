from conversation_manager import ConversationManager
from ai_service import get_ai_response # No longer need update_provider_from_user_input directly here
from utils.answer_modifications import modify_answer_before_sending_to_telegram
from utils.constants import c # For c.reset_dialog_command
from config import (
    BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7,
    ENABLE_ANSWER_QUALITY_CHECK_RETRIES7,
    ANSWER_QUALITY_RETRIES_NUM,
    MIN_ANSWER_QUALITY_SCORE,
    REPLACE_AI_ANSWER_WITH_TEST_ANSWER7,
    TEST_ANSWERS,
    SHOW_DIAG_INFO7
)
from telegram.constants import ChatType # ADDED - for explicit comparison
from workers.quality_checks_worker import QualityChecksWorker
from workers.style_worker import StyleWorker
from utils.prompt_utils import format_user_info_prompt


def _get_effective_username(user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> str:
    """Constructs a comprehensive username string for logging and context."""
    user_id_str = f"{user_id}"
    effective_username = f"id_{user_id_str}"
    if username:
        effective_username += f" @{username}"
    if first_name:
        effective_username += f" {first_name}"
    if last_name:
        effective_username += f" {last_name}"
    return effective_username


class AppLogic:
    def __init__(self, conversation_manager: ConversationManager, allowed_user_ids: list[int], allowed_group_ids: list[int]):
        self.conversation_manager = conversation_manager
        self.allowed_user_ids = allowed_user_ids
        self.allowed_group_ids = allowed_group_ids
        # ai_service is not stored as it's stateless for now, get_ai_response is called directly.
        # mind_manager is managed by conversation_manager for initial prompts.

    def _generate_and_verify_answer(self, messages_history: list[dict[str, str]], raw_user_message: str) -> tuple[str, str | None, dict]:
        """
        Generates an AI response, and if quality checks are enabled, verifies and retries.
        Returns the best answer, the provider report, and a dictionary with diagnostic info.
        """
        best_answer = None
        provider_report = None
        best_score_sum = -1
        best_scores = {}
        retries_taken = 0

        # Determine the number of retries
        retries = ANSWER_QUALITY_RETRIES_NUM if ENABLE_ANSWER_QUALITY_CHECK_RETRIES7 else 1
        
        # Instantiate workers outside the loop for efficiency
        quality_worker = None
        style_worker = None # ADDED
        user_info_prompt = None

        mindfile_instance = self.conversation_manager.mind_manager.get_mindfile()

        if ENABLE_ANSWER_QUALITY_CHECK_RETRIES7:
            quality_worker = QualityChecksWorker(mindfile=mindfile_instance)
            user_info_prompt = format_user_info_prompt()

        # Always instantiate style_worker to test its output
        style_worker = StyleWorker(mindfile=mindfile_instance)


        for attempt in range(retries):
            print(f"\n--- Answer Generation Attempt {attempt + 1}/{retries} ---")
            
            current_answer, current_provider_report = None, None
            use_test_answer7 = REPLACE_AI_ANSWER_WITH_TEST_ANSWER7 and attempt < retries - 1

            if use_test_answer7:
                print("Using a test answer for this attempt.")
                current_answer = TEST_ANSWERS[attempt % len(TEST_ANSWERS)]
                current_provider_report = "Used a predefined test answer for quality check."
            else:
                current_answer, current_provider_report = get_ai_response(messages_history, raw_user_message, max_length=500)
            
            # --- Style Worker Integration ---
            styled_answer = current_answer  # Fallback to the original answer
            if style_worker and current_answer:
                print("--- Running Style Worker ---")
                try:
                    styled_answer = style_worker.process(current_answer, user_info_prompt)
                    print(f"Original answer:\n---\n{current_answer}\n---")
                    print("########################################################")
                    print(f"Styled answer:\n---\n{styled_answer}\n---")
                    print("########################################################")
                except Exception as e:
                    print(f"An error occurred during style worker processing: {e}")
                    # On error, styled_answer remains as the original current_answer
                print("--- Style Worker Finished ---\n")
            # --- End of Style Worker Integration ---

            # The provider report from the first attempt is the most relevant one.
            if provider_report is None:
                provider_report = current_provider_report

            if not quality_worker:
                best_answer = styled_answer
                break

            try:
                print("--- Running Quality Check ---")
                actual_chat_history = messages_history[2:]
                
                quality_scores = quality_worker.process(
                    conversation_history=actual_chat_history[-4:],
                    original_answer=styled_answer,
                    user_info_prompt=user_info_prompt
                )
                print(f"Quality Scores: {quality_scores}")
                print("--- Quality Check Finished ---\n")

                if quality_scores and all(score is not None for score in quality_scores.values()):
                    current_score_sum = sum(quality_scores.values())
                    
                    # This block ensures that even if all answers fall below the quality threshold,
                    # we keep track of and ultimately return the one with the highest total score.
                    if best_answer is None or current_score_sum > best_score_sum:
                        best_answer = styled_answer
                        best_score_sum = current_score_sum
                        best_scores = quality_scores

                    if all(score >= MIN_ANSWER_QUALITY_SCORE for score in quality_scores.values()):
                        print("Quality standards met. Finalizing answer.")
                        retries_taken = attempt
                        best_answer = styled_answer
                        break
                    else:
                        print(f"Quality standards not met (min score: {MIN_ANSWER_QUALITY_SCORE}). Retrying...")
                else:
                    print("Quality check failed to return scores. Using this answer as a fallback.")
                    if best_answer is None:
                        best_answer = styled_answer
                    break 

            except Exception as e:
                print(f"An error occurred during the quality check: {e}")
                if best_answer is None:
                    best_answer = styled_answer
                break
        else:
            # This block runs if the loop completes without a 'break', meaning all retries were used.
            retries_taken = retries - 1 if retries > 0 else 0

        # Fallback to the last generated answer if best_answer is somehow still None
        final_ai_answer = best_answer if best_answer is not None else styled_answer
        
        diag_info = {
            "retries": retries_taken,
            "scores": best_scores,
        }
        
        return final_ai_answer, provider_report, diag_info

    def check_authorization(self, chat_type: str, user_id: int, chat_id: int) -> bool:
        """Checks if the user or chat is authorized based on type and IDs."""
        if chat_type == ChatType.PRIVATE: # Using ChatType constant
            return user_id in self.allowed_user_ids
        elif chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]: # Using ChatType constants
            return chat_id in self.allowed_group_ids
        return False

    def process_user_request(self, 
                             user_id: int, 
                             raw_user_message: str, 
                             chat_id: int,             # ADDED
                             chat_type: str,           # ADDED
                             generate_ai_reply: bool,   # ADDED
                             username: str = None, 
                             first_name: str = None, 
                             last_name: str = None) -> tuple[str | None, str | None]: # Modified return type
        """
        Processes the user's request. Adds user message to history.
        If generate_ai_reply is True, calls AI, adds AI response to history, and returns answer.
        Otherwise, returns (None, None).
        
        Returns:
            tuple[str | None, str | None]: (answer_to_send, provider_report_message_or_none)
        """
        # Determine the conversation key based on chat type and config
        if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP] and BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7:
            conversation_key = str(chat_id)
            print(f"Using CHAT_ID ({chat_id}) as conversation key for group chat.")
        else:
            conversation_key = str(user_id)
            if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                 print(f"Using USER_ID ({user_id}) as conversation key for group chat (BOT_ANSWERS_IN_GROUPS_ONLY_WHEN_MENTIONED7 is False).")
            else:
                 print(f"Using USER_ID ({user_id}) as conversation key for private chat.")

        effective_username = _get_effective_username(user_id, username, first_name, last_name)
        print(f"Processing request from user: {effective_username} in context of conversation_key: {conversation_key}. Generate AI reply: {generate_ai_reply}")

        # Handle reset command
        if raw_user_message.lower() == c.reset_dialog_command:
            if self.conversation_manager.reset_conversation(conversation_key):
                # Reset commands always provide a direct response, not from AI.
                return "Dialog has been reset.", None
            else:
                return "No active dialog to reset. Starting a new one now.", None

        formatted_user_message = f"{effective_username} wrote: {raw_user_message}"
        
        self.conversation_manager.add_user_message(conversation_key, formatted_user_message)
        
        print(f"Added user message from {effective_username} to history for key {conversation_key}.")

        if not generate_ai_reply:
            print(f"AI reply generation skipped for key {conversation_key} as per request.")
            return None, None

        # Proceed with AI response generation
        messages_history = self.conversation_manager.get_conversation_messages(conversation_key)
        
        final_ai_answer, provider_report, diag_info = self._generate_and_verify_answer(messages_history, raw_user_message)
        
        self.conversation_manager.add_assistant_message(conversation_key, final_ai_answer)
        
        print(f"Current conversation length for key {conversation_key}: {self.conversation_manager.get_conversation_length(conversation_key)}")

        final_answer = modify_answer_before_sending_to_telegram(final_ai_answer)

        if SHOW_DIAG_INFO7:
            retries = diag_info.get("retries", "N/A")
            sys_compl = diag_info.get("scores", {}).get("sys_message_compliance", "N/A")
            self_desc = diag_info.get("scores", {}).get("self_description_correctness", "N/A")
            
            diag_str = f"[quality_retries:{retries}; sys_msg_compl:{sys_compl}; self:{self_desc}]"
            
            final_answer += f"\n\n{diag_str}"
        
        return final_answer, provider_report 