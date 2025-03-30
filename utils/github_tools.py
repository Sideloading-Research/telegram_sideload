import subprocess
import os
import shutil


def get_remote_repo_hash(repo_url):
    hash_value = None
    try:
        # Get the hash of the remote repository's HEAD
        result = subprocess.run(
            ["git", "ls-remote", repo_url, "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        hash_value = result.stdout.split()[0]
    except subprocess.CalledProcessError as e:
        print(f"Error checking remote repository: {e}")
    return hash_value


def save_repo_hash(hash_value, hash_file="last_commit_hash.txt"):
    success = False
    try:
        with open(hash_file, "w") as f:
            f.write(hash_value)
        success = True
    except Exception as e:
        print(f"Error saving hash: {e}")
    return success


def load_repo_hash(hash_file="last_commit_hash.txt"):
    hash_value = None
    try:
        with open(hash_file, "r") as f:
            hash_value = f.read().strip()
    except FileNotFoundError:
        pass
    return hash_value


def backup_repo(repo_url, local_repo_dir_path):
    # Create backup directory in user's home directory
    backup_dir = os.path.expanduser("~/BACKUPS")
    os.makedirs(backup_dir, exist_ok=True)

    # Extract repo name from the URL (e.g., "owner/repo" from "https://github.com/owner/repo.git")
    repo_name = repo_url.rstrip(".git").split("/")[-2:]
    repo_backup_name = "_".join(repo_name)
    backup_path = os.path.join(backup_dir, repo_backup_name)

    # Remove existing backup if it exists
    if os.path.exists(backup_path):
        shutil.rmtree(backup_path)
    # Create backup
    shutil.copytree(local_repo_dir_path, backup_path)
    print(f"Created backup at: {backup_path}")


def cleanup_temp_directory(temp_path):
    if os.path.exists(temp_path):
        try:
            shutil.rmtree(temp_path)
            print(f"Cleaned up temporary directory: {temp_path}")
        except Exception as e:
            print(f"Error during backup or cleanup: {e}")


def clone_repo_to_temp(repo_url, temp_path):
    success = False
    try:
        subprocess.run(["git", "clone", repo_url, temp_path], check=True)
        print(f"Successfully cloned repository to temporary location")
        success = True
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e}")
    return success
