# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development Commands
- **Lint**: `./lint` - Runs black, isort, ruff, and pyright on src and tests
- **Test**: `./test` - Runs pytest with auto parallelization on unit tests
- **Build Package**: Standard Python setuptools build via pyproject.toml

### Application Usage
- **CLI**: `pdf-ingest <input_dir> <output_dir>` - Process documents from input to output directory
- **Docker CLI**: `pdf-ingest-docker` - Docker-based processing for remote filesystems
- **Remote paths**: Use format `remote:path` (e.g., `s3:bucket/path`) with `--rclone-config`

## Architecture

### Core Components

**FileSystem Abstraction**:
- `fs_factory.py`: Factory for creating local/remote path objects based on URI format
- `fs_path.py`: UniversalPath wrapper providing unified interface for local and remote paths
- `fsspec_path.py`: FSSpec-based path implementation for cloud storage
- Supports local paths, S3, and Backblaze B2 via rclone configuration

**Document Processing Pipeline**:
- `scan_and_convert.py`: Main orchestration - scans directories, identifies unprocessed files, dispatches to parsers
- `parsers/`: Format-specific processors (PDF, DJVU, EPUB, FB2) that extract text and detect language
- `language_detection.py`: Detects document language and appends ISO code to output filename (e.g., `-EN.txt`)
- `json_util.py`: Manages metadata files tracking processing status and language info

**Processing Flow**:
1. Scan input directory for supported formats (.pdf, .djvu, .epub, .fb2)
2. Check output directory for existing .txt/.json files to avoid reprocessing
3. Extract text using format-specific tools (pdftotext, djvutxt, etc.)
4. Detect language and append code to filename
5. Create JSON metadata with language and processing status

**CLI Architecture**:
- `cli.py`: Main CLI with remote filesystem support, validates paths and configs
- `cli_docker.py`: Docker wrapper for remote processing scenarios
- `types.py`: Core data structures (TranslationItem, Result) with path validation

### Key Design Patterns

**Path Handling**: Uses factory pattern to create appropriate path objects (local Path vs remote FSPath) based on string format detection. All path operations go through UniversalPath interface.

**Processing Strategy**: Files are processed only if corresponding .txt output doesn't exist. JSON files track completion status to handle partial processing scenarios.

**Error Handling**: Comprehensive exception handling with detailed error reporting. Failed files are tracked separately from successful conversions.

### External Dependencies
- Document processing: `pdftotext`, `djvutxt`, `ocrmypdf` 
- Language detection: `langdetect`
- Remote storage: `fsspec`, `rclone` (via config file)
- Format support: `epub-utils`, `fb2reader`

### Testing
- Unit tests in `tests/unit/` using pytest
- Integration tests for Docker scenarios in `tests/integration/`
- Test data provided in `test_data/` directory

## Critical Development Rules

### Path Handling - MANDATORY
- **NEVER use `pathlib.Path` directly** - always use `UniversalPath` from `pdf_ingest.fs_path`
- **NEVER use `str(universal_path)` for external tools** - use `TempFileManager` instead
- All file operations must go through `UniversalPath` abstraction for remote file support

### Import Standards
- **NO RELATIVE IMPORTS** - always use absolute imports: `from pdf_ingest.module_name import ...`
- **NO CONDITIONAL TYPE CHECKING** - no `if TYPE_CHECKING:` imports
- **CRITICAL**: Only import `UniversalPath`, never `pathlib.Path` in main code

### External Tool Integration Pattern
```python
# ✅ CORRECT: Use TempFileManager for external tools
from pdf_ingest.temp_manager import TempFileManager

def process_file(item: TranslationItem):
    with TempFileManager(item.input_file) as local_input:
        subprocess.run(["external_tool", str(local_input)])  # Safe: guaranteed local

# ❌ FORBIDDEN: Direct str() conversion
def bad_process_file(item: TranslationItem):
    subprocess.run(["external_tool", str(item.input_file)])  # BREAKS with remote paths
```

### Function Signatures
- Parsers: `process_*_file(item: TranslationItem) -> tuple[Exception | None, bool]`
- Use `Exception | None` pattern for error handling
- Return tuple with error and success boolean

### Environment
- **ALWAYS use `uv run` for Python commands** - ensures correct virtual environment  
- NEVER use `python` directly - use `uv run python` instead