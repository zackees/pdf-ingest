"""
Unit test file.
"""

from pathlib import Path
from tempfile import TemporaryDirectory


import unittest
import shutil

from pdf_ingest.parsers.fb2 import Fb2Doc, Fb2Entry
from pdf_ingest.scan_and_convert import scan_and_convert
from pdf_ingest.fs_factory import FileSystemFactory

HERE = Path(__file__).parent.resolve()
PROJECT_ROOT = HERE.parent.parent.resolve()
TEST_DATA = PROJECT_ROOT / "test_data"
FB2_SAMPLE = TEST_DATA / "source_test_book_fb2.fb2"



class Fb2Tester(unittest.TestCase):
    """Main tester class."""

    def test_sanity(self) -> None:
        # test that pyproject.toml is present at the root
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        self.assertTrue(pyproject_path.exists(), f"Expected {pyproject_path} to exist.")
        self.assertTrue(FB2_SAMPLE.exists(), f"Expected {FB2_SAMPLE} to exist.")

    def test_parse_epub(self) -> None:
        epub = Fb2Doc.parse(FB2_SAMPLE)
        self.assertIsInstance(epub, Fb2Doc, "Expected epub to be an instance of EpubDoc")
        self.assertGreater(len(epub.contents), 0, "Expected epub to have contents")
        for entry in epub.contents:
            self.assertIsInstance(entry, Fb2Entry, "Expected entry to be an instance of EpubEntry")
            self.assertIsInstance(entry.file_path, str, "Expected file_path to be a string")
            self.assertIsInstance(entry.content, str, "Expected content to be a string")
            self.assertGreater(len(entry.content), 0, "Expected content to be non-empty")
        
        
        combined: str = epub.to_plain_text()
        print("Combined EPUB content:")
        print(combined)
        print("Done")

    def test_process_fb2(self) -> None:
        with TemporaryDirectory() as temp_dir:
            tmp: Path = Path(temp_dir)

            print(f"Temporary directory created at: {temp_dir}")
            input_file: Path = tmp / "input.fb2"
            shutil.copy(FB2_SAMPLE, input_file)

            # Convert pathlib.Path to UniversalPath for the function
            input_universal = FileSystemFactory.create_path(str(tmp))
            output_universal = FileSystemFactory.create_path(str(tmp))
            scan_and_convert(input_dir=input_universal, output_dir=output_universal, depth=0)

            expected_file = tmp / "input-EN.txt"
            self.assertTrue(expected_file.exists())

            file_content = expected_file.read_text(encoding="utf-8")
            self.assertNotIn("<body>", file_content, "Expected no raw FB2 body tags in the output text file")
            print("done")

        


if __name__ == "__main__":
    unittest.main()
