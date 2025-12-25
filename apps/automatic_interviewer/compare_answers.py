import argparse
import re
import random
import shutil
import textwrap
import os
import sys

"""
This command-line tool was inspired by this Marco Baturan's tool:
https://github.com/marcobaturan/self-awarenes-benchmark
"""

def parse_result_file(filepath):
    """
    Parses a result file and returns a dictionary.
    Key: Question ID (int)
    Value: tuple (question_text, answer_text)
    """
    entries = {}
    current_id = None
    current_question = None
    current_answer_lines = []

    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return {}

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line_stripped = line.strip()
        
        # Check for Question line
        match = re.match(r'^# (\d+)\.\s+(.*)', line)
        if match:
            # Save previous entry if exists
            if current_id is not None:
                full_answer = "\n".join(current_answer_lines).strip()
                entries[current_id] = (current_question, full_answer)

            current_id = int(match.group(1))
            current_question = match.group(2).strip()
            current_answer_lines = []
            continue

        # Check for Metadata line
        if line_stripped.startswith('[') and line_stripped.endswith(']'):
            # This marks the end of the answer section
            continue

        # Collect answer lines
        if current_id is not None:
            current_answer_lines.append(line.rstrip())

    # Save the last entry
    if current_id is not None:
        full_answer = "\n".join(current_answer_lines).strip()
        entries[current_id] = (current_question, full_answer)

    return entries

def resolve_vote(vote, left_source, right_source):
    """
    Determines the winner based on user vote.
    vote: input string
    left_source: identifier for left content
    right_source: identifier for right content
    Returns: winner identifier ('equal' for ties) or None if invalid
    """
    v = vote.lower().strip()
    if v in ['left', 'l', '1']:
        return left_source
    if v in ['right', 'r', '2']:
        return right_source
    if v in ['both', 'equal', '=', 'b', 'e']:
        return "equal"
    return None

def wrap_text(text, width):
    """
    Wraps text to the specified width, handling newlines.
    """
    lines = text.split('\n')
    wrapped_lines = []
    for line in lines:
        if not line:
            wrapped_lines.append("")
        else:
            wrapped_lines.extend(textwrap.wrap(line, width=width))
    return wrapped_lines

def print_side_by_side(text_left, text_right, width):
    """
    Prints two texts side by side.
    """
    col_width = (width - 4) // 2
    wrapped_left = wrap_text(text_left, col_width)
    wrapped_right = wrap_text(text_right, col_width)
    
    max_lines = max(len(wrapped_left), len(wrapped_right))
    
    # Separator line
    print("-" * width)
    
    for i in range(max_lines):
        l_line = wrapped_left[i] if i < len(wrapped_left) else ""
        r_line = wrapped_right[i] if i < len(wrapped_right) else ""
        print(f"{l_line:<{col_width}} | {r_line:<{col_width}}")
        
    print("-" * width)

def main():
    parser = argparse.ArgumentParser(description="Compare answers from two result files.")
    parser.add_argument("file1", help="Path to the first result file")
    parser.add_argument("file2", help="Path to the second result file")
    args = parser.parse_args()

    data1 = parse_result_file(args.file1)
    data2 = parse_result_file(args.file2)

    common_ids = sorted(list(set(data1.keys()) & set(data2.keys())))
    
    if not common_ids:
        print("No common questions found between the files.")
        return

    print(f"Found {len(common_ids)} common questions.")
    
    votes = {
        "file1": 0,
        "file2": 0,
        "equal": 0
    }
    
    choices_log = []

    try:
        for q_id in common_ids:
            q_text_1, ans1 = data1[q_id]
            q_text_2, ans2 = data2[q_id]
            
            # Use the question text from file 1
            q_text = q_text_1

            print("\n" * 2)
            print(f"QUESTION {q_id}: {q_text}")
            term_cols = shutil.get_terminal_size().columns
            print("=" * term_cols)
            
            # Randomize placement
            is_swapped7 = random.choice([True, False])
            
            if is_swapped7:
                left_content = ans2
                right_content = ans1
                left_source = "file2"
                right_source = "file1"
            else:
                left_content = ans1
                right_content = ans2
                left_source = "file1"
                right_source = "file2"

            print_side_by_side(left_content, right_content, term_cols)

            while True:
                user_input = input("Which answer is better? (Left/Right/Both): ").strip().lower()
                
                if user_input in ['quit', 'q', 'exit']:
                    print("Exiting...")
                    raise KeyboardInterrupt
                
                winner = resolve_vote(user_input, left_source, right_source)
                if winner:
                    if winner == "equal":
                        votes["equal"] += 1
                        print("You chose: Both/Equal")
                        choices_log.append(f"Q{q_id}: Equal")
                    else:
                        votes[winner] += 1
                        choice_str = "File 1" if winner == "file1" else "File 2"
                        print(f"You chose: {choice_str}")
                        choices_log.append(f"Q{q_id}: {choice_str}")
                    break
                else:
                    print("Invalid input. Please type Left, Right, Both or Quit.")
                    
    except KeyboardInterrupt:
        pass
    
    print("\n\n=== SUMMARY ===")
    print(f"File 1 ({args.file1}): {votes['file1']} votes")
    print(f"File 2 ({args.file2}): {votes['file2']} votes")
    print(f"Equal/Both: {votes['equal']} votes")
    
    report_filename = "comparison_report.txt"
    with open(report_filename, "w") as f:
        f.write(f"Comparison Report\n")
        f.write(f"File 1: {args.file1}\n")
        f.write(f"File 2: {args.file2}\n\n")
        f.write(f"Votes for File 1: {votes['file1']}\n")
        f.write(f"Votes for File 2: {votes['file2']}\n")
        f.write(f"Equal/Both: {votes['equal']}\n\n")
        f.write("Choices:\n")
        for log in choices_log:
            f.write(log + "\n")
            
    print(f"Report saved to {report_filename}")

if __name__ == "__main__":
    main()
