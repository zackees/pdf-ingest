import subprocess
import tempfile
from pathlib import Path
from tempfile import TemporaryDirectory

from pdf_ingest.data_types import TranslationItem
from pdf_ingest.fs_path import is_remote_path
from pdf_ingest.json_util import update_json_with_language
from pdf_ingest.language_detection import detect_language_from_file
from pdf_ingest.temp_manager import TempFileManager


def convert_djvu_to_text(djvu_file: Path, txt_file_out: Path) -> Exception | None:
    """
    Convert a DJVU file to text using djvutxt
    """
    try:
        subprocess.run(
            ["djvutxt", str(djvu_file), str(txt_file_out)],
            check=True,
        )
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error converting {djvu_file.name} to text: {e}")
        return e
    except Exception as e:
        print(f"Unexpected error processing {djvu_file.name}: {e}")
        return e


def convert_djvu_to_text_via_ocr(
    djvu_file: Path, txt_file_out: Path
) -> Exception | None:
    """
    Convert a DJVU file to text using OCR with djvulibre-bin
    """
    try:
        # Create a temporary directory for intermediate files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)

            # Extract all pages as images using ddjvu
            temp_image_pattern = temp_dir_path / f"{djvu_file.stem}-%04d.tif"
            subprocess.run(
                [
                    "ddjvu",
                    "-format=tiff",
                    "-mode=black",
                    "-quality=150",
                    str(djvu_file),
                    str(temp_image_pattern),
                ],
                check=True,
            )

            # Process each image with tesseract OCR and append to output file
            with open(txt_file_out, "w", encoding="utf-8") as output_file:
                for image_file in sorted(temp_dir_path.glob(f"{djvu_file.stem}-*.tif")):
                    # Create temporary text file for this page
                    temp_txt = temp_dir_path / f"{image_file.stem}.txt"

                    # Run OCR on the image
                    subprocess.run(
                        ["tesseract", str(image_file), str(temp_txt.with_suffix(""))],
                        check=True,
                    )

                    # Append the page text to the output file
                    if temp_txt.exists():
                        with open(temp_txt, "r", encoding="utf-8") as page_file:
                            output_file.write(
                                f"\n--- Page {image_file.stem.split('-')[-1]} ---\n\n"
                            )
                            output_file.write(page_file.read())
                            output_file.write("\n\n")

        return None
    except subprocess.CalledProcessError as e:
        print(f"Error OCR'ing and converting {djvu_file.name} to text: {e}")
        return e
    except Exception as e:
        print(f"Unexpected error processing {djvu_file.name}: {e}")
        return e


def process_djvu_file(item: TranslationItem) -> tuple[Exception | None, bool]:
    """
    Process a DJVU file and convert it to text.
    Now supports both local and remote files using temporary file management.

    Args:
        item: TranslationItem containing input and output file paths

    Returns:
        tuple: (error, success) where error is None if successful and success is True if file was processed
    """
    input_is_remote = is_remote_path(item.input_file)
    output_is_remote = is_remote_path(item.output_file)

    print(
        f"Processing DJVU: {item.input_file.name} (input: {'remote' if input_is_remote else 'local'}, "
        f"output: {'remote' if output_is_remote else 'local'})"
    )

    try:
        # Use temporary file managers for remote files
        with TempFileManager(item.input_file) as local_input:
            with TemporaryDirectory() as temp_processing_dir:
                temp_output = (
                    Path(temp_processing_dir) / f"temp_{item.input_file.name}.txt"
                )

                # Try regular DJVU to text conversion
                err = convert_djvu_to_text(local_input, temp_output)

                if err is not None:
                    print(
                        f"Regular conversion failed for {item.input_file.name}, trying OCR..."
                    )
                    err = convert_djvu_to_text_via_ocr(local_input, temp_output)

                    if err is not None:
                        print(f"OCR conversion also failed for {item.input_file.name}")
                        return err, False

                # Both conversions succeeded, now handle language detection and output
                if not temp_output.exists():
                    return (
                        Exception(
                            "Processing completed but no output file was created"
                        ),
                        False,
                    )

                # Detect language from the temporary file
                lang_code, is_reliable = detect_language_from_file(temp_output)
                item.language = lang_code
                item.should_translate = lang_code.lower() == "en"

                # Update the output filename to include language code
                stem = item.output_file.stem
                suffix = item.output_file.suffix
                new_filename = f"{stem}-{lang_code.upper()}{suffix}"
                item.output_file = item.output_file.with_name(new_filename)

                # Write to final output location (handling remote if necessary)
                try:
                    # Ensure output directory exists
                    item.output_file.parent.mkdir(parents=True, exist_ok=True)

                    # Copy content to final destination
                    content = temp_output.read_text(encoding="utf-8")
                    item.output_file.write_text(content, encoding="utf-8")

                    # Update JSON with language information
                    update_json_with_language(item.json_file, lang_code, is_reliable)

                    conversion_method = "OCR" if err is not None else "embedded text"
                    print(
                        f"✓ Successfully converted {item.input_file.name} using {conversion_method} (language: {lang_code})"
                    )
                    return None, True

                except Exception as copy_err:
                    print(
                        f"Error writing to final destination {item.output_file}: {copy_err}"
                    )
                    return copy_err, False

    except Exception as e:
        print(f"Error in DJVU processing pipeline for {item.input_file.name}: {e}")
        return e, False
