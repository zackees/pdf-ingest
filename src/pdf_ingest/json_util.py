import json

from pdf_ingest.fs_path import UniversalPath


def update_json_with_language(
    json_file: UniversalPath, lang_code: str, is_reliable: bool
) -> None:
    """
    Update the JSON file with the language information.
    Now supports both local and remote files.

    Args:
        json_file: Path to the JSON file to update (local or remote)
        lang_code: Language code
        is_reliable: Whether the language detection is reliable
    """
    try:
        # Read existing JSON data
        json_data = {}
        if json_file.exists():
            try:
                json_content = json_file.read_text(encoding="utf-8")
                json_data = json.loads(json_content)
            except (json.JSONDecodeError, Exception) as e:
                print(f"Warning: Could not parse existing JSON in {json_file}: {e}")
                json_data = {}

        # Update language information
        json_data["language"] = lang_code
        json_data["language_detection_reliable"] = is_reliable
        json_data["should_translate"] = lang_code == "EN"

        # Write updated JSON data
        json_content = json.dumps(json_data, indent=2)
        json_file.write_text(json_content, encoding="utf-8")

        print(
            f"Updated language information in {json_file.name}: {lang_code} (reliable: {is_reliable})"
        )

    except Exception as e:
        print(f"Error updating language information in {json_file}: {e}")
        # Don't raise - this is not critical for the conversion process
