

# docker run -d --name test-nfs \
#   --privileged \
#   -v /tmp/nfs_share:/nfsdata \
#   -p 2049:2049 \
#   itsthenetwork/nfs-server-alpine


"""
Unit test file.
"""

import unittest
import subprocess
from pathlib import Path

from pdf_ingest.win_mount import IS_WINDOWS, windows_has_mount, windows_mount

HERE = Path(__file__).parent.resolve()
PROJECT_ROOT = HERE.parent.resolve()
NFS_TEST = PROJECT_ROOT / "tests" / "nfs_test"


def _bring_down_nfs_server() -> None:
    """
    Bring down the NFS server.
    """
    try:
        # Stop and remove the Docker container
        subprocess.run(["docker", "stop", "test-nfs"], check=True)
        subprocess.run(["docker", "rm", "test-nfs"], check=True)
        # print(f"NFS server stopped successfully for path: {path}")
        print("NFS server stopped successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error stopping NFS server: {e}")
    except Exception as e:
        # print(f"Unexpected error stopping NFS server for path {path}: {e}")
        print(f"Unexpected error stopping NFS server: {e}")


class NfsServer:
    def __init__(self, path: Path) -> None:
        """Initialize the NFS server."""
        self.process: subprocess.Popen | None = None
        self.path = path

    def start(self) -> None:
        """Start the NFS server."""
        if self.process is None:
            try:
                # Clean up any existing container with the same name
                try:
                    subprocess.run(["docker", "stop", "test-nfs"], check=False, capture_output=True)
                    subprocess.run(["docker", "rm", "test-nfs"], check=False, capture_output=True)
                except Exception:
                    pass  # Ignore errors if container doesn't exist
                
                # Example command to start an NFS server
                # Adjust the command according to your NFS server setup
                shared_dir = self.path.resolve()
                command: list[str] = [
                    "docker", "run", "-d", "--name", "test-nfs",
                    "--privileged",
                    "-v", f"{shared_dir}:/nfsdata",
                    "-p", "2049:2049",
                    "itsthenetwork/nfs-server-alpine"
                ]
                cmd_str = subprocess.list2cmdline(command)
                print(f"Starting NFS server with command: {cmd_str}")
                # result = subprocess.run(command, capture_output=True, text=True)
                self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                print("NFS server started")
                # Store a dummy process to indicate the server is running
                
            except Exception as e:
                print(f"Error starting NFS server: {e}")
                raise
        else:
            print("NFS server is already running.")

    def stop(self) -> None:
        """Stop the NFS server."""
        if self.process is not None:
            _bring_down_nfs_server()
            assert self.process.stdout is not None, "Process stdout should not be None"
            self.process.stdout.close()
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

    @unittest.skip("Skip this test")
    def test_sanity(self) -> None:
        """Test basic sanity check."""
        self.assertTrue(True, "Sanity check failed, this should always pass.")
        self.assertTrue(IS_WINDOWS, "This test is intended for Windows only.")
        if not windows_has_mount():
            msg = 'Enable-WindowsOptionalFeature -Online -FeatureName "ClientForNFS-Infrastructure", "NFS-Administration" -All'
            raise RuntimeError(
                f"This test requires Windows mount.exe to be available. Please install it\n  {msg}\n"
            )

    def test_main(self) -> None:
        """Test command line interface (CLI)."""
        # Start the NFS server
        with NfsServer(NFS_TEST) as _:
            #nfs_path = Path(temp_dir) / "nfs_share"
            # now create an index.html file in the nfs_path

            #nfs_path.mkdir(parents=True, exist_ok=True)
            print(f"Temporary NFS path created: {NFS_TEST}")

            index_html = NFS_TEST / "index.html"
            index_html.write_text("<html><body><h1>NFS Test</h1></body></html>")

            with NfsServer(NFS_TEST) as _:
                # Here you can add tests that require the NFS server to be running
                print("NFS server is running, you can add your tests here.")
                mount_proc: subprocess.Popen | None = None
                try:
                    mount_proc = windows_mount(ip="192.168.1.100", drive="N")
                    print("NFS mount command executed successfully.")

                except Exception as e:
                    print(f"Error executing NFS mount command: {e}")
                finally:
                    if mount_proc is not None:
                        mount_proc.kill()
                        print("Mount process killed.")
                    else:
                        print("No mount process to kill.")

                index_html.unlink()
        print("Done")


if __name__ == "__main__":
    unittest.main()
