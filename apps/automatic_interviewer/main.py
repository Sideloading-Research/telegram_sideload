import sys
import os
import datetime
from collections import Counter


"""
Overrides ANSWER_QUALITY_RETRIES_NUM from the config.py
If you want to do a quick test, set it to 0. 
"""
ANSWER_QUALITY_RETRIES_NUM_FORCED = 3

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from sideload_api import ask_sideload
from config import MODELS_TO_ATTEMPT

def main():
    questions_file = os.path.join(os.path.dirname(__file__), '32_test_questions.txt')

    if not os.path.exists(questions_file):
        print(f"Error: Questions file not found at {questions_file}")
        return

    # Determine which model to force (the first one in the list)
    target_model = None
    if MODELS_TO_ATTEMPT:
        target_model = MODELS_TO_ATTEMPT[0]
        print(f"Note: Interview will force usage of model: {target_model}")
    else:
        print("Warning: MODELS_TO_ATTEMPT is empty. No model enforcement.")

    with open(questions_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    print("Starting Automatic Interviewer...")
    print(f"Reading questions from {questions_file}")

    # Collect all answers
    answers = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        print("-" * 50)
        print(f"Question: {line}")
        print("-" * 50)

        try:
            # We use a static user_id so context is preserved across questions if needed.
            # Usually an interview is a conversation.
            answer, provider_report, model_name = ask_sideload(
                line,
                user_id="interviewer",
                force_model=target_model,
                quality_retries=ANSWER_QUALITY_RETRIES_NUM_FORCED
            )
            print(f"Answer:\n{answer}\n")
            answers.append((line, answer, model_name))

            # Print summary of all answers so far
            print(f"--- Answers collected so far: {len(answers)} ---")
            for i, (q, a, m) in enumerate(answers, 1):
                print(f"{i}. {q}")
                print(f"   → {a} (model: {m})")
            print("-" * 50)
        except Exception as e:
            print(f"Error asking question: {e}")
            answers.append((line, f"ERROR: {e}", "error"))

    # Save to file
    if answers:
        # Collect model names from all answers and find the most frequent one
        model_names = []
        for _, _, model_name in answers:
            if model_name and model_name != "unknown_model" and model_name != "error":
                model_names.append(model_name)

        # Use most frequent model name, or "unknown_model" if none found
        if model_names:
            most_common_model = Counter(model_names).most_common(1)[0][0]
        else:
            most_common_model = "unknown_model"

        # Create RESULT directory if it doesn't exist
        result_dir = os.path.join(os.path.dirname(__file__), "RESULT")
        os.makedirs(result_dir, exist_ok=True)

        # Create filename: YYMMDD_model_used.txt
        today = datetime.datetime.now()
        filename = f"{today.strftime('%y%m%d')}_{most_common_model}.txt"
        output_path = os.path.join(result_dir, filename)

        print(f"Saving answers to: {output_path}")
        print(f"Most frequent model used: {most_common_model}")

        with open(output_path, 'w', encoding='utf-8') as f:
            for question, answer, _ in answers:
                f.write(f"# {question}\n")
                f.write(f"{answer}\n\n")

        print(f"Successfully saved {len(answers)} answers to {filename}")

if __name__ == "__main__":
    main()

