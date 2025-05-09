from pathlib import Path

from langdetect import detect


def language_detect(text: str) -> tuple[str, bool]:
    """
    Detect the language of the given text using fasttext-langdetect.
    """
    try:
        # fasttext returns ISO 639-1 language codes
        language = detect(text)
        # fasttext doesn't provide reliability info, so we'll consider it reliable
        # if we get a non-empty result
        is_reliable = bool(language)
        return language, is_reliable
    except Exception:
        return "unknown", False


def detect_language_from_file(txt_file: Path) -> tuple[str, bool]:
    """
    Detect the language of the text file.

    Args:
        txt_file: Path to the text file

    Returns:
        tuple: (language_code, is_reliable)
    """
    try:
        # Read the text file
        with open(txt_file, "r", encoding="utf-8") as f:
            text = f.read()

        # Detect language
        lang_code, is_reliable = language_detect(text)
        return lang_code, is_reliable

    except Exception as e:
        print(f"Error detecting language: {e}")
        return "", False
