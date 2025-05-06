# BTW, the logic I would like on this is that your code looks for .pdf or .djvu
# that have no matching .txt filename in the output folder, and then processes
# the files to generate the .txt of the same name.
# And it should handle subfolders under the src folder as well,
# So when it's done processing, every pdf has a txt, in the output folder.


import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from pdf_ingest.scan_and_convert import scan_and_convert_pdfs

HERE = Path(__file__).parent.resolve()
TEST_DATA = "test_data"
OUTPUT_DIR = "test_data_output"


@dataclass
class Args:
    input_dir: Path
    output_dir: Path

    def __post_init__(self):
        if not isinstance(self.input_dir, Path):
            raise TypeError("input_dir must be a Path object")
        if not isinstance(self.output_dir, Path):
            raise TypeError("output_dir must be a Path object")
        if not self.input_dir.exists():
            raise FileNotFoundError(f"{self.input_dir} does not exist")
        if not self.output_dir.exists():
            raise FileNotFoundError(f"{self.output_dir} does not exist")


def _parse_args() -> Args:
    parser = argparse.ArgumentParser(description="Convert PDF and DJVU files to text.")
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Directory containing PDF and DJVU files to convert",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory where text files will be saved",
    )
    args = parser.parse_args()
    if not args.input_dir.exists():
        parser.error(f"Input directory {args.input_dir} does not exist")

    return Args(input_dir=args.input_dir, output_dir=args.output_dir)


def main() -> int:
    args = _parse_args()
    # Create output directory if it doesn't exist
    # OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
    input_dir = args.input_dir
    output_dir = args.output_dir

    # Call the function to scan and convert PDFs and DJVUs
    remaining_files = scan_and_convert_pdfs(input_dir=input_dir, output_dir=output_dir)

    if remaining_files:
        print(f"\nRemaining files that could not be converted: {len(remaining_files)}")
        for item in remaining_files:
            print(f"  - {item.input_file}")
    else:
        print("\nAll files were successfully converted!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
