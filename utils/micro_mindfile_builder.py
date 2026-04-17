import os

from utils.micro_sideload_parser import parse_micro_sideload
from utils.style_samples_builder import build_style_samples_content


def _write_section_to_file(output_dir: str, filename: str, content: str) -> str:
    """Writes content to output_dir/filename.txt and returns the full path."""
    file_path = os.path.join(output_dir, f"{filename}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return file_path


def _sections_to_files_dict(sections: dict[str, str], output_dir: str) -> dict[str, str]:
    """Writes each section to disk and returns {filename: full_path}."""
    return {
        filename: _write_section_to_file(output_dir, filename, content)
        for filename, content in sections.items()
    }


def _maybe_add_style_samples(sections: dict[str, str]) -> dict[str, str]:
    """Generates style_samples from dialogs QUOTE: parts if any exist."""
    dialogs_content = sections.get("dialogs", "")
    style_samples_content = build_style_samples_content(dialogs_content)
    if style_samples_content is None:
        return {}
    print(f"Generated style_samples from {len(dialogs_content)} chars of dialogs.")
    return {"style_samples": style_samples_content}


def build_sideload_files_dict(sideload_path: str, output_dir: str) -> dict[str, str]:
    """
    Parses any sideload txt file, writes each section to output_dir, and returns files_dict.
    Creates output_dir if it does not exist.
    """
    os.makedirs(output_dir, exist_ok=True)
    sections = parse_micro_sideload(sideload_path)
    sections.update(_maybe_add_style_samples(sections))
    return _sections_to_files_dict(sections, output_dir)
