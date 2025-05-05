# BTW, the logic I would like on this is that your code looks for .pdf or .djvu
# that have no matching .txt filename in the same folder, and then processes
# the files to generate the .txt of the same name.
# And it should handle subfolders under the main watch folder as well,
# and the watch folder should be a parameter in a batch that launches it, please.
# So when it's done processing, every pdf has a txt, in the same folder in which it started.
# Don't worry about collisions. I will have a different folder for each workstation,
# so each workstation can ASSUME it's only working on its own file set.

import sys
from pathlib import Path
import subprocess

HERE = Path(__file__).parent.resolve()
TEST_DATA = HERE / "test_data"
OUTPUT_DIR = HERE / "test_data_output"


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


def _scan_for_untreated_files(
    input_dir: Path, output_dir: Path
) -> list[tuple[Path, Path]]:
    # Iterate on all the pdf files in the input directory
    files_to_process: list[tuple[Path, Path]] = []  # input/output path
    for pdf_file in input_dir.glob("*.pdf", case_sensitive=False):
        # Print the name of the file
        print(f"Found PDF file: {pdf_file.name}")
        # Check if the file is a PDF
        if pdf_file.suffix.lower() != ".pdf":
            print(f"{pdf_file.name} is not a PDF file.")
            continue
        if pdf_file.is_dir():
            print(f"{pdf_file.name} is a directory.")
            continue
        # Print the full path of the file
        print(f"Full path: {pdf_file.resolve()}")
        txt_file_output = pdf_file.with_suffix(".txt")
        txt_file_output_name = txt_file_output.name
        txt_file_output = output_dir / txt_file_output_name
        if txt_file_output.exists():
            print(
                f"Text file {txt_file_output_name} already exists. Skipping conversion."
            )
            continue
        files_to_process.append((pdf_file, txt_file_output))
    return files_to_process


def scan_and_convert_pdfs(input_dir: Path, output_dir: Path) -> list[Path]:
    """
    Scan for PDF files in the input directory and convert them to text files in the output directory.

    Args:
        input_dir: Directory containing PDF files
        output_dir: Directory where text files will be saved

    Returns:
        remaining_files: List of files that could not be converted
    """

    # Iterate on all the pdf files in the input directory
    files_to_process: list[tuple[Path, Path]] = _scan_for_untreated_files(
        input_dir=input_dir, output_dir=output_dir
    )

    remaining_files: list[Path] = []
    for pdf_file, txt_file_output in files_to_process:
        err = _try_pdf_convert_to_text(pdf_file=pdf_file, txt_file_out=txt_file_output)
        if err is not None:
            print(f"Error converting {pdf_file.name} to text: {err}")
            remaining_files.append(pdf_file)
    return remaining_files


def main() -> int:
    # Create output directory if it doesn't exist
    # Call the function to scan and convert PDFs
    remaining_files = scan_and_convert_pdfs(input_dir=TEST_DATA, output_dir=OUTPUT_DIR)
    if remaining_files:
        print(f"\nRemaining files that could not be converted: {remaining_files}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
