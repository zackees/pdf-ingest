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
