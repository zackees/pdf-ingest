# Import necessary modules
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup
from fb2reader import fb2book

from pdf_ingest.json_util import update_json_with_language
from pdf_ingest.language_detection import language_detect
from pdf_ingest.types import TranslationItem


@dataclass
class Fb2Entry:
    file_path: str
    content: str

    def to_plain_text(self) -> str:
        out: str = ""
        out += f"------- File Path: {self.file_path} -------\n"
        out += f"{self.content}\n"
        return out


@dataclass
class Fb2Doc:
    contents: list[Fb2Entry]

    @staticmethod
    def parse(path: Path) -> "Fb2Doc":
        return _parse_fb2(path)

    def to_plain_text(self) -> str:
        parts: list[str] = []
        for entry in self.contents:
            parts.append(entry.to_plain_text())
        out: str = "\n".join(parts)
        return out


def _parse_fb2(fb2_path: Path) -> Fb2Doc:
    book: fb2book = fb2book(str(fb2_path))  # Example: replace with actual method
    content: list[Fb2Entry] = []
    # Assuming fb2reader provides a way to get content similar to epub_utils
    body = book.get_body()

    if body is None:
        raise ValueError(f"FB2 file {fb2_path} has no body content.")

    if isinstance(body, bytes):
        body = body.decode("utf-8")

    if not isinstance(body, str):
        raise TypeError(f"Expected body content to be a string, got {type(body)}")

    html_text = str(body).strip()
    soup = BeautifulSoup(html_text, "html.parser")
    plain_text = soup.get_text(separator="\n", strip=True)

    assert isinstance(plain_text, str), "Expected plain_text to be a string"
    entry = Fb2Entry(file_path=str(fb2_path), content=plain_text)
    content.append(entry)
    return Fb2Doc(contents=content)


def process_fb2_file(item: TranslationItem) -> tuple[Exception | None, bool]:
    try:
        # Parse the FB2 file
        fb2_doc = Fb2Doc.parse(item.input_file)

        # Convert the FB2 document to plain text
        plain_text = fb2_doc.to_plain_text()

        # Detect language from the plain text
        lang_code, is_reliable = language_detect(plain_text)
        item.language = lang_code
        item.should_translate = lang_code.lower() == "en"

        # Update the output filename to include language code
        stem = item.output_file.stem
        suffix = item.output_file.suffix
        new_filename = f"{stem}-{lang_code.upper()}{suffix}"
        item.output_file = item.output_file.with_name(new_filename)

        # Update JSON with language information
        update_json_with_language(item.json_file, lang_code, is_reliable)

        # Write the plain text to the output file
        with open(item.output_file, "w", encoding="utf-8") as f:
            f.write(plain_text)

        print(f"Successfully processed {item.input_file.name} (language: {lang_code})")
        return None, True
    except Exception as e:
        print(f"Error processing {item.input_file.name}: {e}")
        return e, False
