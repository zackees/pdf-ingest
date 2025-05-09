# BTW, the logic I would like on this is that your code looks for .pdf or .djvu
# that have no matching .txt filename in the output folder, and then processes
# the files to generate the .txt of the same name.
# And it should handle subfolders under the src folder as well,
# So when it's done processing, every pdf has a txt, in the output folder.
# Additionally, check for corresponding .json files - missing .json files indicate
# that translation is not done.


import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from pdf_ingest.djvu import convert_djvu_to_text, convert_djvu_to_text_via_ocr
from pdf_ingest.json_util import update_json_with_language
from pdf_ingest.language_detection import detect_language_from_file
from pdf_ingest.pdf import process_pdf_file
from pdf_ingest.types import TranslationItem

HERE = Path(__file__).parent.resolve()
TEST_DATA = HERE / "input"
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
    missing_json_files: list[Path]

    def __post_init__(self):
        if not isinstance(self.input_files, list):
            raise TypeError("input_files must be a list of Path objects")
        if not isinstance(self.output_files, list):
            raise TypeError("output_files must be a list of Path objects")
        if not isinstance(self.errors, list):
            raise TypeError("errors must be a list of Exception objects")
        if not isinstance(self.missing_json_files, list):
            raise TypeError("missing_json_files must be a list of Path objects")

        for file in self.input_files:
            if not isinstance(file, Path):
                raise TypeError("input_files must be a list of Path objects")
        for file in self.output_files:
            if not isinstance(file, Path):
                raise TypeError("output_files must be a list of Path objects")
        for file in self.missing_json_files:
            if not isinstance(file, Path):
                raise TypeError("missing_json_files must be a list of Path objects")


def _scan_for_untreated_files(
    input_dir: Path, output_dir: Path
) -> list[TranslationItem]:
    """
    Scan for PDF and DJVU files in the input directory that don't have corresponding
    text files in the output directory. Also checks for corresponding JSON files.

    Args:
        input_dir: Directory containing PDF and DJVU files
        output_dir: Directory where text files will be saved

    Returns:
        list[TranslationItem]: List of files to process with their metadata
    """
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
        # We'll update this with language code later after detection
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

        # Check if corresponding .json file exists
        json_file = output_dir / rel_path.with_suffix(".json")
        json_exists = json_file.exists()

        if not json_exists:
            print(f"JSON file {json_file} does not exist. Translation not done.")
            # Create empty JSON file
            with open(json_file, "w") as f:
                json.dump({"language": ""}, f)
            print(f"Created empty JSON file: {json_file}")

        files_to_process.append(
            TranslationItem(
                input_file=file_path,
                output_file=txt_file_output,
                json_file=json_file,
                json_exists=json_exists,
            )
        )

    return files_to_process


def _process_djvu_file(item: TranslationItem) -> tuple[Exception | None, bool]:
    """
    Process a DJVU file and convert it to text.
    Uses a temporary directory for the conversion process and then copies the result to the final destination.

    Args:
        item: TranslationItem containing input and output file paths

    Returns:
        tuple: (error, success) where error is None if successful and success is True if file was processed
    """
    with TemporaryDirectory() as temp_dir:
        # Create a temporary output file path
        temp_output = Path(temp_dir) / f"temp_{item.input_file.name}.txt"

        # First try regular DJVU to text conversion
        err = convert_djvu_to_text(djvu_file=item.input_file, txt_file_out=temp_output)
        if err is not None:
            print(
                f"Regular conversion failed for {item.input_file.name}, trying OCR..."
            )
            # If regular conversion fails, try OCR
            err = convert_djvu_to_text_via_ocr(
                djvu_file=item.input_file, txt_file_out=temp_output
            )
            if err is not None:
                print(f"OCR conversion also failed for {item.input_file.name}")
                return err, False
            else:
                # Detect language from the temporary file
                lang_code, is_reliable = detect_language_from_file(temp_output)
                item.language = lang_code
                item.should_translate = lang_code.lower() == "en"

                # Update the output filename to include language code
                stem = item.output_file.stem
                suffix = item.output_file.suffix
                new_filename = f"{stem}-{lang_code.upper()}{suffix}"
                item.output_file = item.output_file.with_name(new_filename)

                # Update JSON with language information
                update_json_with_language(item.json_file, lang_code, is_reliable)

                # Copy from temp location to final destination
                try:
                    shutil.copy2(temp_output, item.output_file)
                    print(
                        f"Successfully converted {item.input_file.name} using OCR (language: {lang_code})"
                    )
                    return None, True
                except Exception as copy_err:
                    print(f"Error copying file from temporary location: {copy_err}")
                    return copy_err, False
        else:
            # Detect language from the temporary file
            lang_code, is_reliable = detect_language_from_file(temp_output)
            item.language = lang_code
            item.should_translate = lang_code.lower() == "en"

            # Update the output filename to include language code
            stem = item.output_file.stem
            suffix = item.output_file.suffix
            new_filename = f"{stem}-{lang_code.upper()}{suffix}"
            item.output_file = item.output_file.with_name(new_filename)

            # Update JSON with language information
            update_json_with_language(item.json_file, lang_code, is_reliable)

            # Copy from temp location to final destination
            try:
                shutil.copy2(temp_output, item.output_file)
                print(
                    f"Successfully converted {item.input_file.name} using embedded text (language: {lang_code})"
                )
                return None, True
            except Exception as copy_err:
                print(f"Error copying file from temporary location: {copy_err}")
                return copy_err, False


def _update_language_in_json(txt_file: Path, json_file: Path) -> None:
    """
    Detect the language of the text file and update the JSON file with the language information.

    Args:
        txt_file: Path to the text file
        json_file: Path to the JSON file to update
    """
    lang_code, is_reliable = detect_language_from_file(txt_file)
    update_json_with_language(json_file, lang_code, is_reliable)


def scan_and_convert_pdfs(input_dir: Path, output_dir: Path) -> Result:
    """
    Scan for PDF and DJVU files in the input directory and convert them to text files in the output directory.
    Also checks for corresponding .json files - missing .json files indicate translation is not done.

    Args:
        input_dir: Directory containing PDF and DJVU files
        output_dir: Directory where text files will be saved

    Returns:
        Result: Object containing lists of input files, output files, errors, and missing json files
    """

    # Iterate on all the pdf and djvu files in the input directory
    files_to_process = _scan_for_untreated_files(
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
            err, success = process_pdf_file(item)
        elif suffix == ".djvu":
            err, success = _process_djvu_file(item)
        else:
            print(f"Unsupported file type: {item.input_file.suffix}")
            remaining_files.append(item)
            errors.append(Exception(f"Unsupported file type: {item.input_file.suffix}"))
            continue

        if success:
            output_files.append(item.output_file)
            # Language detection and JSON update already done during processing
        else:
            remaining_files.append(item)
            if err is not None:
                errors.append(err)

    # Create list of untranslatable files from remaining_files
    untranslatable = [item.input_file for item in remaining_files]

    # Create list of missing JSON files from files_to_process
    missing_json_files = [
        item.input_file for item in files_to_process if not item.json_exists
    ]

    # Create and return the Result object
    return Result(
        input_files=input_files,
        output_files=output_files,
        untranstlatable=untranslatable,
        errors=errors,
        missing_json_files=missing_json_files,
    )
