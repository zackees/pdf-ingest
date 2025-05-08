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


def unit_test() -> None:
    # Example usage
    # text = "これは日本語のテキストです"
    text = "This is a test sentence in English."
    language, is_reliable = language_detect(text)

    assert language == "en", f"Expected 'en', got '{language}'"
    assert is_reliable is True, f"Expected reliable detection, got {is_reliable}"

    text = "これは日本語のテキストです"
    language, is_reliable = language_detect(text)
    # print(f"Detected language: {language}, Reliable: {is_reliable}")
    assert language == "ja", f"Expected 'ja', got '{language}'"
    assert is_reliable is True, f"Expected reliable detection, got {is_reliable}"


if __name__ == "__main__":
    unit_test()
