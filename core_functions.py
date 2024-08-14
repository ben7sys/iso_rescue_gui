import os
import sys
import shutil
import subprocess
from config import SUDO_ERROR, MOUNT_PATH

def check_sudo():
    """Check if the script is run with sudo privileges and get the original user."""
    if os.geteuid() != 0:
        print(SUDO_ERROR)
        sys.exit(1)
    return os.environ.get('SUDO_USER') or os.environ.get('USER')

def check_tool_installed(tool_name):
    """Check if a tool is installed on the system."""
    return shutil.which(tool_name) is not None

def check_writable_directory(path):
    """Check if the directory is writable."""
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except PermissionError:
            return False
    return os.access(directory, os.W_OK)

def get_device_size(device):
    """Get the size of the DVD device in MB."""
    try:
        result = subprocess.run(['blockdev', '--getsize64', device], capture_output=True, text=True, check=True)
        size_bytes = int(result.stdout.strip())
        return size_bytes // (1024 * 1024)  # Convert to MB
    except Exception:
        return None

def try_mount_iso(iso_path):
    """Attempt to mount the ISO to verify its integrity."""
    try:
        subprocess.run(['sudo', 'mount', '-o', 'loop', iso_path, MOUNT_PATH], check=True)
        subprocess.run(['sudo', 'umount', MOUNT_PATH], check=True)
        return True
    except subprocess.CalledProcessError:
        return False