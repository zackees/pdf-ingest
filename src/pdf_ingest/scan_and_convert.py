# BTW, the logic I would like on this is that your code looks for .pdf or .djvu
# that have no matching .txt filename in the output folder, and then processes
# the files to generate the .txt of the same name.
# And it should handle subfolders under the src folder as well,
# So when it's done processing, every pdf has a txt, in the output folder.
# Additionally, check for corresponding .json files - missing .json files indicate
# that translation is not done.

import json
from typing import Callable

from pdf_ingest.fs_factory import FileSystemFactory
from pdf_ingest.fs_path import UniversalPath, is_remote_path
from pdf_ingest.parsers.djvu import process_djvu_file
from pdf_ingest.parsers.epub import process_epub_file
from pdf_ingest.parsers.fb2 import process_fb2_file
from pdf_ingest.parsers.pdf import process_pdf_file
from pdf_ingest.types import Result, TranslationItem

TRANSLATION_FUNCTIONS: dict[
    str, Callable[[TranslationItem], tuple[Exception | None, bool]]
] = {
    ".pdf": process_pdf_file,
    ".djvu": process_djvu_file,
    ".epub": process_epub_file,
    ".fb2": process_fb2_file,
}

TRANSLATABLE_EXTENSIONS = TRANSLATION_FUNCTIONS.keys()


def prompt_for_input_dir() -> str:
    """
    Prompt the user for an input directory path string.

    Returns:
        str: The input directory path string (local or remote format)
    """
    while True:
        input_dir_str = input(
            "Enter the input directory path (local path or remote:path): "
        )

        try:
            # Try to create the path to validate it
            input_dir = FileSystemFactory.create_path(input_dir_str)
            if input_dir.exists() and input_dir.is_dir():
                return input_dir_str
            else:
                print(
                    f"Directory {input_dir_str} does not exist or is not a directory. Please try again."
                )
        except Exception as e:
            print(f"Invalid path format '{input_dir_str}': {e}. Please try again.")


def _scan_for_untreated_files(
    input_dir: UniversalPath, output_dir: UniversalPath, depth: int
) -> list[TranslationItem]:
    """
    Scan for PDF and DJVU files in the input directory that don't have corresponding
    text files in the output directory. Also checks for corresponding JSON files.
    Now supports both local and remote filesystems.

    Args:
        input_dir: Directory containing PDF and DJVU files (local or remote)
        output_dir: Directory where text files will be saved (local or remote)
        depth: Maximum depth for subdirectory scanning

    Returns:
        list[TranslationItem]: List of files to process with their metadata
    """
    files_to_process: list[TranslationItem] = []

    # Validate directories exist
    assert input_dir.exists(), f"Input directory {input_dir} does not exist"
    assert output_dir.exists(), f"Output directory {output_dir} does not exist"

    fs_type_input = "remote" if is_remote_path(input_dir) else "local"
    fs_type_output = "remote" if is_remote_path(output_dir) else "local"

    print(
        f"Scanning for files in {input_dir} ({fs_type_input}) -> {output_dir} ({fs_type_output})"
    )
    print(f"Scan depth: {depth}")

    try:
        # Get list of files - this works for both FSPath and Path
        file_list = list(input_dir.glob("*"))
        print(f"Found {len(file_list)} items in {input_dir}")

        for item in file_list:
            print(f"  - {item.name}")

    except Exception as e:
        raise Exception(f"Failed to list files in {input_dir}: {e}")

    # Filter for translatable files
    search_list: list[UniversalPath] = []
    for file_path in file_list:
        try:
            if file_path.is_dir():
                continue

            # Check depth limitation
            if depth > 0:
                # Calculate relative path for depth checking using path methods
                try:
                    if is_remote_path(input_dir):
                        # For remote paths, use a safer approach
                        file_parts = str(file_path).split("/")
                        input_parts = str(input_dir).split("/")
                        # Find relative depth by comparing path components
                        if len(file_parts) > len(input_parts):
                            rel_depth = len(file_parts) - len(input_parts)
                            if rel_depth > depth:
                                continue
                    else:
                        # For local paths, use relative_to method
                        rel_path = file_path.relative_to(input_dir)
                        if len(str(rel_path).split("/")) > depth:
                            continue
                except Exception:
                    # If we can't determine depth, continue processing
                    pass

            if file_path.suffix.lower() in TRANSLATABLE_EXTENSIONS:
                search_list.append(file_path)

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue

    print(f"Found {len(search_list)} translatable files")

    # Process each translatable file
    for file_path in search_list:
        try:
            print(f"Processing: {file_path.name}")

            # Calculate relative path from input_dir
            # Use path methods instead of string manipulation for better compatibility
            try:
                if is_remote_path(input_dir):
                    # For remote paths, try relative_to first, fallback to name comparison
                    try:
                        rel_path = file_path.relative_to(input_dir)
                        rel_path_str = str(rel_path)
                    except Exception:
                        # Fallback: use just the filename if relative path calculation fails
                        rel_path_str = file_path.name
                else:
                    # For local paths, use the standard relative_to method
                    rel_path = file_path.relative_to(input_dir)
                    rel_path_str = str(rel_path)
            except Exception:
                # Ultimate fallback: use just the filename
                rel_path_str = file_path.name

            # Create output file path with same relative structure
            txt_file_output = output_dir / rel_path_str.replace(
                file_path.suffix, ".txt"
            )

            # Ensure parent directories exist
            try:
                txt_file_output.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(
                    f"Warning: Could not create parent directory for {txt_file_output}: {e}"
                )

            # Check if output file already exists
            if txt_file_output.exists():
                print(
                    f"Text file {txt_file_output.name} already exists. Skipping conversion."
                )
                continue

            # Check for corresponding JSON file
            json_file = output_dir / rel_path_str.replace(file_path.suffix, ".json")
            json_exists = json_file.exists()

            # Check if JSON indicates processing is complete
            if json_exists:
                try:
                    json_content = json_file.read_text()
                    json_data = json.loads(json_content)

                    if json_data.get("language_detection_reliable"):
                        print(
                            f"JSON file {json_file.name} indicates processing complete. Skipping."
                        )
                        continue
                except Exception as e:
                    print(f"Warning: Could not read JSON file {json_file}: {e}")

            # Create empty JSON file if it doesn't exist
            if not json_exists:
                print(f"Creating JSON metadata file: {json_file.name}")
                try:
                    json_file.parent.mkdir(parents=True, exist_ok=True)
                    json_file.write_text('{"language": ""}')
                except Exception as e:
                    print(f"Warning: Could not create JSON file {json_file}: {e}")

            print(f"Input: {file_path.name} -> Output: {txt_file_output.name}")

            files_to_process.append(
                TranslationItem(
                    input_file=file_path,
                    output_file=txt_file_output,
                    json_file=json_file,
                    json_exists=json_exists,
                )
            )

        except Exception as e:
            print(f"Error setting up processing for {file_path}: {e}")
            continue

    return files_to_process


def scan_and_convert(
    input_dir: UniversalPath, output_dir: UniversalPath, depth: int
) -> Result:
    """
    Scan for PDF and DJVU files in the input directory and convert them to text files in the output directory.
    Now supports both local and remote filesystems.

    Args:
        input_dir: Directory containing PDF and DJVU files (local or remote)
        output_dir: Directory where text files will be saved (local or remote)
        depth: Maximum depth for subdirectory scanning

    Returns:
        Result: Object containing lists of input files, output files, errors, and missing json files
    """

    # Scan for files to process
    files_to_process = _scan_for_untreated_files(
        input_dir=input_dir, output_dir=output_dir, depth=depth
    )

    print(f"Found {len(files_to_process)} files to process")

    input_files: list[UniversalPath] = []
    output_files: list[UniversalPath] = []
    errors: list[Exception] = []
    remaining_files: list[TranslationItem] = []

    # Process each file
    for item in files_to_process:
        input_files.append(item.input_file)

        try:
            # Get processing function for file type
            suffix = item.input_file.suffix.lower()
            process_function = TRANSLATION_FUNCTIONS.get(suffix)

            if process_function is None:
                err = Exception(f"Unsupported file type: {suffix}")
                errors.append(err)
                remaining_files.append(item)
                continue

            # Process the file
            print(f"Processing {item.input_file.name} with {process_function.__name__}")
            err, success = process_function(item)

            if success:
                output_files.append(item.output_file)
                print(f"✓ Successfully processed {item.input_file.name}")
            else:
                remaining_files.append(item)
                if err is not None:
                    errors.append(err)
                    print(f"✗ Failed to process {item.input_file.name}: {err}")
                else:
                    print(f"✗ Failed to process {item.input_file.name} (unknown error)")

        except Exception as e:
            errors.append(e)
            remaining_files.append(item)
            print(f"✗ Exception processing {item.input_file.name}: {e}")

    # Create result summary
    untranslatable = [item.input_file for item in remaining_files]
    missing_json_files = [
        item.input_file for item in files_to_process if not item.json_exists
    ]

    print("\nProcessing complete:")
    print(f"  Successful: {len(output_files)}")
    print(f"  Failed: {len(untranslatable)}")
    print(f"  Errors: {len(errors)}")

    return Result(
        input_files=input_files,
        output_files=output_files,
        untranstlatable=untranslatable,
        errors=errors,
        missing_json_files=missing_json_files,
    )
