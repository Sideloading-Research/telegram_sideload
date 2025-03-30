import os


def print_file_dict(files_dict, directory):
    print("\nFiles in full_dataset directory:")
    for name, path in files_dict.items():
        print(f"{name}: {path}")

def build_files_dict(directory):
    """Helper function to build dictionary of files with names as keys and full paths as values."""
    return {
        os.path.splitext(f)[0]: os.path.join(directory, f)
        for f in os.listdir(directory)
    }


def get_existing_local_files(destination_path):
    files_dict = build_files_dict(destination_path)
    print_file_dict(files_dict, destination_path)
    return files_dict