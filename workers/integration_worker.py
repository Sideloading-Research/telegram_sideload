from workers.base_worker import BaseWorker
from utils.mindfile import Mindfile
from workers.quality_checks_worker import QualityChecksWorker
from workers.style_worker import StyleWorker
from workers.data_worker import DataWorker
from workers.doorman_worker import DoormanWorker
from utils.prompt_utils import format_user_info_prompt
from utils.tags_utils import optionally_remove_answer_sections
from config import (
    ANSWER_QUALITY_RETRIES_NUM,
    MIN_ANSWER_QUALITY_SCORE,
    INTEGRATION_WORKER_MAX_TOKENS,
    JAILBREAK_ALARM_TEXT,
    JAILBREAK_TRUNCATE_LEN,
    MAX_COMBINED_ANSWERS_FOR_INTEGRATION_WORKER_CHAR_LEN,
    STYLE_WORKER_ITERATIONS_NUM,
    REWRITE_LONG_ANSWERS7,
    REWRITE_THRESHOLD_CHARS,
    STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT,
)
from ai_service import get_ai_response
from utils.prompt_utils import build_initial_conversation_history, extract_conversational_messages
from prompts.integration_worker_prompt import construct_prompt as construct_integration_prompt
from utils.diag_utils import build_diag_info


class IntegrationWorker(BaseWorker):
    def __init__(self, mindfile: Mindfile):
        super().__init__("integration_worker")
        self.mindfile = mindfile
        self.quality_worker = None
        self.style_worker = None
        self.generalist_data_worker = None
        self.compendium_data_workers: list[DataWorker] = []
        self.user_info_prompt = None
        self.doorman_worker = None

    def _has_leftover(self) -> bool:
        """
        Checks if leftover content exists in the mindfile.
        
        Returns:
            True if leftover exists, False otherwise
        """
        return STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT in self.mindfile.files_dict

    def _initialize_workers(self):
        """Initializes all necessary worker instances."""
        self.quality_worker = QualityChecksWorker(mindfile=self.mindfile)
        self.user_info_prompt = format_user_info_prompt()
        self.style_worker = StyleWorker(mindfile=self.mindfile)
        self.generalist_data_worker = DataWorker(mindfile=self.mindfile)
        self.doorman_worker = DoormanWorker(mindfile=self.mindfile)

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
        self, actual_chat_history: list[dict[str, str]], raw_user_message: str, deep_dive7: bool = True
    ) -> tuple[list[str], str | None, set[str]]:
        """
        Polls all data workers and returns their answers.
        The generalist worker's answer is always at index 0.
        Also returns a set of unique model names used by the workers.
        
        Args:
            actual_chat_history: Already-extracted conversational messages (no system message).
                                 This is pure user/assistant exchanges that data workers will append
                                 to their own system message + context.
            raw_user_message: The raw user message for provider selection.
            deep_dive7: Whether to poll compendium workers in addition to generalist.
        """
        answers = []
        models_used = set()
        
        generalist_answer, provider_report, model_name = self.generalist_data_worker.process(
            actual_chat_history, raw_user_message, self.user_info_prompt
        )
        if not model_name or model_name in ("N/A", "unknown"):
            self.record_diag_event("data_worker_model_invalid", f"generalist:{model_name}")
        models_used.add(model_name)
        
        cleaned_generalist_answer = optionally_remove_answer_sections(
            generalist_answer, remove_cot7=True, remove_internal_dialog7=True
        )
        answers.append(cleaned_generalist_answer)

        if not deep_dive7:
            return answers, provider_report, models_used

        for worker in self.compendium_data_workers:
            answer, _, model_name = worker.process(
                actual_chat_history, raw_user_message, self.user_info_prompt
            )
            if not model_name or model_name in ("N/A", "unknown"):
                self.record_diag_event("data_worker_model_invalid", f"{worker.display_name}:{model_name}")
            models_used.add(model_name)
            print(f"--- Answer from {worker.display_name} ---\n{answer}\n---")
            cleaned_answer = optionally_remove_answer_sections(
                answer, remove_cot7=True, remove_internal_dialog7=True
            )
            answers.append(cleaned_answer)

        return answers, provider_report, models_used

    def merge_answers(self, answers: list[str]) -> str:
        """Legacy concatenation of answers; kept as a fallback/debug tool."""
        separator = "\n--------------\n"
        
        # Standard merge
        result = separator.join(answers)

        # If the result is too long, use the fallback mode
        if len(result) > MAX_COMBINED_ANSWERS_FOR_INTEGRATION_WORKER_CHAR_LEN:
            original_len = len(result)
            original_num_answers = len(answers)
            print(f"# Merged answers are too long ({original_len} chars), using fallback mode.")
            
            sorted_answers = sorted(answers, key=len)
            
            included_answers = []
            for answer in sorted_answers:
                # Tentatively add the next answer and check the length
                temp_list = included_answers + [answer]
                if len(separator.join(temp_list)) > MAX_COMBINED_ANSWERS_FOR_INTEGRATION_WORKER_CHAR_LEN:
                    break
                included_answers.append(answer)

            result = separator.join(included_answers)
            num_answers_included = len(included_answers)

            len_diff = original_len - len(result)
            answers_diff = original_num_answers - num_answers_included
            print(f"# Fallback mode reduced length by {len_diff} chars and removed {answers_diff} answers.")

        else:
            print(f"# Merged answers are of a good length, using standard mode.")

        print(f"Merged answers:\n##\n{result}\n##")
        return result

    def synthesize_answers(
        self,
        conversation_history: list[dict[str, str]],
        answers: list[str],
        raw_user_message: str,
    ) -> tuple[str, str]:
        """
        Rewrites multiple candidate answers into one unified answer using an LLM.
        Returns the unified answer and the model name used for synthesis.
        
        Args:
            conversation_history: Already-extracted conversational messages (used for prompt context).
            answers: List of candidate answers to synthesize.
            raw_user_message: The raw user message for provider selection.
        """

        print(f"# Synthesizing answers ---")

        print("Answer candidates:")
        for i, answer in enumerate(answers):
            print(f"--- Candidate {i+1} ---")
            print(answer)
            print("--------------------------------")

        # Get system message from mindfile according to worker_config
        system_message = self.get_worker_system_message(additional_prompt=self.user_info_prompt)

        # Keep only the most recent part of the conversation for brevity
        recent_history = conversation_history[-6:]
        merged_answers = self.merge_answers(answers)
        integration_prompt = construct_integration_prompt(recent_history, merged_answers)

        llm_conversation_history = build_initial_conversation_history(
            system_message=system_message,
            context=None,
            user_prompt=integration_prompt,
        )

        try:
            unified_answer, _, model_name = get_ai_response(
                messages_history=llm_conversation_history,
                user_input_for_provider_selection=raw_user_message,
                max_length=INTEGRATION_WORKER_MAX_TOKENS,
            )
            if not unified_answer or not unified_answer.strip():
                print("Synthesis returned empty answer. Falling back to legacy merge.")
                self.record_diag_event("synthesis_empty_answer", None)
                return self.merge_answers(answers), "fallback_merge"
            if not model_name or model_name in ("N/A", "unknown"):
                self.record_diag_event("synthesis_model_invalid", str(model_name))
            return unified_answer, model_name
        except Exception as e:
            print(f"An error occurred during integration synthesis: {e}. Falling back to legacy merge.")
            self.record_diag_event("synthesis_exception", str(e))
            return self.merge_answers(answers), "fallback_merge"

    def _get_initial_answer(
        self, messages_history: list[dict[str, str]], raw_user_message: str, deep_dive7: bool
    ) -> tuple[str, str | None, set[str]]:
        """
        Gets an initial answer from the generalist data worker and polls compendium workers.
        Returns the answer, provider report, and the model name from the synthesis step.
        """
        actual_chat_history = extract_conversational_messages(messages_history)
        
        answers, provider_report, models_used = self.poll_data_workers(
            actual_chat_history, raw_user_message, deep_dive7=deep_dive7
        )
        current_answer, synthesis_model = self.synthesize_answers(actual_chat_history, answers, raw_user_message)
        if synthesis_model == "fallback_merge":
            self.record_diag_event("synthesis_fallback_merge", None)
        models_used.add(synthesis_model)

        return current_answer, provider_report, models_used

    def _apply_style(self, answer: str, messages_history: list[dict]) -> tuple[str, str, int]:
        """Applies styling to the answer using the StyleWorker."""
        if not self.style_worker or not answer:
            self.record_diag_event("style_skipped", None)
            return answer, "N/A", 0
        
        try:
            styled_answer = answer
            model_name = "N/A"

            user_facing_answer = optionally_remove_answer_sections(
                styled_answer, remove_cot7=True, remove_internal_dialog7=True
            )

            should_rewrite_iteratively = REWRITE_LONG_ANSWERS7 and len(user_facing_answer) > REWRITE_THRESHOLD_CHARS
            iterations = STYLE_WORKER_ITERATIONS_NUM if should_rewrite_iteratively else 1

            for i in range(iterations):
                print(f"--- Style Worker Iteration {i + 1}/{iterations} ---")
                
                user_facing_answer_for_style = optionally_remove_answer_sections(
                    styled_answer, remove_cot7=True, remove_internal_dialog7=True
                )
                
                styled_answer, model_name = self.style_worker.process(user_facing_answer_for_style, self.user_info_prompt, messages_history)
                
                if not model_name or model_name in ("N/A", "unknown"):
                    self.record_diag_event("style_model_invalid", f"iteration_{i+1}:{model_name}")

                print(f"Input for this iteration:\n---\n{user_facing_answer_for_style}\n---")
                print("########################################################")
                print(f"Output of this iteration:\n---\n{styled_answer}\n---")
                print("########################################################")

            return styled_answer, model_name, iterations
        except Exception as e:
            print(f"An error occurred during style worker processing: {e}")
            self.record_diag_event("style_exception", str(e))
            return answer, "N/A", 0

    def _evaluate_quality(self, messages_history: list[dict[str, str]], answer: str) -> tuple[dict | None, str]:
        """Evaluates the quality of the answer using the QualityChecksWorker."""
        try:
            actual_chat_history = extract_conversational_messages(messages_history)
            quality_scores, model_name = self.quality_worker.process(
                conversation_history=actual_chat_history[-4:],
                original_answer=answer,
                user_info_prompt=self.user_info_prompt
            )
            if not model_name or model_name in ("N/A", "unknown"):
                self.record_diag_event("quality_model_invalid", str(model_name))
            print(f"Quality Scores: {quality_scores}")
            return quality_scores, model_name
        except Exception as e:
            print(f"An error occurred during the quality check: {e}")
            self.record_diag_event("quality_exception", str(e))
            return None, "N/A"

    def _update_best_answer(self, current_answer: str, quality_scores: dict, best_answer_data: dict, models_used: set[str]) -> bool:
        """
        Updates the best answer based on quality scores.
        Returns True if the quality threshold is met.
        """
        if not quality_scores or not all(score is not None for score in quality_scores.values()):
            print("Quality check failed to return scores. Using this answer as a fallback.")
            self.record_diag_event("quality_missing_scores", None)
            if best_answer_data["answer"] is None:
                best_answer_data["answer"] = current_answer
            return True

        current_score_sum = sum(quality_scores.values())
        if best_answer_data["answer"] is None or current_score_sum > best_answer_data["score_sum"]:
            best_answer_data["answer"] = current_answer
            best_answer_data["score_sum"] = current_score_sum
            best_answer_data["scores"] = quality_scores
            best_answer_data["models_used"].update(models_used)

        if all(score >= MIN_ANSWER_QUALITY_SCORE for score in quality_scores.values()):
            print("Quality standards met. Finalizing answer.")
            return True
        
        print(f"Quality standards not met (min score: {MIN_ANSWER_QUALITY_SCORE}). Retrying...")
        return False

    def _process(self, messages_history: list[dict[str, str]], raw_user_message: str) -> tuple[str, str | None, dict]:
        self._initialize_workers()
        self.clear_diag_events()

        # Isolate the doorman's context: it should not see the latest user message in the history.
        # Note: doorman will automatically extract conversational messages (skipping system and context loads)
        history_for_doorman = messages_history[:-1]
        request_type = self.doorman_worker.process(raw_user_message, history_for_doorman)
        
        user_message_for_workers = raw_user_message
        sanitized_messages_history = messages_history

        if request_type in ["jailbreak", "exploitation"]:
            deep_dive7 = False
            truncated_message = raw_user_message[:JAILBREAK_TRUNCATE_LEN]
            user_message_for_workers = f"{JAILBREAK_ALARM_TEXT} {truncated_message}"
            
            # Sanitize the last message in the history for downstream workers
            if sanitized_messages_history and sanitized_messages_history[-1].get("role") == "user":
                # Create a copy to avoid modifying the original list in place
                sanitized_messages_history = list(sanitized_messages_history)
                sanitized_messages_history[-1] = {"role": "user", "content": user_message_for_workers}
        else:
            # Check if leftover exists - if so, force deep mode
            # Reason: In shallow mode, only the generalist worker is used, which may not
            # have access to all leftover content. Deep mode ensures compendium workers
            # with leftover content are consulted.
            has_leftover7 = self._has_leftover()
            
            if has_leftover7 and request_type == "shallow":
                print("Leftover detected: forcing deep mode to ensure all preserved data is consulted")
                deep_dive7 = True
            else:
                deep_dive7 = request_type == "deep"

        best_answer_data = {"answer": None, "score_sum": -1, "scores": {}, "models_used": set()}
        provider_report = None
        retries_taken = 0
        style_iterations_taken = 0
        
        retries = ANSWER_QUALITY_RETRIES_NUM

        for attempt in range(retries):
            print(f"\n--- Answer Generation Attempt {attempt + 1}/{retries} ---")
            retries_taken = attempt

            current_answer, current_provider_report, models_used_this_attempt = self._get_initial_answer(
                sanitized_messages_history, user_message_for_workers, deep_dive7
            )
            
            if provider_report is None:
                provider_report = current_provider_report

            styled_answer, style_model, style_iterations_taken = self._apply_style(current_answer, sanitized_messages_history)
            models_used_this_attempt.add(style_model)

            quality_scores, quality_model = self._evaluate_quality(sanitized_messages_history, styled_answer)
            models_used_this_attempt.add(quality_model)

            should_break = self._update_best_answer(styled_answer, quality_scores, best_answer_data, models_used_this_attempt)
            if should_break:
                break
        else:
            retries_taken = retries

        final_ai_answer = best_answer_data["answer"] if best_answer_data["answer"] is not None else ""
        
        # Aggregate diagnostics across all workers
        aggregated_events = []
        try:
            def _extend_with(worker_name: str, events: list[dict]):
                for ev in events:
                    aggregated_events.append({
                        "worker": worker_name,
                        "event": ev.get("event"),
                        "details": ev.get("details")
                    })
            _extend_with(self.display_name, self.get_diag_events())
            if self.generalist_data_worker:
                _extend_with(self.generalist_data_worker.display_name, self.generalist_data_worker.get_diag_events())
            if self.doorman_worker:
                _extend_with(self.doorman_worker.display_name, self.doorman_worker.get_diag_events())
            for worker in self.compendium_data_workers:
                _extend_with(worker.display_name, worker.get_diag_events())
            if self.style_worker:
                _extend_with(self.style_worker.display_name, self.style_worker.get_diag_events())
            if self.quality_worker:
                _extend_with(self.quality_worker.display_name, self.quality_worker.get_diag_events())
            if aggregated_events:
                print("Self-diagnostics:")
                for evt in aggregated_events:
                    prefix = evt.get("worker") or ""
                    event = evt.get("event")
                    details = evt.get("details")
                    if details:
                        print(f"- {prefix}: {event}: {details}")
                    else:
                        print(f"- {prefix}: {event}")
        except Exception:
            pass

        diag_info = build_diag_info(
            retries_taken=retries_taken,
            scores=best_answer_data["scores"],
            models_used=best_answer_data["models_used"],
            request_type=request_type,
            style_iterations=style_iterations_taken,
        )
        
        return final_ai_answer, provider_report, diag_info
