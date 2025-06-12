# BTW, the logic I would like on this is that your code looks for .pdf or .djvu
# that have no matching .txt filename in the output folder, and then processes
# the files to generate the .txt of the same name.
# And it should handle subfolders under the src folder as well,
# So when it's done processing, every pdf has a txt, in the output folder.
# Additionally, check for corresponding .json files - missing .json files indicate
# that translation is not done.


import json
from pathlib import Path

from pdf_ingest.djvu import process_djvu_file
from pdf_ingest.epub import process_epub_file
from pdf_ingest.pdf import process_pdf_file
from pdf_ingest.types import Result, TranslationItem

HERE = Path(__file__).parent.resolve()
TEST_DATA = HERE / "input"
OUTPUT_DIR = HERE / "test_data_output"


def prompt_for_input_dir() -> Path:
    """
    Prompt the user for an input directory and validate it exists.

    Returns:
        Path: The validated input directory path
    """
    while True:
        input_dir_str = input("Enter the input directory path: ")
        input_dir = Path(input_dir_str)

        if input_dir.exists() and input_dir.is_dir():
            return input_dir
        else:
            print(
                f"Directory {input_dir} does not exist or is not a directory. Please try again."
            )


def _scan_for_untreated_files(
    input_dir: Path, output_dir: Path, depth: int
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

    print(f"Scanning for PDF and DJVU files in {input_dir}... with depth {depth}")

    file_list = list(input_dir.glob("*"))

    print(f"Found {len(file_list)} files in {input_dir}")
    for file_path in file_list:
        print(f"  - {file_path.name}")

    search_list = []
    for file_path in file_list:
        if file_path.is_dir():
            continue
        if depth > 0 and len(file_path.relative_to(input_dir).parts) > depth:
            continue
        if file_path.suffix.lower() in [".pdf", ".djvu"]:
            search_list.append(file_path)

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

        # Check if corresponding .json file exists
        json_file = output_dir / rel_path.with_suffix(".json")
        json_exists = json_file.exists()

        # Skip if JSON file already exists (translation already done)
        if json_exists:
            # now check that the json is not empty
            with open(json_file, "r") as f:
                try:
                    json_data = json.load(f)

                    key = "language_detection_reliable"
                    if json_data.get(key):
                        print(
                            f"JSON file {json_file} already exists. Skipping this file as it's already processed."
                        )
                        continue
                except json.JSONDecodeError:
                    pass

        # Print the full path of the file
        print(f"Input file: {file_path.name}")
        print(f"Output file: {txt_file_output.name}")

        assert not json_exists
        # Create empty JSON file if it doesn't exist
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


def scan_and_convert_pdfs(input_dir: Path, output_dir: Path, depth: int) -> Result:
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
        input_dir=input_dir, output_dir=output_dir, depth=depth  # or any desired depth
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
            err, success = process_djvu_file(item)
        elif suffix == ".epub":
            err, success = process_epub_file(
                item
            )  # Assuming you have a function for EPUB
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
