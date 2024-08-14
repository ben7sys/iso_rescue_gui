import os
from config import DEFAULT_DVD_DEVICES
from core_functions import get_device_size

def detect_dvd_devices():
    """Automatically detect available DVD drives.
    
    This function checks a predefined list of possible DVD device paths (DEFAULT_DVD_DEVICES).
    For each valid path, it checks if the device exists and attempts to get its size.
    If a size is detected, it appends the device and its size to the list; otherwise,
    it simply appends the device path. If no devices are found, it returns a message indicating
    that no DVD devices were detected."""
    dvd_devices = []
    for device in DEFAULT_DVD_DEVICES:
        if os.path.exists(device):
            size = get_device_size(device)
            if size:
                dvd_devices.append(f"{device} ({size} MB)")
            else:
                dvd_devices.append(device)
    if not dvd_devices:
        dvd_devices.append("No DVD device found")
    return dvd_devices
