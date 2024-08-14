import os

# Global variables
process = None
stop_event = None

# Constants
DEFAULT_DVD_DEVICES = ["/dev/sr0", "/dev/sr1", "/dev/cdrom", "/dev/dvd"]
DDRESCUE_DEFAULT_OPTIONS = ['--force']
DD_BS_SIZE = "1M"

# File paths
MOUNT_PATH = "/mnt/iso"

# GUI-related constants
WINDOW_TITLE = "ISO Rescue GUI"
FONT_FAMILY = "Courier"
FONT_SIZE = 10

# Error messages
SUDO_ERROR = "This script must be run with root privileges. Please start it with 'sudo'."
NO_DVD_DEVICE = "No DVD drive detected. Please check your hardware."
DDRESCUE_NOT_INSTALLED = "ddrescue is not installed on this system. Please install it and try again."
DVDISASTER_NOT_INSTALLED = "dvdisaster is not installed. Some recovery options are disabled."

# Success messages
ISO_CREATION_SUCCESS = "ISO image successfully created at {}"
EJECT_PROMPT = "ISO successfully created. Would you like to eject the DVD?"

# Command templates
DDRESCUE_COMMAND_TEMPLATE = "sudo /usr/bin/ddrescue {options} {device} {iso_path} {mapfile}"
DD_COMMAND_TEMPLATE = "sudo dd if={device} of={iso_path} bs={bs_size} status=progress"