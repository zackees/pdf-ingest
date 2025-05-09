import json
from pathlib import Path


def update_json_with_language(
    json_file: Path, lang_code: str, is_reliable: bool
) -> None:
    """
    Update the JSON file with the language information.

    Args:
        json_file: Path to the JSON file to update
        lang_code: Language code
        is_reliable: Whether the language detection is reliable
    """
    try:
        # Read existing JSON data
        json_data = {}
        if json_file.exists():
            with open(json_file, "r", encoding="utf-8") as f:
                try:
                    json_data = json.load(f)
                except json.JSONDecodeError:
                    json_data = {}

        # Update language information
        json_data["language"] = lang_code
        json_data["language_detection_reliable"] = is_reliable
        json_data["should_translate"] = lang_code == "EN"

        # Write updated JSON data
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)

        print(
            f"Updated language information in {json_file}: {lang_code} (reliable: {is_reliable})"
        )

    except Exception as e:
        print(f"Error updating language information: {e}")
