import os
import shutil

from config import DATASET_DIR_NAME_IN_REPO
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
