# BTW, the logic I would like on this is that your code looks for .pdf or .djvu
# that have no matching .txt filename in the output folder, and then processes
# the files to generate the .txt of the same name.
# And it should handle subfolders under the src folder as well,
# So when it's done processing, every pdf has a txt, in the output folder.


import argparse
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pdf_ingest.djvu import convert_djvu_to_text, convert_djvu_to_text_via_ocr

HERE = Path(__file__).parent.resolve()
TEST_DATA = HERE / "test_data"
OUTPUT_DIR = HERE / "test_data_output"


_DISABLE_TEXT_EMBEDDING_EXTRACTION = False


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


@dataclass
class TranslationItem:
    """
    Class to hold the translation item.
    """

    input_file: Path
    output_file: Path

    def __post_init__(self):
        if not isinstance(self.input_file, Path):
            raise TypeError("input_file must be a Path object")
        if not isinstance(self.output_file, Path):
            raise TypeError("output_file must be a Path object")
        if not self.input_file.exists():
            raise FileNotFoundError(f"{self.input_file} does not exist")


def _try_pdf_convert_to_text(pdf_file: Path, txt_file_out: Path) -> Exception | None:
    # pdftotext "Doing Business in Spain by Ian S Blackshaw.pdf" - | more
    if _DISABLE_TEXT_EMBEDDING_EXTRACTION:
        print(f"Skipping text extraction for {pdf_file.name} due to disabled setting.")
        return NotImplementedError("Text extraction is disabled.")
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
) -> list[TranslationItem]:
    # Iterate on all the pdf and djvu files in the input directory, including subfolders
    files_to_process: list[TranslationItem] = []  # input/output path

    # Create output directory if it doesn't exist
    # output_dir.mkdir(exist_ok=True, parents=True)
    assert input_dir.exists(), f"Input directory {input_dir} does not exist"
    assert output_dir.exists(), f"Output directory {output_dir} does not exist"

    # Find all PDF and DJVU files recursively
    for file_path in list(input_dir.glob("**/*.pdf")) + list(
        input_dir.glob("**/*.djvu")
    ):
        # Skip directories
        if file_path.is_dir():
            continue

        # Print the name of the file
        print(f"Found file: {file_path.name}")

        # Determine the relative path from input_dir
        rel_path = file_path.relative_to(input_dir)

        # Create the output file path with the same relative structure
        txt_file_output = output_dir / rel_path.with_suffix(".txt")

        # Create parent directories for output file if they don't exist
        txt_file_output.parent.mkdir(exist_ok=True, parents=True)

        # Check if output file already exists
        if txt_file_output.exists():
            print(f"Text file {txt_file_output} already exists. Skipping conversion.")
            continue

        # Print the full path of the file
        print(f"Full path: {file_path.resolve()}")
        print(f"Output will be: {txt_file_output}")

        files_to_process.append(
            TranslationItem(input_file=file_path, output_file=txt_file_output)
        )

    return files_to_process


def _convert_pdf_to_text_via_ocr(
    pdf_file: Path, txt_file_out: Path
) -> Exception | None:
    """
    uses ocrmypdf to write a pdf to a temporary file,
    then pdftotext to convert it to text, which is
    written to the output file"""

    try:
        # Create a temporary directory for the OCR'd PDF
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_pdf = Path(temp_dir) / f"{pdf_file.stem}_ocr.pdf"

            # Run OCR on the PDF
            subprocess.run(
                ["ocrmypdf", "--force-ocr", str(pdf_file), str(temp_pdf)],
                check=True,
            )

            # Convert the OCR'd PDF to text
            subprocess.run(
                ["pdftotext", str(temp_pdf), str(txt_file_out)],
                check=True,
            )

            # The temporary file will be automatically deleted when the context manager exits

        return None
    except subprocess.CalledProcessError as e:
        print(f"Error OCR'ing and converting {pdf_file.name} to text: {e}")
        return e
    except Exception as e:
        print(f"Unexpected error processing {pdf_file.name}: {e}")
        return e


def scan_and_convert_pdfs(input_dir: Path, output_dir: Path) -> list[TranslationItem]:
    """
    Scan for PDF and DJVU files in the input directory and convert them to text files in the output directory.

    Args:
        input_dir: Directory containing PDF and DJVU files
        output_dir: Directory where text files will be saved

    Returns:
        remaining_files: List of files that could not be converted
    """

    # Iterate on all the pdf and djvu files in the input directory
    files_to_process: list[TranslationItem] = _scan_for_untreated_files(
        input_dir=input_dir, output_dir=output_dir
    )

    print(f"Found {len(files_to_process)} files to process")

    remaining_files: list[TranslationItem] = []
    for item in files_to_process:
        # Handle different file types
        suffix = item.input_file.suffix.lower()
        if suffix == ".pdf":
            # First try regular PDF to text conversion
            err = _try_pdf_convert_to_text(
                pdf_file=item.input_file, txt_file_out=item.output_file
            )
            if err is not None:
                print(
                    f"Regular conversion failed for {item.input_file.name}, trying OCR..."
                )
                # If regular conversion fails, try OCR
                err = _convert_pdf_to_text_via_ocr(
                    pdf_file=item.input_file, txt_file_out=item.output_file
                )
                if err is not None:
                    print(f"OCR conversion also failed for {item.input_file.name}")
                    remaining_files.append(item)
                else:
                    print(f"Successfully converted {item.input_file.name} using OCR")
            else:
                print(
                    f"Successfully converted {item.input_file.name} using embedded text"
                )
        elif suffix == ".djvu":
            # First try regular DJVU to text conversion
            err = convert_djvu_to_text(
                djvu_file=item.input_file, txt_file_out=item.output_file
            )
            if err is not None:
                print(
                    f"Regular conversion failed for {item.input_file.name}, trying OCR..."
                )
                # If regular conversion fails, try OCR
                err = convert_djvu_to_text_via_ocr(
                    djvu_file=item.input_file, txt_file_out=item.output_file
                )
                if err is not None:
                    print(f"OCR conversion also failed for {item.input_file.name}")
                    remaining_files.append(item)
                else:
                    print(f"Successfully converted {item.input_file.name} using OCR")
            else:
                print(
                    f"Successfully converted {item.input_file.name} using embedded text"
                )
        else:
            print(f"Unsupported file type: {item.input_file.suffix}")
            remaining_files.append(item)

    # Try one more time with OCR for any remaining PDF and DJVU files
    if remaining_files:
        retry_pdf_files = [
            item for item in remaining_files if item.input_file.suffix.lower() == ".pdf"
        ]
        retry_djvu_files = [
            item
            for item in remaining_files
            if item.input_file.suffix.lower() == ".djvu"
        ]
        still_remaining = []

        # Retry PDF files with OCR
        if retry_pdf_files:
            print(f"\nRetrying {len(retry_pdf_files)} PDF files with OCR...")
            for item in retry_pdf_files:
                print(f"Attempting to OCR {item.input_file.name}")
                err = _convert_pdf_to_text_via_ocr(
                    pdf_file=item.input_file, txt_file_out=item.output_file
                )
                if err is not None:
                    print(f"OCR conversion failed for {item.input_file.name}")
                    still_remaining.append(item)
                else:
                    print(f"Successfully converted {item.input_file.name} using OCR")

        # Retry DJVU files with OCR
        if retry_djvu_files:
            print(f"\nRetrying {len(retry_djvu_files)} DJVU files with OCR...")
            for item in retry_djvu_files:
                print(f"Attempting to OCR {item.input_file.name}")
                err = convert_djvu_to_text_via_ocr(
                    djvu_file=item.input_file, txt_file_out=item.output_file
                )
                if err is not None:
                    print(f"OCR conversion failed for {item.input_file.name}")
                    still_remaining.append(item)
                else:
                    print(f"Successfully converted {item.input_file.name} using OCR")

        # Update remaining_files to only include files that still failed
        remaining_files = still_remaining

    return remaining_files


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
