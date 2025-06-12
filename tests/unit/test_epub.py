"""
Unit test file.
"""

from pathlib import Path

import unittest

from epub_utils import Document
from epub_utils.content import XHTMLContent


HERE = Path(__file__).parent.resolve()
PROJECT_ROOT = HERE.parent.parent.resolve()
TEST_DATA = PROJECT_ROOT / "test_data"
EPUB_SAMPLE = TEST_DATA / "Sway.epub"

class Fb2Tester(unittest.TestCase):
    """Main tester class."""

    def test_sanity(self) -> None:
        # test that pyproject.toml is present at the root
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        self.assertTrue(pyproject_path.exists(), f"Expected {pyproject_path} to exist.")
        self.assertTrue(EPUB_SAMPLE.exists(), f"Expected {EPUB_SAMPLE} to exist.")

    def test_main(self) -> None:
        """Test command line interface (CLI)."""
        # ai - please implement this
        doc = Document(str(EPUB_SAMPLE))
        # Print metadata
        # metadata = doc.get_metadata()  # Assuming this method exists
        # print("Metadata:")
        # for key, value in metadata.items():
        #     print(f"{key}: {value}")

        # Print content
        print("\nContent:")

        files_info: list[dict[str, str | int]] = doc.get_files_info()  # Assuming this method exists
        info: dict[str, str | int]
        for info in files_info:
            try:
                # Assuming get_file_by_path returns content for each file
                file_path:str | int = info['path']
                # self.assertTrue(isinstance(file_path, str), f"Expected file_path to be a string, got {type(file_path)}")
                assert isinstance(file_path, str), f"Expected file_path to be a string, got {type(file_path)}"
                # content = doc.get_file_by_path(info['path'])
                epub = doc.get_file_by_path(file_path)

                if not isinstance(epub, XHTMLContent):
                    print(f"Skipping non-XHTML content: {file_path}")
                    continue

                content_plain: str = epub.to_plain()

                # epub_type = type(epub).__name__
                # print(f"Found file: {file_path} of type {epub_type}")

                #print(f"Processing {file_path}...")
                #print(f"Epub file: {epub}")

                # context_txt = content.to_plain()
                print(f"Found {file_path} with content: {content_plain[:100]}...")  # Print first 100 characters
                # print(f"Content was {len(context_txt)} characters long")
                # print(content)
            except ValueError as e:
                print(f"File not found: {e}")

        print("Done")

        


if __name__ == "__main__":
    unittest.main()
