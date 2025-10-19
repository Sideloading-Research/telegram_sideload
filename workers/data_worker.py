from prompts.data_worker_prompt import data_worker_prompt_addition
from workers.base_worker import BaseWorker
from utils.mindfile import Mindfile
from ai_service import get_ai_response
from config import DATA_WORKER_MAX_TOKENS
from utils.prompt_utils import build_initial_conversation_history


class DataWorker(BaseWorker):
    def __init__(
        self,
        mindfile: Mindfile,
        custom_worker_context: str | None = None,
        custom_display_name: str | None = None,
    ):
        super().__init__(
            "data_worker", custom_display_name=custom_display_name
        )
        self.mindfile = mindfile
        self.custom_worker_context = custom_worker_context

    def _get_worker_context(self) -> str:
        """
        Retrieves and formats the mindfile context for the worker.
        If a custom context is provided during initialization, it will be used instead.
        """
        if self.custom_worker_context:
            return self.custom_worker_context

        # get_context automatically excludes system_message to prevent duplication
        worker_context = self.mindfile.get_context(self.mindfile_parts)
        return worker_context

    def _process(
        self,
        messages_history: list[dict[str, str]],
        raw_user_message: str,
        user_info_prompt: str | None = None,
    ) -> tuple[str, str | None, str]:
        """
        Generates a raw AI response based on the conversation history and mindfile context.

        Args:
            messages_history (list[dict[str, str]]): Conversational messages (user/assistant exchanges).
                                                      This should already be extracted (no system message).
            raw_user_message (str): The latest raw message from the user.

        Returns:
            tuple[str, str | None, str]: A tuple containing the generated answer, 
                                        a potential provider report, and the model name used.
        """

        # Get system message and context from mindfile according to worker_config
        # (not from conversation history - workers load their own data)
        system_message = self.get_worker_system_message(additional_prompt=user_info_prompt)
        worker_context = self._get_worker_context()

        system_message += "\n\n" + data_worker_prompt_addition

        # Build initial conversation history using the standard pattern
        # (system message + context as assistant message, not as a second system message)
        llm_conversation_history = build_initial_conversation_history(
            system_message=system_message,
            context=worker_context
        )

        # Append the conversational messages (already extracted by caller)
        # These are pure user/assistant exchanges with no system message
        llm_conversation_history.extend(messages_history)

        # The last user message is already in `messages_history`.
        # `get_ai_response` uses `raw_user_message` primarily for provider selection.

        answer, provider_report, model_name = get_ai_response(
            messages_history=llm_conversation_history,
            user_input_for_provider_selection=raw_user_message,
            max_length=DATA_WORKER_MAX_TOKENS,
        )

        if not answer or not answer.strip():
            self.record_diag_event("ai_response_empty", None)
        if not model_name or model_name in ("N/A", "unknown"):
            self.record_diag_event("model_invalid", str(model_name))

        return answer, provider_report, model_name
