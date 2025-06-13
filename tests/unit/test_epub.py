"""
Unit test file.
"""

from pathlib import Path
from tempfile import TemporaryDirectory


import unittest
import shutil

from pdf_ingest.parsers.epub import EpubDoc, EpubEntry
from pdf_ingest.scan_and_convert import scan_and_convert_pdfs

HERE = Path(__file__).parent.resolve()
PROJECT_ROOT = HERE.parent.parent.resolve()
TEST_DATA = PROJECT_ROOT / "test_data"
EPUB_SAMPLE = TEST_DATA / "Sway.epub"



class EpubTester(unittest.TestCase):
    """Main tester class."""

    def test_sanity(self) -> None:
        # test that pyproject.toml is present at the root
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        self.assertTrue(pyproject_path.exists(), f"Expected {pyproject_path} to exist.")
        self.assertTrue(EPUB_SAMPLE.exists(), f"Expected {EPUB_SAMPLE} to exist.")

    def test_parse_epub(self) -> None:
        epub = EpubDoc.parse(EPUB_SAMPLE)
        self.assertIsInstance(epub, EpubDoc, "Expected epub to be an instance of EpubDoc")
        self.assertGreater(len(epub.contents), 0, "Expected epub to have contents")
        for entry in epub.contents:
            self.assertIsInstance(entry, EpubEntry, "Expected entry to be an instance of EpubEntry")
            self.assertIsInstance(entry.file_path, str, "Expected file_path to be a string")
            self.assertIsInstance(entry.content, str, "Expected content to be a string")
            self.assertGreater(len(entry.content), 0, "Expected content to be non-empty")
        
        
        combined: str = epub.to_plain_text()
        print("Combined EPUB content:")
        print(combined)
        print("Done")

    def test_process_epub(self) -> None:
        with TemporaryDirectory() as temp_dir:
            tmp: Path = Path(temp_dir)

            print(f"Temporary directory created at: {temp_dir}")
            input_file: Path = tmp / "input.epub"
            shutil.copy(EPUB_SAMPLE, input_file)

            scan_and_convert_pdfs(input_dir=tmp, output_dir=tmp, depth=0)

            expected_file = tmp / "input-EN.txt"
            self.assertTrue(expected_file.exists())
            print("done")

        


if __name__ == "__main__":
    unittest.main()
