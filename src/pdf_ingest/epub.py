"""
Epub parser
"""

from dataclasses import dataclass
from pathlib import Path

from epub_utils import Document
from epub_utils.content import XHTMLContent

from pdf_ingest.json_util import update_json_with_language
from pdf_ingest.language_detection import detect_language_from_file
from pdf_ingest.types import TranslationItem


def process_epub_file(item: TranslationItem) -> tuple[Exception | None, bool]:
    """
    Process an EPUB file and convert it to text.
    Uses a temporary directory for the conversion process and then copies the result to the final destination.

    Args:
        item: TranslationItem containing input and output file paths

    Returns:
        tuple: (error, success) where error is None if successful and success is True if file was processed
    """
    try:
        # Parse the EPUB file
        epub_doc = EpubDoc.parse(item.input_file)

        # Convert the EPUB document to plain text
        plain_text = epub_doc.to_plain_text()

        # Detect language from the plain text
        lang_code, is_reliable = detect_language_from_file(item.input_file)
        item.language = lang_code
        item.should_translate = lang_code.lower() == "en"

        # Update the output filename to include language code
        stem = item.output_file.stem
        suffix = item.output_file.suffix
        new_filename = f"{stem}-{lang_code.upper()}{suffix}"
        item.output_file = item.output_file.with_name(new_filename)

        # Update JSON with language information
        update_json_with_language(item.json_file, lang_code, is_reliable)

        # Write the plain text to the output file
        with open(item.output_file, "w", encoding="utf-8") as f:
            f.write(plain_text)

        print(f"Successfully processed {item.input_file.name} (language: {lang_code})")
        return None, True
    except Exception as e:
        print(f"Error processing {item.input_file.name}: {e}")
        return e, False


@dataclass
class EpubEntry:
    file_path: str
    content: str  # Content of the file as a string

    def to_plain_text(self) -> str:
        """
        Serializes the EpubEntry to a string representation.

        Returns:
            str: A string representation of the EpubEntry.
        """
        out: str = ""
        out += f"------- File Path: {self.file_path} -------\n"
        out += f"{self.content}\n"
        return out


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

    def to_plain_text(self) -> str:
        """
        Serializes the EpubDoc to a string representation.

        Returns:
            str: A string representation of the EpubDoc.
        """
        parts: list[str] = []
        for entry in self.contents:
            parts.append(entry.to_plain_text())
        out: str = "\n".join(parts)
        return out


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
