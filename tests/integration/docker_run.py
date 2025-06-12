"""
Unit test file.
"""

from pathlib import Path

import os
import unittest
import subprocess

from tempfile import TemporaryDirectory
from pdf_ingest.cli import main as cli_main


class EpubTester(unittest.TestCase):
    """Main tester class."""

    @classmethod
    def setUpClass(cls) -> None:
        here = Path(__file__).parent.resolve()
        project_root = here.parent.parent.resolve()
        os.chdir(project_root)

    def test_sanity(self) -> None:
        # test that pyproject.toml is present at the root
        # cli_main()

        test_data = Path("test_data")
        self.assertTrue(test_data.exists(), f"Expected {test_data} to exist.")

        with TemporaryDirectory() as temp_dir:
            out_dir: Path = Path(temp_dir)
            print(f"Temporary directory created at: {out_dir}")

            arg_list: list[str] = [
                str(test_data),  # input_dir
                "--output_dir",
                str(out_dir),
                "--depth",
                "0"
            ]

            arg_str = subprocess.list2cmdline(arg_list)
            print("running command with args:", arg_str)

            rtn = cli_main(arg_list)
            self.assertEqual(rtn, 0, f"Expected return code 0, got {rtn}")


        


if __name__ == "__main__":
    unittest.main()
