import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk, font
import threading

from config import *
from core_functions import check_sudo, check_tool_installed
from device_detection import detect_dvd_devices
from gui_utils import disable_gui_elements, reset_gui_state, apply_preset, update_gui_for_media_type, update_progress, update_log
from iso_creation import create_iso, stop_process
from media_detection import detect_media_type
from iso_utils import try_mount_iso, attempt_iso_recovery

# Get the original user who ran sudo
original_user = check_sudo()

# Initialize the main application window
app = tk.Tk()
app.title("ISO Rescue GUI")

# Define the tk.BooleanVar() variables after the root window is created
n_option_var = tk.BooleanVar()
r3_option_var = tk.BooleanVar()
b_option_var = tk.BooleanVar(value=True)
d_option_var = tk.BooleanVar(value=True)
c_option_var = tk.BooleanVar(value=False)

frame = tk.Frame(app)
frame.pack(pady=10, padx=10)

label = tk.Label(frame, text="Create ISO Image from a CD/DVD")
label.pack(pady=10)

dvd_device_var = tk.StringVar(value="No DVD device found")
dvd_devices = detect_dvd_devices()
dvd_device_label = tk.Label(frame, text="Select DVD Drive:")
dvd_device_label.pack(anchor=tk.W)

dvd_device_combobox = ttk.Combobox(frame, textvariable=dvd_device_var, values=dvd_devices, state='readonly')
dvd_device_combobox.pack(anchor=tk.W)
dvd_device_combobox.current(0)

method_var = tk.StringVar(value="ddrescue")
method_label = tk.Label(frame, text="Select Method for ISO Creation:")
method_label.pack(anchor=tk.W)

method_combobox = ttk.Combobox(frame, textvariable=method_var, values=["dd", "ddrescue"], state='readonly')
method_combobox.pack(anchor=tk.W)

# Options for ddrescue
options_frame = tk.LabelFrame(frame, text="ddrescue Options")
options_frame.pack(anchor=tk.W, fill="x", pady=5)

n_option_checkbox = tk.Checkbutton(options_frame, text="Skip Error Correction Pass (-n)", variable=n_option_var)
n_option_checkbox.pack(anchor=tk.W)

r3_option_checkbox = tk.Checkbutton(options_frame, text="Retry Faulty Sectors 3 Times (-r3)", variable=r3_option_var)
r3_option_checkbox.pack(anchor=tk.W)

b_option_checkbox = tk.Checkbutton(options_frame, text="Set Block Size to 2048 Bytes (-b 2048)", variable=b_option_var)
b_option_checkbox.pack(anchor=tk.W)

d_option_checkbox = tk.Checkbutton(options_frame, text="Use Direct Access Mode (-d)", variable=d_option_var)
d_option_checkbox.pack(anchor=tk.W)

c_option_checkbox = tk.Checkbutton(options_frame, text="Reading from partial copy (-C)", variable=c_option_var)
c_option_checkbox.pack(anchor=tk.W)

# Add presets
presets_frame = tk.LabelFrame(frame, text="Presets")
presets_frame.pack(anchor=tk.W, fill="x", pady=5)

intact_button = tk.Button(presets_frame, text="Intact DVD", command=lambda: apply_preset("intact", method_var, n_option_var, r3_option_var, b_option_var, d_option_var))
intact_button.pack(side=tk.LEFT, padx=5)

damaged_button = tk.Button(presets_frame, text="Damaged DVD", command=lambda: apply_preset("damaged", method_var, n_option_var, r3_option_var, b_option_var, d_option_var))
damaged_button.pack(side=tk.LEFT, padx=5)

irrecoverable_button = tk.Button(presets_frame, text="Irrecoverable DVD", command=lambda: apply_preset("irrecoverable", method_var, n_option_var, r3_option_var, b_option_var, d_option_var))
irrecoverable_button.pack(side=tk.LEFT, padx=5)

# Set default output path to the original user's home directory
default_output_path = os.path.expanduser(f"~{original_user}/ddrescue.iso")
output_path_var = tk.StringVar(value=default_output_path)
output_path_label = tk.Label(frame, text="Output Path for ISO File:")
output_path_label.pack(anchor=tk.W)

output_path_entry = tk.Entry(frame, textvariable=output_path_var, width=50)
output_path_entry.pack(anchor=tk.W)

select_output_button = tk.Button(frame, text="Browse...", command=lambda: output_path_var.set(filedialog.asksaveasfilename(defaultextension=".iso", filetypes=[("ISO files", "*.iso")])))
select_output_button.pack(anchor=tk.W, pady=5)

# Create a frame for buttons
button_frame = tk.Frame(frame)
button_frame.pack(fill=tk.X, pady=5)

def start_iso_creation():
    # Run the ISO creation process in a separate thread to avoid freezing the GUI
    threading.Thread(target=create_iso, args=(dvd_device_var, output_path_var, method_var, n_option_var, r3_option_var, b_option_var, d_option_var, c_option_var, log_text, app, stop_button, progress_bar)).start()

create_iso_button = tk.Button(button_frame, text="Create ISO", command=start_iso_creation)
create_iso_button.pack(side=tk.LEFT, padx=(0, 5))

# Define the Stop button
stop_button = tk.Button(button_frame, text="Stop", command=stop_process, state=tk.DISABLED)
stop_button.pack(side=tk.LEFT)

log_frame = tk.Frame(app)
log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Add a progress bar
progress_bar = ttk.Progressbar(log_frame, orient='horizontal', length=300, mode='determinate')
progress_bar.pack(fill=tk.X, pady=(0, 5))

# Set a monospaced font for the log output
log_font = font.Font(family="Courier", size=10)
log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, font=log_font)
log_text.pack(fill=tk.BOTH, expand=True)

# Check if dvdisaster tool is installed and disable certain options if it's not available
if not check_tool_installed("dvdisaster"):
    d_option_checkbox.config(state=tk.DISABLED)
    messagebox.showwarning("dvdisaster not installed", "dvdisaster is not installed. Some recovery options are disabled.")

# Bind the media type update function
dvd_device_combobox.bind("<<ComboboxSelected>>", lambda _: update_gui_for_media_type(dvd_device_var, method_var, options_frame.winfo_children()))

app.mainloop()