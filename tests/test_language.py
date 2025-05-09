"""
Unit test file.
"""

import os
import unittest

from pdf_ingest.language_detection import language_detect


class LanguageDetectTester(unittest.TestCase):
    """Main tester class."""

    def test_main(self) -> None:
        """Test command line interface (CLI)."""
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
    unittest.main()
