# Get-Command C:\Windows\System32\mount.exe


import platform
import shutil
import subprocess
import time

IS_WINDOWS = platform.system() == "Windows"


def windows_has_mount() -> bool:
    if not IS_WINDOWS:
        return False
    return shutil.which("mount.exe") is not None


def windows_mount(ip: str, drive: str) -> subprocess.Popen:
    # mount -o anon \\192.168.1.100\share Z:
    if not IS_WINDOWS:
        raise RuntimeError("This function is for Windows only.")
    drive = drive.replace(":", "").upper()
    cmd_list: list[str] = ["mount.exe", "-o", "anon", f"\\\\{ip}\\share", drive + ":"]
    cmd_str = subprocess.list2cmdline(cmd_list)
    print(f"Running command: {cmd_str}")
    process = subprocess.Popen(
        cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    time.sleep(1)
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        print(f"Command output: {stdout}")
        print(f"Command error: {stderr}")
        raise RuntimeError(f"Mount command failed with error: {stderr.strip()}")
    return process


if __name__ == "__main__":
    if IS_WINDOWS:
        if windows_has_mount():
            print("Windows mount.exe is available.")
        else:
            print("Windows mount.exe is not available.")
    else:
        print("This script is intended for Windows only.")
