# # Docker
#   * Install
#     * docker pull niteris/transcribe-everything

#   * Help
#     * docker run --rm -it niteris/transcribe-everything --help

import argparse

#   * Running
#     * Windows cmd.exe: `docker run --rm -it -v "%cd%\rclone.conf:/app/rclone.conf" niteris/transcribe-everything dst:TorrentBooks/podcast/dialogueworks01/youtube`
#     * Macos/Linux: `docker run --rm -it -v "$(pwd)/rclone.conf:/app/rclone.conf" niteris/transcribe-everything dst:TorrentBooks/podcast/dialogueworks01/youtube`
import os
import platform
import subprocess
import sys
from pathlib import Path

from pdf_ingest.cli import Args

_DOCKER_INPUT_DIR = "/app/input"
_DOCKER_OUTPUT_DIR = "/app/output"
_DOCKER_IMAGE = "niteris/pdf-ingest"


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
        type=Path,
        help="Directory containing PDF files to process",
    )

    parser.add_argument(
        "--output_dir",
        type=Path,
        default="test_data_output",
        help="Directory to save output files",
    )

    args = parser.parse_args()
    if not args.input_dir.exists():
        parser.error(f"Input directory {args.input_dir} does not exist")

    if args.output_dir is None:
        # Set output_dir to input_dir if not provided
        args.output_dir = args.input_dir
    return Args(input_dir=args.input_dir, output_dir=args.output_dir)


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
    cmd_list_run: list[str] = [
        "docker",
        "run",
        "--rm",
    ]
    # Add interactive terminal if stdout is a TTY
    if sys.stdout.isatty():
        cmd_list_run.append("-t")
    # Add volume mapping for input directory
    input_volume = _to_volume_path(input_dir, _DOCKER_INPUT_DIR)
    output_volume = _to_volume_path(output_dir, _DOCKER_OUTPUT_DIR)
    cmd_list_run += [
        "-v",
        input_volume,
        "-v",
        output_volume,
        _DOCKER_IMAGE,
        _DOCKER_INPUT_DIR,  # Pass the input directory as an argument
    ]
    cmd_run = subprocess.list2cmdline(cmd_list_run)
    # print(f"Running command: {cmd_pull}")
    # rtn = subprocess.call(cmd_pull, shell=True)
    # if rtn != 0:
    #     print(f"Failed to run docker image: {rtn}")
    #     return 1
    print(f"Running command: {cmd_run}")
    subprocess.run(cmd_run, shell=True)


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
    sys.exit(main())
