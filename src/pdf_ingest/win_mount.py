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
        result = subprocess.run(cmd_list, capture_output=True, text=True, check=True)
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return False


if __name__ == "__main__":
    if IS_WINDOWS:
        if windows_has_mount():
            print("Windows mount.exe is available.")
        else:
            print("Windows mount.exe is not available.")
    else:
        print("This script is intended for Windows only.")
