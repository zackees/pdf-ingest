# BTW, the logic I would like on this is that your code looks for .pdf or .djvu
# that have no matching .txt filename in the output folder, and then processes
# the files to generate the .txt of the same name.
# And it should handle subfolders under the src folder as well,
# So when it's done processing, every pdf has a txt, in the output folder.
# Additionally, check for corresponding .json files - missing .json files indicate
# that translation is not done.

import json
import logging
import sys
from typing import Callable

from pdf_ingest.data_types import Result, TranslationItem
from pdf_ingest.fs_factory import FileSystemFactory
from pdf_ingest.fs_path import UniversalPath, is_remote_path
from pdf_ingest.parsers.djvu import process_djvu_file
from pdf_ingest.parsers.epub import process_epub_file
from pdf_ingest.parsers.fb2 import process_fb2_file
from pdf_ingest.parsers.pdf import process_pdf_file

TRANSLATION_FUNCTIONS: dict[
    str, Callable[[TranslationItem], tuple[Exception | None, bool]]
] = {
    ".pdf": process_pdf_file,
    ".djvu": process_djvu_file,
    ".epub": process_epub_file,
    ".fb2": process_fb2_file,
}

TRANSLATABLE_EXTENSIONS = TRANSLATION_FUNCTIONS.keys()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def prompt_for_input_dir() -> str:
    """
    Prompt the user for an input directory path string.

    Returns:
        str: The input directory path string (local or remote format)
    """
    logger.info("Prompting user for input directory")
    while True:
        input_dir_str = input(
            "Enter the input directory path (local path or remote:path): "
        )
        logger.debug(f"User entered path: {input_dir_str}")

        try:
            # Try to create the path to validate it
            logger.debug(f"Attempting to validate path: {input_dir_str}")
            input_dir = FileSystemFactory.create_path(input_dir_str)
            if input_dir.exists() and input_dir.is_dir():
                logger.info(f"Successfully validated input directory: {input_dir_str}")
                return input_dir_str
            else:
                logger.warning(
                    f"Path validation failed: {input_dir_str} does not exist or is not a directory"
                )
                print(
                    f"Directory {input_dir_str} does not exist or is not a directory. Please try again."
                )
        except Exception as e:
            logger.error(f"Invalid path format '{input_dir_str}': {e}")
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
    logger.info(
        f"Starting scan for untreated files: input_dir={input_dir}, output_dir={output_dir}, depth={depth}"
    )
    logger.debug(
        f"Input filesystem: {type(input_dir.fs).__name__}, protocol={input_dir.fs.protocol}"
    )
    logger.debug(
        f"Output filesystem: {type(output_dir.fs).__name__}, protocol={output_dir.fs.protocol}"
    )

    files_to_process: list[TranslationItem] = []

    # Validate directories exist
    logger.debug(
        f"Validating directory existence: input_dir={input_dir}, output_dir={output_dir}"
    )
    try:
        input_exists = input_dir.exists()
        logger.debug(f"Input directory exists: {input_exists}")
        assert input_exists, f"Input directory {input_dir} does not exist"

        output_exists = output_dir.exists()
        logger.debug(f"Output directory exists: {output_exists}")
        assert output_exists, f"Output directory {output_dir} does not exist"

        logger.info("Directory validation successful")
    except Exception as e:
        logger.error(f"Directory validation failed: {e}")
        raise

    fs_type_input = "remote" if is_remote_path(input_dir) else "local"
    fs_type_output = "remote" if is_remote_path(output_dir) else "local"

    logger.info(f"Filesystem types: input={fs_type_input}, output={fs_type_output}")
    logger.info(f"Scan depth: {depth}")

    print(
        f"Scanning for files in {input_dir} ({fs_type_input}) -> {output_dir} ({fs_type_output})"
    )
    print(f"Scan depth: {depth}")

    try:
        logger.debug(f"Attempting to list files in {input_dir}")
        logger.debug("Using UniversalPath.iterdir() method (FSSpec-based)")

        # Use the unified UniversalPath interface
        file_list = list(input_dir.iterdir())
        logger.debug(f"Found {len(file_list)} items via iterdir()")

        # Separate files and directories
        files = []
        directories = []
        for item in file_list:
            try:
                if item.is_dir():
                    directories.append(item)
                    logger.debug(f"Directory: {item.name}")
                elif item.is_file():
                    files.append(item)
                    logger.debug(f"File: {item.name}")
                else:
                    logger.debug(f"Unknown item type: {item.name}")
            except Exception as e:
                logger.warning(f"Could not determine type of {item.name}: {e}")
                # Assume it's a file if we can't determine
                files.append(item)

        logger.info(
            f"Found {len(files)} files and {len(directories)} directories in {input_dir}"
        )
        print(
            f"Found {len(files)} files and {len(directories)} directories in {input_dir}"
        )

        # Log first few items for debugging
        for i, item in enumerate(file_list[:10]):  # Show first 10 items
            item_type = "DIR" if item in directories else "FILE"
            print(f"  {item_type} {item.name}")
            logger.debug(f"  {item_type} {item.name} (path: {item.path})")

        if len(file_list) > 10:
            print(f"  ... and {len(file_list) - 10} more items")
            logger.debug(f"  ... and {len(file_list) - 10} more items")

    except Exception as e:
        logger.error(f"Failed to list files in {input_dir}: {e}")
        logger.error(
            f"Input dir type: {type(input_dir)}, filesystem: {type(input_dir.fs).__name__}"
        )
        raise Exception(f"Failed to list files in {input_dir}: {e}")

    # Filter for translatable files
    logger.debug(
        f"🔍 Filtering for translatable files with extensions: {list(TRANSLATABLE_EXTENSIONS)}"
    )
    search_list: list[UniversalPath] = []

    logger.debug(f"📋 Processing {len(files)} files for translation candidates")

    for file_path in files:  # Only process files, not directories
        try:
            logger.debug(f"🔍 Examining file: {file_path.name}")

            # Check depth limitation using UniversalPath methods
            if depth > 0:
                logger.debug(f"📏 Checking depth limitation (max depth: {depth})")
                try:
                    relative_path = file_path.relative_to(input_dir)
                    # Count directory separators to determine depth
                    rel_depth = len(relative_path.path.strip("/").split("/")) - 1
                    logger.debug(
                        f"📊 File depth: {rel_depth}, relative path: {relative_path.path}"
                    )

                    if rel_depth > depth:
                        logger.debug(
                            f"⏭️  Skipping {file_path.name} due to depth limit: {rel_depth} > {depth}"
                        )
                        continue
                except Exception as e:
                    logger.warning(
                        f"⚠️  Could not calculate relative depth for {file_path.name}: {e}"
                    )
                    logger.debug(
                        f"🔧 File path: {file_path.path}, Input dir: {input_dir.path}"
                    )
                    # If we can't calculate depth, process the file anyway
                    pass

            # Check if file has translatable extension
            file_suffix = file_path.suffix.lower()
            logger.debug(f"🔍 File extension: '{file_suffix}'")

            if file_suffix in TRANSLATABLE_EXTENSIONS:
                logger.debug(
                    f"✅ Added translatable file: {file_path.name} (extension: {file_suffix})"
                )
                search_list.append(file_path)
            else:
                logger.debug(
                    f"⏭️  Skipped {file_path.name}: unsupported extension '{file_suffix}'"
                )

        except Exception as e:
            logger.warning(f"⚠️  Error processing {file_path}: {e}")
            logger.debug(
                f"🔧 File type: {type(file_path)}, path: {getattr(file_path, 'path', 'unknown')}"
            )
            print(f"Error processing {file_path}: {e}")
            continue

    logger.info(f"📊 Found {len(search_list)} translatable files")
    print(f"Found {len(search_list)} translatable files")

    # Process each translatable file
    logger.debug(
        f"🔄 Processing {len(search_list)} translatable files for output file checking"
    )
    for file_path in search_list:
        try:
            logger.debug(f"🔄 Processing file: {file_path.name}")
            logger.debug(f"📂 File path: {file_path.path}")
            print(f"Processing: {file_path.name}")

            # Calculate relative path from input_dir using UniversalPath methods
            logger.debug("📐 Calculating relative path for output structure")
            try:
                rel_path = file_path.relative_to(input_dir)
                rel_path_str = rel_path.path
                logger.debug(f"✅ Relative path calculated: {rel_path_str}")
            except Exception as e:
                logger.warning(
                    f"⚠️  Could not calculate relative path for {file_path.name}: {e}"
                )
                # Fallback: use just the filename
                rel_path_str = file_path.name
                logger.debug(f"🔄 Using filename fallback: {rel_path_str}")

            # Create output file path with same relative structure
            output_filename = rel_path_str.replace(file_path.suffix, ".txt")
            logger.debug(f"📝 Output filename: {output_filename}")

            txt_file_output = output_dir / output_filename
            logger.debug(f"📍 Full output path: {txt_file_output.path}")

            # Ensure parent directories exist
            try:
                logger.debug(
                    f"📁 Ensuring parent directory exists: {txt_file_output.parent.path}"
                )
                txt_file_output.parent.mkdir(parents=True, exist_ok=True)
                logger.debug("✅ Parent directory created/verified")
            except Exception as e:
                logger.warning(f"⚠️  Could not create parent directory: {e}")
                print(
                    f"Warning: Could not create parent directory for {txt_file_output.name}: {e}"
                )

            # Check if output file already exists
            logger.debug(f"🔍 Checking if output file exists: {txt_file_output.name}")
            try:
                output_exists = txt_file_output.exists()
                logger.debug(f"📋 Output file exists: {output_exists}")

                if output_exists:
                    logger.debug(
                        f"⏭️  Text file {txt_file_output.name} already exists, skipping"
                    )
                    print(
                        f"Text file {txt_file_output.name} already exists. Skipping conversion."
                    )
                    continue
            except Exception as e:
                logger.warning(f"⚠️  Could not check if output file exists: {e}")
                # Assume it doesn't exist and continue processing

            # Check for corresponding JSON file
            json_filename = rel_path_str.replace(file_path.suffix, ".json")
            json_file = output_dir / json_filename
            logger.debug(f"📋 JSON metadata file: {json_file.path}")

            try:
                json_exists = json_file.exists()
                logger.debug(f"📋 JSON file exists: {json_exists}")
            except Exception as e:
                logger.warning(f"⚠️  Could not check JSON file existence: {e}")
                json_exists = False

            # Check if JSON indicates processing is complete
            if json_exists:
                logger.debug(
                    f"📖 JSON file exists: {json_file.name}, checking completion status"
                )
                try:
                    json_content = json_file.read_text()
                    json_data = json.loads(json_content)
                    logger.debug(f"📋 JSON content loaded: {list(json_data.keys())}")

                    if json_data.get("language_detection_reliable"):
                        logger.debug(
                            f"✅ JSON file {json_file.name} indicates processing complete, skipping"
                        )
                        print(
                            f"JSON file {json_file.name} indicates processing complete. Skipping."
                        )
                        continue
                    else:
                        logger.debug(
                            "🔄 JSON indicates incomplete processing, will continue"
                        )
                except Exception as e:
                    logger.warning(f"⚠️  Could not read JSON file {json_file.name}: {e}")
                    print(f"Warning: Could not read JSON file {json_file.name}: {e}")

            # Create empty JSON file if it doesn't exist
            if not json_exists:
                logger.debug(f"📝 Creating JSON metadata file: {json_file.name}")
                print(f"Creating JSON metadata file: {json_file.name}")
                try:
                    logger.debug(
                        f"📁 Ensuring JSON parent directory: {json_file.parent.path}"
                    )
                    json_file.parent.mkdir(parents=True, exist_ok=True)
                    json_file.write_text('{"language": ""}')
                    logger.debug(f"✅ Successfully created JSON file: {json_file.name}")
                except Exception as e:
                    logger.warning(
                        f"⚠️  Could not create JSON file {json_file.name}: {e}"
                    )
                    print(f"Warning: Could not create JSON file {json_file.name}: {e}")

            logger.debug(
                f"➕ Adding to processing queue: {file_path.name} -> {txt_file_output.name}"
            )
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
            logger.error(f"Error setting up processing for {file_path}: {e}")
            print(f"Error setting up processing for {file_path}: {e}")
            continue

    logger.info(f"Completed scan: found {len(files_to_process)} files to process")
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
    logger.info(
        f"🚀 Starting scan_and_convert: input={input_dir}, output={output_dir}, depth={depth}"
    )
    logger.debug(f"📊 Input filesystem: {type(input_dir.fs).__name__}")
    logger.debug(f"📊 Output filesystem: {type(output_dir.fs).__name__}")

    # Scan for files to process
    logger.info("🔍 Scanning for files to process...")
    files_to_process = _scan_for_untreated_files(
        input_dir=input_dir, output_dir=output_dir, depth=depth
    )

    logger.info(f"📊 Found {len(files_to_process)} files to process")
    print(f"Found {len(files_to_process)} files to process")

    input_files: list[UniversalPath] = []
    output_files: list[UniversalPath] = []
    errors: list[Exception] = []
    remaining_files: list[TranslationItem] = []

    # Process each file
    logger.info(f"⚙️  Starting file processing loop for {len(files_to_process)} files")
    for i, item in enumerate(files_to_process, 1):
        logger.debug(
            f"🔄 Processing file {i}/{len(files_to_process)}: {item.input_file.name}"
        )
        input_files.append(item.input_file)

        try:
            # Get processing function for file type
            suffix = item.input_file.suffix.lower()
            logger.debug(f"📄 File type: {suffix}")
            process_function = TRANSLATION_FUNCTIONS.get(suffix)

            if process_function is None:
                logger.error(f"❌ Unsupported file type: {suffix}")
                err = Exception(f"Unsupported file type: {suffix}")
                errors.append(err)
                remaining_files.append(item)
                continue

            # Process the file
            logger.info(
                f"⚙️  Processing {item.input_file.name} with {process_function.__name__}"
            )
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

    result = Result(
        input_files=input_files,
        output_files=output_files,
        untranstlatable=untranslatable,
        errors=errors,
        missing_json_files=missing_json_files,
    )

    logger.info(
        f"scan_and_convert completed successfully with {len(result.output_files)}/{len(result.input_files)} successful conversions"
    )
    return result
