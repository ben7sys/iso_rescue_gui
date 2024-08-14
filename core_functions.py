import os
import sys
import shutil
import subprocess
from config import SUDO_ERROR, MOUNT_PATH

def check_sudo():
    """Check if the script is run with sudo privileges and get the original user.
    The function checks if the effective user ID is 0 (root) and retrieves the original 
    user who ran sudo using environment variables."""
    if os.geteuid() != 0:
        print(SUDO_ERROR)
        sys.exit(1)
    return os.environ.get('SUDO_USER') or os.environ.get('USER')

def check_tool_installed(tool_name):
    """Check if a tool is installed on the system.
    This function uses shutil.which() to check if the specified tool is available in the system's PATH."""
    return shutil.which(tool_name) is not None

def check_writable_directory(path):
    """Check if the directory is writable.
    This function ensures the directory exists and is writable by attempting to create it if it doesn't exist 
    and then checking write permissions."""
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except (PermissionError, OSError) as e:
            return False
    return os.access(directory, os.W_OK)

def get_device_size(device):
    """Get the size of the DVD device in MB.
    This function retrieves the size of the given device using the 'blockdev' command
    and converts the size from bytes to megabytes (MB) for easier handling."""
    try:
        result = subprocess.run(['blockdev', '--getsize64', device], capture_output=True, text=True, check=True)
        size_bytes = int(result.stdout.strip())
        return size_bytes // (1024 * 1024)  # Convert to MB
    except Exception:
        return None

def try_mount_iso(iso_path):
    """Attempt to mount the ISO to verify its integrity.
    This function mounts the ISO to a temporary mount point and then unmounts it to check 
    if the ISO file is valid and not corrupted."""
    try:
        subprocess.run(['sudo', 'mount', '-o', 'loop', iso_path, MOUNT_PATH], check=True)
        subprocess.run(['sudo', 'umount', MOUNT_PATH], check=True)
        return True
    except subprocess.CalledProcessError:
        return False
