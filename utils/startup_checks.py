import os
from typing import Tuple
from worker_config import WORKERS_CONFIG


def check_worker_mindfile_parts(
    files_dict: dict[str, str]
) -> Tuple[bool, str, str]:
    """
    Checks if all mindfile parts specified in WORKERS_CONFIG are present.

    Args:
        files_dict: A dictionary mapping mindfile part names to their file paths.

    Returns:
        A tuple containing:
        - valid7 (bool): True if all mandatory files are present, False otherwise.
        - error_report (str): An error message if mandatory files are missing.
        - warning_report (str): A warning message if optional files are missing.
    """
    mandatory_parts = set()
    optional_parts = set()
    for worker_name, specs in WORKERS_CONFIG.items():
        for part in specs.get("mindfile_parts", []):
            mandatory_parts.add(part)
        for part in specs.get("mindfile_parts_optional", []):
            optional_parts.add(part)

    missing_mandatory_files = _find_missing_files(mandatory_parts, files_dict)
    missing_optional_files = _find_missing_files(optional_parts, files_dict)

    valid7 = not missing_mandatory_files
    error_report = ""
    if not valid7:
        error_report = "The following required mindfile parts are missing:\n"
        for missing_file in missing_mandatory_files:
            error_report += f"- {missing_file}\n"

    warning_report = ""
    if missing_optional_files:
        warning_report = "The following optional mindfile parts are missing:\n"
        for missing_file in missing_optional_files:
            warning_report += f"- {missing_file}\n"

    return valid7, error_report, warning_report


def _find_missing_files(parts: set, files_dict: dict[str, str]) -> list[str]:
    """Helper function to find missing files from a set of parts."""
    missing_files = []
    for part in sorted(list(parts)):
        if part.startswith("internal_assets:"):
            asset_name = part.split(":", 1)[1]
            file_path = os.path.join("internal_assets", f"{asset_name}.txt")
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        else:
            if part not in files_dict:
                missing_files.append(f"'{part}' (expected in mindfile directory)")
    return missing_files
