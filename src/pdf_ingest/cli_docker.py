# BTW, the logic I would like on this is that your code looks for .pdf or .djvu
# that have no matching .txt filename in the output folder, and then processes
# the files to generate the .txt of the same name.
# And it should handle subfolders under the src folder as well,
# So when it's done processing, every pdf has a txt, in the output folder.

import sys
from dataclasses import dataclass
from pathlib import Path

from pdf_ingest.scan_and_convert import Result, scan_and_convert_pdfs

_PATH_APP = Path("/app")
_INPUT_DIR = _PATH_APP / "input"
_OUTPUT_DIR = _PATH_APP / "output"


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


def main() -> int:

    # Create output directory if it doesn't exist
    # OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
    input_dir = _INPUT_DIR
    output_dir = _OUTPUT_DIR

    # Call the function to scan and convert PDFs and DJVUs
    # remaining_files = scan_and_convert_pdfs(input_dir=input_dir, output_dir=output_dir)
    result: Result = scan_and_convert_pdfs(input_dir=input_dir, output_dir=output_dir)
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
