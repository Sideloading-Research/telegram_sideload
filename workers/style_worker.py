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

        # Get system message and context from mindfile according to worker_config
        system_message = self.get_worker_system_message(additional_prompt=user_info_prompt)
        worker_context = self.get_worker_context()
        style_prompt = construct_prompt(original_answer, chat_history_for_prompt)
        
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
