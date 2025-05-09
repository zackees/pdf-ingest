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
