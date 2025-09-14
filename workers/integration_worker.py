from workers.base_worker import BaseWorker
from utils.mindfile import Mindfile
from workers.quality_checks_worker import QualityChecksWorker
from workers.style_worker import StyleWorker
from workers.data_worker import DataWorker
from utils.prompt_utils import format_user_info_prompt
from utils.tags_utils import optionally_remove_answer_sections
from config import (
    ANSWER_QUALITY_RETRIES_NUM,
    MIN_ANSWER_QUALITY_SCORE,
)

class IntegrationWorker(BaseWorker):
    def __init__(self, mindfile: Mindfile):
        super().__init__("integration_worker")
        self.mindfile = mindfile
        self.quality_worker = None
        self.style_worker = None
        self.generalist_data_worker = None
        self.compendium_data_workers: list[DataWorker] = []
        self.user_info_prompt = None

    def _initialize_workers(self):
        """Initializes all necessary worker instances."""
        self.quality_worker = QualityChecksWorker(mindfile=self.mindfile)
        self.user_info_prompt = format_user_info_prompt()
        self.style_worker = StyleWorker(mindfile=self.mindfile)
        self.generalist_data_worker = DataWorker(mindfile=self.mindfile)

        compendiums = self.mindfile.get_mindfile_data_packed_into_compendiums()
        for i, compendium in enumerate(compendiums):
            starting_chars = compendium[:100].replace("#", "")
            num_name = f"{i+1}_of_{len(compendiums)}"
            worker = DataWorker(
                mindfile=self.mindfile,
                custom_worker_context=compendium,
                custom_display_name=f"Compendium worker {num_name}: {starting_chars}",
            )
            self.compendium_data_workers.append(worker)

    def poll_data_workers(
        self, actual_chat_history: list[dict[str, str]], raw_user_message: str
    ) -> tuple[list[str], str | None]:
        """
        Polls all data workers and returns their answers.
        The generalist worker's answer is always at index 0.
        """
        answers = []
        generalist_answer, provider_report = self.generalist_data_worker.process(
            actual_chat_history, raw_user_message, self.user_info_prompt
        )
        cleaned_generalist_answer = optionally_remove_answer_sections(
            generalist_answer, remove_cot7=True, remove_internal_dialog7=True
        )
        answers.append(cleaned_generalist_answer)

        for worker in self.compendium_data_workers:
            answer, _ = worker.process(
                actual_chat_history, raw_user_message, self.user_info_prompt
            )
            print(f"--- Answer from {worker.display_name} ---\n{answer}\n---")
            cleaned_answer = optionally_remove_answer_sections(
                answer, remove_cot7=True, remove_internal_dialog7=True
            )
            answers.append(cleaned_answer)

        return answers, provider_report

    def merge_answers(self, answers: list[str]) -> str:
        """Merges a list of answers into a single string."""
        separator = "\n--------------\n"
        res = ""
        for answer in answers:
            res += answer + separator
        res = res[:-len(separator)]
        print(f"Merged answers:\n##\n{res}\n##")
        return res

    def _get_initial_answer(
        self, messages_history: list[dict[str, str]], raw_user_message: str
    ) -> tuple[str, str | None]:
        """
        Gets an initial answer from the generalist data worker and polls compendium workers.
        """
        actual_chat_history = messages_history[2:]
        
        answers, provider_report = self.poll_data_workers(
            actual_chat_history, raw_user_message
        )
        current_answer = self.merge_answers(answers)

        return current_answer, provider_report

    def _apply_style(self, answer: str) -> str:
        """Applies styling to the answer using the StyleWorker."""
        if not self.style_worker or not answer:
            return answer
        
        try:
            styled_answer = self.style_worker.process(answer, self.user_info_prompt)
            print(f"Original answer:\n---\n{answer}\n---")
            print("########################################################")
            print(f"Styled answer:\n---\n{styled_answer}\n---")
            print("########################################################")
            return styled_answer
        except Exception as e:
            print(f"An error occurred during style worker processing: {e}")
            return answer

    def _evaluate_quality(self, messages_history: list[dict[str, str]], answer: str) -> dict | None:
        """Evaluates the quality of the answer using the QualityChecksWorker."""
        try:
            actual_chat_history = messages_history[2:]
            quality_scores = self.quality_worker.process(
                conversation_history=actual_chat_history[-4:],
                original_answer=answer,
                user_info_prompt=self.user_info_prompt
            )
            print(f"Quality Scores: {quality_scores}")
            return quality_scores
        except Exception as e:
            print(f"An error occurred during the quality check: {e}")
            return None

    def _update_best_answer(self, current_answer: str, quality_scores: dict, best_answer_data: dict) -> bool:
        """
        Updates the best answer based on quality scores.
        Returns True if the quality threshold is met.
        """
        if not quality_scores or not all(score is not None for score in quality_scores.values()):
            print("Quality check failed to return scores. Using this answer as a fallback.")
            if best_answer_data["answer"] is None:
                best_answer_data["answer"] = current_answer
            return True # Break the loop

        current_score_sum = sum(quality_scores.values())
        if best_answer_data["answer"] is None or current_score_sum > best_answer_data["score_sum"]:
            best_answer_data["answer"] = current_answer
            best_answer_data["score_sum"] = current_score_sum
            best_answer_data["scores"] = quality_scores

        if all(score >= MIN_ANSWER_QUALITY_SCORE for score in quality_scores.values()):
            print("Quality standards met. Finalizing answer.")
            return True # Break the loop
        
        print(f"Quality standards not met (min score: {MIN_ANSWER_QUALITY_SCORE}). Retrying...")
        return False

    def _process(self, messages_history: list[dict[str, str]], raw_user_message: str) -> tuple[str, str | None, dict]:
        self._initialize_workers()

        best_answer_data = {"answer": None, "score_sum": -1, "scores": {}}
        provider_report = None
        retries_taken = 0
        
        retries = ANSWER_QUALITY_RETRIES_NUM

        for attempt in range(retries):
            print(f"\n--- Answer Generation Attempt {attempt + 1}/{retries} ---")
            retries_taken = attempt

            current_answer, current_provider_report = self._get_initial_answer(messages_history, raw_user_message)
            
            if provider_report is None:
                provider_report = current_provider_report

            styled_answer = self._apply_style(current_answer)

            quality_scores = self._evaluate_quality(messages_history, styled_answer)

            should_break = self._update_best_answer(styled_answer, quality_scores, best_answer_data)
            if should_break:
                break
        else: # This block runs if the loop completes without a 'break'
            retries_taken = retries

        final_ai_answer = best_answer_data["answer"] if best_answer_data["answer"] is not None else ""
        
        diag_info = {
            "retries": retries_taken,
            "scores": best_answer_data["scores"],
        }
        
        return final_ai_answer, provider_report, diag_info
