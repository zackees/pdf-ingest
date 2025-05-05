# BTW, the logic I would like on this is that your code looks for .pdf or .djvu
# that have no matching .txt filename in the output folder, and then processes
# the files to generate the .txt of the same name.
# And it should handle subfolders under the src folder as well,
# So when it's done processing, every pdf has a txt, in the output folder.


import sys
from pathlib import Path
import subprocess
import tempfile
from dataclasses import dataclass

HERE = Path(__file__).parent.resolve()
TEST_DATA = HERE / "test_data"
OUTPUT_DIR = HERE / "test_data_output"


_DISABLE_TEXT_EMBEDDING_EXTRACTION = False

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
    # Iterate on all the pdf files in the input directory
    files_to_process: list[TranslationItem] = []  # input/output path
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
        files_to_process.append(TranslationItem(input_file=pdf_file, output_file=txt_file_output))
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
    Scan for PDF files in the input directory and convert them to text files in the output directory.

    Args:
        input_dir: Directory containing PDF files
        output_dir: Directory where text files will be saved

    Returns:
        remaining_files: List of files that could not be converted
    """

    # Iterate on all the pdf files in the input directory
    files_to_process: list[TranslationItem] = _scan_for_untreated_files(
        input_dir=input_dir, output_dir=output_dir
    )

    remaining_files: list[TranslationItem] = []
    for item in files_to_process:
        # First try regular PDF to text conversion
        err = _try_pdf_convert_to_text(pdf_file=item.input_file, txt_file_out=item.output_file)
        if err is not None:
            print(f"Regular conversion failed for {item.input_file.name}, trying OCR...")
            # If regular conversion fails, try OCR
            err = _convert_pdf_to_text_via_ocr(pdf_file=item.input_file, txt_file_out=item.output_file)
            if err is not None:
                print(f"OCR conversion also failed for {item.input_file.name}")
                remaining_files.append(item)
            else:
                print(f"Successfully converted {item.input_file.name} using OCR")


    if len(remaining_files) > 0:
        remaining_files, remaining_files_ocr = [], remaining_files
        print(f"{len(remaining_files_ocr)} files do not have embedded text, using ocr")
        for item in remaining_files_ocr:
            print(f"Attempting to OCR {item.input_file.name}")
            err = _convert_pdf_to_text_via_ocr(pdf_file=item.input_file, txt_file_out=item.output_file)
            if err is not None:
                print(f"OCR conversion failed for {item.input_file.name}")
                remaining_files.append(item)
            else:
                print(f"Successfully converted {item.input_file.name} using OCR")
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
