print("Hello, World!")


import os
import sys
from pathlib import Path
import subprocess

HERE = Path(__file__).parent.resolve()
TEST_DATA = HERE / "test_data"


def _pdf_convert_to_text(pdf_file: Path) -> str:
    # pdftotext "Doing Business in Spain by Ian S Blackshaw.pdf" - | more
    subprocess.run(
        ["pdftotext", str(pdf_file)],
        check=True,
        text=True,
        capture_output=True,
    )




def main() -> int:
    # Iterate on all the pdf files in the test_data directory
    for pdf_file in TEST_DATA.glob("*.pdf"):
        # Print the name of the file
        print(f"Found PDF file: {pdf_file.name}")

        # Check if the file is a PDF
        if pdf_file.suffix.lower() != ".pdf":
            print(f"{pdf_file.name} is not a PDF file.")
            continue

        # Print the full path of the file
        print(f"Full path: {pdf_file.resolve()}")
        _pdf_convert_to_text(pdf_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())