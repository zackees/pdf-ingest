# BTW, the logic I would like on this is that your code looks for .pdf or .djvu
# that have no matching .txt filename in the output folder, and then processes
# the files to generate the .txt of the same name.
# And it should handle subfolders under the src folder as well,
# So when it's done processing, every pdf has a txt, in the output folder.

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from pdf_ingest.scan_and_convert import Result, scan_and_convert_pdfs

_PATH_APP = Path("/app")
_INPUT_DIR = _PATH_APP / "input"
_OUTPUT_DIR = _PATH_APP / "output"


@dataclass
class Args:
    depth: int  # default is 0, but when > 0 it will scan subdirectories

    def __post_init__(self):
        if not isinstance(self.depth, int):
            raise TypeError("depth must be an integer")
        if self.depth < 0:
            raise ValueError("depth must be a non-negative integer")

    @staticmethod
    def parse_args() -> "Args":
        parser = argparse.ArgumentParser(
            description="Scan and convert PDF and DJVU files."
        )
        parser.add_argument(
            "--depth",
            type=int,
            default=0,
            help="Depth of subdirectory scanning (default: 0, no subdirectories)",
        )
        args = parser.parse_args()

        return Args(depth=args.depth)


def main() -> int:

    args = Args.parse_args()

    # Create output directory if it doesn't exist
    # OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
    input_dir = _INPUT_DIR
    output_dir = _OUTPUT_DIR

    # Call the function to scan and convert PDFs and DJVUs
    # remaining_files = scan_and_convert_pdfs(input_dir=input_dir, output_dir=output_dir)
    result: Result = scan_and_convert_pdfs(
        input_dir=input_dir, output_dir=output_dir, depth=args.depth
    )
    remaining_files: list[Path] = result.untranstlatable
    if remaining_files:
        print(f"\nRemaining files that could not be converted: {len(remaining_files)}")
        for item in remaining_files:
            print(f"  - {item.name}")
    else:
        print("\nAll files were successfully converted!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
