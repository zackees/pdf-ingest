import os

import subprocess

# os.system("tools\\WinNFSd.exe -path tests\\nfs_test -id 0 -gid 0")

cmd_list: list[str] = [
    "tools\\WinNFSd.exe",
    r"C:\Users\niteris\dev\pdf-ingest\tests\nfs_test",
    "/exports",
]

cmd: str = subprocess.list2cmdline(cmd_list)
print(f"Running command: {cmd}")
proc = subprocess.Popen(
    cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
)

MOUNT = r"C:\Windows\system32\mount.exe"

# C:\Windows\system32\mount.exe -o anon \\0.0.0.0\exports N:

# mount -o anon \\127.0.0.1\exports N:
cmd = f"{MOUNT} -o anon \\\\127.0.0.1\exports N:"
print(f"Running command: {cmd}")
os.system(cmd)
print("Mounted")
