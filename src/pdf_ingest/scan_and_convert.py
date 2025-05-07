# BTW, the logic I would like on this is that your code looks for .pdf or .djvu
# that have no matching .txt filename in the output folder, and then processes
# the files to generate the .txt of the same name.
# And it should handle subfolders under the src folder as well,
# So when it's done processing, every pdf has a txt, in the output folder.


from dataclasses import dataclass
from pathlib import Path

from pdf_ingest.djvu import convert_djvu_to_text, convert_djvu_to_text_via_ocr
from pdf_ingest.pdf import convert_pdf_to_text_via_ocr, try_pdf_convert_to_text

# from pdf_ingest.language_detect import language_detect

HERE = Path(__file__).parent.resolve()
TEST_DATA = HERE / "test_data"
OUTPUT_DIR = HERE / "test_data_output"


@dataclass
class Result:
    """
    Class to hold the result of the conversion.
    """

    input_files: list[Path]
    output_files: list[Path]
    untranstlatable: list[Path]
    errors: list[Exception]

    def __post_init__(self):
        if not isinstance(self.input_files, list):
            raise TypeError("input_files must be a list of Path objects")
        if not isinstance(self.output_files, list):
            raise TypeError("output_files must be a list of Path objects")
        if not isinstance(self.errors, list):
            raise TypeError("errors must be a list of Exception objects")

        for file in self.input_files:
            if not isinstance(file, Path):
                raise TypeError("input_files must be a list of Path objects")
        for file in self.output_files:
            if not isinstance(file, Path):
                raise TypeError("output_files must be a list of Path objects")


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


def _scan_for_untreated_files(
    input_dir: Path, output_dir: Path
) -> list[TranslationItem]:
    # Iterate on all the pdf and djvu files in the input directory, including subfolders
    files_to_process: list[TranslationItem] = []  # input/output path

    # Create output directory if it doesn't exist
    # output_dir.mkdir(exist_ok=True, parents=True)
    assert input_dir.exists(), f"Input directory {input_dir} does not exist"
    assert output_dir.exists(), f"Output directory {output_dir} does not exist"

    search_list = list(input_dir.glob("**/*.pdf"))
    search_list += list(input_dir.glob("**/*.djvu"))

    # Find all PDF and DJVU files recursively
    for file_path in search_list:
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


def _process_pdf_file(item: TranslationItem) -> tuple[Exception | None, bool]:
    """
    Process a PDF file and convert it to text.

    Args:
        item: TranslationItem containing input and output file paths

    Returns:
        tuple: (error, success) where error is None if successful and success is True if file was processed
    """
    # First try regular PDF to text conversion
    err = try_pdf_convert_to_text(
        pdf_file=item.input_file, txt_file_out=item.output_file
    )
    if err is not None:
        print(f"Regular conversion failed for {item.input_file.name}, trying OCR...")
        # If regular conversion fails, try OCR
        err = convert_pdf_to_text_via_ocr(
            pdf_file=item.input_file, txt_file_out=item.output_file
        )
        if err is not None:
            print(f"OCR conversion also failed for {item.input_file.name}")
            return err, False
        else:
            print(f"Successfully converted {item.input_file.name} using OCR")
            return None, True
    else:
        print(f"Successfully converted {item.input_file.name} using embedded text")
        return None, True


def _process_djvu_file(item: TranslationItem) -> tuple[Exception | None, bool]:
    """
    Process a DJVU file and convert it to text.

    Args:
        item: TranslationItem containing input and output file paths

    Returns:
        tuple: (error, success) where error is None if successful and success is True if file was processed
    """
    # First try regular DJVU to text conversion
    err = convert_djvu_to_text(djvu_file=item.input_file, txt_file_out=item.output_file)
    if err is not None:
        print(f"Regular conversion failed for {item.input_file.name}, trying OCR...")
        # If regular conversion fails, try OCR
        err = convert_djvu_to_text_via_ocr(
            djvu_file=item.input_file, txt_file_out=item.output_file
        )
        if err is not None:
            print(f"OCR conversion also failed for {item.input_file.name}")
            return err, False
        else:
            print(f"Successfully converted {item.input_file.name} using OCR")
            return None, True
    else:
        print(f"Successfully converted {item.input_file.name} using embedded text")
        return None, True


def _retry_pdf_ocr(item: TranslationItem) -> tuple[Exception | None, bool]:
    """
    Retry PDF conversion using OCR.

    Args:
        item: TranslationItem containing input and output file paths

    Returns:
        tuple: (error, success) where error is None if successful and success is True if file was processed
    """
    print(f"Attempting to OCR {item.input_file.name}")
    err = convert_pdf_to_text_via_ocr(
        pdf_file=item.input_file, txt_file_out=item.output_file
    )
    if err is not None:
        print(f"OCR conversion failed for {item.input_file.name}")
        return err, False
    else:
        print(f"Successfully converted {item.input_file.name} using OCR")
        return None, True


def _retry_djvu_ocr(item: TranslationItem) -> tuple[Exception | None, bool]:
    """
    Retry DJVU conversion using OCR.

    Args:
        item: TranslationItem containing input and output file paths

    Returns:
        tuple: (error, success) where error is None if successful and success is True if file was processed
    """
    print(f"Attempting to OCR {item.input_file.name}")
    err = convert_djvu_to_text_via_ocr(
        djvu_file=item.input_file, txt_file_out=item.output_file
    )
    if err is not None:
        print(f"OCR conversion failed for {item.input_file.name}")
        return err, False
    else:
        print(f"Successfully converted {item.input_file.name} using OCR")
        return None, True


def scan_and_convert_pdfs(input_dir: Path, output_dir: Path) -> Result:
    """
    Scan for PDF and DJVU files in the input directory and convert them to text files in the output directory.

    Args:
        input_dir: Directory containing PDF and DJVU files
        output_dir: Directory where text files will be saved

    Returns:
        Result: Object containing lists of input files, output files, and errors
    """

    # Iterate on all the pdf and djvu files in the input directory
    files_to_process: list[TranslationItem] = _scan_for_untreated_files(
        input_dir=input_dir, output_dir=output_dir
    )

    print(f"Found {len(files_to_process)} files to process")

    input_files: list[Path] = []
    output_files: list[Path] = []
    errors: list[Exception] = []
    remaining_files: list[TranslationItem] = []

    for item in files_to_process:
        # Add input file to the list
        input_files.append(item.input_file)

        # Handle different file types
        suffix = item.input_file.suffix.lower()
        if suffix == ".pdf":
            err, success = _process_pdf_file(item)
            if success:
                output_files.append(item.output_file)
            else:
                remaining_files.append(item)
                if err is not None:
                    errors.append(err)
        elif suffix == ".djvu":
            err, success = _process_djvu_file(item)
            if success:
                output_files.append(item.output_file)
            else:
                remaining_files.append(item)
                if err is not None:
                    errors.append(err)
        else:
            print(f"Unsupported file type: {item.input_file.suffix}")
            remaining_files.append(item)
            errors.append(Exception(f"Unsupported file type: {item.input_file.suffix}"))

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
                err, success = _retry_pdf_ocr(item)
                if success:
                    output_files.append(item.output_file)
                else:
                    still_remaining.append(item)
                    if err is not None:
                        errors.append(err)

        # Retry DJVU files with OCR
        if retry_djvu_files:
            print(f"\nRetrying {len(retry_djvu_files)} DJVU files with OCR...")
            for item in retry_djvu_files:
                err, success = _retry_djvu_ocr(item)
                if success:
                    output_files.append(item.output_file)
                else:
                    still_remaining.append(item)
                    if err is not None:
                        errors.append(err)

        # Update remaining_files to only include files that still failed
        remaining_files = still_remaining

    # Create list of untranslatable files from remaining_files
    untranslatable = [item.input_file for item in remaining_files]

    # Create and return the Result object
    return Result(
        input_files=input_files,
        output_files=output_files,
        untranstlatable=untranslatable,
        errors=errors,
    )
