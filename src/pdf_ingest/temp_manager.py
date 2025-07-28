from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from pdf_ingest.fs_path import UniversalPath, is_remote_path


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
                raise Exception(
                    f"Failed to download remote file {self.remote_file}: {e}"
                )
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
        if (
            exc_type is None
            and self._is_remote
            and self.local_file
            and self.local_file.exists()
        ):
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
