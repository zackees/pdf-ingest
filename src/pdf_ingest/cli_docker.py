# # Docker
#   * Install
#     * docker pull niteris/transcribe-everything

#   * Help
#     * docker run --rm -it niteris/transcribe-everything --help

#   * Running
#     * Windows cmd.exe: `docker run --rm -it -v "%cd%\rclone.conf:/app/rclone.conf" niteris/transcribe-everything dst:TorrentBooks/podcast/dialogueworks01/youtube`
#     * Macos/Linux: `docker run --rm -it -v "$(pwd)/rclone.conf:/app/rclone.conf" niteris/transcribe-everything dst:TorrentBooks/podcast/dialogueworks01/youtube`

import subprocess
import sys
from pathlib import Path


def _to_volume_path(rclone_config_path: Path) -> str:
    """Convert a Path to a volume path for Docker."""
    abs_path = rclone_config_path.resolve()
    return f"{abs_path}:/app/rclone.conf"


def main() -> int:
    """Main entry point for the template_python_cmd package."""

    # switch to the directory of the rclone.conf file
    # os.chdir(args.rclone_conf.parent)
    # Here you would call your main function, e.g.:
    # err_count = run(args)
    # return 0 if not err_count else 1
    cmd_pull = "docker pull niteris/pdf-ingest"
    cmd_list_run: list[str] = [
        "docker",
        "run",
        "--rm",
    ]
    if sys.stdout.isatty():
        cmd_list_run.append("-t")

    cmd_list_run += [
        "niteris/pdf-ingest",
    ]
    cmd_run = subprocess.list2cmdline(cmd_list_run)
    print(f"Running command: {cmd_pull}")
    rtn = subprocess.call(cmd_pull, shell=True)
    if rtn != 0:
        print(f"Failed to pull docker image: {rtn}")
        return 1
    print(f"Running command: {cmd_run}")
    rtn = subprocess.call(cmd_run, shell=True)
    return rtn


if __name__ == "__main__":
    import sys

    src = "dst:TorrentBooks/podcast/dialogueworks01/youtube"
    sys.argv.append(src)
    # sys.argv.append("--batch-size")
    # sys.argv.append("20")
    # sys.exit(main())
    main()
