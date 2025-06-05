

# docker run -d --name test-nfs \
#   --privileged \
#   -v /tmp/nfs_share:/nfsdata \
#   -p 2049:2049 \
#   itsthenetwork/nfs-server-alpine


"""
Unit test file.
"""

import os
import unittest
import subprocess
from pathlib import Path

HERE = Path(__file__).parent.resolve()
PROJECT_ROOT = HERE.parent.resolve()





def _bring_down_nfs_server(path: Path) -> None:
    """
    Bring down the NFS server.
    """
    try:
        # Stop and remove the Docker container
        subprocess.run(["docker", "stop", "test-nfs"], check=True)
        subprocess.run(["docker", "rm", "test-nfs"], check=True)
        print(f"NFS server stopped successfully for path: {path}")
    except subprocess.CalledProcessError as e:
        print(f"Error stopping NFS server for path {path}: {e}")
    except Exception as e:
        print(f"Unexpected error stopping NFS server for path {path}: {e}")


class NfsServer:
    def __init__(self, path: Path) -> None:
        """Initialize the NFS server."""
        self.process: subprocess.Popen | None = None
        self.path = path

    def start(self) -> None:
        """Start the NFS server."""
        if self.process is None:
            try:
                # Example command to start an NFS server
                # Adjust the command according to your NFS server setup
                command = ["docker", "run", "-d", "--name", "test-nfs",
                           "--privileged", "-v", "/tmp/nfs_share:/nfsdata",
                           "-p", "2049:2049", "itsthenetwork/nfs-server-alpine"]
                self.process = subprocess.Popen(command)
                print("NFS server started.")
            except Exception as e:
                print(f"Error starting NFS server: {e}")
                raise
        else:
            print("NFS server is already running.")

    def stop(self) -> None:
        """Stop the NFS server."""
        if self.process is not None:
            _bring_down_nfs_server(self.path)
            self.process = None
            print("NFS server stopped.")
        else:
            print("NFS server is not running.")

    def __enter__(self) -> "NfsServer":
        """Enter the context manager."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Exit the context manager."""
        self.stop()
    

class NfsTester(unittest.TestCase):
    """Main tester class."""

    def test_sanity(self) -> None:
        """Test basic sanity check."""
        self.assertTrue(True, "Sanity check failed, this should always pass.")

    def test_main(self) -> None:
        """Test command line interface (CLI)."""
        # Start the NFS server
        test_path = Path("/tmp/nfs_share")
        with NfsServer(test_path) as nfs_server:
            nfs_server.start()
            # Here you can add tests that require the NFS server to be running
            print("NFS server is running, you can add your tests here.")


if __name__ == "__main__":
    unittest.main()
