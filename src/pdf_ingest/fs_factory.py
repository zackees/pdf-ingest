import configparser
from pathlib import Path
from typing import Optional

from pdf_ingest.fs_path import UniversalPath

# Default endpoint for Backblaze B2's S3-compatible API
_DEFAULT_BACKBLAZE_ENDPOINT = "https://s3.us-west-002.backblazeb2.com"


class FileSystemFactory:
    """Factory for creating appropriate path objects based on path string format."""

    @staticmethod
    def create_path(
        path_str: str, rclone_config: Optional[Path] = None
    ) -> UniversalPath:
        """
        Create appropriate path object based on path string format.

        Args:
            path_str: Path string (local path or remote:path format)
            rclone_config: Optional rclone configuration file path

        Returns:
            UniversalPath: FSSpec-based path object for local or remote access
        """
        import logging

        logger = logging.getLogger(__name__)

        logger.debug(
            f"FileSystemFactory.create_path called with: path_str='{path_str}', rclone_config={rclone_config}"
        )

        # Check if it's a remote path (contains : but not Windows drive letter)
        is_remote = ":" in path_str and not (len(path_str) > 1 and path_str[1] == ":")
        logger.debug(f"Path analysis: is_remote={is_remote}")

        if is_remote:
            # Remote path format like "remote:bucket/path"
            logger.info(f"Processing remote path: {path_str}")
            try:
                logger.debug("Parsing rclone configuration...")
                storage_options = FileSystemFactory._parse_rclone_config(
                    path_str, rclone_config
                )
                logger.debug(f"Storage options parsed: {list(storage_options.keys())}")

                logger.debug("Converting rclone format to URI...")
                uri = FileSystemFactory._convert_rclone_to_uri(path_str)
                logger.debug(f"Converted URI: {uri}")

                logger.debug("Creating UniversalPath from URI...")
                result = UniversalPath.from_uri(uri, **storage_options)
                logger.info(
                    f"Remote path created successfully: {type(result.fs).__name__} filesystem"
                )
                return result
            except Exception as e:
                logger.error(f"Failed to create remote path: {e}")
                raise ValueError(
                    f"Failed to initialize remote filesystem for '{path_str}': {e}"
                )
        else:
            # Local path
            logger.info(f"Processing local path: {path_str}")
            try:
                result = UniversalPath.from_uri(path_str)
                logger.info(
                    f"Local path created successfully: {type(result.fs).__name__} filesystem"
                )
                return result
            except Exception as e:
                logger.error(f"Failed to create local path: {e}")
                raise

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
            return "remote"
        else:
            return "local"

    @staticmethod
    def _parse_rclone_config(
        path_str: str, rclone_config: Optional[Path] = None
    ) -> dict:
        """
        Parse rclone.conf to extract storage options for fsspec.

        Args:
            path_str: Remote path string like "dst:TorrentBooks/file.pdf"
            rclone_config: Optional path to rclone.conf file

        Returns:
            dict: Storage options for fsspec filesystem
        """
        import logging

        logger = logging.getLogger(__name__)

        remote_name = path_str.split(":")[0]
        logger.debug(f"Parsing config for remote: '{remote_name}'")

        # Default to rclone.conf in current directory
        config_file = rclone_config or Path("rclone.conf")
        logger.debug(f"Config file: {config_file}")

        if not config_file.exists():
            logger.warning(f"Config file not found: {config_file}")
            return {}

        try:
            config = configparser.ConfigParser()
            config.read(config_file)
            logger.debug(f"Config sections found: {config.sections()}")

            if remote_name not in config.sections():
                logger.error(f"Remote '{remote_name}' not found in config sections")
                raise ValueError(f"Remote '{remote_name}' not found in rclone config")

            remote_config = config[remote_name]
            remote_type = remote_config.get("type")
            logger.info(f"Remote type detected: {remote_type}")

            if remote_type == "b2":
                # Convert B2 config to S3-compatible format for fsspec
                logger.debug("Converting B2 config to S3-compatible format")
                storage_options = {
                    "key": remote_config.get("account"),  # B2 Application Key ID
                    "secret": remote_config.get("key"),  # B2 Application Key
                    "endpoint_url": _DEFAULT_BACKBLAZE_ENDPOINT,
                    "client_kwargs": {"region_name": "us-west-002"},
                }
                key_id = storage_options["key"]
                key_preview = f"{key_id[:8]}..." if key_id else "None"
                logger.debug(
                    f"B2 credentials configured: key_id='{key_preview}', endpoint={storage_options['endpoint_url']}"
                )
                return storage_options
            elif remote_type == "s3":
                # Direct S3 config
                logger.debug("Using direct S3 configuration")
                storage_options = {
                    "key": remote_config.get("access_key_id"),
                    "secret": remote_config.get("secret_access_key"),
                    "endpoint_url": remote_config.get("endpoint"),
                }
                key_id = storage_options["key"]
                key_preview = f"{key_id[:8]}..." if key_id else "None"
                logger.debug(
                    f"S3 credentials configured: key_id='{key_preview}', endpoint={storage_options.get('endpoint_url', 'default')}"
                )
                return storage_options
            else:
                # For other types, return empty dict (may need extension)
                logger.warning(
                    f"Unsupported remote type '{remote_type}', returning empty config"
                )
                return {}

        except Exception as e:
            logger.error(f"Config parsing failed: {e}")
            raise ValueError(f"Failed to parse rclone config for '{remote_name}': {e}")

    @staticmethod
    def _convert_rclone_to_uri(path_str: str) -> str:
        """
        Convert rclone format 'remote:path' to URI format 'protocol://path'.

        Args:
            path_str: rclone path like "dst:TorrentBooks/file.pdf"

        Returns:
            str: URI format like "s3://TorrentBooks/file.pdf"
        """
        if ":" not in path_str:
            return path_str

        remote_name, path_part = path_str.split(":", 1)

        # For now, assume all remote paths are S3-compatible
        # This could be enhanced to read the remote type from config
        return f"s3://{path_part}"
