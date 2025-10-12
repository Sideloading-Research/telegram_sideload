from ai_service import get_ai_response
from config import (
    ANSWER_TO_USER_TAG,
    CHAIN_OF_THOUGHT_TAG,
    INTERNAL_DIALOG_TAG,
    MAX_MESSAGE_LEN_TO_TRIGGER_LLM_BASED_POSTPROCESSING,
    MAX_TELEGRAM_MESSAGE_LEN,
    REMOVE_CHAIN_OF_THOUGHT_FROM_ANSWER7,
    REMOVE_INTERNAL_DIALOG_FROM_ANSWER7,
    RESPONSE_FORMAT_REMINDER,
    ANSWER_MODIFICATION_MAX_TOKENS,
)
from utils.tags_utils import optionally_remove_answer_sections


def reduce_answer_len_to_comply_with_telegram_limit(answer, cut_str="<...>"):
    if len(answer) > MAX_TELEGRAM_MESSAGE_LEN:
        print(
            f"Answer is too long. Cutting it to {MAX_TELEGRAM_MESSAGE_LEN} characters."
        )

        # preserve the last chars
        effective_len = MAX_TELEGRAM_MESSAGE_LEN - len(cut_str)
        answer = cut_str + answer[-effective_len:]
    return answer


def llm_based_answer_postprocessing(answer):
    """
    Postprocess the answer using an LLM.

    TODO: move a prompts dir
    """

    prompt = f"""
    We have to process a text written by another LLM.

    The problem with the LLM is that it often fails to follow the response format.

    You can guess the target response format from the following reminder we gave to the LLM:
    <reminder_to_another_llm>
    {RESPONSE_FORMAT_REMINDER}
    </reminder_to_another_llm>

    A common failure mode is that the LLM fails to use the proper tags. Because of it, 
    our script often fails to cleanly extract the text between the <{ANSWER_TO_USER_TAG}>
	</{ANSWER_TO_USER_TAG}> tags, which is the user-facing answer.

    Please extract it, to the best of your ability.  
    
    Sometimes it's already exracted, in which case you can just return the text as is.

    Often, it's not properly extracted, due to missing tags. In this case, 
    you have to guess where the '{ANSWER_TO_USER_TAG}' part starts and ends.

    <example>

    In the example below, the LLM forgot to use the '{ANSWER_TO_USER_TAG}' tags.
    As you can see from the text, the intended user-facing answer is "Hi Joe! I don't like pineapple pizza."

	<{CHAIN_OF_THOUGHT_TAG}>
	The user Joe asked me if I like pineapple pizza. 
    I play the role of a pizza chef who dislikes pineapple.
	</{CHAIN_OF_THOUGHT_TAG}>
	
	<{INTERNAL_DIALOG_TAG}>
	Some people like pineapple pizza, but I definetly don't. I will answer honestly about my preference.  
	</{INTERNAL_DIALOG_TAG}>
	
	Hi Joe! I don't like pineapple pizza.

    </example>

    Here is the actual text we want to process today:
    <text_to_process>
    {answer}
    </text_to_process>

    Please return only the user-facing answer, and no commentary of yours.

    The user-facing answer:
    """

    system_message = """
    You are a helpful assistant who is exceptionally good at correcting other LLM's mistakes.
    """

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt},
    ]

    modified_answer, _, _ = get_ai_response(messages, "", max_length=ANSWER_MODIFICATION_MAX_TOKENS)
    print(f"Modified answer: {modified_answer}")
    print(f"Reduced the length from {len(answer)} to {len(modified_answer)}")
    return modified_answer


def modify_answer_before_sending_to_telegram(answer):
    answer = optionally_remove_answer_sections(
        answer,
        remove_cot7=REMOVE_CHAIN_OF_THOUGHT_FROM_ANSWER7,
        remove_internal_dialog7=REMOVE_INTERNAL_DIALOG_FROM_ANSWER7,
    )

    if (
        REMOVE_CHAIN_OF_THOUGHT_FROM_ANSWER7
        and REMOVE_INTERNAL_DIALOG_FROM_ANSWER7
        and len(answer) > MAX_MESSAGE_LEN_TO_TRIGGER_LLM_BASED_POSTPROCESSING
    ):
        print(
            f"Triggering LLM-based answer postprocessing for answer length {len(answer)}"
        )
        answer = llm_based_answer_postprocessing(answer)

    answer = reduce_answer_len_to_comply_with_telegram_limit(answer)
    return answer
