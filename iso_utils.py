import subprocess
import os
import tempfile

def try_mount_iso(iso_path):
    try:
        # Create a temporary mount point
        with tempfile.TemporaryDirectory() as temp_mount:
            subprocess.run(['sudo', 'mount', '-o', 'loop', iso_path, temp_mount], check=True)
            subprocess.run(['sudo', 'umount', temp_mount], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def attempt_iso_recovery(iso_path):
    if shutil.which("dvdisaster"):
        recovery_command = f"dvdisaster -r -i {iso_path} -o {iso_path.replace('.iso', '-recovered.iso')}"
    else:
        recovery_command = f"iso-read -i {iso_path} -o {iso_path.replace('.iso', '-recovered.iso')}"
    
    try:
        subprocess.run(recovery_command, shell=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False
