"""
UniversalPath implementation using FSSpec for both local and remote file access.
Replaces the virtual-fs based approach with a unified FSSpec-based implementation.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator, Protocol, runtime_checkable

import fsspec

# Default endpoint for Backblaze B2's S3-compatible API
_DEFAULT_BACKBLAZE_ENDPOINT = "https://s3.us-west-002.backblazeb2.com"


@runtime_checkable
class PathLike(Protocol):
    """Protocol defining the interface that UniversalPath must implement."""

    def exists(self) -> bool: ...
    def is_dir(self) -> bool: ...
    def is_file(self) -> bool: ...
    def mkdir(self, parents: bool = True, exist_ok: bool = True) -> None: ...
    def read_text(self, encoding: str = "utf-8") -> str: ...
    def write_text(self, data: str, encoding: str = "utf-8") -> None: ...
    def read_bytes(self) -> bytes: ...
    def write_bytes(self, data: bytes) -> None: ...
    def unlink(self) -> None: ...
    def glob(self, pattern: str) -> Iterator["UniversalPath"]: ...
    def iterdir(self) -> Iterator["UniversalPath"]: ...

    @property
    def name(self) -> str: ...
    @property
    def stem(self) -> str: ...
    @property
    def suffix(self) -> str: ...
    @property
    def parent(self) -> "UniversalPath": ...

    def __truediv__(self, other: str) -> "UniversalPath": ...
    def __str__(self) -> str: ...
    def with_suffix(self, suffix: str) -> "UniversalPath": ...
    def with_name(self, name: str) -> "UniversalPath": ...
    def relative_to(self, other: "UniversalPath") -> "UniversalPath": ...
    def resolve(self) -> "UniversalPath": ...


class UniversalPath:
    """
    Unified path interface for both local and remote files using FSSpec.
    Supports local filesystem and remote backends (B2, S3, etc.).

    Replaces the Union[Path, FSPath] approach with a single FSSpec-based implementation.
    """

    def __init__(self, fs: fsspec.AbstractFileSystem, path: str):
        self.fs = fs
        # Always normalize to forward slashes for consistency
        self.path = path.replace(os.sep, "/")

    @classmethod
    def from_uri(cls, uri: str, **storage_options) -> "UniversalPath":
        """Create UniversalPath from URI like 'file:///local/path' or '/local/path'."""
        if "://" not in uri:
            # Local path - don't use os.path.abspath to avoid Windows drive letter issues
            fs = fsspec.filesystem("file")
            # Normalize path but keep original format for consistency
            normalized_path = uri.replace(os.sep, "/")
            return cls(fs, normalized_path)
        else:
            # Remote path
            protocol = uri.split("://")[0]
            fs = fsspec.filesystem(protocol, **storage_options)
            path = uri.split("://", 1)[1]
            return cls(fs, path)

    def exists(self) -> bool:
        """Check if path exists."""
        return self.fs.exists(self.path)

    def is_dir(self) -> bool:
        """Check if path is a directory."""
        return self.fs.isdir(self.path)

    def is_file(self) -> bool:
        """Check if path is a file."""
        return self.fs.isfile(self.path)

    def mkdir(self, parents: bool = True, exist_ok: bool = True) -> None:
        """Create directory."""
        if not exist_ok and self.exists():
            raise FileExistsError(f"Directory {self.path} already exists")

        if parents:
            # Create all parent directories
            current = ""
            for part in self.path.strip("/").split("/"):
                current = f"{current}/{part}" if current else part
                if not self.fs.exists(current):
                    try:
                        self.fs.mkdir(current)
                    except Exception:
                        pass  # Some filesystems auto-create directories
        else:
            self.fs.mkdir(self.path)

    def read_text(self, encoding: str = "utf-8") -> str:
        """Read file content as text."""
        return self.fs.cat_file(self.path).decode(encoding)

    def read_bytes(self) -> bytes:
        """Read file content as bytes."""
        out = self.fs.cat_file(self.path)
        if isinstance(out, bytes):
            return out
        else:
            return out.encode("utf-8")

    def write_text(self, data: str, encoding: str = "utf-8") -> None:
        """Write text to file."""
        self.write_bytes(data.encode(encoding))

    def write_bytes(self, data: bytes) -> None:
        """Write bytes to file."""
        # Ensure parent directory exists
        parent_path = "/".join(self.path.split("/")[:-1])
        if parent_path and not self.fs.exists(parent_path):
            self.fs.makedirs(parent_path, exist_ok=True)

        with self.fs.open(self.path, "wb") as f:
            f.write(data)

    def unlink(self) -> None:
        """Remove file."""
        self.fs.rm(self.path)

    def rmdir(self) -> None:
        """Remove directory."""
        self.fs.rmdir(self.path)

    def glob(self, pattern: str) -> Iterator["UniversalPath"]:
        """Glob for files matching pattern."""
        full_pattern = f"{self.path.rstrip('/')}/{pattern}"
        for path in self.fs.glob(full_pattern):
            yield UniversalPath(self.fs, path)

    def iterdir(self) -> Iterator["UniversalPath"]:
        """Iterate over directory contents."""
        for item in self.fs.ls(self.path, detail=False):
            yield UniversalPath(self.fs, item)

    def relative_to(self, other: "UniversalPath") -> "UniversalPath":
        """Get relative path."""
        if not self.path.startswith(other.path):
            raise ValueError(f"{self.path} is not relative to {other.path}")

        rel_path = self.path[len(other.path) :].lstrip("/")
        return UniversalPath(self.fs, rel_path)

    def __truediv__(self, other: str) -> "UniversalPath":
        """Join paths with /."""
        new_path = f"{self.path.rstrip('/')}/{other.lstrip('/')}"
        return UniversalPath(self.fs, new_path)

    def __str__(self) -> str:
        """String representation."""
        return self.path

    def __repr__(self) -> str:
        return f"UniversalPath(fs={type(self.fs).__name__}, path='{self.path}')"

    @property
    def name(self) -> str:
        """Get filename."""
        return self.path.split("/")[-1]

    @property
    def stem(self) -> str:
        """Get filename without extension."""
        name = self.name
        return name.rsplit(".", 1)[0] if "." in name else name

    @property
    def suffix(self) -> str:
        """Get file extension."""
        name = self.name
        return f".{name.rsplit('.', 1)[1]}" if "." in name else ""

    @property
    def parent(self) -> "UniversalPath":
        """Get parent directory."""
        parent_path = "/".join(self.path.split("/")[:-1])
        return UniversalPath(self.fs, parent_path)

    def with_suffix(self, suffix: str) -> "UniversalPath":
        """Change file extension."""
        stem = self.stem
        parent = "/".join(self.path.split("/")[:-1])
        new_name = f"{stem}{suffix}"
        new_path = f"{parent}/{new_name}" if parent else new_name
        return UniversalPath(self.fs, new_path)

    def with_name(self, name: str) -> "UniversalPath":
        """Change filename."""
        parent = "/".join(self.path.split("/")[:-1])
        new_path = f"{parent}/{name}" if parent else name
        return UniversalPath(self.fs, new_path)

    def resolve(self) -> "UniversalPath":
        """Resolve to absolute path."""
        # For remote filesystems, already absolute
        return self


def is_remote_path(path) -> bool:
    """Check if a path is remote (non-file protocol)."""
    # Handle legacy pathlib.Path objects during migration
    if isinstance(path, Path):
        return False  # pathlib.Path is always local

    # Handle new UniversalPath objects
    if hasattr(path, "fs"):
        protocol = path.fs.protocol
        if isinstance(protocol, tuple):
            return "file" not in protocol
        return protocol != "file"

    # Handle other legacy cases
    return False


def ensure_local_path(path) -> Path:
    """Convert a UniversalPath to a local Path, downloading if necessary."""
    # Handle legacy pathlib.Path objects during migration
    if isinstance(path, Path):
        return path

    if not is_remote_path(path):
        # For local files, convert FSSpec path to pathlib.Path
        return Path(str(path))
    else:
        # This should still use TempFileManager for remote files
        raise NotImplementedError("Use TempFileManager for remote file access")
