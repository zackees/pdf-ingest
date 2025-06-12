"""
Unit test file.
"""

from pathlib import Path
from dataclasses import dataclass

import unittest

from epub_utils import Document
from epub_utils.content import XHTMLContent

@dataclass
class EpubEntry:
    file_path: str
    content: str  # Content of the file as a string

@dataclass
class EpubDoc:
    contents: list[EpubEntry]  # List of tuples (file_path, content)


HERE = Path(__file__).parent.resolve()
PROJECT_ROOT = HERE.parent.parent.resolve()
TEST_DATA = PROJECT_ROOT / "test_data"
EPUB_SAMPLE = TEST_DATA / "Sway.epub"


def parse_epub(epub_path: Path) -> EpubDoc:
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
        file_path: str | int = info['path']
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

class EpubTester(unittest.TestCase):
    """Main tester class."""

    def test_sanity(self) -> None:
        # test that pyproject.toml is present at the root
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        self.assertTrue(pyproject_path.exists(), f"Expected {pyproject_path} to exist.")
        self.assertTrue(EPUB_SAMPLE.exists(), f"Expected {EPUB_SAMPLE} to exist.")

    def test_parse_epub(self) -> None:
        epub: EpubDoc = parse_epub(EPUB_SAMPLE)
        self.assertIsInstance(epub, EpubDoc, "Expected epub to be an instance of EpubDoc")
        self.assertGreater(len(epub.contents), 0, "Expected epub to have contents")
        for entry in epub.contents:
            self.assertIsInstance(entry, EpubEntry, "Expected entry to be an instance of EpubEntry")
            self.assertIsInstance(entry.file_path, str, "Expected file_path to be a string")
            self.assertIsInstance(entry.content, str, "Expected content to be a string")
            self.assertGreater(len(entry.content), 0, "Expected content to be non-empty")
        print("Done")

    # def test_main(self) -> None:
    #     """Test command line interface (CLI)."""
    #     # ai - please implement this
    #     doc = Document(str(EPUB_SAMPLE))
    #     # Print metadata
    #     # metadata = doc.get_metadata()  # Assuming this method exists
    #     # print("Metadata:")
    #     # for key, value in metadata.items():
    #     #     print(f"{key}: {value}")

    #     # toc: TableOfContents | None = doc.toc  # Assuming this method exists

    #     # print(f"Table of Contents: {toc if toc else 'No TOC found'}")

    #     # Print content
    #     # print("\nContent:")

    #     files_info: list[dict[str, str | int]] = doc.get_files_info()  # Assuming this method exists
    #     info: dict[str, str | int]
    #     for info in files_info:
    #         try:
    #             # Assuming get_file_by_path returns content for each file
    #             file_path:str | int = info['path']
    #             # self.assertTrue(isinstance(file_path, str), f"Expected file_path to be a string, got {type(file_path)}")
    #             assert isinstance(file_path, str), f"Expected file_path to be a string, got {type(file_path)}"
    #             # content = doc.get_file_by_path(info['path'])
    #             epub = doc.get_file_by_path(file_path)

    #             if not isinstance(epub, XHTMLContent):
    #                 print(f"Skipping non-XHTML content: {file_path}")
    #                 continue

    #             content_plain: str = epub.to_plain()

    #             # epub_type = type(epub).__name__
    #             # print(f"Found file: {file_path} of type {epub_type}")

    #             #print(f"Processing {file_path}...")
    #             #print(f"Epub file: {epub}")

    #             # context_txt = content.to_plain()
    #             print(f"Found {file_path} with content: {content_plain[:100]}...")  # Print first 100 characters
    #             # print(f"Content was {len(context_txt)} characters long")
    #             # print(content)
    #         except ValueError as e:
    #             print(f"File not found: {e}")

    #     print("Done")

        


if __name__ == "__main__":
    unittest.main()
