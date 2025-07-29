"""
fsspec-based path implementation to replace virtual-fs FSPath.
"""

from __future__ import annotations

import os
from typing import Iterator

import fsspec

# Default endpoint for Backblaze B2's S3-compatible API
_DEFAULT_BACKBLAZE_ENDPOINT = "https://s3.us-west-002.backblazeb2.com"


class FSSpecPath:
    """
    Path-like wrapper around fsspec filesystems that mimics pathlib.Path interface.
    Supports both local filesystem and remote backends (B2, S3, etc.).
    """

    def __init__(self, fs: fsspec.AbstractFileSystem, path: str):
        self.fs = fs
        # Always normalize to forward slashes for consistency
        self.path = path.replace(os.sep, "/")

    @classmethod
    def from_uri(cls, uri: str, **storage_options) -> "FSSpecPath":
        """Create FSSpecPath from URI like 'file:///local/path' or '/local/path'."""
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

    def glob(self, pattern: str) -> Iterator["FSSpecPath"]:
        """Glob for files matching pattern."""
        full_pattern = f"{self.path.rstrip('/')}/{pattern}"
        for path in self.fs.glob(full_pattern):
            yield FSSpecPath(self.fs, path)

    def iterdir(self) -> Iterator["FSSpecPath"]:
        """Iterate over directory contents."""
        for item in self.fs.ls(self.path, detail=False):
            yield FSSpecPath(self.fs, item)

    def relative_to(self, other: "FSSpecPath") -> "FSSpecPath":
        """Get relative path."""
        if not self.path.startswith(other.path):
            raise ValueError(f"{self.path} is not relative to {other.path}")

        rel_path = self.path[len(other.path) :].lstrip("/")
        return FSSpecPath(self.fs, rel_path)

    def __truediv__(self, other: str) -> "FSSpecPath":
        """Join paths with /."""
        new_path = f"{self.path.rstrip('/')}/{other.lstrip('/')}"
        return FSSpecPath(self.fs, new_path)

    def __str__(self) -> str:
        """String representation."""
        return self.path

    def __repr__(self) -> str:
        return f"FSSpecPath(fs={type(self.fs).__name__}, path='{self.path}')"

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
    def parent(self) -> "FSSpecPath":
        """Get parent directory."""
        parent_path = "/".join(self.path.split("/")[:-1])
        return FSSpecPath(self.fs, parent_path)

    def with_suffix(self, suffix: str) -> "FSSpecPath":
        """Change file extension."""
        stem = self.stem
        parent = "/".join(self.path.split("/")[:-1])
        new_name = f"{stem}{suffix}"
        new_path = f"{parent}/{new_name}" if parent else new_name
        return FSSpecPath(self.fs, new_path)

    def with_name(self, name: str) -> "FSSpecPath":
        """Change filename."""
        parent = "/".join(self.path.split("/")[:-1])
        new_path = f"{parent}/{name}" if parent else name
        return FSSpecPath(self.fs, new_path)

    def resolve(self) -> "FSSpecPath":
        """Resolve to absolute path."""
        # For remote filesystems, already absolute
        return self
