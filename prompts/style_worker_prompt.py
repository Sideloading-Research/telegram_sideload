from config import ANSWER_TO_USER_TAG, IM_CHAT_LENGTH_NOTE

def construct_prompt(original_answer: str) -> str:
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
