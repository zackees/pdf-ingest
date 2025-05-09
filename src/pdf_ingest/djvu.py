import shutil
import subprocess
import tempfile
from pathlib import Path
from tempfile import TemporaryDirectory

from pdf_ingest.json_util import update_json_with_language
from pdf_ingest.language_detection import detect_language_from_file
from pdf_ingest.types import TranslationItem


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
