import textwrap


def dedent_and_strip(text: str) -> str:
    """
    Dedents a multiline string and removes leading/trailing whitespace.
    """
    return textwrap.dedent(text).strip()
