# Updated CLI with remote path support

import argparse
import logging
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from pdf_ingest.fs_factory import FileSystemFactory
from pdf_ingest.fs_path import UniversalPath, is_remote_path
from pdf_ingest.scan_and_convert import scan_and_convert

_DOCKER_INPUT_DIR = "/app/input"
_DOCKER_OUTPUT_DIR = "/app/output"
_DOCKER_IMAGE = "niteris/pdf-ingest"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@dataclass
class Args:
    input_dir: UniversalPath
    output_dir: UniversalPath
    rclone_config: Path | None = None
    depth: int = 0

    def __post_init__(self):
        # Validate that paths have the required interface
        if not hasattr(self.input_dir, "exists"):
            raise TypeError("input_dir must be a PathLike object")
        if not hasattr(self.output_dir, "exists"):
            raise TypeError("output_dir must be a PathLike object")

        # Check existence - use different approach for remote paths
        if not self._path_exists(self.input_dir):
            raise FileNotFoundError(f"{self.input_dir} does not exist")
        if not self._path_exists(self.output_dir):
            # Try to create output directory
            try:
                self.output_dir.mkdir(parents=True, exist_ok=True)
                print(f"Created output directory: {self.output_dir}")
            except Exception as e:
                raise FileNotFoundError(
                    f"Output directory {self.output_dir} does not exist and could not be created: {e}"
                )

    def _path_exists(self, path: UniversalPath) -> bool:
        """
        Check if a path exists, using a more reliable method for remote paths.

        Args:
            path: Path to check (local or remote)

        Returns:
            bool: True if path exists and is accessible
        """
        try:
            if hasattr(path, "lspaths"):
                # For remote FSPath objects, try listing contents instead of exists()
                # This is more reliable than exists() which can timeout
                path.lspaths()
                return True
            else:
                # For local Path objects, use the standard exists() method
                return path.exists()
        except Exception:
            return False


def parse_arguments() -> Args:
    """Parse command line arguments with support for remote paths."""
    logger.info("Starting argument parsing")

    parser = argparse.ArgumentParser(
        description="Convert PDF, DJVU, EPUB, and FB2 files to text with language detection.",
        epilog="""
Examples:
  Local processing:
    %(prog)s /path/to/input /path/to/output
    
  Remote processing:
    %(prog)s s3:my-bucket/documents s3:my-bucket/output --rclone-config ./rclone.conf
    %(prog)s drive:Documents local-output --rclone-config ./rclone.conf
    
  Mixed local/remote:
    %(prog)s /local/input s3:my-bucket/output --rclone-config ./rclone.conf
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "input_dir",
        help="Input directory path (local path or remote:path format like 's3:bucket/path')",
    )
    parser.add_argument(
        "output_dir", help="Output directory path (local path or remote:path format)"
    )
    parser.add_argument(
        "--rclone-config",
        type=str,
        help="Path to rclone configuration file (required for remote paths)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=0,
        help="Maximum depth for subdirectory scanning (default: 0, no subdirectories)",
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Force Docker execution (for remote paths, Docker is used automatically)",
    )

    args = parser.parse_args()

    logger.info(
        f"Parsed arguments: input_dir='{args.input_dir}', output_dir='{args.output_dir}', depth={args.depth}"
    )
    if args.rclone_config:
        logger.info(f"Rclone config specified: {args.rclone_config}")
    if args.docker:
        logger.info("Docker execution forced via --docker flag")

    # Validate rclone config for remote paths
    rclone_config = None
    if args.rclone_config:
        rclone_config = Path(args.rclone_config)
        logger.info(f"Validating rclone config file: {rclone_config}")
        if not rclone_config.exists():
            logger.error(f"Rclone config file not found: {rclone_config}")
            parser.error(f"Rclone config file not found: {rclone_config}")
        logger.info("Rclone config file validation successful")

    # Check if either path is remote
    is_input_remote = ":" in args.input_dir and not (
        len(args.input_dir) > 1 and args.input_dir[1] == ":"
    )
    is_output_remote = ":" in args.output_dir and not (
        len(args.output_dir) > 1 and args.output_dir[1] == ":"
    )

    logger.info(
        f"Path type analysis: input_remote={is_input_remote}, output_remote={is_output_remote}"
    )

    if (is_input_remote or is_output_remote) and not rclone_config:
        logger.error("Remote paths detected but no rclone config provided")
        parser.error("--rclone-config is required when using remote paths")

    # Create path objects
    logger.info("Creating UniversalPath objects via FileSystemFactory")
    try:
        logger.debug(f"Creating input path for: {args.input_dir}")
        input_dir = FileSystemFactory.create_path(args.input_dir, rclone_config)
        logger.info(
            f"Successfully created input path: {input_dir} (type: {type(input_dir).__name__})"
        )

        logger.debug(f"Creating output path for: {args.output_dir}")
        output_dir = FileSystemFactory.create_path(args.output_dir, rclone_config)
        logger.info(
            f"Successfully created output path: {output_dir} (type: {type(output_dir).__name__})"
        )
    except Exception as e:
        logger.error(f"Failed to initialize paths: {e}")
        parser.error(f"Failed to initialize paths: {e}")

    return Args(
        input_dir=input_dir,
        output_dir=output_dir,
        rclone_config=rclone_config,
        depth=args.depth,
    )


def _is_nfs_path(path: UniversalPath) -> bool:
    """Check if a path is on an NFS mount (local paths only)."""
    # Only applicable to local paths
    if is_remote_path(path):
        return False

    try:
        local_path = Path(str(path))
        abs_path = local_path.resolve()

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
        return False


def main():
    """Main CLI entry point with remote path support."""
    logger.info("=== PDF Ingest Tool Started ===")
    try:
        logger.info("Parsing command line arguments")
        args = parse_arguments()
        logger.info("Command line arguments parsed successfully")

        # Log the configuration being used
        input_type = "remote" if is_remote_path(args.input_dir) else "local"
        output_type = "remote" if is_remote_path(args.output_dir) else "local"

        logger.info("Configuration summary:")
        logger.info(f"  Input directory: {args.input_dir} ({input_type})")
        logger.info(f"  Output directory: {args.output_dir} ({output_type})")
        logger.info(f"  Scan depth: {args.depth}")
        if args.rclone_config:
            logger.info(f"  Rclone config: {args.rclone_config}")

        print("PDF Ingest Tool - Remote File System Support")
        print(f"Input:  {args.input_dir} ({input_type})")
        print(f"Output: {args.output_dir} ({output_type})")
        if args.rclone_config:
            print(f"Rclone config: {args.rclone_config}")
        print(f"Scan depth: {args.depth}")
        print()

        # For remote paths, recommend Docker usage but allow local execution
        has_remote = is_remote_path(args.input_dir) or is_remote_path(args.output_dir)
        logger.info(f"Remote filesystem detection: has_remote={has_remote}")
        if has_remote:
            print(
                "⚠️  Remote paths detected. Consider using Docker for better isolation:"
            )
            print('   docker run --rm -it -v "$(pwd)/rclone.conf:/app/rclone.conf" \\')
            print(
                f'     {_DOCKER_IMAGE} "{args.input_dir}" "{args.output_dir}" --depth {args.depth}'
            )
            print()

            response = input("Continue with local execution? (y/N): ").strip().lower()
            if response not in ["y", "yes"]:
                logger.info("User chose to abort execution")
                print("Aborted.")
                return
            logger.info("User chose to continue with local execution")
            print()

        # Execute the conversion
        logger.info("Starting document scanning and conversion process")
        logger.info(
            f"Calling scan_and_convert with input={args.input_dir}, output={args.output_dir}, depth={args.depth}"
        )
        result = scan_and_convert(args.input_dir, args.output_dir, args.depth)
        logger.info("Document scanning and conversion process completed")

        # Log and print results
        logger.info("Processing results summary:")
        logger.info(f"  Files processed: {len(result.input_files)}")
        logger.info(f"  Successful conversions: {len(result.output_files)}")
        logger.info(f"  Failed conversions: {len(result.untranstlatable)}")
        logger.info(f"  Errors encountered: {len(result.errors)}")

        if result.errors:
            logger.warning(f"Encountered {len(result.errors)} errors during processing")
            for i, error in enumerate(result.errors, 1):
                logger.error(f"Error {i}: {error}")

        print(f"\n{'='*60}")
        print("CONVERSION COMPLETE")
        print(f"{'='*60}")
        print(f"Files processed: {len(result.input_files)}")
        print(f"Successful conversions: {len(result.output_files)}")
        print(f"Failed conversions: {len(result.untranstlatable)}")
        print(f"Errors encountered: {len(result.errors)}")

        if result.errors:
            print("\nErrors:")
            for i, error in enumerate(result.errors[:5], 1):  # Show first 5 errors
                print(f"  {i}. {error}")
            if len(result.errors) > 5:
                print(f"  ... and {len(result.errors) - 5} more errors")

        # Exit with appropriate code
        exit_code = 0 if len(result.errors) == 0 else 1
        logger.info(f"Exiting with code {exit_code}")
        sys.exit(exit_code)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user (KeyboardInterrupt)")
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Fatal error occurred: {e}", exc_info=True)
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
