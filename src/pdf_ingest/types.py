from dataclasses import dataclass
from pathlib import Path


@dataclass
class TranslationItem:
    """
    Class to hold the translation item.
    """

    input_file: Path
    output_file: Path
    json_file: Path
    json_exists: bool
    language: str = ""
    should_translate: bool = False

    def __post_init__(self):
        if not isinstance(self.input_file, Path):
            raise TypeError("input_file must be a Path object")
        if not isinstance(self.output_file, Path):
            raise TypeError("output_file must be a Path object")
        if not isinstance(self.json_file, Path):
            raise TypeError("json_file must be a Path object")
        if not self.input_file.exists():
            raise FileNotFoundError(f"{self.input_file} does not exist")


@dataclass
class Result:
    """
    Class to hold the result of the conversion.
    """

    input_files: list[Path]
    output_files: list[Path]
    untranstlatable: list[Path]
    errors: list[Exception]
    missing_json_files: list[Path]

    def __post_init__(self):
        if not isinstance(self.input_files, list):
            raise TypeError("input_files must be a list of Path objects")
        if not isinstance(self.output_files, list):
            raise TypeError("output_files must be a list of Path objects")
        if not isinstance(self.errors, list):
            raise TypeError("errors must be a list of Exception objects")
        if not isinstance(self.missing_json_files, list):
            raise TypeError("missing_json_files must be a list of Path objects")

        for file in self.input_files:
            if not isinstance(file, Path):
                raise TypeError("input_files must be a list of Path objects")
        for file in self.output_files:
            if not isinstance(file, Path):
                raise TypeError("output_files must be a list of Path objects")
        for file in self.missing_json_files:
            if not isinstance(file, Path):
                raise TypeError("missing_json_files must be a list of Path objects")
