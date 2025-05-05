print("Hello, World!")


import os
import sys
from pathlib import Path
import subprocess

HERE = Path(__file__).parent.resolve()
TEST_DATA = HERE / "test_data"


def _try_pdf_convert_to_text(pdf_file: Path, txt_file_out: Path) -> Exception | None:
    # pdftotext "Doing Business in Spain by Ian S Blackshaw.pdf" - | more
    try:
        subprocess.run(
            ["pdftotext", str(pdf_file), txt_file_out],
            check=True,
        )
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error converting {pdf_file.name} to text: {e}")
        return e




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

        txt_file_output = pdf_file.with_suffix(".txt")
        txt_file_output_name = txt_file_output.name
        txt_file_output = Path("test_data_output") / txt_file_output_name
        _try_pdf_convert_to_text(
            pdf_file=pdf_file,
            txt_file_out=txt_file_output
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())