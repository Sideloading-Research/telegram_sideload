from workers.base_worker import BaseWorker
from utils.mindfile import Mindfile
from ai_service import get_ai_response
from utils.text_shrinkage_utils.controller import shrink_any_text
from utils.tokens import count_tokens, MAX_TOKENS_ALLOWED_IN_REQUEST
from config import TOKEN_SAFETY_MARGIN, SOURCE_TAG_OPEN, SOURCE_TAG_CLOSE
from utils.prompt_utils import build_initial_conversation_history, extract_conversational_messages
from prompts.style_worker_prompt import construct_prompt

class StyleWorker(BaseWorker):
    def __init__(self, mindfile: Mindfile):
        super().__init__("style_worker")
        self.mindfile = mindfile

    def _process(self, original_answer: str, user_info_prompt: str | None = None, chat_history: list[dict] | None = None) -> tuple[str, str]:
        if not original_answer or not original_answer.strip():
            print("StyleWorker: Received empty answer to style. Returning it as is.")
            self.record_diag_event("style_input_empty", None)
            return original_answer, "N/A"

        chat_history_for_prompt = ""
        if chat_history:
            conversational_messages = extract_conversational_messages(chat_history)
            if conversational_messages:
                chat_history_for_prompt = "\n\n## Recent Conversation History:\n"
                for message in conversational_messages[-5:]:
                    role = message.get("role", "unknown")
                    content = message.get("content", "")
                    chat_history_for_prompt += f"- {role.capitalize()}: {content}\n"

        # --- Token Calculation and Content Shrinking ---

        # 1. Calculate tokens for fixed parts of the request
        # Get system message from mindfile according to worker_config
        system_message = self.get_worker_system_message(additional_prompt=user_info_prompt)

        self_facts = self.mindfile.get_file_content('structured_self_facts')
        style_prompt = construct_prompt(original_answer, chat_history_for_prompt)
        
        fixed_content = system_message + self_facts + style_prompt
        fixed_tokens = count_tokens(fixed_content)

        # 2. Determine available tokens for shrinkable content
        max_allowed_tokens = MAX_TOKENS_ALLOWED_IN_REQUEST / TOKEN_SAFETY_MARGIN
        available_tokens_for_shrinkable = max_allowed_tokens - fixed_tokens

        if available_tokens_for_shrinkable <= 0:
            print("StyleWorker: Not enough tokens for shrinkable content. Proceeding with empty context for them.")
            self.record_diag_event("style_shrink_context_empty", None)
            shrunk_dialogs = ""
            shrunk_interviews = ""
        else:
            # 3. Allocate tokens and shrink content
            # Simple 50/50 split for now. Can be adjusted if needed.
            dialogs_token_budget = available_tokens_for_shrinkable / 2
            interviews_token_budget = available_tokens_for_shrinkable / 2

            dialogs_content = self.mindfile.get_file_content('dialogs')
            interviews_content = self.mindfile.get_file_content('interviews_etc')

            dialogs_tokens_per_char = count_tokens(dialogs_content) / max(1, len(dialogs_content))
            interviews_tokens_per_char = count_tokens(interviews_content) / max(1, len(interviews_content))

            dialogs_target_len = int(dialogs_token_budget / dialogs_tokens_per_char) if dialogs_tokens_per_char > 0 else 0
            interviews_target_len = int(interviews_token_budget / interviews_tokens_per_char) if interviews_tokens_per_char > 0 else 0

            shrunk_dialogs = shrink_any_text(dialogs_content, dialogs_target_len, 'dialogs')
            shrunk_interviews = shrink_any_text(interviews_content, interviews_target_len, 'dialogs') # Using dialogs shrinker for interviews as well

        # --- Prompt Construction ---

        worker_context = f"""
            {SOURCE_TAG_OPEN}structured_self_facts>
            {self_facts}
            {SOURCE_TAG_CLOSE}structured_self_facts>

            {SOURCE_TAG_OPEN}dialogs>
            {shrunk_dialogs}
            {SOURCE_TAG_CLOSE}dialogs>

            {SOURCE_TAG_OPEN}interviews_etc>
            {shrunk_interviews}
            {SOURCE_TAG_CLOSE}interviews_etc>
        """

        llm_conversation_history = build_initial_conversation_history(
            system_message=system_message,
            context=worker_context,
            user_prompt=style_prompt
        )

        styled_answer, _, model_name = get_ai_response(
            messages_history=llm_conversation_history,
            user_input_for_provider_selection=style_prompt,
            max_length=4000 
        )

        if not model_name or model_name in ("N/A", "unknown"):
            self.record_diag_event("style_model_invalid", str(model_name))

        return styled_answer, model_name


if __name__ == '__main__':
    pass
