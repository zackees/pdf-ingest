# PDF Ingest Remote Storage Refactoring: virtual-fs → fsspec + Backblaze B2

## Overview

This document outlines the plan to refactor the PDF Ingest tool's remote file system support from `virtual-fs` (which uses rclone) to `fsspec` with Backblaze B2 as the cloud storage backend. This migration will provide better Python integration, simpler configuration, and direct B2 API usage without external dependencies on rclone.

## Current Architecture Analysis

### Dependencies
- **Current**: `virtual-fs>=1.0.0` (which depends on `rclone-api`)
- **Target**: `fsspec[b2]` + `b2sdk` for Backblaze B2 support

### Current Implementation Files
1. `src/pdf_ingest/fs_path.py` - UniversalPath abstraction
2. `src/pdf_ingest/fs_factory.py` - Path creation factory
3. `src/pdf_ingest/temp_manager.py` - Remote file download/upload management
4. `src/pdf_ingest/types.py` - TranslationItem data structure
5. Multiple parsers using TempFileManager pattern

### Current Flow
```
Path String → FileSystemFactory → UniversalPath (Path | FSPath) → TempFileManager → Local Processing
```

## Target Architecture

### New Dependencies
```toml
# requirements.txt changes
# Remove: virtual-fs>=1.0.0
# Add:
fsspec[b2]>=2023.12.0
b2sdk>=1.19.0
```

### New Implementation Structure
```
Path String → FileSystemFactory → UniversalPath (Path | B2FileSystem.path) → TempFileManager → Local Processing
```

## Migration Plan

### Phase 1: Create fsspec Adapter Layer

#### 1.1 Create fsspec Path Wrapper (`src/pdf_ingest/fsspec_path.py`)

```python
"""
fsspec-based path implementation to replace virtual-fs FSPath.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterator, Union

import fsspec
from fsspec.implementations.memory import MemoryFile


class FSSpecPath:
    """
    Path-like wrapper around fsspec filesystems that mimics pathlib.Path interface.
    Supports both local filesystem and remote backends (B2, S3, etc.).
    """
    
    def __init__(self, fs: fsspec.AbstractFileSystem, path: str):
        self.fs = fs
        self.path = path.replace(os.sep, "/")  # Normalize to forward slashes
        
    @classmethod
    def from_uri(cls, uri: str, **storage_options) -> "FSSpecPath":
        """Create FSSpecPath from URI like 'b2://bucket/path' or '/local/path'."""
        if "://" not in uri:
            # Local path
            fs = fsspec.filesystem("file")
            return cls(fs, os.path.abspath(uri))
        else:
            # Remote path
            fs = fsspec.filesystem(uri.split("://")[0], **storage_options)
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
        return self.fs.cat_file(self.path)
    
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
        
        rel_path = self.path[len(other.path):].lstrip("/")
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
```

#### 1.2 Update UniversalPath Definition (`src/pdf_ingest/fs_path.py`)

```python
"""
Updated path abstraction using fsspec instead of virtual-fs.
"""
from pathlib import Path
from typing import Iterator, Protocol, Union, runtime_checkable

from pdf_ingest.fsspec_path import FSSpecPath


@runtime_checkable
class PathLike(Protocol):
    """Protocol defining the interface that both Path and FSSpecPath must implement."""
    
    def exists(self) -> bool: ...
    def is_dir(self) -> bool: ...
    def is_file(self) -> bool: ...
    def mkdir(self, parents: bool = True, exist_ok: bool = True) -> None: ...
    def read_text(self, encoding: str = "utf-8") -> str: ...
    def write_text(self, data: str, encoding: str = "utf-8") -> None: ...
    def read_bytes(self) -> bytes: ...
    def write_bytes(self, data: bytes) -> None: ...
    def glob(self, pattern: str) -> Iterator["PathLike"]: ...
    
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
UniversalPath = Union[Path, FSSpecPath]


def is_remote_path(path: UniversalPath) -> bool:
    """Check if a path is a remote FSSpecPath."""
    return isinstance(path, FSSpecPath)


def ensure_local_path(path: UniversalPath) -> Path:
    """Convert a UniversalPath to a local Path, downloading if necessary."""
    if isinstance(path, Path):
        return path
    else:
        # This would be handled by TempFileManager for actual files
        raise NotImplementedError("Use TempFileManager for remote file access")
```

#### 1.3 Update FileSystemFactory (`src/pdf_ingest/fs_factory.py`)

```python
"""
Updated filesystem factory using fsspec for remote storage.
"""
from pathlib import Path
from typing import Optional

from pdf_ingest.fs_path import UniversalPath
from pdf_ingest.fsspec_path import FSSpecPath


class FileSystemFactory:
    """Factory for creating appropriate path objects based on path string format."""
    
    @staticmethod
    def create_path(
        path_str: str, 
        b2_account_info: Optional[dict] = None
    ) -> UniversalPath:
        """
        Create appropriate path object based on path string format.
        
        Args:
            path_str: Path string (local path or b2://bucket/path format)
            b2_account_info: Optional B2 credentials dict with keys:
                           - account_id: B2 account ID
                           - application_key: B2 application key
        
        Returns:
            UniversalPath: Either a Path (local) or FSSpecPath (remote) object
        """
        # Check for B2 URI format
        if path_str.startswith("b2://"):
            if not b2_account_info:
                raise ValueError("B2 credentials required for b2:// paths")
            
            try:
                storage_options = {
                    "account_id": b2_account_info["account_id"],
                    "application_key": b2_account_info["application_key"],
                }
                return FSSpecPath.from_uri(path_str, **storage_options)
            except Exception as e:
                raise ValueError(f"Failed to initialize B2 filesystem for '{path_str}': {e}")
        
        # Check for other remote URIs (s3://, etc.)
        elif "://" in path_str:
            try:
                return FSSpecPath.from_uri(path_str)
            except Exception as e:
                raise ValueError(f"Failed to initialize remote filesystem for '{path_str}': {e}")
        
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
            if isinstance(path, FSSpecPath):
                return f"remote({type(path.fs).__name__})"
            return "remote"
        else:
            return "local"
```

### Phase 2: Update Configuration and CLI

#### 2.1 Add B2 Configuration Support

Create `src/pdf_ingest/b2_config.py`:

```python
"""
Backblaze B2 configuration management.
"""
import os
from typing import Optional, Dict


class B2Config:
    """Manages Backblaze B2 configuration from environment variables or config files."""
    
    @staticmethod
    def from_environment() -> Optional[Dict[str, str]]:
        """
        Get B2 credentials from environment variables.
        
        Expected environment variables:
        - B2_ACCOUNT_ID: Backblaze B2 account ID
        - B2_APPLICATION_KEY: Backblaze B2 application key
        
        Returns:
            Dict with account_id and application_key, or None if not found
        """
        account_id = os.getenv("B2_ACCOUNT_ID")
        app_key = os.getenv("B2_APPLICATION_KEY")
        
        if account_id and app_key:
            return {
                "account_id": account_id,
                "application_key": app_key,
            }
        return None
    
    @staticmethod
    def from_config_file(config_path: str) -> Optional[Dict[str, str]]:
        """
        Load B2 credentials from a config file.
        
        Expected format (JSON):
        {
            "account_id": "your_account_id",
            "application_key": "your_application_key"
        }
        """
        import json
        from pathlib import Path
        
        config_file = Path(config_path)
        if not config_file.exists():
            return None
        
        try:
            with config_file.open() as f:
                config = json.load(f)
            
            if "account_id" in config and "application_key" in config:
                return {
                    "account_id": config["account_id"],
                    "application_key": config["application_key"],
                }
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def get_credentials() -> Optional[Dict[str, str]]:
        """
        Get B2 credentials from environment or default config locations.
        
        Priority order:
        1. Environment variables
        2. ~/.b2_credentials.json
        3. ./b2_credentials.json
        """
        # Try environment first
        creds = B2Config.from_environment()
        if creds:
            return creds
        
        # Try user config
        home_config = os.path.expanduser("~/.b2_credentials.json")
        creds = B2Config.from_config_file(home_config)
        if creds:
            return creds
        
        # Try local config
        creds = B2Config.from_config_file("./b2_credentials.json")
        if creds:
            return creds
        
        return None
```

#### 2.2 Update CLI to Support B2 Configuration

Update `src/pdf_ingest/cli.py` to include B2 configuration options:

```python
# Add to argument parser:
parser.add_argument(
    "--b2-account-id",
    help="Backblaze B2 account ID (or set B2_ACCOUNT_ID env var)",
)
parser.add_argument(
    "--b2-application-key", 
    help="Backblaze B2 application key (or set B2_APPLICATION_KEY env var)",
)
parser.add_argument(
    "--b2-config",
    help="Path to B2 credentials JSON file",
)

# In main() function:
from pdf_ingest.b2_config import B2Config

# Get B2 credentials
b2_creds = None
if args.b2_config:
    b2_creds = B2Config.from_config_file(args.b2_config)
elif args.b2_account_id and args.b2_application_key:
    b2_creds = {
        "account_id": args.b2_account_id,
        "application_key": args.b2_application_key,
    }
else:
    b2_creds = B2Config.get_credentials()

# Update path creation
input_path = FileSystemFactory.create_path(args.input_dir, b2_account_info=b2_creds)
output_path = FileSystemFactory.create_path(args.output_dir, b2_account_info=b2_creds)
```

### Phase 3: Update TempFileManager

The TempFileManager logic can remain largely the same, but needs updates for the new FSSpecPath:

```python
# In src/pdf_ingest/temp_manager.py

from pdf_ingest.fs_path import UniversalPath, is_remote_path
from pdf_ingest.fsspec_path import FSSpecPath

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
        """Download remote file to temporary local file for processing."""
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
    
    # ... rest remains the same
```

### Phase 4: Migration Steps

#### 4.1 Pre-migration Preparation

1. **Backup current configuration**:
   ```bash
   # Save current rclone config if using remote storage
   cp ~/.config/rclone/rclone.conf ~/rclone_backup.conf
   ```

2. **Set up B2 credentials**:
   ```bash
   # Option 1: Environment variables
   export B2_ACCOUNT_ID="your_account_id"
   export B2_APPLICATION_KEY="your_application_key"
   
   # Option 2: Config file
   cat > ~/.b2_credentials.json << EOF
   {
       "account_id": "your_account_id", 
       "application_key": "your_application_key"
   }
   EOF
   ```

#### 4.2 Update Dependencies

```bash
# Remove old dependency
uv remove virtual-fs

# Add new dependencies  
uv add "fsspec[b2]>=2023.12.0"
uv add "b2sdk>=1.19.0"
```

#### 4.3 Code Migration Order

1. **Update `fs_path.py`** - Replace virtual-fs imports with fsspec
2. **Update `fs_factory.py`** - Replace Vfs with FSSpecPath
3. **Update `temp_manager.py`** - Update for new FSSpecPath interface
4. **Update CLI files** - Add B2 configuration support
5. **Update path creation calls** - Pass B2 credentials where needed

#### 4.4 Path Format Migration

**Before (rclone format)**:
```
input_dir: "b2remote:my-bucket/input/"
output_dir: "b2remote:my-bucket/output/"
```

**After (fsspec format)**:
```
input_dir: "b2://my-bucket/input/"
output_dir: "b2://my-bucket/output/"
```

#### 4.5 Testing Migration

1. **Unit tests**: Update existing tests to mock fsspec instead of virtual-fs
2. **Integration tests**: Test with actual B2 bucket (if available)
3. **Backward compatibility**: Ensure local path processing still works

### Phase 5: Benefits and Considerations

#### Benefits of fsspec + B2

1. **Native Python Integration**: No external rclone dependency
2. **Direct B2 API**: Better performance and error handling
3. **Ecosystem Compatibility**: Works with pandas, dask, other Python tools
4. **Simpler Configuration**: Environment variables or JSON config vs rclone config
5. **Better Error Messages**: Python exceptions vs rclone subprocess errors

#### Considerations

1. **Breaking Change**: Existing rclone configurations won't work
2. **Feature Loss**: May lose some rclone-specific features (checksums, retries)
3. **B2 Specific**: Migration targets B2 specifically vs rclone's many backends
4. **Authentication**: Need to handle B2 API key management securely

### Phase 6: Documentation Updates

#### 6.1 Update README.md

- Remove rclone installation instructions
- Add B2 credentials setup
- Update path format examples
- Add fsspec installation instructions

#### 6.2 Update Docker Support

```dockerfile
# Remove rclone installation
# RUN apt-get install -y rclone

# fsspec and B2 dependencies already included via pip
# Add environment variable support for B2 credentials
ENV B2_ACCOUNT_ID=""
ENV B2_APPLICATION_KEY=""
```

#### 6.3 Add Migration Guide

Create `MIGRATION.md` with step-by-step instructions for users to migrate from rclone to B2 direct access.

## Implementation Timeline

1. **Week 1**: Implement fsspec adapter layer and update core path handling
2. **Week 2**: Update CLI, configuration, and temp managers  
3. **Week 3**: Update all parsers and test thoroughly
4. **Week 4**: Documentation, Docker updates, and final testing

## Rollback Plan

If issues arise:
1. Revert to `virtual-fs>=1.0.0` in requirements.txt
2. Restore original fs_path.py, fs_factory.py implementations
3. Remove B2-specific configuration code
4. Keep both implementations temporarily during transition period

## Success Metrics

- [ ] All existing local file processing works unchanged
- [ ] B2 remote file processing works with new URI format
- [ ] Performance is equal or better than rclone approach
- [ ] Configuration is simpler than rclone setup
- [ ] All tests pass with new implementation
- [ ] Docker container builds and runs successfully 