from dataclasses import dataclass

from pdf_ingest.fs_path import UniversalPath


@dataclass
class TranslationItem:
    """
    Class to hold the translation item.
    """

    input_file: UniversalPath
    output_file: UniversalPath
    json_file: UniversalPath
    json_exists: bool
    language: str = ""
    should_translate: bool = False

    def __post_init__(self):
        # Check that objects have the required PathLike interface
        for field_name, field_value in [
            ("input_file", self.input_file),
            ("output_file", self.output_file),
            ("json_file", self.json_file),
        ]:
            if not hasattr(field_value, "exists"):
                raise TypeError(f"{field_name} must be a PathLike object")

        # Only check existence for input files (output files may not exist yet)
        if not self.input_file.exists():
            raise FileNotFoundError(f"{self.input_file} does not exist")


@dataclass
class Result:
    """
    Class to hold the result of the conversion.
    """

    input_files: list[UniversalPath]
    output_files: list[UniversalPath]
    untranstlatable: list[UniversalPath]
    errors: list[Exception]
    missing_json_files: list[UniversalPath]

    def __post_init__(self):
        # Type validation for lists
        for field_name, field_value in [
            ("input_files", self.input_files),
            ("output_files", self.output_files),
            ("untranstlatable", self.untranstlatable),
            ("missing_json_files", self.missing_json_files),
        ]:
            if not isinstance(field_value, list):
                raise TypeError(f"{field_name} must be a list")

        if not isinstance(self.errors, list):
            raise TypeError("errors must be a list of Exception objects")

        # Validate that all path objects have the required interface
        for file_list_name, file_list in [
            ("input_files", self.input_files),
            ("output_files", self.output_files),
            ("untranstlatable", self.untranstlatable),
            ("missing_json_files", self.missing_json_files),
        ]:
            for i, file_obj in enumerate(file_list):
                if not hasattr(file_obj, "exists"):
                    raise TypeError(f"{file_list_name}[{i}] must be a PathLike object")
