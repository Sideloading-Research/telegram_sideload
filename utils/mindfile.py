import os
import shutil


from config import (
    DATASET_DIR_NAME_IN_REPO,
    SYSTEM_MESSAGE_FILE_WITHOUT_EXT,
    STRUCTURED_SELF_FACTS_FILE_WITHOUT_EXT,
    STRUCTURED_MEMORIES_FILE_WITHOUT_EXT,
    EXPENDABLE_MINDFILE_PART,
)
from utils.files_utils import get_existing_local_files
from utils.github_tools import (
    backup_repo,
    cleanup_temp_directory,
    clone_repo_to_temp,
    get_remote_repo_hash,
    load_repo_hash,
    save_repo_hash,
)


def verify_dataset_path(dataset_path):
    """Verify the dataset path exists."""
    if not os.path.exists(dataset_path):
        print(f"Error: {DATASET_DIR_NAME_IN_REPO} dir not found in {dataset_path}")
        return False
    return True


def move_dataset(source_path, destination_path):
    """Move dataset to destination, removing old data if it exists."""
    if os.path.exists(destination_path):
        shutil.rmtree(destination_path)
    shutil.move(source_path, destination_path)


def update_files_and_hashes(temp_path, destination_path, current_hash, repo_url):
    files = []
    dataset_path = os.path.join(temp_path, DATASET_DIR_NAME_IN_REPO)

    if not verify_dataset_path(dataset_path):
        return files

    try:
        backup_repo(repo_url, dataset_path)
        move_dataset(dataset_path, destination_path)
        print(
            f"\nCleaned up repository. Only {DATASET_DIR_NAME_IN_REPO} directory remains at {destination_path}"
        )

        save_repo_hash(current_hash)
        files = get_existing_local_files(destination_path)
    except Exception as e:
        print(f"Error updating mindfile: {e}")

    return files


def refresh_local_mindfile_data(repo_url, destination_path):
    files_dict = dict()
    temp_path = destination_path + "_temp"

    # Check if we've downloaded this before
    current_hash = get_remote_repo_hash(repo_url)
    if current_hash is not None:
        last_hash = load_repo_hash()

        # If hashes match and dataset exists, use existing files
        if last_hash == current_hash and os.path.exists(destination_path):
            print("Repository hasn't changed. Using existing files.")
            files_dict = get_existing_local_files(destination_path)
        else:
            print("Repository has changed. Updating the mindfile.")
            try:
                sucessfully_cloned7 = clone_repo_to_temp(repo_url, temp_path)
                if sucessfully_cloned7:
                    files_dict = update_files_and_hashes(
                        temp_path, destination_path, current_hash, repo_url
                    )
            finally:
                cleanup_temp_directory(temp_path)

    return files_dict


def sort_context_contents(contents, facts_filename, memories_filename):
    """Sort context contents to ensure structured facts appear first and memories last.
    
    Args:
        contents: List of (filename, content) tuples
        facts_filename: Filename of structured facts to place first
        memories_filename: Filename of structured memories to place last
        
    Returns:
        Sorted list of (filename, content) tuples
    """
    # Split into three categories
    structured_facts = []
    structured_memories = []
    other_content = []
    
    for item in contents:
        if item[0] == facts_filename:
            structured_facts.append(item)
        elif item[0] == memories_filename:
            structured_memories.append(item)
        else:
            other_content.append(item)
            
    # Combine with structured facts first, regular content in middle, memories last
    return (
        structured_facts
        + sorted(other_content, key=lambda x: x[0])
        + structured_memories
    )


def build_source_tags(filename):
    open_tag = f"<source:{filename}>"
    close_tag = f"</source:{filename}>"
    return open_tag, close_tag


def split_context_by_importance(context):
    """
    Split the context into three parts: before the expendable part, the expendable part, and after the expendable part.

    Args:
        context: The full context string

    Returns:
        Tuple of (before_expendable, expendable, after_expendable) strings
    """
    open_tag, close_tag = build_source_tags(EXPENDABLE_MINDFILE_PART)

    # Find the start and end positions of the expendable part
    start_pos = context.find(open_tag)
    if start_pos == -1:  # Tag not found
        return context, "", ""

    end_pos = context.find(close_tag, start_pos) + len(close_tag)
    if end_pos <= len(close_tag):  # Closing tag not found
        # Return everything up to the opening tag as non-expendable, and everything after as expendable
        return context[:start_pos], context[start_pos:], ""

    # Extract the parts
    before_expendable = context[:start_pos]
    expendable = context[start_pos:end_pos]
    after_expendable = context[end_pos:]

    return before_expendable, expendable, after_expendable




def get_system_message_and_context(files_dict, save_context_to_file7=False):
    system_message = None
    non_system_contents = []
    for file, path in files_dict.items():
        if file == SYSTEM_MESSAGE_FILE_WITHOUT_EXT:
            with open(path, "r") as f:
                system_message = f.read()
        else:
            with open(path, "r") as f:
                file_content = f.read().strip()
                non_system_contents.append((file, file_content))

    # Sort contents to ensure structured facts appear first and memories last
    non_system_contents = sort_context_contents(
        non_system_contents, 
        STRUCTURED_SELF_FACTS_FILE_WITHOUT_EXT,
        STRUCTURED_MEMORIES_FILE_WITHOUT_EXT,
    )

    # Merge contents with source tags
    context = ""
    for filename, content in non_system_contents:
        open_tag, close_tag = build_source_tags(filename)
        context += f"{open_tag}\n\n{content}\n\n{close_tag}\n\n\n"

    if system_message is None:
        msg = "System message not found."
        msg += f"It should be named {SYSTEM_MESSAGE_FILE_WITHOUT_EXT},"
        msg += (
            f"and be located in the directory {DATASET_DIR_NAME_IN_REPO} in the repo."
        )
        raise ValueError(msg)

    if save_context_to_file7:
        with open(f"context_for_debug.txt", "w") as f:
            f.write(context)

    return system_message, context.strip()
