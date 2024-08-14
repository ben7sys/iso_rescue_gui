import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk, font
import threading

from config import *
from core_functions import check_sudo, check_tool_installed
from device_detection import detect_dvd_devices
from gui_utils import disable_gui_elements, reset_gui_state, apply_preset
from iso_creation import create_iso, stop_process

# Get the original user who ran sudo
original_user = check_sudo()

# Initialize the main application window
app = tk.Tk()
app.title("ISO Rescue GUI")

frame = tk.Frame(app)
frame.pack(pady=10, padx=10)

label = tk.Label(frame, text="ISO-Image von einer CD/DVD erstellen")
label.pack(pady=10)

dvd_device_var = tk.StringVar(value="No DVD device found")
dvd_devices = detect_dvd_devices()
dvd_device_label = tk.Label(frame, text="DVD-Laufwerk auswählen:")
dvd_device_label.pack(anchor=tk.W)

dvd_device_combobox = ttk.Combobox(frame, textvariable=dvd_device_var, values=dvd_devices, state='readonly')
dvd_device_combobox.pack(anchor=tk.W)
dvd_device_combobox.current(0)

method_var = tk.StringVar(value="ddrescue")
method_label = tk.Label(frame, text="Methode für ISO-Erstellung auswählen:")
method_label.pack(anchor=tk.W)

method_combobox = ttk.Combobox(frame, textvariable=method_var, values=["dd", "ddrescue"], state='readonly')
method_combobox.pack(anchor=tk.W)

# Options for ddrescue
options_frame = tk.LabelFrame(frame, text="ddrescue Optionen")
options_frame.pack(anchor=tk.W, fill="x", pady=5)

n_option_var = tk.BooleanVar()
n_option_checkbox = tk.Checkbutton(options_frame, text="Fehlerkorrektur-Durchgang überspringen (-n)", variable=n_option_var)
n_option_checkbox.pack(anchor=tk.W)

r3_option_var = tk.BooleanVar()
r3_option_checkbox = tk.Checkbutton(options_frame, text="Fehlerhafte Sektoren 3 Mal wiederholen (-r3)", variable=r3_option_var)
r3_option_checkbox.pack(anchor=tk.W)

b_option_var = tk.BooleanVar(value=True)
b_option_checkbox = tk.Checkbutton(options_frame, text="Blockgröße auf 2048 Bytes setzen (-b 2048)", variable=b_option_var)
b_option_checkbox.pack(anchor=tk.W)

d_option_var = tk.BooleanVar(value=True)
d_option_checkbox = tk.Checkbutton(options_frame, text="Direkten Zugriffsmodus verwenden (-d)", variable=d_option_var)
d_option_checkbox.pack(anchor=tk.W)

# Add presets
presets_frame = tk.LabelFrame(frame, text="Voreinstellungen")
presets_frame.pack(anchor=tk.W, fill="x", pady=5)

intact_button = tk.Button(presets_frame, text="Intakte DVD", command=lambda: apply_preset("intact", method_var, n_option_var, r3_option_var, b_option_var, d_option_var))
intact_button.pack(side=tk.LEFT, padx=5)

damaged_button = tk.Button(presets_frame, text="Beschädigte DVD", command=lambda: apply_preset("damaged", method_var, n_option_var, r3_option_var, b_option_var, d_option_var))
damaged_button.pack(side=tk.LEFT, padx=5)

irrecoverable_button = tk.Button(presets_frame, text="Irreparable DVD", command=lambda: apply_preset("irrecoverable", method_var, n_option_var, r3_option_var, b_option_var, d_option_var))
irrecoverable_button.pack(side=tk.LEFT, padx=5)

# Set default output path to the original user's home directory
default_output_path = os.path.expanduser(f"~{original_user}/ddrescue.iso")
output_path_var = tk.StringVar(value=default_output_path)
output_path_label = tk.Label(frame, text="Ausgabepfad für ISO-Datei:")
output_path_label.pack(anchor=tk.W)

output_path_entry = tk.Entry(frame, textvariable=output_path_var, width=50)
output_path_entry.pack(anchor=tk.W)

select_output_button = tk.Button(frame, text="Durchsuchen...", command=lambda: output_path_var.set(filedialog.asksaveasfilename(defaultextension=".iso", filetypes=[("ISO files", "*.iso")])))
select_output_button.pack(anchor=tk.W, pady=5)

# Create a frame for buttons
button_frame = tk.Frame(frame)
button_frame.pack(fill=tk.X, pady=5)

create_iso_button = tk.Button(button_frame, text="ISO erstellen", command=lambda: create_iso(dvd_device_var, output_path_var, method_var, n_option_var, r3_option_var, b_option_var, d_option_var, log_text, app))
create_iso_button.pack(side=tk.LEFT, padx=(0, 5))

stop_button = tk.Button(button_frame, text="Stop", command=stop_process, state=tk.DISABLED)
stop_button.pack(side=tk.LEFT)

log_frame = tk.Frame(app)
log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Set a monospaced font for the log output
log_font = font.Font(family="Courier", size=10)
log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, font=log_font)
log_text.pack(fill=tk.BOTH, expand=True)

# Disable dvdisaster options if not installed
if not check_tool_installed("dvdisaster"):
    d_option_checkbox.config(state=tk.DISABLED)
    messagebox.showwarning("dvdisaster nicht installiert", "dvdisaster ist nicht installiert. Einige Wiederherstellungsoptionen sind deaktiviert.")

app.mainloop()