# FSPath Transition Design: Remote File System Support

## Overview

This document outlines the plan to transition the PDF Ingest tool from `pathlib.Path` to `FSPath` objects using the [`virtual-fs`](https://github.com/zackees/virtual-fs) package. This transition will enable the tool to work with remote file systems (cloud storage, network drives, any rclone-supported backend) while maintaining full compatibility with local file operations.

## Current State Analysis

### Current pathlib.Path Usage

The codebase currently uses `pathlib.Path` in several key areas:

1. **Data Structures** (`src/pdf_ingest/types.py`):
   - `TranslationItem` - Contains input_file, output_file, json_file as Path objects
   - `Result` - Contains lists of Path objects for various file categories

2. **Core Processing** (`src/pdf_ingest/scan_and_convert.py`):
   - Directory scanning and file discovery with `.glob()` operations
   - Path manipulation and relative path calculations with `.relative_to()`
   - File existence checks with `.exists()` and directory creation with `.mkdir()`

3. **Parsers** (`src/pdf_ingest/parsers/*.py`):
   - Temporary file creation and management with `TemporaryDirectory`
   - External tool subprocess calls requiring string paths
   - File copying operations with `shutil.copy2()`

4. **CLI/Docker** (`src/pdf_ingest/cli.py`, `src/pdf_ingest/cli_docker.py`):
   - Input/output directory validation and existence checks
   - NFS mount detection and handling for Windows
   - Docker volume mapping with path string conversion

### Key Challenges

- External tools (pdftotext, tesseract, etc.) require local file paths
- Temporary file management for remote file processing
- Maintaining type safety and existing error handling patterns
- Docker containerization with remote file access
- NFS mount handling and optimization

## Design Strategy

### Phase 1: Create FSPath Abstraction Layer

Create a wrapper that can handle both local `Path` and remote `FSPath` objects seamlessly.

**File: `src/pdf_ingest/fs_path.py`**

```python
from pathlib import Path
from typing import Union, Protocol, runtime_checkable, Iterator, Any
from virtual_fs import FSPath

@runtime_checkable
class PathLike(Protocol):
    """Protocol defining the interface that both Path and FSPath must implement."""
    
    def exists(self) -> bool: ...
    def is_dir(self) -> bool: ...
    def mkdir(self, parents: bool = True, exist_ok: bool = True) -> None: ...
    def read_text(self, encoding: str = "utf-8") -> str: ...
    def write_text(self, data: str, encoding: str = "utf-8") -> None: ...
    def read_bytes(self) -> bytes: ...
    def write_bytes(self, data: bytes) -> None: ...
    
    @property
    def name(self) -> str: ...
    @property
    def stem(self) -> str: ...
    @property
    def suffix(self) -> str: ...
    @property
    def parent(self) -> "PathLike": ...
    
    def __truediv__(self, other: str) -> "PathLike": ...
    def __str__(self) -> str: ...
    def with_suffix(self, suffix: str) -> "PathLike": ...
    def with_name(self, name: str) -> "PathLike": ...
    def relative_to(self, other: "PathLike") -> "PathLike": ...
    def resolve(self) -> "PathLike": ...

# Type alias for paths that can be either local or remote
UniversalPath = Union[Path, FSPath]

def is_remote_path(path: UniversalPath) -> bool:
    """Check if a path is a remote FSPath."""
    return hasattr(path, 'is_real_fs') and not path.is_real_fs()

def ensure_local_path(path: UniversalPath) -> Path:
    """Convert a UniversalPath to a local Path, downloading if necessary."""
    if isinstance(path, Path):
        return path
    else:
        # This would be handled by TempFileManager for actual files
        raise NotImplementedError("Use TempFileManager for remote file access")
```

### Phase 2: Create File System Factory

Create a factory for initializing the appropriate file system based on path strings.

**File: `src/pdf_ingest/fs_factory.py`**

```python
from pathlib import Path
from typing import Union, Optional
from virtual_fs import Vfs, FSPath
from .fs_path import UniversalPath

class FileSystemFactory:
    """Factory for creating appropriate path objects based on path string format."""
    
    @staticmethod
    def create_path(path_str: str, rclone_config: Optional[Path] = None) -> UniversalPath:
        """
        Create appropriate path object based on path string format.
        
        Args:
            path_str: Path string (local path or remote:path format)
            rclone_config: Optional rclone configuration file path
            
        Returns:
            UniversalPath: Either a Path (local) or FSPath (remote) object
        """
        # Check if it's a remote path (contains : but not Windows drive letter)
        if ":" in path_str and not (len(path_str) > 1 and path_str[1] == ":"):
            # Remote path format like "remote:bucket/path"
            try:
                vfs = Vfs.begin(path_str, config=rclone_config)
                return vfs  # Returns FSPath
            except Exception as e:
                raise ValueError(f"Failed to initialize remote filesystem for '{path_str}': {e}")
        else:
            # Local path
            return Path(path_str)
    
    @staticmethod
    def create_output_path(base_path: UniversalPath, relative_path: str) -> UniversalPath:
        """
        Create output path maintaining the same filesystem type as base.
        
        Args:
            base_path: Base directory path
            relative_path: Relative path to append
            
        Returns:
            UniversalPath: Output path of the same type as base_path
        """
        return base_path / relative_path
    
    @staticmethod
    def get_fs_type(path: UniversalPath) -> str:
        """Get filesystem type string for logging/debugging."""
        if isinstance(path, FSPath):
            return "remote"
        else:
            return "local"
```

### Phase 3: Create Temporary File Manager

Handle the complexity of downloading remote files for local processing by external tools.

**File: `src/pdf_ingest/temp_manager.py`**

```python
import tempfile
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional
from .fs_path import UniversalPath, is_remote_path

class TempFileManager:
    """
    Context manager for handling remote files that need local processing.
    Downloads remote files to temporary local storage for external tool processing.
    """
    
    def __init__(self, remote_file: UniversalPath):
        self.remote_file = remote_file
        self.temp_dir: Optional[TemporaryDirectory] = None
        self.local_file: Optional[Path] = None
        self._is_remote = is_remote_path(remote_file)
    
    def __enter__(self) -> Path:
        """
        Download remote file to temporary local file for processing.
        
        Returns:
            Path: Local file path (either original local file or downloaded copy)
        """
        if self._is_remote:
            # Remote file - download to temp
            self.temp_dir = TemporaryDirectory(prefix="pdf_ingest_remote_")
            temp_path = Path(self.temp_dir.name)
            self.local_file = temp_path / self.remote_file.name
            
            print(f"Downloading remote file {self.remote_file} to {self.local_file}")
            try:
                data = self.remote_file.read_bytes()
                self.local_file.write_bytes(data)
                print(f"Successfully downloaded {len(data)} bytes")
            except Exception as e:
                self.temp_dir.cleanup()
                raise Exception(f"Failed to download remote file {self.remote_file}: {e}")
        else:
            # Local file - just return the path
            self.local_file = Path(str(self.remote_file))
            
        return self.local_file
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up temporary files."""
        if self.temp_dir:
            try:
                self.temp_dir.cleanup()
            except Exception as e:
                print(f"Warning: Failed to cleanup temporary directory: {e}")

class TempOutputManager:
    """
    Context manager for handling output files that may be remote.
    Creates temporary local files for writing, then uploads to remote destination.
    """
    
    def __init__(self, output_file: UniversalPath):
        self.output_file = output_file
        self.temp_dir: Optional[TemporaryDirectory] = None
        self.local_file: Optional[Path] = None
        self._is_remote = is_remote_path(output_file)
    
    def __enter__(self) -> Path:
        """
        Create temporary local file for output.
        
        Returns:
            Path: Local file path for writing
        """
        if self._is_remote:
            # Remote output - create temp file
            self.temp_dir = TemporaryDirectory(prefix="pdf_ingest_output_")
            temp_path = Path(self.temp_dir.name)
            self.local_file = temp_path / self.output_file.name
        else:
            # Local output - use directly
            self.local_file = Path(str(self.output_file))
            # Ensure parent directory exists
            self.local_file.parent.mkdir(parents=True, exist_ok=True)
            
        return self.local_file
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Upload to remote destination if needed and cleanup."""
        if exc_type is None and self._is_remote and self.local_file and self.local_file.exists():
            # Upload to remote destination
            try:
                print(f"Uploading {self.local_file} to remote {self.output_file}")
                data = self.local_file.read_bytes()
                
                # Ensure parent directory exists on remote
                self.output_file.parent.mkdir(parents=True, exist_ok=True)
                
                self.output_file.write_bytes(data)
                print(f"Successfully uploaded {len(data)} bytes")
            except Exception as e:
                print(f"Error uploading to remote destination {self.output_file}: {e}")
                raise
        
        # Clean up temporary files
        if self.temp_dir:
            try:
                self.temp_dir.cleanup()
            except Exception as e:
                print(f"Warning: Failed to cleanup temporary directory: {e}")
```

### Phase 4: Update Data Structures

Modify the core data structures to use the new abstraction.

**File: `src/pdf_ingest/types.py` (Updated)**

```python
from dataclasses import dataclass
from .fs_path import UniversalPath

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
            ("json_file", self.json_file)
        ]:
            if not hasattr(field_value, 'exists'):
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
            ("missing_json_files", self.missing_json_files)
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
            ("missing_json_files", self.missing_json_files)
        ]:
            for i, file_obj in enumerate(file_list):
                if not hasattr(file_obj, 'exists'):
                    raise TypeError(f"{file_list_name}[{i}] must be a PathLike object")
```

### Phase 5: Update Core Processing Logic

Modify the main scanning and conversion logic to work with both filesystem types.

**File: `src/pdf_ingest/scan_and_convert.py` (Updated)**

```python
# BTW, the logic I would like on this is that your code looks for .pdf or .djvu
# that have no matching .txt filename in the output folder, and then processes
# the files to generate the .txt of the same name.
# And it should handle subfolders under the src folder as well,
# So when it's done processing, every pdf has a txt, in the output folder.
# Additionally, check for corresponding .json files - missing .json files indicate
# that translation is not done.

import json
from typing import Callable
from .fs_path import UniversalPath, is_remote_path
from .fs_factory import FileSystemFactory
from .parsers.djvu import process_djvu_file
from .parsers.epub import process_epub_file
from .parsers.fb2 import process_fb2_file
from .parsers.pdf import process_pdf_file
from .types import Result, TranslationItem

TRANSLATION_FUNCTIONS: dict[
    str, Callable[[TranslationItem], tuple[Exception | None, bool]]
] = {
    ".pdf": process_pdf_file,
    ".djvu": process_djvu_file,
    ".epub": process_epub_file,
    ".fb2": process_fb2_file,
}

TRANSLATABLE_EXTENSIONS = TRANSLATION_FUNCTIONS.keys()

def prompt_for_input_dir() -> str:
    """
    Prompt the user for an input directory path string.
    
    Returns:
        str: The input directory path string (local or remote format)
    """
    while True:
        input_dir_str = input("Enter the input directory path (local path or remote:path): ")
        
        try:
            # Try to create the path to validate it
            input_dir = FileSystemFactory.create_path(input_dir_str)
            if input_dir.exists() and input_dir.is_dir():
                return input_dir_str
            else:
                print(f"Directory {input_dir_str} does not exist or is not a directory. Please try again.")
        except Exception as e:
            print(f"Invalid path format '{input_dir_str}': {e}. Please try again.")

def _scan_for_untreated_files(
    input_dir: UniversalPath, output_dir: UniversalPath, depth: int
) -> list[TranslationItem]:
    """
    Scan for PDF and DJVU files in the input directory that don't have corresponding
    text files in the output directory. Also checks for corresponding JSON files.
    Now supports both local and remote filesystems.

    Args:
        input_dir: Directory containing PDF and DJVU files (local or remote)
        output_dir: Directory where text files will be saved (local or remote)
        depth: Maximum depth for subdirectory scanning

    Returns:
        list[TranslationItem]: List of files to process with their metadata
    """
    files_to_process: list[TranslationItem] = []

    # Validate directories exist
    assert input_dir.exists(), f"Input directory {input_dir} does not exist"
    assert output_dir.exists(), f"Output directory {output_dir} does not exist"

    fs_type_input = "remote" if is_remote_path(input_dir) else "local"
    fs_type_output = "remote" if is_remote_path(output_dir) else "local"
    
    print(f"Scanning for files in {input_dir} ({fs_type_input}) -> {output_dir} ({fs_type_output})")
    print(f"Scan depth: {depth}")

    try:
        # Get list of files - this works for both FSPath and Path
        file_list = list(input_dir.glob("*"))
        print(f"Found {len(file_list)} items in {input_dir}")
        
        for item in file_list:
            print(f"  - {item.name}")

    except Exception as e:
        raise Exception(f"Failed to list files in {input_dir}: {e}")

    # Filter for translatable files
    search_list: list[UniversalPath] = []
    for file_path in file_list:
        try:
            if file_path.is_dir():
                continue
                
            # Check depth limitation
            if depth > 0:
                # Calculate relative path for depth checking
                rel_path_str = str(file_path).replace(str(input_dir), "").lstrip("/\\")
                if len(rel_path_str.split("/")) > depth:
                    continue
            
            if file_path.suffix.lower() in TRANSLATABLE_EXTENSIONS:
                search_list.append(file_path)
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue

    print(f"Found {len(search_list)} translatable files")

    # Process each translatable file
    for file_path in search_list:
        try:
            print(f"Processing: {file_path.name}")

            # Calculate relative path from input_dir
            # For remote paths, we need to handle this differently
            if is_remote_path(input_dir):
                # For remote paths, construct relative path manually
                input_str = str(input_dir).rstrip('/')
                file_str = str(file_path)
                if file_str.startswith(input_str):
                    rel_path_str = file_str[len(input_str):].lstrip('/')
                else:
                    rel_path_str = file_path.name
            else:
                rel_path_str = str(file_path.relative_to(input_dir))

            # Create output file path with same relative structure
            txt_file_output = output_dir / rel_path_str.replace(file_path.suffix, ".txt")
            
            # Ensure parent directories exist
            try:
                txt_file_output.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"Warning: Could not create parent directory for {txt_file_output}: {e}")

            # Check if output file already exists
            if txt_file_output.exists():
                print(f"Text file {txt_file_output.name} already exists. Skipping conversion.")
                continue

            # Check for corresponding JSON file
            json_file = output_dir / rel_path_str.replace(file_path.suffix, ".json")
            json_exists = json_file.exists()

            # Check if JSON indicates processing is complete
            if json_exists:
                try:
                    json_content = json_file.read_text()
                    json_data = json.loads(json_content)
                    
                    if json_data.get("language_detection_reliable"):
                        print(f"JSON file {json_file.name} indicates processing complete. Skipping.")
                        continue
                except Exception as e:
                    print(f"Warning: Could not read JSON file {json_file}: {e}")

            # Create empty JSON file if it doesn't exist
            if not json_exists:
                print(f"Creating JSON metadata file: {json_file.name}")
                try:
                    json_file.parent.mkdir(parents=True, exist_ok=True)
                    json_file.write_text('{"language": ""}')
                except Exception as e:
                    print(f"Warning: Could not create JSON file {json_file}: {e}")

            print(f"Input: {file_path.name} -> Output: {txt_file_output.name}")

            files_to_process.append(
                TranslationItem(
                    input_file=file_path,
                    output_file=txt_file_output,
                    json_file=json_file,
                    json_exists=json_exists,
                )
            )

        except Exception as e:
            print(f"Error setting up processing for {file_path}: {e}")
            continue

    return files_to_process

def scan_and_convert(input_dir: UniversalPath, output_dir: UniversalPath, depth: int) -> Result:
    """
    Scan for PDF and DJVU files in the input directory and convert them to text files in the output directory.
    Now supports both local and remote filesystems.

    Args:
        input_dir: Directory containing PDF and DJVU files (local or remote)
        output_dir: Directory where text files will be saved (local or remote)
        depth: Maximum depth for subdirectory scanning

    Returns:
        Result: Object containing lists of input files, output files, errors, and missing json files
    """

    # Scan for files to process
    files_to_process = _scan_for_untreated_files(
        input_dir=input_dir, output_dir=output_dir, depth=depth
    )

    print(f"Found {len(files_to_process)} files to process")

    input_files: list[UniversalPath] = []
    output_files: list[UniversalPath] = []
    errors: list[Exception] = []
    remaining_files: list[TranslationItem] = []

    # Process each file
    for item in files_to_process:
        input_files.append(item.input_file)

        try:
            # Get processing function for file type
            suffix = item.input_file.suffix.lower()
            process_function = TRANSLATION_FUNCTIONS.get(suffix)
            
            if process_function is None:
                err = Exception(f"Unsupported file type: {suffix}")
                errors.append(err)
                remaining_files.append(item)
                continue

            # Process the file
            print(f"Processing {item.input_file.name} with {process_function.__name__}")
            err, success = process_function(item)

            if success:
                output_files.append(item.output_file)
                print(f"✓ Successfully processed {item.input_file.name}")
            else:
                remaining_files.append(item)
                if err is not None:
                    errors.append(err)
                    print(f"✗ Failed to process {item.input_file.name}: {err}")
                else:
                    print(f"✗ Failed to process {item.input_file.name} (unknown error)")

        except Exception as e:
            errors.append(e)
            remaining_files.append(item)
            print(f"✗ Exception processing {item.input_file.name}: {e}")

    # Create result summary
    untranslatable = [item.input_file for item in remaining_files]
    missing_json_files = [
        item.input_file for item in files_to_process if not item.json_exists
    ]

    print(f"\nProcessing complete:")
    print(f"  Successful: {len(output_files)}")
    print(f"  Failed: {len(untranslatable)}")
    print(f"  Errors: {len(errors)}")

    return Result(
        input_files=input_files,
        output_files=output_files,
        untranstlatable=untranslatable,
        errors=errors,
        missing_json_files=missing_json_files,
    )
```

### Phase 6: Update JSON Utilities

Update JSON handling to work with remote files.

**File: `src/pdf_ingest/json_util.py` (Updated)**

```python
import json
from .fs_path import UniversalPath

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

        print(f"Updated language information in {json_file.name}: {lang_code} (reliable: {is_reliable})")

    except Exception as e:
        print(f"Error updating language information in {json_file}: {e}")
        # Don't raise - this is not critical for the conversion process
```

### Phase 7: Update Parsers

Update all parsers to handle remote files through the temporary file manager.

**File: `src/pdf_ingest/parsers/pdf.py` (Updated)**

```python
import shutil
import subprocess
from tempfile import TemporaryDirectory
from pathlib import Path
from ..json_util import update_json_with_language
from ..language_detection import detect_language_from_file
from ..types import TranslationItem
from ..temp_manager import TempFileManager, TempOutputManager
from ..fs_path import is_remote_path

_DISABLE_TEXT_EMBEDDING_EXTRACTION = False

def try_pdf_convert_to_text(pdf_file: Path, txt_file_out: Path) -> Exception | None:
    """Convert PDF to text using pdftotext (local files only)."""
    if _DISABLE_TEXT_EMBEDDING_EXTRACTION:
        print(f"Skipping text extraction for {pdf_file.name} due to disabled setting.")
        return NotImplementedError("Text extraction is disabled.")
    try:
        subprocess.run(
            ["pdftotext", str(pdf_file), str(txt_file_out)],
            check=True,
        )
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error converting {pdf_file.name} to text: {e}")
        return e

def convert_pdf_to_text_via_ocr(pdf_file: Path, txt_file_out: Path) -> Exception | None:
    """Convert PDF to text using OCR with ocrmypdf (local files only)."""
    try:
        with TemporaryDirectory() as temp_dir:
            temp_pdf = Path(temp_dir) / f"{pdf_file.stem}_ocr.pdf"

            # Run OCR on the PDF
            subprocess.run(
                ["ocrmypdf", "--force-ocr", str(pdf_file), str(temp_pdf)],
                check=True,
            )

            # Convert the OCR'd PDF to text
            subprocess.run(
                ["pdftotext", str(temp_pdf), str(txt_file_out)],
                check=True,
            )

        return None
    except subprocess.CalledProcessError as e:
        print(f"Error OCR'ing and converting {pdf_file.name} to text: {e}")
        return e
    except Exception as e:
        print(f"Unexpected error processing {pdf_file.name}: {e}")
        return e

def process_pdf_file(item: TranslationItem) -> tuple[Exception | None, bool]:
    """
    Process a PDF file and convert it to text.
    Now supports both local and remote files using temporary file management.

    Args:
        item: TranslationItem containing input and output file paths

    Returns:
        tuple: (error, success) where error is None if successful and success is True if file was processed
    """
    input_is_remote = is_remote_path(item.input_file)
    output_is_remote = is_remote_path(item.output_file)
    
    print(f"Processing PDF: {item.input_file.name} (input: {'remote' if input_is_remote else 'local'}, "
          f"output: {'remote' if output_is_remote else 'local'})")

    try:
        # Use temporary file managers for remote files
        with TempFileManager(item.input_file) as local_input:
            with TemporaryDirectory() as temp_processing_dir:
                temp_output = Path(temp_processing_dir) / f"temp_{item.input_file.name}.txt"

                # Try regular PDF to text conversion
                err = try_pdf_convert_to_text(local_input, temp_output)
                
                if err is not None:
                    print(f"Regular conversion failed for {item.input_file.name}, trying OCR...")
                    err = convert_pdf_to_text_via_ocr(local_input, temp_output)
                    
                    if err is not None:
                        print(f"OCR conversion also failed for {item.input_file.name}")
                        return err, False

                # Both conversions succeeded, now handle language detection and output
                if not temp_output.exists():
                    return Exception("Processing completed but no output file was created"), False

                # Detect language from the temporary file
                lang_code, is_reliable = detect_language_from_file(temp_output)
                item.language = lang_code
                item.should_translate = lang_code.lower() == "en"

                # Update the output filename to include language code
                stem = item.output_file.stem
                suffix = item.output_file.suffix
                new_filename = f"{stem}-{lang_code.upper()}{suffix}"
                item.output_file = item.output_file.with_name(new_filename)

                # Write to final output location (handling remote if necessary)
                try:
                    # Ensure output directory exists
                    item.output_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy content to final destination
                    content = temp_output.read_text(encoding="utf-8")
                    item.output_file.write_text(content, encoding="utf-8")
                    
                    # Update JSON with language information
                    update_json_with_language(item.json_file, lang_code, is_reliable)
                    
                    conversion_method = "OCR" if err is not None else "embedded text"
                    print(f"✓ Successfully converted {item.input_file.name} using {conversion_method} (language: {lang_code})")
                    return None, True
                    
                except Exception as copy_err:
                    print(f"Error writing to final destination {item.output_file}: {copy_err}")
                    return copy_err, False

    except Exception as e:
        print(f"Error in PDF processing pipeline for {item.input_file.name}: {e}")
        return e, False
```

### Phase 8: Update CLI for Remote Path Support

Enhance the CLI to accept and handle remote path specifications.

**File: `src/pdf_ingest/cli.py` (Updated)**

```python
# Updated CLI with remote path support

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .fs_factory import FileSystemFactory
from .fs_path import UniversalPath, is_remote_path
from .scan_and_convert import scan_and_convert

_DOCKER_INPUT_DIR = "/app/input"
_DOCKER_OUTPUT_DIR = "/app/output"
_DOCKER_IMAGE = "niteris/pdf-ingest"

@dataclass
class Args:
    input_dir: UniversalPath
    output_dir: UniversalPath
    rclone_config: Path | None = None
    depth: int = 0

    def __post_init__(self):
        # Validate that paths have the required interface
        if not hasattr(self.input_dir, 'exists'):
            raise TypeError("input_dir must be a PathLike object")
        if not hasattr(self.output_dir, 'exists'):
            raise TypeError("output_dir must be a PathLike object")
        
        # Check existence
        if not self.input_dir.exists():
            raise FileNotFoundError(f"{self.input_dir} does not exist")
        if not self.output_dir.exists():
            # Try to create output directory
            try:
                self.output_dir.mkdir(parents=True, exist_ok=True)
                print(f"Created output directory: {self.output_dir}")
            except Exception as e:
                raise FileNotFoundError(f"Output directory {self.output_dir} does not exist and could not be created: {e}")

def parse_arguments() -> Args:
    """Parse command line arguments with support for remote paths."""
    parser = argparse.ArgumentParser(
        description="Convert PDF, DJVU, EPUB, and FB2 files to text with language detection.",
        epilog="""
Examples:
  Local processing:
    %(prog)s /path/to/input /path/to/output
    
  Remote processing:
    %(prog)s s3:my-bucket/documents s3:my-bucket/output --rclone-config ./rclone.conf
    %(prog)s drive:Documents local-output --rclone-config ./rclone.conf
    
  Mixed local/remote:
    %(prog)s /local/input s3:my-bucket/output --rclone-config ./rclone.conf
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "input_dir",
        help="Input directory path (local path or remote:path format like 's3:bucket/path')"
    )
    parser.add_argument(
        "output_dir", 
        help="Output directory path (local path or remote:path format)"
    )
    parser.add_argument(
        "--rclone-config",
        type=str,
        help="Path to rclone configuration file (required for remote paths)"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=0,
        help="Maximum depth for subdirectory scanning (default: 0, no subdirectories)"
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Force Docker execution (for remote paths, Docker is used automatically)"
    )
    
    args = parser.parse_args()
    
    # Validate rclone config for remote paths
    rclone_config = None
    if args.rclone_config:
        rclone_config = Path(args.rclone_config)
        if not rclone_config.exists():
            parser.error(f"Rclone config file not found: {rclone_config}")
    
    # Check if either path is remote
    is_input_remote = ":" in args.input_dir and not (len(args.input_dir) > 1 and args.input_dir[1] == ":")
    is_output_remote = ":" in args.output_dir and not (len(args.output_dir) > 1 and args.output_dir[1] == ":")
    
    if (is_input_remote or is_output_remote) and not rclone_config:
        parser.error("--rclone-config is required when using remote paths")
    
    # Create path objects
    try:
        input_dir = FileSystemFactory.create_path(args.input_dir, rclone_config)
        output_dir = FileSystemFactory.create_path(args.output_dir, rclone_config)
    except Exception as e:
        parser.error(f"Failed to initialize paths: {e}")
    
    return Args(
        input_dir=input_dir,
        output_dir=output_dir,
        rclone_config=rclone_config,
        depth=args.depth
    )

def _is_nfs_path(path: UniversalPath) -> bool:
    """Check if a path is on an NFS mount (local paths only)."""
    # Only applicable to local paths
    if is_remote_path(path):
        return False
        
    try:
        local_path = Path(str(path))
        abs_path = local_path.resolve()

        if platform.system() == "Windows":
            # On Windows, check if it's a UNC path (\\server\share)
            path_str = str(abs_path)
            if path_str.startswith("\\\\"):
                return True

            # Check if it's a mapped network drive
            try:
                result = subprocess.run(
                    ["net", "use"], capture_output=True, text=True, check=True
                )
                drive_letter = path_str[:2]  # e.g., "Z:"
                if drive_letter in result.stdout:
                    return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        else:
            # On Unix-like systems, check mount points
            try:
                result = subprocess.run(
                    ["mount"], capture_output=True, text=True, check=True
                )
                # Look for NFS mounts that contain our path
                for line in result.stdout.splitlines():
                    if "nfs" in line.lower():
                        mount_point = line.split()[2]
                        if str(abs_path).startswith(mount_point):
                            return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

        return False
    except Exception:
        return False

def main():
    """Main CLI entry point with remote path support."""
    try:
        args = parse_arguments()
        
        print(f"PDF Ingest Tool - Remote File System Support")
        print(f"Input:  {args.input_dir} ({'remote' if is_remote_path(args.input_dir) else 'local'})")
        print(f"Output: {args.output_dir} ({'remote' if is_remote_path(args.output_dir) else 'local'})")
        if args.rclone_config:
            print(f"Rclone config: {args.rclone_config}")
        print(f"Scan depth: {args.depth}")
        print()
        
        # For remote paths, recommend Docker usage but allow local execution
        has_remote = is_remote_path(args.input_dir) or is_remote_path(args.output_dir)
        if has_remote:
            print("⚠️  Remote paths detected. Consider using Docker for better isolation:")
            print("   docker run --rm -it -v \"$(pwd)/rclone.conf:/app/rclone.conf\" \\")
            print(f"     {_DOCKER_IMAGE} \"{args.input_dir}\" \"{args.output_dir}\" --depth {args.depth}")
            print()
            
            response = input("Continue with local execution? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Aborted.")
                return
            print()
        
        # Execute the conversion
        result = scan_and_convert(args.input_dir, args.output_dir, args.depth)
        
        # Print results
        print(f"\n{'='*60}")
        print(f"CONVERSION COMPLETE")
        print(f"{'='*60}")
        print(f"Files processed: {len(result.input_files)}")
        print(f"Successful conversions: {len(result.output_files)}")
        print(f"Failed conversions: {len(result.untranstlatable)}")
        print(f"Errors encountered: {len(result.errors)}")
        
        if result.errors:
            print(f"\nErrors:")
            for i, error in enumerate(result.errors[:5], 1):  # Show first 5 errors
                print(f"  {i}. {error}")
            if len(result.errors) > 5:
                print(f"  ... and {len(result.errors) - 5} more errors")
        
        # Exit with appropriate code
        sys.exit(0 if len(result.errors) == 0 else 1)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Implementation Plan

### Dependencies

Add to `pyproject.toml`:

```toml
[project]
dependencies = [
    # ... existing dependencies
    "virtual-fs>=1.0.0",
]

[project.optional-dependencies]
remote = [
    "virtual-fs>=1.0.0",
]
```

### Migration Steps

1. **✅ Add virtual-fs dependency**
2. **✅ Create abstraction layer files**:
   - `src/pdf_ingest/fs_path.py`
   - `src/pdf_ingest/fs_factory.py` 
   - `src/pdf_ingest/temp_manager.py`
3. **✅ Update core data structures**:
   - `src/pdf_ingest/types.py`
4. **✅ Update core processing logic**:
   - `src/pdf_ingest/scan_and_convert.py`
5. **✅ Update utilities**:
   - `src/pdf_ingest/json_util.py`
6. **✅ Update all parsers**:
   - `src/pdf_ingest/parsers/pdf.py`
   - `src/pdf_ingest/parsers/djvu.py`
   - `src/pdf_ingest/parsers/epub.py`
   - `src/pdf_ingest/parsers/fb2.py`
7. **✅ Update CLI modules**:
   - `src/pdf_ingest/cli.py`
   - `src/pdf_ingest/cli_docker.py`
8. **✅ Update helper function signatures**:
   - Helper functions now correctly use `Path` for local files from TempFileManager
   - `EpubDoc.parse(path: Path)` - Expects local Path from TempFileManager
   - `Fb2Doc.parse(path: Path)` - Expects local Path from TempFileManager  
   - `_parse_epub(path: Path)` - Safe to use external tools with str(path)
   - `_parse_fb2(path: Path)` - Safe to use external tools with str(path)
9. **🔄 Refactor remaining Path() constructor usage**:
   - Scan for all `Path(` patterns in codebase
   - Replace direct `Path()` constructors with `FileSystemFactory.create_path()`
   - Ensure CLI, Docker CLI, and internal utilities use UniversalPath
   - Validate that only TempFileManager contexts use local `Path` objects
10. **Create comprehensive tests**:
   - Unit tests for abstraction layer
   - Integration tests with mock remote filesystems
   - Docker tests with rclone configurations
11. **Update documentation**:
    - README with remote path examples
    - Docker documentation for remote usage
12. **Performance optimization**:
    - Caching strategies for remote file access
    - Parallel processing improvements

### ⚠️ Important: Complete UniversalPath Migration Required

The FSPath transition requires **ALL** functions that work with file paths to use `UniversalPath` instead of `Path`. This includes:

- **Parser helper functions**: Static methods like `EpubDoc.parse()` and `Fb2Doc.parse()`
- **Internal parsing functions**: Functions like `_parse_epub()` and `_parse_fb2()`
- **Any function that receives file paths**: Even if passed through from TempFileManager

### 🚫 **CRITICAL: Never Use str() on UniversalPath Objects**

**FORBIDDEN PATTERN**: 
```python
# ❌ NEVER DO THIS - Breaks abstraction layer
def bad_function(path: UniversalPath):
    external_tool_call(str(path))  # This bypasses remote file handling!
```

**CORRECT PATTERN**:
```python
# ✅ ALWAYS DO THIS - Use TempFileManager for external tools
def good_function(path: UniversalPath):
    with TempFileManager(path) as local_path:
        external_tool_call(str(local_path))  # Now it's guaranteed to be local
```

**Why this matters**:
- `str()` on FSPath objects may return remote URLs, not local file paths
- External tools (pdftotext, tesseract, etc.) require actual local file paths
- Using `str()` directly breaks the download/upload mechanism for remote files
- The TempFileManager ensures files are available locally before tool execution

**Cleanup Required**: All instances of `str(universal_path)` must be replaced with proper TempFileManager usage or path-specific operations that maintain the abstraction.

### 🔧 **Required: Detection and Cleanup Script**

A script must be created to automatically detect and flag all problematic `str()` usage patterns in the codebase:

**Detection Patterns to Find**:
- `str(.*path)` - Direct string conversion of path objects
- `Document(str(` - External library calls with string conversion
- `subprocess.*str(.*path` - Subprocess calls with string-converted paths
- Function calls that bypass TempFileManager for UniversalPath objects

**Script Requirements**:
1. **Scan all Python files** in `src/pdf_ingest/` directory
2. **Identify dangerous patterns** using regex and AST analysis  
3. **Categorize findings**:
   - Critical: External tool calls with `str(path)`
   - Warning: String operations on paths that may be remote
   - Info: Legitimate string conversions (logging, display)
4. **Generate report** with file locations and suggested fixes
5. **Auto-fix capability** where patterns are clear and safe

**Example Script Output**:
```
🚫 CRITICAL: src/pdf_ingest/parsers/epub.py:141
   doc = Document(str(epub_path))
   FIX: Ensure epub_path is local via TempFileManager before this call

⚠️  WARNING: src/pdf_ingest/scan_and_convert.py:107  
   rel_path_str = str(file_path).replace(str(input_dir), "")
   FIX: Use path.relative_to() method instead of string manipulation

ℹ️  INFO: src/pdf_ingest/cli.py:160
   print(f"Processing: {str(path)}")
   OK: Logging/display usage is acceptable
```

This detection script is **MANDATORY** before the FSPath transition can be considered complete and production-ready.

### ✅ **CRITICAL str() Usage Issues - RESOLVED**

**Detection and Analysis Completed**: A comprehensive detection script was created and run to identify all problematic `str()` usage patterns in the codebase. 

**Key Findings & Resolution**:
1. **Helper Function Design**: Parser helper functions (`EpubDoc.parse()`, `Fb2Doc.parse()`, `_parse_epub()`, `_parse_fb2()`) now correctly accept `Path` objects (local files from TempFileManager) rather than `UniversalPath` objects
2. **Proper Abstraction**: The main parser functions use `TempFileManager` to handle UniversalPath → local Path conversion, then pass local Path objects to helper functions  
3. **External Tool Safety**: All external tool calls (`Document()`, `fb2book()`, subprocess calls) now receive guaranteed local file paths
4. **Type Safety**: Proper imports and type hints ensure Path vs UniversalPath usage is explicit and correct

**Design Pattern Established**:
```python
# ✅ CORRECT: Main parser function handles UniversalPath
def process_epub_file(item: TranslationItem) -> tuple[Exception | None, bool]:
    with TempFileManager(item.input_file) as local_input:  # UniversalPath → Path
        epub_doc = EpubDoc.parse(local_input)  # Path accepted here
        # ... rest of processing

# ✅ CORRECT: Helper functions work with local Path objects
@staticmethod  
def parse(path: Path) -> "EpubDoc":  # Expects local Path from TempFileManager
    return _parse_epub(path)

def _parse_epub(epub_path: Path) -> EpubDoc:  # Safe to use str(epub_path)
    doc = Document(str(epub_path))  # External tool gets local path
```

**Status**: All critical `str()` usage issues have been identified and resolved. The abstraction layer is now safe for remote file operations.

### 🔄 **REMAINING WORK: Path() Constructor Usage**

**Issue**: There are still instances of `Path()` constructor calls throughout the codebase that need to be refactored to use `UniversalPath` and `FileSystemFactory.create_path()`.

**Pattern to Find and Fix**:
```python
# ❌ CURRENT: Direct Path() constructor usage
some_path = Path("/some/directory") 
other_path = Path(str(existing_path))

# ✅ TARGET: Use FileSystemFactory or ensure it's from TempFileManager
some_path = FileSystemFactory.create_path("/some/directory")
# OR (if guaranteed local from TempFileManager context)
other_path = existing_local_path  # Already a Path from TempFileManager
```

**Specific Instances Found Requiring Refactor**:

**Critical - Main Code**:
- `src/pdf_ingest/cli.py:94` - `rclone_config = Path(args.rclone_config)`
- `src/pdf_ingest/cli.py:131` - `local_path = Path(str(path))` 
- `src/pdf_ingest/cli_docker.py:14` - `_PATH_APP = Path("/app")`
- `src/pdf_ingest/temp_manager.py:29,79` - `temp_path = Path(self.temp_dir.name)`
- `src/pdf_ingest/temp_manager.py:44,83` - `Path(str(self.remote_file))`
- `src/pdf_ingest/fs_factory.py:45` - `return Path(path_str)` (legitimate)

**Acceptable - Temporary Directory Context**:
- `src/pdf_ingest/parsers/pdf.py:39,88` - Creating paths in TemporaryDirectory (OK)
- `src/pdf_ingest/parsers/djvu.py:39,109` - Creating paths in TemporaryDirectory (OK)
- Test files using `Path(__file__)` and temp directories (OK)

**Priority**: Focus on CLI and TempFileManager Path() usage as these bypass the UniversalPath abstraction and could break remote file support.

**Previous Issues - NOW RESOLVED:**
```python
# ✅ FINAL CORRECT DESIGN:
# Main parser handles UniversalPath and uses TempFileManager
def process_epub_file(item: TranslationItem) -> tuple[Exception | None, bool]:
    with TempFileManager(item.input_file) as local_input:  # UniversalPath → Path
        epub_doc = EpubDoc.parse(local_input)  # Helper gets guaranteed local Path

# Helper functions work with local Path objects
@staticmethod
def parse(path: Path) -> "EpubDoc":  # Path from TempFileManager
    return _parse_epub(path)

def _parse_epub(epub_path: Path) -> EpubDoc:  # Local Path - safe for external tools
    doc = Document(str(epub_path))  # External tool gets local file path
    # ...
```

**All helper function updates completed:**
- ✅ `src/pdf_ingest/parsers/epub.py`: `EpubDoc.parse()`, `_parse_epub()` 
- ✅ `src/pdf_ingest/parsers/fb2.py`: `Fb2Doc.parse()`, `_parse_fb2()`

### Backward Compatibility

- ✅ **Full compatibility**: All existing local file workflows continue to work unchanged
- ✅ **Automatic detection**: Local vs remote paths detected automatically from path format
- ✅ **No breaking changes**: Existing CLI interfaces work exactly as before for local paths
- ✅ **Environment variables**: Support for `RCLONE_CONFIG` and `RCLONE_CONFIG_JSON` environment variables

### New Capabilities

- **Remote input directories**: Process documents stored on cloud storage (S3, Google Drive, etc.)
- **Remote output directories**: Save converted text and metadata to cloud storage
- **Mixed workflows**: Local input → remote output, or remote input → local output
- **Rclone backend support**: Any filesystem supported by rclone (40+ cloud providers)
- **Docker optimization**: Enhanced Docker support for remote file processing
- **Progress tracking**: Better progress indication for remote file transfers

### Usage Examples

```bash
# Local processing (unchanged)
pdf-ingest /local/input /local/output

# Remote to local
pdf-ingest s3:my-bucket/documents /local/output --rclone-config rclone.conf

# Local to remote
pdf-ingest /local/docs s3:my-bucket/processed --rclone-config rclone.conf

# Remote to remote
pdf-ingest drive:Documents s3:backup/processed --rclone-config rclone.conf

# Docker with remote (recommended)
docker run --rm -it -v "$(pwd)/rclone.conf:/app/rclone.conf" \
  niteris/pdf-ingest "s3:docs/input" "s3:docs/output" --depth 2
```

### Testing Strategy

- **Unit tests**: Mock FSPath objects for testing abstraction layer
- **Integration tests**: Test with real rclone configurations and temporary remote storage
- **Docker tests**: Validate Docker workflow with remote paths
- **Performance tests**: Compare local vs remote processing speeds
- **Error handling tests**: Network failures, permission issues, invalid paths
- **Compatibility tests**: Ensure all existing functionality works unchanged

### Performance Considerations

- **Lazy downloading**: Only download remote files when processing begins
- **Streaming uploads**: Upload processed files immediately rather than batching
- **Parallel processing**: Process multiple files concurrently where possible
- **Caching**: Cache remote directory listings to reduce API calls
- **Progress reporting**: Show transfer progress for large remote files

### Error Handling

- **Network resilience**: Retry failed transfers with exponential backoff
- **Partial failures**: Continue processing other files if individual files fail
- **Clear error messages**: Distinguish between local and remote errors
- **Graceful degradation**: Fall back to local processing if remote access fails
- **Cleanup**: Ensure temporary files are cleaned up even on errors

This design provides a comprehensive transition plan that maintains full backward compatibility while adding powerful remote file system capabilities to the PDF Ingest tool.
