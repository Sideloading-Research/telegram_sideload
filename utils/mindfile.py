import os
import shutil


from config import (
    DATASET_DIR_NAME_IN_REPO,
    SYSTEM_MESSAGE_FILE_WITHOUT_EXT,
    STRUCTURED_SELF_FACTS_FILE_WITHOUT_EXT,
    STRUCTURED_MEMORIES_FILE_WITHOUT_EXT,
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


class Mindfile:
    def __init__(self, files_dict: dict[str, str]):
        if not files_dict:
            raise ValueError("files_dict cannot be empty.")
        self.files_dict = files_dict
        self._validate_required_files()

    def _validate_required_files(self):
        required_files = [
            SYSTEM_MESSAGE_FILE_WITHOUT_EXT,
            STRUCTURED_SELF_FACTS_FILE_WITHOUT_EXT,
            STRUCTURED_MEMORIES_FILE_WITHOUT_EXT,
        ]
        for req_file in required_files:
            if req_file not in self.files_dict:
                raise ValueError(f"Required mindfile part '{req_file}' not found in files_dict.")

    def _read_file_content(self, filename: str) -> str:
        """Reads content of a specific file from the files_dict."""
        file_path = self.files_dict.get(filename)
        if not file_path or not os.path.exists(file_path):
            # This should ideally not happen if _validate_required_files is comprehensive
            raise FileNotFoundError(f"File '{filename}' not found at path: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    def get_file_content(self, filename: str) -> str:
        """Reads and returns the content of a specific file."""
        return self._read_file_content(filename)

    def get_system_message(self) -> str:
        """Extracts and returns the system message."""
        return self._read_file_content(SYSTEM_MESSAGE_FILE_WITHOUT_EXT)

    def get_context(self, mindfile_parts: list[str] | None = None) -> str:
        """
        Builds and returns the context string from the specified mindfile parts.

        Args:
            mindfile_parts: A list of filenames (without extension) to include in the context.
                            If None, all available files except the system message will be used.

        Returns:
            A string containing the combined and formatted context.
        """
        non_system_contents = []
        
        # Determine which files to process
        files_to_process = mindfile_parts
        if files_to_process is None:
            files_to_process = [f for f in self.files_dict.keys() if f != SYSTEM_MESSAGE_FILE_WITHOUT_EXT]

        for file in files_to_process:
            if file in self.files_dict and file != SYSTEM_MESSAGE_FILE_WITHOUT_EXT:
                content = self._read_file_content(file)
                non_system_contents.append((file, content))

        # Sort contents to ensure structured facts appear first and memories last (if they exist in the list)
        sorted_contents = self._sort_context_contents(non_system_contents)

        # Merge contents with source tags
        context = ""
        for filename, content in sorted_contents:
            open_tag, close_tag = build_source_tags(filename)
            context += f"{open_tag}\n\n{content}\n\n{close_tag}\n\n\n"

        return context.strip()

    def _sort_context_contents(self, contents: list[tuple[str, str]]) -> list[tuple[str, str]]:
        """
        Sorts context contents to ensure structured facts appear first and memories last.
        Other content is sorted alphabetically by filename.
        """
        structured_facts = []
        structured_memories = []
        other_content = []
        
        facts_filename = STRUCTURED_SELF_FACTS_FILE_WITHOUT_EXT
        memories_filename = STRUCTURED_MEMORIES_FILE_WITHOUT_EXT

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


def split_context_by_importance(context, expendable_tag: str = "dialogs"):
    """
    Split the context into three parts: before the expendable part, the expendable part, and after the expendable part.

    Args:
        context: The full context string

    Returns:
        Tuple of (before_expendable, expendable, after_expendable) strings
    """
    open_tag, close_tag = build_source_tags(expendable_tag)

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
    """
    This function is now a wrapper around the Mindfile class for backward compatibility.
    """
    try:
        mindfile = Mindfile(files_dict)
        system_message = mindfile.get_system_message()
        context = mindfile.get_context() # Gets context from all available files
        
        if save_context_to_file7:
            with open("context_for_debug.txt", "w", encoding="utf-8") as f:
                f.write(f"--- SYSTEM MESSAGE ---\n{system_message}\n\n--- CONTEXT ---\n{context}")
        
        return system_message, context
    except (ValueError, FileNotFoundError) as e:
        # Provide a more informative error message that guides the user.
        msg = f"Error processing mindfile: {e}. "
        msg += f"Ensure the '{DATASET_DIR_NAME_IN_REPO}' directory in your repo contains the required files, "
        msg += f"including '{SYSTEM_MESSAGE_FILE_WITHOUT_EXT}.txt'."
        print(msg)
        # Raising the exception again to halt execution, as this is a critical error.
        raise ValueError(msg) from e
