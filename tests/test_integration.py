

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




def _bring_up_nfs_server()-> subprocess.Popen:
    """
    Bring up the NFS server.
    This is a placeholder function. Implement the logic to bring up the NFS server.
    """
    try:
        # Example command to start an NFS server
        # Adjust the command according to your NFS server setup
        command = ["docker", "run", "-d", "--name", "test-nfs",
                   "--privileged", "-v", "/tmp/nfs_share:/nfsdata",
                   "-p", "2049:2049", "itsthenetwork/nfs-server-alpine"]
        return subprocess.Popen(command)
    except Exception as e:
        print(f"Error starting NFS server: {e}")
        raise


def _bring_down_nfs_server(process: subprocess.Popen) -> None:
    """
    Bring down the NFS server.
    """
    try:
        process.terminate()
        process.wait()
        print("NFS server stopped successfully.")
    except Exception as e:
        print(f"Error stopping NFS server: {e}")


class NfsServer:
    def __init__(self) -> None:
        """Initialize the NFS server."""
        self.process: subprocess.Popen | None = None

    def start(self) -> None:
        """Start the NFS server."""
        if self.process is None:
            self.process = _bring_up_nfs_server()
            print("NFS server started.")
        else:
            print("NFS server is already running.")

    def stop(self) -> None:
        """Stop the NFS server."""
        if self.process is not None:
            _bring_down_nfs_server(self.process)
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

    def test_main(self) -> None:
        """Test command line interface (CLI)."""
        # Start the NFS server
        with NfsServer() as nfs_server:
            nfs_server.start()
            # Here you can add tests that require the NFS server to be running
            print("NFS server is running, you can add your tests here.")


if __name__ == "__main__":
    unittest.main()
