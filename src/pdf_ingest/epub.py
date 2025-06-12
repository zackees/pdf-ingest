"""
Epub parser
"""

from dataclasses import dataclass
from pathlib import Path

from epub_utils import Document
from epub_utils.content import XHTMLContent


@dataclass
class EpubEntry:
    file_path: str
    content: str  # Content of the file as a string


@dataclass
class EpubDoc:
    contents: list[EpubEntry]  # List of tuples (file_path, content)

    @staticmethod
    def parse(path: Path) -> "EpubDoc":
        """
        Static method to parse an EPUB file and return an EpubDoc instance.

        Args:
            path (Path): Path to the EPUB file.

        Returns:
            EpubDoc: An instance containing the parsed contents.
        """
        return _parse_epub(path)


def _parse_epub(epub_path: Path) -> EpubDoc:
    """
    Parses the EPUB file and returns a structured representation of its contents.

    Args:
        epub_path (Path): Path to the EPUB file.

    Returns:
        EpubDoc: An object containing the contents of the EPUB file.
    """
    doc = Document(str(epub_path))
    content: list[EpubEntry] = []
    files_info = doc.get_files_info()  # Assuming this method exists
    for info in files_info:
        file_path: str | int = info["path"]
        if not isinstance(file_path, str):
            print(f"Expected file_path to be a string, got {type(file_path)}")
            continue
        try:
            epub_content = doc.get_file_by_path(file_path)
            if not isinstance(epub_content, XHTMLContent):
                print(f"Skipping non-XHTML content: {file_path}")
                continue
            plain_text = epub_content.to_plain()
            entry = EpubEntry(file_path=file_path, content=plain_text)
            content.append(entry)
        except ValueError as e:
            print(f"File not found: {e}")

    return EpubDoc(contents=content)
