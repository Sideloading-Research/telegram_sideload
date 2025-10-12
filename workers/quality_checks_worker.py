import re

from config import QUALITY_CHECKS_WORKER_MAX_TOKENS
from prompts.quality_checks_worker_prompt import construct_prompt
from workers.base_worker import BaseWorker
from utils.mindfile import Mindfile
from ai_service import get_ai_response
from utils.prompt_utils import build_initial_conversation_history

class QualityChecksWorker(BaseWorker):
    def __init__(self, mindfile: Mindfile):
        super().__init__("quality_checks_worker")
        self.mindfile = mindfile



    def _process(self, conversation_history: list[dict[str, str]], original_answer: str, user_info_prompt: str | None = None) -> tuple[dict[str, int | None], str]:
        if not original_answer or not original_answer.strip():
            print("QualityChecksWorker: Received empty answer to check. Returning None.")
            return {
                "sys_message_compliance": None,
                "self_description_correctness": None,
                #"factual_correctness": None, # disabled for now
                #"style_similarity": None, # disabled for now
            }, "N/A"

        # Get system message and context from mindfile according to worker_config
        # (not from conversation history - workers load their own data)
        system_message = self.get_worker_system_message(additional_prompt=user_info_prompt)
        worker_context = self.get_worker_context()
        quality_prompt = construct_prompt(conversation_history, original_answer)

        llm_conversation_history = build_initial_conversation_history(
            system_message=system_message,
            context=worker_context,
            user_prompt=quality_prompt
        )

        # We don't need the provider report for this internal call.
        raw_quality_assessment, _, model_name = get_ai_response(
            messages_history=llm_conversation_history,
            user_input_for_provider_selection=quality_prompt, # The prompt itself is used for provider selection logic
            max_length=QUALITY_CHECKS_WORKER_MAX_TOKENS 
        )

        if not raw_quality_assessment or not raw_quality_assessment.strip():
            self.record_diag_event("quality_assessment_empty", None)
        if not model_name or model_name in ("N/A", "unknown"):
            self.record_diag_event("quality_model_invalid", str(model_name))

        print(f"QualityChecksWorker: Raw quality assessment: {raw_quality_assessment}")

        return self._parse_scores(raw_quality_assessment), model_name

    def _parse_scores(self, assessment_text: str) -> dict[str, int | None]:
        scores = {
            "sys_message_compliance": None,
            "self_description_correctness": None,
            #"factual_correctness": None, # disabled for now
            #"style_similarity": None, # disabled for now
        }
        
        if not assessment_text:
            return scores

        # Regex to find key-score pairs, allowing for different separators and optional whitespace.
        # It looks for lines starting with one of the score keys.
        for key in scores.keys():
            match = re.search(fr"^{key}\s*[:\-]\s*(\d+)", assessment_text, re.IGNORECASE | re.MULTILINE)
            if match:
                try:
                    score = int(match.group(1))
                    scores[key] = max(1, min(10, score)) # Clamp score between 1 and 10
                except (ValueError, IndexError):
                    print(f"QualityChecksWorker: Could not parse score for '{key}' from assessment.")
                    
        return scores
