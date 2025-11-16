from workers.base_worker import BaseWorker
from ai_service import get_ai_response
from utils.prompt_utils import build_initial_conversation_history, extract_conversational_messages
from prompts.doorman_worker_prompt import construct_prompt
from utils.mindfile import Mindfile
from config import DOORMAN_WORKER_MAX_TOKENS

class DoormanWorker(BaseWorker):
    def __init__(self, mindfile: Mindfile):
        super().__init__("doorman_worker")
        self.mindfile = mindfile

    def _extract_request_type(self, response_text: str) -> str | None:
        """
        Extracts the request type from the AI's response.
        First, it checks if any line (from last to first) starts with a possible type.
        If not found, it checks if any possible type is present anywhere in the response.
        """
        possible_types = ["JAILBREAK", "EXPLOITATION", "SHALLOW", "DEEP", "GENIUS"]
        lines = response_text.split('\n')

        # First pass: check line starts, from last to first
        for line in reversed(lines):
            cleaned_line = line.strip()
            for t in possible_types:
                if cleaned_line.startswith(t):
                    return t.lower()

        # Second pass: check anywhere in the response
        upper_response = response_text.upper()
        for t in possible_types:
            if t in upper_response:
                return t.lower()

        return None

    def _process(self, user_message: str, chat_history: list[dict]) -> str:
        """
        Determines if a user's request is "shallow" or "deep".

        Returns:
            str: "shallow" or "deep"
        """
        
        # Extract only conversational messages (skips system message and large context loads)
        # and take the last 5 messages for context
        conversational_messages = extract_conversational_messages(chat_history)
        
        chat_history_for_prompt = ""
        if conversational_messages:
            chat_history_for_prompt = "\n\n## Recent Conversation History:\n"
            for message in conversational_messages[-5:]:
                role = message.get("role", "unknown")
                content = message.get("content", "")
                chat_history_for_prompt += f"- {role.capitalize()}: {content}\n"

        user_prompt = construct_prompt(user_message, chat_history_for_prompt)
        
        # Get system message and context from mindfile according to worker_config
        # (not from conversation history - workers load their own data)
        system_message = self.get_worker_system_message()
        worker_context = self.get_worker_context()

        llm_conversation_history = build_initial_conversation_history(
            system_message=system_message,
            context=worker_context,
            user_prompt=user_prompt
        )

        raw_response, _, _ = get_ai_response(
            messages_history=llm_conversation_history,
            user_input_for_provider_selection=user_prompt,
            max_length=DOORMAN_WORKER_MAX_TOKENS
        )

        response_text = raw_response.strip()

        request_type = self._extract_request_type(response_text)

        if request_type:
            print(f"Doorman classification: {request_type}")
            return request_type
        
        self.record_diag_event("doorman_invalid_type", raw_response)
        print("Doorman: Could not determine request type, defaulting to 'deep'.")
        return "deep"
