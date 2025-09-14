class MF_entry:
    """
    A class to represent an entry in the mindfile.
    Each entry is a document with some text content.
    """
    def __init__(self, text: str, header: str):
        """
        Initializes an MF_entry object.

        Args:
            text (str): The text content of the entry.
            header (str): The header of the entry.
        """
        self.text = text
        self.header = header

    def get_length(self) -> int:
        """
        Returns the length of the entry's text.

        Returns:
            int: The number of characters in the text.
        """
        return len(self.text)
