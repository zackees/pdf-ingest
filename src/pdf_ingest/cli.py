# # Docker
#   * Install
#     * docker pull niteris/transcribe-everything

#   * Help
#     * docker run --rm -it niteris/transcribe-everything --help

#   * Running
#     * Windows cmd.exe: `docker run --rm -it -v "%cd%\rclone.conf:/app/rclone.conf" niteris/transcribe-everything dst:TorrentBooks/podcast/dialogueworks01/youtube`
#     * Macos/Linux: `docker run --rm -it -v "$(pwd)/rclone.conf:/app/rclone.conf" niteris/transcribe-everything dst:TorrentBooks/podcast/dialogueworks01/youtube`

import argparse
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_DOCKER_INPUT_DIR = "/app/input"
_DOCKER_OUTPUT_DIR = "/app/output"
_DOCKER_IMAGE = "niteris/pdf-ingest"


@dataclass
class Args:
    input_dir: Path
    output_dir: Path

    def __post_init__(self):
        if not isinstance(self.input_dir, Path):
            raise TypeError("input_dir must be a Path object")
        if not isinstance(self.output_dir, Path):
            raise TypeError("output_dir must be a Path object")
        if not self.input_dir.exists():
            raise FileNotFoundError(f"{self.input_dir} does not exist")
        if not self.output_dir.exists():
            raise FileNotFoundError(f"{self.output_dir} does not exist")


def _is_nfs_path(path: Path) -> bool:
    """Check if a path is on an NFS mount.

    Args:
        path: Path to check

    Returns:
        True if the path is on an NFS mount, False otherwise
    """
    try:
        abs_path = path.resolve()

        if platform.system() == "Windows":
            # On Windows, check if it's a UNC path (\\server\share)
            path_str = str(abs_path)
            if path_str.startswith("\\\\"):
                return True

            # Check if it's a mapped network drive
            try:
                result = subprocess.run(
                    ["net", "use"], capture_output=True, text=True, check=True
                )
                drive_letter = path_str[:2]  # e.g., "Z:"
                if drive_letter in result.stdout:
                    return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

        else:
            # On Unix-like systems, check mount points
            try:
                result = subprocess.run(
                    ["mount"], capture_output=True, text=True, check=True
                )
                # Look for NFS mounts that contain our path
                for line in result.stdout.splitlines():
                    if "nfs" in line.lower():
                        mount_point = line.split()[2]
                        if str(abs_path).startswith(mount_point):
                            return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

        return False
    except Exception:
        # If we can't determine, assume it's not NFS
        return False


def _copy_to_local_temp(nfs_path: Path) -> Path:
    """Copy NFS directory contents to a local temporary directory.

    Args:
        nfs_path: Path on NFS mount

    Returns:
        Path to local temporary directory
    """
    import tempfile

    temp_dir = Path(tempfile.mkdtemp(prefix="pdf_ingest_"))
    print(f"Copying NFS directory {nfs_path} to local temp directory {temp_dir}")

    try:
        shutil.copytree(nfs_path, temp_dir / "input", dirs_exist_ok=True)
        return temp_dir / "input"
    except Exception as e:
        print(f"Error copying NFS directory: {e}", file=sys.stderr)
        # Clean up on failure
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def _to_volume_path(host_path: Path, container_path: str) -> str:
    """Convert a Path to a volume path for Docker.

    Args:
        host_path: Path on the host system
        container_path: Path in the container

    Returns:
        Docker volume mapping string
    """
    abs_path = host_path.resolve()

    # Handle Windows paths differently
    if platform.system() == "Windows":
        # Convert Windows path to Docker format (C:\path -> C:/path)
        docker_path = str(abs_path).replace("\\", "/")
        return f"{docker_path}:{container_path}"
    else:
        # Unix paths work as-is
        return f"{abs_path}:{container_path}"


def parse_args() -> Args:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run PDF ingest in a Docker container")
    parser.add_argument(
        "input_dir",
        nargs="?",
        type=Path,
        help="Directory containing PDF files to process",
    )

    parser.add_argument(
        "--output_dir",
        type=Path,
        default="test_data_output",
        help="Directory to save output files",
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=None,
        help="Depth of subdirectory scanning",
    )

    parser.add_argument(
        "--update",
        action="store_true",
        help="Update existing files instead of skipping them",
    )

    args = parser.parse_args()
    first = True
    while args.input_dir is None:
        is_first = first
        first = False
        if is_first:
            response = input("Please specify the input directory: ")
        else:
            response = input(": ")
        input_path = Path(response)
        if input_path.exists() and input_path.is_dir():
            args.input_dir = input_path
        else:
            print(f"Invalid directory '{input_path}'. Please try again", end="")
            continue
    while args.depth is None:
        response = input("How deep do you want to search?: ")
        try:
            args.depth = int(response)
        except ValueError:
            print(f"Invalid depth '{response}'. Please enter a valid integer", end="")
            continue
    if not args.input_dir.exists():
        parser.error(f"Input directory {args.input_dir} does not exist")
    if args.output_dir is None or args.output_dir.exists() is False:
        # Set output_dir to input_dir if not provided
        print(f"Using input directory as output directory: {args.input_dir}")
        args.output_dir = args.input_dir
    return Args(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
    )


def _docker_build_image(remove_previous=True, remove_orphanes=True) -> None:
    """Build the Docker image.

    Args:
        remove_previous: Whether to remove previous images with the same tag
        remove_orphanes: Whether to remove orphaned images
    """
    # First, check if we need to remove previous images
    if remove_previous:
        cmd_remove = f"docker rmi {_DOCKER_IMAGE} --force"
        print(f"Removing previous image: {cmd_remove}")
        # Ignore errors if the image doesn't exist
        subprocess.call(cmd_remove, shell=True)

    # Build the image from the Dockerfile in the current directory
    cmd_build = f"docker build -t {_DOCKER_IMAGE} ."
    print(f"Building image: {cmd_build}")
    result = subprocess.call(cmd_build, shell=True)

    if result != 0:
        print("Failed to build Docker image", file=sys.stderr)
        return

    # Clean up orphaned images if requested
    if remove_orphanes:
        cmd_prune = "docker image prune -f"
        print(f"Removing orphaned images: {cmd_prune}")
        subprocess.call(cmd_prune, shell=True)


def _docker_pull_image() -> None:
    """Pull the Docker image."""
    cmd_pull = "docker pull niteris/pdf-ingest"
    print(f"Running command: {cmd_pull}")
    subprocess.run(cmd_pull, shell=True, check=True)


def _docker_run(input_dir: Path, output_dir: Path) -> None:
    """Run the Docker image."""
    temp_dir_to_cleanup = None
    actual_input_dir = input_dir

    # Check if input directory is on NFS
    if _is_nfs_path(input_dir):
        print(f"Warning: Input directory {input_dir} is on an NFS mount.")
        print("Docker volume mounting may not work properly with NFS.")
        print("Copying files to local temporary directory...")

        try:
            actual_input_dir = _copy_to_local_temp(input_dir)
            temp_dir_to_cleanup = actual_input_dir.parent
        except Exception as e:
            print(f"Failed to copy NFS directory: {e}", file=sys.stderr)
            print("Attempting to proceed with direct NFS mount (may fail)...")
            actual_input_dir = input_dir

    try:
        cmd_list_run: list[str] = [
            "docker",
            "run",
            "--rm",
        ]

        # Add NFS mount support for Windows only when needed
        if platform.system() == "Windows" and _is_nfs_path(input_dir):
            cmd_list_run.extend(
                [
                    "--mount",
                    "type=bind,source=//host.docker.internal,target=/nfs",
                    "--privileged",
                ]
            )

        # Add interactive terminal if stdout is a TTY
        if sys.stdout.isatty():
            cmd_list_run.append("-t")
        # Add volume mapping for input directory
        input_volume = _to_volume_path(actual_input_dir, _DOCKER_INPUT_DIR)
        output_volume = _to_volume_path(output_dir, _DOCKER_OUTPUT_DIR)
        cmd_list_run += [
            "-v",
            input_volume,
            "-v",
            output_volume,
            _DOCKER_IMAGE,
        ]

        cmd_run = subprocess.list2cmdline(cmd_list_run)
        print(f"Running command: {cmd_run}")
        subprocess.run(cmd_run, shell=True)

    finally:
        # Clean up temporary directory if we created one
        if temp_dir_to_cleanup and temp_dir_to_cleanup.exists():
            print(f"Cleaning up temporary directory {temp_dir_to_cleanup}")
            shutil.rmtree(temp_dir_to_cleanup, ignore_errors=True)


def _is_in_repo() -> bool:
    files_list = os.listdir(".")
    if "docker-compose.yml" in files_list:
        return True
    return False


def main() -> int:
    """Main entry point for the pdf_ingest Docker wrapper."""
    try:
        args = parse_args()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    input_dir: Path = args.input_dir
    output_dir: Path = args.output_dir
    if _is_in_repo():
        print("Build docker image from repo")
        _docker_build_image(remove_previous=True, remove_orphanes=True)
    else:
        print("Pull docker image from Docker Hub")
        _docker_pull_image()
    # Use pull for now, but the build function is available
    # _docker_pull_image()
    # Uncomment to build instead of pull:
    # _docker_build_image(remove_previous=True, remove_orphanes=True)
    _docker_run(input_dir=input_dir, output_dir=output_dir)
    return 0


if __name__ == "__main__":
    sys.argv.append("test_data")
    sys.argv.append("--output_dir")
    sys.argv.append("test_data_output")
    sys.exit(main())
