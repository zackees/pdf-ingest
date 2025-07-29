"""
Test fsspec-based path implementation for local files.
"""
import tempfile
from pathlib import Path

import pytest

from pdf_ingest.fsspec_path import FSSpecPath


class TestFSSpecPath:
    """Test FSSpecPath implementation with local filesystem."""

    def test_from_uri_local_path(self):
        """Test creating FSSpecPath from local path string."""
        test_path = "/tmp/test_file.txt"
        fs_path = FSSpecPath.from_uri(test_path)
        
        assert isinstance(fs_path, FSSpecPath)
        # On Windows, paths get normalized, so just check it contains the expected parts
        assert "tmp" in fs_path.path
        assert "test_file.txt" in fs_path.path
        # Check protocol is file-related
        protocol = fs_path.fs.protocol
        if isinstance(protocol, tuple):
            assert "file" in protocol
        else:
            assert protocol == "file"

    def test_from_uri_file_protocol(self):
        """Test creating FSSpecPath from file:// URI."""
        test_path = "file:///tmp/test_file.txt"
        fs_path = FSSpecPath.from_uri(test_path)
        
        assert isinstance(fs_path, FSSpecPath)
        assert fs_path.path == "/tmp/test_file.txt"
        # Handle protocol as either string or tuple
        protocol = fs_path.fs.protocol
        if isinstance(protocol, tuple):
            assert "file" in protocol
        else:
            assert protocol == "file"

    def test_basic_file_operations(self):
        """Test basic file operations: create, read, write, delete."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create FSSpecPath
            test_file = FSSpecPath.from_uri(f"{temp_dir}/test_file.txt")
            
            # Test file doesn't exist initially
            assert not test_file.exists()
            assert not test_file.is_file()
            assert not test_file.is_dir()
            
            # Write content
            test_content = "Hello, fsspec world!"
            test_file.write_text(test_content)
            
            # Test file exists and has correct content
            assert test_file.exists()
            assert test_file.is_file()
            assert not test_file.is_dir()
            assert test_file.read_text() == test_content
            
            # Test binary operations
            binary_content = b"Binary data \x00\x01\x02"
            test_file.write_bytes(binary_content)
            assert test_file.read_bytes() == binary_content
            
            # Delete file
            test_file.unlink()
            assert not test_file.exists()

    def test_directory_operations(self):
        """Test directory operations: create, list, remove."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create nested directory structure
            test_dir = FSSpecPath.from_uri(f"{temp_dir}/test_dir/nested")
            
            assert not test_dir.exists()
            
            # Create directory with parents
            test_dir.mkdir(parents=True, exist_ok=True)
            assert test_dir.exists()
            assert test_dir.is_dir()
            
            # Create some test files
            (test_dir / "file1.txt").write_text("Content 1")
            (test_dir / "file2.txt").write_text("Content 2")
            
            # Test directory listing
            files = list(test_dir.iterdir())
            file_names = [f.name for f in files]
            assert "file1.txt" in file_names
            assert "file2.txt" in file_names
            assert len(file_names) == 2

    def test_path_properties(self):
        """Test path properties: name, stem, suffix, parent."""
        # Use a relative path to avoid Windows absolute path issues
        test_path = FSSpecPath.from_uri("documents/report.pdf")
        
        assert test_path.name == "report.pdf"
        assert test_path.stem == "report"
        assert test_path.suffix == ".pdf"
        assert test_path.parent.path == "documents"

    def test_path_manipulation(self):
        """Test path manipulation methods."""
        test_path = FSSpecPath.from_uri("documents/document.txt")
        
        # Test with_suffix
        pdf_path = test_path.with_suffix(".pdf")
        assert pdf_path.name == "document.pdf"
        assert pdf_path.suffix == ".pdf"
        
        # Test with_name
        new_path = test_path.with_name("report.docx")
        assert new_path.name == "report.docx"
        assert new_path.parent.path == test_path.parent.path
        
        # Test path joining
        joined = test_path.parent / "subfolder" / "file.txt"
        assert joined.path == "documents/subfolder/file.txt"

    def test_glob_operations(self):
        """Test glob pattern matching."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = FSSpecPath.from_uri(temp_dir)
            
            # Create test files
            (base_dir / "test1.txt").write_text("content")
            (base_dir / "test2.txt").write_text("content")
            (base_dir / "other.pdf").write_text("content")
            (base_dir / "subdir").mkdir()
            (base_dir / "subdir" / "test3.txt").write_text("content")
            
            # Test glob patterns
            txt_files = list(base_dir.glob("*.txt"))
            txt_names = [f.name for f in txt_files]
            assert "test1.txt" in txt_names
            assert "test2.txt" in txt_names
            assert "other.pdf" not in txt_names
            assert len(txt_names) == 2

    def test_path_compatibility_with_pathlib(self):
        """Test that FSSpecPath behaves similarly to pathlib.Path for local operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Compare behavior with pathlib.Path
            pathlib_path = Path(temp_dir) / "pathlib_test.txt"
            fsspec_path = FSSpecPath.from_uri(temp_dir) / "fsspec_test.txt"
            
            # Write content using both
            pathlib_path.write_text("Pathlib content")
            fsspec_path.write_text("FSSpec content")
            
            # Both should exist
            assert pathlib_path.exists()
            assert fsspec_path.exists()
            
            # Both should be files
            assert pathlib_path.is_file()
            assert fsspec_path.is_file()
            
            # Content should match
            assert pathlib_path.read_text() == "Pathlib content"
            assert fsspec_path.read_text() == "FSSpec content"
            
            # Properties should behave similarly
            assert pathlib_path.name == "pathlib_test.txt"
            assert fsspec_path.name == "fsspec_test.txt"
            
            assert pathlib_path.suffix == ".txt"
            assert fsspec_path.suffix == ".txt"

    def test_error_handling(self):
        """Test error handling for common failure cases."""
        # Test reading non-existent file
        non_existent = FSSpecPath.from_uri("/tmp/does_not_exist.txt")
        
        with pytest.raises(FileNotFoundError):
            non_existent.read_text()
        
        with pytest.raises(FileNotFoundError):
            non_existent.read_bytes()
        
        # Test creating directory that already exists without exist_ok
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = FSSpecPath.from_uri(temp_dir)
            
            with pytest.raises(FileExistsError):
                test_dir.mkdir(exist_ok=False)

    def test_temp_file_manager_integration(self):
        """Test integration pattern similar to how TempFileManager would use FSSpecPath."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Simulate remote file downloaded to local temp
            remote_file = FSSpecPath.from_uri(f"{temp_dir}/remote_file.txt")
            remote_file.write_text("Remote content")
            
            # Use with TempFileManager pattern - local processing
            local_path = Path(str(remote_file))  # Convert to local Path for external tools
            assert local_path.exists()
            assert local_path.read_text() == "Remote content"
            
            # Simulate processing and writing back
            processed_content = local_path.read_text().upper()
            remote_file.write_text(processed_content)
            
            assert remote_file.read_text() == "REMOTE CONTENT"

    def test_string_representation(self):
        """Test string representation and repr methods."""
        test_path = FSSpecPath.from_uri("documents/test.txt")
        
        assert str(test_path) == "documents/test.txt"
        assert "FSSpecPath" in repr(test_path)
        assert "LocalFileSystem" in repr(test_path)
        assert "documents/test.txt" in repr(test_path)

    def test_relative_path_operations(self):
        """Test relative path operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = FSSpecPath.from_uri(temp_dir)
            sub_file = base_dir / "subdir" / "file.txt"
            
            # Create the file
            sub_file.parent.mkdir(parents=True, exist_ok=True)
            sub_file.write_text("content")
            
            # Test relative_to
            relative = sub_file.relative_to(base_dir)
            assert relative.path == "subdir/file.txt" 