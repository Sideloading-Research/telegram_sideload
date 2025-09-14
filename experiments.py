import os

from config import DATASET_LOCAL_DIR_PATH, REPO_URL
from utils.dataset_files import refresh_local_mindfile_data
from utils.mf_entry import MF_entry
from utils.mindfile import Mindfile
from utils.text_utils import split_text_into_rougthly_same_size_parts_context_aware


def save_to_file(text, index: int, output_dir: str):
    """
    Saves an entry to a file with its length in the filename.
    """
    entry_len = len(text)
    filename = f"compendium_{index}_{entry_len}.txt"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    files_dict = refresh_local_mindfile_data(REPO_URL, DATASET_LOCAL_DIR_PATH)
    if not files_dict:
        print("No files found. Exiting.")
        return

    mindfile = Mindfile(files_dict)
    entries = mindfile.get_entries()

    compendiums = mindfile.get_mindfile_data_packed_into_compendiums()

    # create output dir if it doesn't exist
    output_dir = "compendiums_output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for i, compendium in enumerate(compendiums):
        save_to_file(compendium, i, "compendiums_output")



if __name__ == "__main__":
    main()
