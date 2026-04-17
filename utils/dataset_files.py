import os
import shutil

import config
from utils.files_utils import get_existing_local_files
from utils.github_tools import (
    backup_repo,
    cleanup_temp_directory,
    clone_repo_to_temp,
    get_remote_repo_hash,
    load_repo_hash,
    save_repo_hash,
)
from utils.micro_mindfile_builder import build_sideload_files_dict
from utils.startup_checks import check_worker_mindfile_parts


def _copy_fallback_dir(temp_path: str) -> None:
    """Copies the fallback dir from a temp repo clone to the local MINDFILE_FROM_GITHUB tree."""
    src = os.path.join(temp_path, config.FALLBACKS_DIR_PATH_IN_REPO)
    dst = config.FALLBACKS_LOCAL_DIR_PATH
    if not os.path.exists(src):
        print(f"Warning: fallback dir not found in cloned repo at {src}")
        return
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copytree(src, dst)
    print(f"Fallback files saved to: {dst}")


def _get_sideload_path(filename: str) -> str:
    return os.path.join(config.FALLBACKS_LOCAL_DIR_PATH, filename)


def _validate_sideload_files(files_dict: dict[str, str], label: str) -> None:
    valid7, error_report, warning_report = check_worker_mindfile_parts(files_dict)
    if warning_report:
        print(f"Warning from {label} mindfile:\n{warning_report}")
    if not valid7:
        raise ValueError(f"{label} mindfile validation failed:\n{error_report}")


def _clone_repo_and_copy_fallbacks(repo_url: str, destination_path: str) -> None:
    """Clones the corpus repo just to extract the fallback files."""
    temp_path = destination_path + "_temp"
    print("Cloning repo to retrieve fallback files...")
    try:
        successfully_cloned7 = clone_repo_to_temp(repo_url, temp_path)
        if successfully_cloned7:
            _copy_fallback_dir(temp_path)
    finally:
        cleanup_temp_directory(temp_path)


def _ensure_sideload_exists(filename: str, repo_url: str, destination_path: str) -> None:
    """Clones the repo if the sideload file is not yet available locally."""
    if not os.path.exists(_get_sideload_path(filename)):
        _clone_repo_and_copy_fallbacks(repo_url, destination_path)


def _refresh_sideload_mindfile_data(
    filename: str, temp_dir: str, label: str, repo_url: str, destination_path: str
) -> dict[str, str]:
    """Shared entry point for sideload-based modes (MICRO, NANO)."""
    _ensure_sideload_exists(filename, repo_url, destination_path)
    sideload_path = _get_sideload_path(filename)
    if not os.path.exists(sideload_path):
        raise FileNotFoundError(f"{filename} not available at {sideload_path}")
    print(f"Building mindfile from {sideload_path}")
    files_dict = build_sideload_files_dict(sideload_path, temp_dir)
    _validate_sideload_files(files_dict, label)
    return files_dict


def refresh_micro_mindfile_data(repo_url: str, destination_path: str) -> dict[str, str]:
    """Entry point for MICRO mode: builds files_dict from micro_sideload.txt."""
    return _refresh_sideload_mindfile_data(
        config.MICRO_SIDELOAD_FILENAME, config.MICRO_MINDFILE_TEMP_DIR, "MICRO", repo_url, destination_path
    )


def refresh_nano_mindfile_data(repo_url: str, destination_path: str) -> dict[str, str]:
    """Entry point for NANO mode: builds files_dict from nano_sideload.txt."""
    return _refresh_sideload_mindfile_data(
        config.NANO_SIDELOAD_FILENAME, config.NANO_MINDFILE_TEMP_DIR, "NANO", repo_url, destination_path
    )


def verify_dataset_path(dataset_path):
    """Verify the dataset path exists."""
    if not os.path.exists(dataset_path):
        print(f"Error: {config.DATASET_DIR_NAME_IN_REPO} dir not found in {dataset_path}")
        return False
    return True


def move_dataset(source_path, destination_path):
    """Move dataset to destination, removing old data if it exists."""
    if os.path.exists(destination_path):
        shutil.rmtree(destination_path)
    shutil.move(source_path, destination_path)


def update_files_and_hashes(temp_path, destination_path, current_hash, repo_url):
    files = {}
    dataset_path = os.path.join(temp_path, config.DATASET_DIR_NAME_IN_REPO)

    if not verify_dataset_path(dataset_path):
        return files

    temp_files_dict = get_existing_local_files(dataset_path)
    valid7, error_report, warning_report = check_worker_mindfile_parts(
        temp_files_dict
    )
    if warning_report:
        print(f"Warning from remote mindfile validation:\n{warning_report}")
    if not valid7:
        print("=" * 50)
        print("Validation of remote mindfile repository failed. Update aborted.")
        print("The current local mindfile data will be used.")
        print(f"Validation error:\n{error_report}")
        print("=" * 50)
        return {}  # Return empty dict to signal failure

    try:
        backup_repo(repo_url, destination_path)
        move_dataset(dataset_path, destination_path)
        _copy_fallback_dir(temp_path)
        print(
            f"\nCleaned up repository. Only {config.DATASET_DIR_NAME_IN_REPO} directory remains at {destination_path}"
        )

        save_repo_hash(current_hash)
        files = get_existing_local_files(destination_path)
    except Exception as e:
        print(f"Error updating mindfile: {e}")

    return files


def refresh_local_mindfile_data(repo_url, destination_path):
    if config.LOCAL_MINDFILE_DIR_PATH:
        if os.path.isdir(config.LOCAL_MINDFILE_DIR_PATH):
            print(f"Using local mindfile from: {config.LOCAL_MINDFILE_DIR_PATH}")
            files_dict = get_existing_local_files(config.LOCAL_MINDFILE_DIR_PATH)

            valid7, error_report, warning_report = check_worker_mindfile_parts(
                files_dict
            )
            if warning_report:
                print(f"Warning:\n{warning_report}")
            if not valid7:
                raise FileNotFoundError(
                    f"Local mindfile validation failed:\n{error_report}"
                )
            return files_dict
        else:
            print(
                f"Warning: LOCAL_MINDFILE_DIR_PATH '{config.LOCAL_MINDFILE_DIR_PATH}' not found or not a directory. Falling back to repo."
            )

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
