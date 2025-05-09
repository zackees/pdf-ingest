import shutil
import subprocess
import tempfile
from pathlib import Path
from tempfile import TemporaryDirectory

from pdf_ingest.json_util import update_json_with_language
from pdf_ingest.language_detection import detect_language_from_file
from pdf_ingest.types import TranslationItem

_DISABLE_TEXT_EMBEDDING_EXTRACTION = False


def try_pdf_convert_to_text(pdf_file: Path, txt_file_out: Path) -> Exception | None:
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


def convert_pdf_to_text_via_ocr(pdf_file: Path, txt_file_out: Path) -> Exception | None:
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


def process_pdf_file(item: TranslationItem) -> tuple[Exception | None, bool]:
    """
    Process a PDF file and convert it to text.
    Uses a temporary directory for the conversion process and then copies the result to the final destination.

    Args:
        item: TranslationItem containing input and output file paths

    Returns:
        tuple: (error, success) where error is None if successful and success is True if file was processed
    """
    with TemporaryDirectory() as temp_dir:
        # Create a temporary output file path
        temp_output = Path(temp_dir) / f"temp_{item.input_file.name}.txt"

        # First try regular PDF to text conversion
        err = try_pdf_convert_to_text(
            pdf_file=item.input_file, txt_file_out=temp_output
        )
        if err is not None:
            print(
                f"Regular conversion failed for {item.input_file.name}, trying OCR..."
            )
            # If regular conversion fails, try OCR
            err = convert_pdf_to_text_via_ocr(
                pdf_file=item.input_file, txt_file_out=temp_output
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
