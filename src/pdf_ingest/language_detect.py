import cld3  # type: ignore

# text = "これは日本語のテキストです"
# result = cld3.get_language(text)
# print(result.language, result.is_reliable)


def language_detect(text: str) -> tuple[str, bool]:
    """
    Detect the language of the given text using cld3.
    """
    result = cld3.get_language(text)
    if result.is_reliable:
        return result.language, result.is_reliable
    else:
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
