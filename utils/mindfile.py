import math
import os


from config import (
    DATASET_DIR_NAME_IN_REPO,
    BATCH_TITLE_PREFIX,
    ENTRY_SEPARATOR_PREFIX,
    SOURCE_TAG_CLOSE,
    SOURCE_TAG_OPEN,
    SYSTEM_MESSAGE_FILE_WITHOUT_EXT,
    STRUCTURED_SELF_FACTS_FILE_WITHOUT_EXT,
    STRUCTURED_MEMORIES_FILE_WITHOUT_EXT,
    STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT,
    ULTRA_SMALL_CONTEXT_WINDOW_MODE7,
    MAX_TOKENS_ALLOWED_IN_REQUEST,
    CHARS_PER_TOKEN,
    WORKERS_OBLIGATORY_PARTS,
    ANSWER_TO_USER_TAG,
    RESPONSE_FORMAT_REMINDER,
)

from utils.mf_entry import MF_entry
from utils.tags_utils import build_source_tags, split_string_by_delimiters_with_max_len
from utils.text_utils import get_splitting_params, truncate_text, truncate_text_by_tokens
from utils.tokens import get_max_chars_allowed, count_tokens
from utils.boxes_sorting import pack_into_boxes, verify_packing
from utils.leftover_manager import process_and_generate_leftover
from utils.compendium_logger import (
    log_files_being_packed,
    log_entry_sources,
    log_compendium_distribution,
)


class Mindfile:
    def __init__(self, files_dict: dict[str, str]):
        if not files_dict:
            raise ValueError("files_dict cannot be empty.")
        self.files_dict = files_dict.copy()  # Make a copy to allow modification
        self._validate_required_files()
        self._process_and_inject_leftover()

    def _log_truncation(
        self, filename: str, limit: int, unit: str, reason: str, original_len: int
    ):
        """Logs the details of a truncation event."""
        print(f"Original {filename} length: {original_len} {unit}")
        print(f"Truncating {filename} to {limit} {unit}. Reason: {reason}")

    def _process_and_inject_leftover(self):
        """
        Detects if structured_self_facts will be truncated, extracts leftover,
        saves it to file, and adds it to files_dict for normal processing.
        
        This method is called early in __init__ to ensure leftover is available
        before any other processing methods access files_dict.
        """
        facts_filename = STRUCTURED_SELF_FACTS_FILE_WITHOUT_EXT
        system_msg_filename = SYSTEM_MESSAGE_FILE_WITHOUT_EXT
        
        # Check if we have the required files
        if facts_filename not in self.files_dict or system_msg_filename not in self.files_dict:
            return
        
        # Read contents
        facts_content = self._read_file_content(facts_filename)
        system_message_content = self._read_file_content(system_msg_filename)
        
        # Generate leftover if truncation is needed
        leftover_dict = process_and_generate_leftover(
            facts_content=facts_content,
            system_message_content=system_message_content,
            ultra_small_mode7=ULTRA_SMALL_CONTEXT_WINDOW_MODE7,
            max_tokens_allowed=MAX_TOKENS_ALLOWED_IN_REQUEST,
            leftover_filename_key=STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT
        )
        
        # If leftover was generated, inject it into files_dict
        if leftover_dict:
            self.files_dict.update(leftover_dict)
            print(f"Leftover injected into files_dict as '{STRUCTURED_SELF_FACTS_LEFTOVER_FILE_WITHOUT_EXT}'")

    def _truncate_facts_if_needed(
        self, facts_content: str, system_message_content: str
    ) -> str:
        """
        Truncates the facts content based on token limits and ultra-small context mode.
        """
        original_tokens = count_tokens(facts_content)

        # The general limit is 30% of the total request size.
        final_token_limit = int(0.3 * MAX_TOKENS_ALLOWED_IN_REQUEST)
        reason = f"file exceeds {final_token_limit} tokens limit"

        # In ultra-small mode, there's a stricter limit to leave space for the system message.
        if ULTRA_SMALL_CONTEXT_WINDOW_MODE7:
            max_tokens_for_combo = MAX_TOKENS_ALLOWED_IN_REQUEST / 2
            system_message_tokens = count_tokens(system_message_content)
            small_mode_token_limit = max(
                0, int(max_tokens_for_combo - system_message_tokens)
            )

            # Use the stricter (smaller) limit
            if small_mode_token_limit < final_token_limit:
                final_token_limit = small_mode_token_limit
                reason = "ULTRA_SMALL_CONTEXT_WINDOW_MODE7"

        if original_tokens > final_token_limit:
            self._log_truncation(
                filename=STRUCTURED_SELF_FACTS_FILE_WITHOUT_EXT,
                limit=final_token_limit,
                unit="tokens",
                reason=reason,
                original_len=original_tokens,
            )
            facts_content = truncate_text_by_tokens(
                facts_content, final_token_limit
            )

        return facts_content

    def _get_processed_obligatory_parts(self) -> dict[str, str]:
        contents = {
            filename: self._read_file_content(filename)
            for filename in WORKERS_OBLIGATORY_PARTS
            if filename in self.files_dict
        }

        system_message = contents.get(SYSTEM_MESSAGE_FILE_WITHOUT_EXT, "")
        tag_to_check = f"<{ANSWER_TO_USER_TAG}>"
        if system_message and tag_to_check not in system_message:
            print(f"'{tag_to_check}' not found in system message. Appending reminder.")
            system_message += RESPONSE_FORMAT_REMINDER
            contents[SYSTEM_MESSAGE_FILE_WITHOUT_EXT] = system_message

        facts_content = contents.get(STRUCTURED_SELF_FACTS_FILE_WITHOUT_EXT, "")
        if facts_content:
            truncated_facts = self._truncate_facts_if_needed(
                facts_content, system_message
            )

            # Update contents if truncation happened
            if truncated_facts is not facts_content:
                contents[STRUCTURED_SELF_FACTS_FILE_WITHOUT_EXT] = truncated_facts

        return contents

    def get_entries(self, max_len: int | None = None) -> list[MF_entry]:
        """
        Splits the mindfile content into entries and returns a list of MF_entry objects.
        
        Args:
            max_len: Maximum length for each entry. If None, uses get_max_chars_allowed().
        """
        full_content = self.get_full_mindfile_content()

        end_delimiters = [BATCH_TITLE_PREFIX, SOURCE_TAG_OPEN, SOURCE_TAG_CLOSE]
        
        if max_len is None:
            max_len = get_max_chars_allowed()

        text_chunks = split_string_by_delimiters_with_max_len(
            text=full_content,
            start_delimiter=ENTRY_SEPARATOR_PREFIX,
            end_delimiters=end_delimiters,
            max_len=max_len,
        )

        entries = [
            MF_entry(text=chunk.text, header=chunk.header) for chunk in text_chunks
        ]

        return entries

    def get_mindfile_data_packed_into_compendiums(self) -> list[str]:
        """
        Packs entry texts into compendiums not exceeding the max allowed length,
        minimizing the number of compendiums.
        """
        # Log which files are being packed (includes leftover tracking)
        log_files_being_packed(self.files_dict)
        
        processed_obligatory_parts = self._get_processed_obligatory_parts()
        max_chars = get_max_chars_allowed(
            consider_obligatory_worker_parts7=True,
            files_content_override=processed_obligatory_parts,
        )
        entries = self.get_entries(max_len=max_chars)
        compendiums: list[str] = []
        if entries:
            # Log entry distribution
            log_entry_sources(entries)
            
            lengths = get_entry_lengths(entries)
            boxes = pack_into_boxes(lengths, max_chars)
            verify_packing(boxes, max_chars)
            size_to_indices = build_size_to_indices_map(lengths)
            compendiums = build_compendiums_from_boxes(boxes, entries, size_to_indices)
            
            # Log detailed compendium distribution
            log_compendium_distribution(compendiums, self.files_dict)
        
        return compendiums

    def _validate_required_files(self):
        required_files = [
            SYSTEM_MESSAGE_FILE_WITHOUT_EXT,
            STRUCTURED_SELF_FACTS_FILE_WITHOUT_EXT,
            STRUCTURED_MEMORIES_FILE_WITHOUT_EXT,
        ]
        for req_file in required_files:
            if req_file not in self.files_dict:
                raise ValueError(
                    f"Required mindfile part '{req_file}' not found in files_dict."
                )

    def _read_file_content(self, filename: str) -> str:
        """
        Reads content of a specific file from the files_dict or internal_assets.
        """
        if filename.startswith("internal_assets:"):
            # Handle internal assets
            asset_name = filename.split(":", 1)[1]
            file_path = os.path.join("internal_assets", f"{asset_name}.txt")
            if not os.path.exists(file_path):
                raise FileNotFoundError(
                    f"Internal asset '{asset_name}' not found at path: {file_path}"
                )
        else:
            # Handle standard mindfile parts
            file_path = self.files_dict.get(filename)
            if not file_path or not os.path.exists(file_path):
                raise FileNotFoundError(
                    f"Mindfile part '{filename}' not found at path: {file_path}"
                )

        with open(file_path, "r", encoding="utf-8") as f:
            # print(f"Reading file: {file_path}")
            return f.read().strip()

    def get_file_content(self, filename: str) -> str:
        """Reads and returns the content of a specific file."""
        if filename in WORKERS_OBLIGATORY_PARTS:
            # Return the processed version, which may be truncated
            return self._get_processed_obligatory_parts().get(filename, "")
        
        # For optional files, they might not be in files_dict if missing.
        if filename not in self.files_dict:
            return "" # Return empty string if optional file is missing
            
        return self._read_file_content(filename)

    def get_system_message(self) -> str:
        """Extracts and returns the system message."""
        return self._get_processed_obligatory_parts().get(
            SYSTEM_MESSAGE_FILE_WITHOUT_EXT, ""
        )

    def get_context(self, mindfile_parts: list[str] | None = None) -> str:
        """
        Builds and returns the context string from the specified mindfile parts.

        Args:
            mindfile_parts: A list of filenames (without extension) to include in the context.
                            If None, all available files except the system message will be used.
                            Note: system_message is ALWAYS excluded from context, even if explicitly provided.

        Returns:
            A string containing the combined and formatted context.
        """
        non_system_contents = []

        # Determine which files to process
        files_to_process = mindfile_parts
        if files_to_process is None:
            files_to_process = [f for f in self.files_dict.keys()]
        
        # Always filter out system_message to prevent duplication
        # (system_message should be retrieved separately via get_system_message())
        files_to_process = [f for f in files_to_process if f != SYSTEM_MESSAGE_FILE_WITHOUT_EXT]

        processed_obligatory_parts = self._get_processed_obligatory_parts()

        for file in files_to_process:
            content = ""
            if file in processed_obligatory_parts:
                content = processed_obligatory_parts[file]
            elif file.startswith("internal_assets:") or file in self.files_dict:
                content = self._read_file_content(file)
            
            if content:
                non_system_contents.append((file, content))
                    
        # Sort contents to ensure structured facts appear first and memories last (if they exist in the list)
        sorted_contents = self._sort_context_contents(non_system_contents)

        # Merge contents with source tags
        context = ""
        for filename, content in sorted_contents:
            open_tag, close_tag = build_source_tags(filename)
            context += f"{open_tag}\n\n{content}\n\n{close_tag}\n\n\n"

        return context.strip()

    def get_full_mindfile_content(self) -> str:
        """
        Reads all mindfile parts, sorts them, and returns them as a single string,
        with each part wrapped in source tags.
        """
        processed_obligatory_parts = self._get_processed_obligatory_parts()
        all_contents = []

        # Add all files from files_dict, using the processed version for obligatory parts
        for filename in self.files_dict.keys():
            if filename in processed_obligatory_parts:
                content = processed_obligatory_parts[filename]
                all_contents.append((filename, content))
            elif self.files_dict.get(filename):
                content = self._read_file_content(filename)
                all_contents.append((filename, content))

        sorted_contents = self._sort_context_contents(all_contents)

        content_parts = []
        for filename, content in sorted_contents:
            # print(f"Building source tags for: {filename}")
            open_tag, close_tag = build_source_tags(filename)
            content_parts.append(f"{open_tag}\n\n{content}\n\n{close_tag}")

        res = "\n\n\n".join(content_parts)

        # print(f"Full mindfile content length: {len(res)}")
        return res

    def get_mindfile_split_into_context_window_chunks(self) -> list[str]:
        """
        Splits the full mindfile content into chunks suitable for a context window.
        """
        full_content = self.get_full_mindfile_content()
        if not full_content:
            return []

        max_chars = get_max_chars_allowed()

        # num_chunks_float = len(full_content) / max_chars
        # n = math.floor(num_chunks_float) + 1
        # chunk_size = math.ceil(len(full_content) / n)
        _, chunk_size = get_splitting_params(full_content, max_chars)

        return [
            full_content[i : i + chunk_size]
            for i in range(0, len(full_content), chunk_size)
        ]

    def _sort_context_contents(
        self, contents: list[tuple[str, str]]
    ) -> list[tuple[str, str]]:
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


def get_entry_lengths(entries: list[MF_entry]) -> list[int]:
    """Return a list of entry text lengths."""
    lengths: list[int] = []
    for e in entries:
        lengths.append(e.get_length())
    return lengths


def build_size_to_indices_map(lengths: list[int]) -> dict[int, list[int]]:
    """Map each size to a list of indices having that size (for duplicates)."""
    size_to_indices: dict[int, list[int]] = {}
    for idx, size in enumerate(lengths):
        if size not in size_to_indices:
            size_to_indices[size] = []
        size_to_indices[size].append(idx)
    return size_to_indices


def build_compendiums_from_boxes(
    boxes: list[list[int]],
    entries: list[MF_entry],
    size_to_indices: dict[int, list[int]],
) -> list[str]:
    """Construct compendium strings by following packed box size assignments."""
    compendiums: list[str] = []
    for box in boxes:
        parts: list[str] = []
        for size in box:
            idx_list = size_to_indices.get(size)
            if idx_list is None or len(idx_list) == 0:
                # Should not happen if sizes match; skip defensively
                continue
            entry_idx = idx_list.pop()
            parts.append(entries[entry_idx].text)
        compendiums.append("".join(parts))
    return compendiums


def get_system_message_and_context(files_dict, save_context_to_file7=False):
    """
    This function is now a wrapper around the Mindfile class for backward compatibility.
    """
    try:
        mindfile = Mindfile(files_dict)
        system_message = mindfile.get_system_message()
        context = mindfile.get_context()  # Gets context from all available files

        if save_context_to_file7:
            with open("context_for_debug.txt", "w", encoding="utf-8") as f:
                f.write(
                    f"--- SYSTEM MESSAGE ---\n{system_message}\n\n--- CONTEXT ---\n{context}"
                )

        return system_message, context
    except (ValueError, FileNotFoundError) as e:
        # Provide a more informative error message that guides the user.
        msg = f"Error processing mindfile: {e}. "
        msg += f"Ensure the '{DATASET_DIR_NAME_IN_REPO}' directory in your repo contains the required files, "
        msg += f"including '{SYSTEM_MESSAGE_FILE_WITHOUT_EXT}.txt'."
        print(msg)
        # Raising the exception again to halt execution, as this is a critical error.
        raise ValueError(msg) from e
