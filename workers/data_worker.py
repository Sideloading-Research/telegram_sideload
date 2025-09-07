from workers.base_worker import BaseWorker
from utils.mindfile import Mindfile
from ai_service import get_ai_response

class DataWorker(BaseWorker):
    def __init__(self, mindfile: Mindfile):
        super().__init__("data_worker")
        self.mindfile = mindfile

    def _process(self, messages_history: list[dict[str, str]], raw_user_message: str, user_info_prompt: str | None = None) -> tuple[str, str | None]:
        """
        Generates a raw AI response based on the conversation history and mindfile context.

        Args:
            messages_history (list[dict[str, str]]): The history of the conversation from the ConversationManager.
            raw_user_message (str): The latest raw message from the user.

        Returns:
            tuple[str, str | None]: A tuple containing the generated answer and a potential provider report.
        """
        from config import SYSTEM_MESSAGE_FILE_WITHOUT_EXT

        system_message = self.mindfile.get_system_message()
        if user_info_prompt:
            system_message += "\n\n" + user_info_prompt
        
        # Filter out the system message from the parts list before building the context
        context_parts = [part for part in self.mindfile_parts if part != SYSTEM_MESSAGE_FILE_WITHOUT_EXT]
        worker_context = self.mindfile.get_context(context_parts)

        # Start with the foundational elements
        llm_conversation_history = [
            {"role": "system", "content": system_message},
            {"role": "system", "content": f"<context>\n{worker_context}\n</context>"},
        ]
        
        # Append the existing messages from the conversation manager
        # The history from conversation_manager already contains the formatted user messages and previous assistant responses.
        llm_conversation_history.extend(messages_history)
        
        # The last user message is already in `messages_history`.
        # `get_ai_response` uses `raw_user_message` primarily for provider selection.

        answer, provider_report = get_ai_response(
            messages_history=llm_conversation_history,
            user_input_for_provider_selection=raw_user_message,
            max_length=1500  # A higher max_length for the initial answer generation
        )

        return answer, provider_report
