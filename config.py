import os
import tkinter as tk

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
SUDO_ERROR = "Dieses Script muss mit Root-Rechten ausgeführt werden. Bitte starten Sie es mit 'sudo'."
NO_DVD_DEVICE = "Kein DVD-Laufwerk erkannt. Bitte überprüfen Sie Ihre Hardware."
DDRESCUE_NOT_INSTALLED = "ddrescue ist nicht auf diesem System installiert. Bitte installieren Sie es und versuchen Sie es erneut."
DVDISASTER_NOT_INSTALLED = "dvdisaster ist nicht installiert. Einige Wiederherstellungsoptionen sind deaktiviert."

# Success messages
ISO_CREATION_SUCCESS = "ISO-Image erfolgreich erstellt unter {}"
EJECT_PROMPT = "ISO erfolgreich erstellt. Möchten Sie die DVD auswerfen?"

# Command templates
DDRESCUE_COMMAND_TEMPLATE = "sudo /usr/bin/ddrescue {options} {device} {iso_path} {mapfile}"
DD_COMMAND_TEMPLATE = "sudo dd if={device} of={iso_path} bs={bs_size} status=progress"

# GUI Options
n_option_var = tk.BooleanVar()
r3_option_var = tk.BooleanVar()
b_option_var = tk.BooleanVar(value=True)
d_option_var = tk.BooleanVar(value=True)
c_option_var = tk.BooleanVar(value=False)
