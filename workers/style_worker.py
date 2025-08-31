from workers.base_worker import BaseWorker
from utils.mindfile import Mindfile
from ai_service import get_ai_response
from utils.text_shrinkage_utils.controller import shrink_any_text
from utils.tokens import count_tokens, MAX_TOKENS_ALLOWED_IN_REQUEST
from config import ANSWER_TO_USER_TAG, IM_CHAT_LENGTH_NOTE, TOKEN_SAFETY_MARGIN
from utils.prompt_utils import build_initial_conversation_history

class StyleWorker(BaseWorker):
    def __init__(self, mindfile: Mindfile):
        super().__init__("style_worker")
        self.mindfile = mindfile

    def _construct_prompt(self, original_answer: str) -> str:
        prompt = f"""
            Another (experimental) instance of you wrote an answer.
            Our goal is to rewrite it in such a way, as to make it sound just like you.
            
            I've attached our dialogs and interviews as the golden reference.

            <evaluation_points>
            Points to consider (and fix):
            - Does the answer sound too much like a typical LLM?
            - Avoid cliche phrases that are typical of LLMs:
            ---- "This is exactly the kind of..."
            ---- "you're spot on..."
            ---- "you're absolutely right..."
            ---- "you're hitting on some..."
            ---- "Your insights into..."
            ---- "That's the way to..."
            ---- "This not merely X, but Y..."
            ---- "It's about X, not just Y..."
            ---- "It's less about X and more about Y..."
            ---- This extremely annoying habit of repeating the user's question:
            -------- "X, you say?..."
            -------- "Ah, X..."
            -------- "X, eh?..."
            -------- "X?..."
            -------- "X? Nah,..."
            - Does it contain the formatting overused by LLMs? (**bold**, *italic*, etc.). Avoid any use of the "*" symbol for formatting, too typical of LLMs. Remove it completely.
            - Another thing massively overused by LLMs are bullet points. Avoid them too. In a normal conversation, humans almost never use them.
            - Does it much your authentic style, voice, personality, vocabulary, sentence structure, tone, emotion, vibe?
            - Does it contains things explicitly forbidden by the system message?
            - Does it follow the formatting and style requirements outlined in the system message?
            - Is the answer too long? Can you make it even shorter? {IM_CHAT_LENGTH_NOTE}
            </evaluation_points>
            
            <examples>
                <bad_example>
                    User: Hi! Which places are worth visiting in Germany?
                    Bot: "Worth visiting," eh? You know my take on aimless wandering...
                    # In this example, the bot used the annoying LLM-ism of repeating the user. Avoid it.
                </bad_example>
            </examples>

            Evaluate the original answer point by point, and then rewrite it. 

            Original Answer to Rewrite:
            <original_answer>
            '{original_answer}'
            </original_answer>

            Don't forget to wrap the user-facing part of the answer with the proper tags:
            <{ANSWER_TO_USER_TAG}>
            The rewritten answer goes here.
            </{ANSWER_TO_USER_TAG}>

            The proper tags are extremely important! Otherwise, our system will fail to parse your answer correctly. Always include them.
        """
        return prompt

    def process(self, original_answer: str, user_info_prompt: str | None = None) -> str:
        if not original_answer or not original_answer.strip():
            print("StyleWorker: Received empty answer to style. Returning it as is.")
            return original_answer

        # --- Token Calculation and Content Shrinking ---

        # 1. Calculate tokens for fixed parts of the request
        system_message = self.mindfile.get_system_message()
        if user_info_prompt:
            system_message += "\n\n" + user_info_prompt

        self_facts = self.mindfile.get_file_content('structured_self_facts')
        style_prompt = self._construct_prompt(original_answer)
        
        fixed_content = system_message + self_facts + style_prompt
        fixed_tokens = count_tokens(fixed_content)

        # 2. Determine available tokens for shrinkable content
        max_allowed_tokens = MAX_TOKENS_ALLOWED_IN_REQUEST / TOKEN_SAFETY_MARGIN
        available_tokens_for_shrinkable = max_allowed_tokens - fixed_tokens

        if available_tokens_for_shrinkable <= 0:
            print("StyleWorker: Not enough tokens for shrinkable content. Proceeding with empty context for them.")
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
            <source:structured_self_facts>
            {self_facts}
            </source:structured_self_facts>

            <source:dialogs>
            {shrunk_dialogs}
            </source:dialogs>

            <source:interviews_etc>
            {shrunk_interviews}
            </source:interviews_etc>
        """

        llm_conversation_history = build_initial_conversation_history(
            system_message=system_message,
            context=worker_context,
            user_prompt=style_prompt
        )

        styled_answer, _ = get_ai_response(
            messages_history=llm_conversation_history,
            user_input_for_provider_selection=style_prompt,
            max_length=4000 
        )

        return styled_answer


if __name__ == '__main__':
    # This is a test block to run the worker standalone.
    # It requires a Mindfile instance.
    # You would need to initialize it with a valid files_dict.
    
    # from utils.mindfile import refresh_local_mindfile_data
    # from config import MIND_REPO_URL, MIND_DATA_DIR
    
    # print("Refreshing mindfile data...")
    # files_dict = refresh_local_mindfile_data(MIND_REPO_URL, MIND_DATA_DIR)
    
    # if files_dict:
    #     print("Mindfile data refreshed successfully.")
    #     mindfile = Mindfile(files_dict)
    #     style_worker = StyleWorker(mindfile)
        
    #     test_answer = "Hello, this is a test. I am writing in a very generic and boring way. Please rewrite me."
        
    #     print(f"\nOriginal answer:\n{test_answer}")
        
    #     styled_answer = style_worker.process(test_answer)
        
    #     print(f"\nStyled answer:\n{styled_answer}")
    # else:
    #     print("Could not refresh mindfile data. Aborting test.")
    pass
