import os
from config import DEFAULT_DVD_DEVICES
from core_functions import get_device_size

def detect_dvd_devices():
    """Automatically detect available DVD drives."""
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