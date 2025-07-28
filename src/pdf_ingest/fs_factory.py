from pathlib import Path
from typing import Optional

try:
    from virtual_fs import Vfs
except ImportError:
    # If virtual-fs is not available, create stubs
    class Vfs:
        @staticmethod
        def begin(path_str: str, config: Optional[Path] = None):
            raise ImportError("virtual-fs package not available")


from pdf_ingest.fs_path import UniversalPath


class FileSystemFactory:
    """Factory for creating appropriate path objects based on path string format."""

    @staticmethod
    def create_path(
        path_str: str, rclone_config: Optional[Path] = None
    ) -> UniversalPath:
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
                raise ValueError(
                    f"Failed to initialize remote filesystem for '{path_str}': {e}"
                )
        else:
            # Local path
            return Path(path_str)

    @staticmethod
    def create_output_path(
        base_path: UniversalPath, relative_path: str
    ) -> UniversalPath:
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
        from pdf_ingest.fs_path import is_remote_path

        if is_remote_path(path):
            return "remote"
        else:
            return "local"
