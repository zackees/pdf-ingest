# Get-Command C:\Windows\System32\mount.exe


import platform
import subprocess

IS_WINDOWS = platform.system() == "Windows"


def windows_has_mount() -> bool:
    cmd_list: list[str] = [
        "PowerShell",
        "-Command",
        "Get-Command C:\\Windows\\System32\\mount.exe -ErrorAction SilentlyContinue",
    ]
    try:
        cmd: str = subprocess.list2cmdline(cmd_list)
        print(f"Checking for mount.exe with command: {cmd}")
        result = subprocess.run(cmd_list, capture_output=True, text=True, check=False)
        stdout = result.stdout.strip()
        return len(stdout) == 0
    except subprocess.CalledProcessError as ce:
        print(f"Command failed with error: {ce.stderr.strip()}")
        return False


if __name__ == "__main__":
    if IS_WINDOWS:
        if windows_has_mount():
            print("Windows mount.exe is available.")
        else:
            print("Windows mount.exe is not available.")
    else:
        print("This script is intended for Windows only.")
