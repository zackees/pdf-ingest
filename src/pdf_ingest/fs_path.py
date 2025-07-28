from pathlib import Path
from typing import Iterator, Protocol, Union, runtime_checkable

try:
    from virtual_fs import FSPath
except ImportError:
    # Create a proper stub for FSPath with all required methods
    class FSPath:
        def exists(self) -> bool:
            raise ImportError("virtual-fs package not available")

        def is_dir(self) -> bool:
            raise ImportError("virtual-fs package not available")

        def mkdir(self, parents: bool = True, exist_ok: bool = True) -> None:
            raise ImportError("virtual-fs package not available")

        def read_text(self, encoding: str = "utf-8") -> str:
            raise ImportError("virtual-fs package not available")

        def write_text(self, data: str, encoding: str = "utf-8") -> None:
            raise ImportError("virtual-fs package not available")

        def read_bytes(self) -> bytes:
            raise ImportError("virtual-fs package not available")

        def write_bytes(self, data: bytes) -> None:
            raise ImportError("virtual-fs package not available")

        @property
        def name(self) -> str:
            raise ImportError("virtual-fs package not available")

        @property
        def stem(self) -> str:
            raise ImportError("virtual-fs package not available")

        @property
        def suffix(self) -> str:
            raise ImportError("virtual-fs package not available")

        @property
        def parent(self) -> "FSPath":
            raise ImportError("virtual-fs package not available")

        def __truediv__(self, other: str) -> "FSPath":
            raise ImportError("virtual-fs package not available")

        def __str__(self) -> str:
            raise ImportError("virtual-fs package not available")

        def with_suffix(self, suffix: str) -> "FSPath":
            raise ImportError("virtual-fs package not available")

        def with_name(self, name: str) -> "FSPath":
            raise ImportError("virtual-fs package not available")

        def relative_to(self, other: "FSPath") -> "FSPath":
            raise ImportError("virtual-fs package not available")

        def resolve(self) -> "FSPath":
            raise ImportError("virtual-fs package not available")

        def glob(self, pattern: str) -> Iterator["FSPath"]:
            raise ImportError("virtual-fs package not available")

        def is_real_fs(self) -> bool:
            raise ImportError("virtual-fs package not available")


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
    def glob(self, pattern: str) -> Iterator["PathLike"]: ...


# Type alias for paths that can be either local or remote
UniversalPath = Union[Path, FSPath]


def is_remote_path(path: UniversalPath) -> bool:
    """Check if a path is a remote FSPath."""
    return hasattr(path, "is_real_fs") and not path.is_real_fs()


def ensure_local_path(path: UniversalPath) -> Path:
    """Convert a UniversalPath to a local Path, downloading if necessary."""
    if isinstance(path, Path):
        return path
    else:
        # This would be handled by TempFileManager for actual files
        raise NotImplementedError("Use TempFileManager for remote file access")
