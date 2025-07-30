"""
Epub parser
"""

from dataclasses import dataclass
from pathlib import Path

from epub_utils import Document
from epub_utils.content import XHTMLContent

from pdf_ingest.data_types import TranslationItem
from pdf_ingest.fs_path import is_remote_path
from pdf_ingest.json_util import update_json_with_language
from pdf_ingest.language_detection import language_detect
from pdf_ingest.temp_manager import TempFileManager


def process_epub_file(item: TranslationItem) -> tuple[Exception | None, bool]:
    """
    Process an EPUB file and convert it to text.
    Now supports both local and remote files using temporary file management.

    Args:
        item: TranslationItem containing input and output file paths

    Returns:
        tuple: (error, success) where error is None if successful and success is True if file was processed
    """
    input_is_remote = is_remote_path(item.input_file)
    output_is_remote = is_remote_path(item.output_file)

    print(
        f"Processing EPUB: {item.input_file.name} (input: {'remote' if input_is_remote else 'local'}, "
        f"output: {'remote' if output_is_remote else 'local'})"
    )

    try:
        # Use temporary file managers for remote files
        with TempFileManager(item.input_file) as local_input:
            # Parse the EPUB file
            epub_doc = EpubDoc.parse(local_input)

            # Convert the EPUB document to plain text
            plain_text = epub_doc.to_plain_text()

            # Detect language from the plain text
            lang_code, is_reliable = language_detect(plain_text)
            item.language = lang_code
            item.should_translate = lang_code.lower() == "en"

            # Update the output filename to include language code
            stem = item.output_file.stem
            suffix = item.output_file.suffix
            new_filename = f"{stem}-{lang_code.upper()}{suffix}"
            item.output_file = item.output_file.with_name(new_filename)

            # Write to final output location (handling remote if necessary)
            try:
                # Ensure output directory exists
                item.output_file.parent.mkdir(parents=True, exist_ok=True)

                # Write content to final destination
                item.output_file.write_text(plain_text, encoding="utf-8")

                # Update JSON with language information
                update_json_with_language(item.json_file, lang_code, is_reliable)

                print(
                    f"✓ Successfully processed {item.input_file.name} (language: {lang_code})"
                )
                return None, True

            except Exception as write_err:
                print(
                    f"Error writing to final destination {item.output_file}: {write_err}"
                )
                return write_err, False

    except Exception as e:
        print(f"Error in EPUB processing pipeline for {item.input_file.name}: {e}")
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

        Note: This method expects a local Path object (from TempFileManager).

        Args:
            path (Path): Local path to the EPUB file.

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

    Note: This function expects a local Path object, typically obtained via TempFileManager.

    Args:
        epub_path (Path): Local path to the EPUB file.

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
