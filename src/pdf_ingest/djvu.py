import subprocess
import tempfile
from pathlib import Path


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
