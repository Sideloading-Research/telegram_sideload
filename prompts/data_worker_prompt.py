from config import ANSWER_TO_USER_TAG, NO_RELEVANT_DATA_HINT


data_worker_prompt_addition = f"""
Often you don't have any sufficiently relevant data. If it's the case, add a special hint {NO_RELEVANT_DATA_HINT} to your answer.

Another common issue is that the seemingly relevant data is actually about other people, not you. That's also the case where the hint will help.

Note: the hint should be placed right after the free-form answer, but before the </{ANSWER_TO_USER_TAG}> tag.

For example:
<{ANSWER_TO_USER_TAG}>
[Your free-form answer here. E.g. "I can't recall any relevant data about it."]
{NO_RELEVANT_DATA_HINT}
</{ANSWER_TO_USER_TAG}>

"""
