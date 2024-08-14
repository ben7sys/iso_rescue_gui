import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk, font
import subprocess
import shutil
import sys
import signal
import threading
from datetime import datetime
import tempfile
import logging

"""
This script provides a graphical user interface for creating ISO images from various optical media types.
It supports Data CD/DVD, Audio CD, and Video/Music DVD formats, offering different extraction methods for each.
The script includes functionality for detecting media types, checking for installed tools, and managing the extraction process.
"""

# Global variables
process = None
stop_event = threading.Event()

def check_sudo():
    """Check if the script is run with sudo privileges and get the original user."""
    if os.geteuid() != 0:
        messagebox.showerror("Error", "This script must be run with root privileges. Please start it with 'sudo'.")
        sys.exit(1)
    return os.environ.get('SUDO_USER') or os.environ.get('USER')

def check_tool_installed(tool_name):
    """Check if a tool is installed on the system."""
    return shutil.which(tool_name) is not None

def select_output():
    """Open a file dialog for selecting the output path or directory."""
    if use_custom_filename_var.get():
        output_path = filedialog.asksaveasfilename(defaultextension=".iso", filetypes=[("ISO files", "*.iso")])
    else:
        output_path = filedialog.askdirectory()
    
    if output_path:
        output_path_var.set(output_path)

# Generate a filename based on the current date and time
# Format: YYYYMMDDHHMMSS_ddrescue.iso
def generate_filename():
    now = datetime.now()
    return now.strftime("%Y%m%d%H%M%S_ddrescue.iso")

# Detect media type using blkid and additional checks
def detect_media_type(device):
    try:
        result = subprocess.run(['blkid', '-p', '-o', 'value', '-s', 'TYPE', device], 
                                capture_output=True, text=True, check=True)
        media_type = result.stdout.strip()
        
        if media_type == "udf":
            return "Data CD/DVD"
        elif media_type == "iso9660":
            # Check for audio CD regardless of /dev/cdrom existence
            audio_check = subprocess.run(['cdparanoia', '-d', device, '-Q'], 
                                         capture_output=True, text=True)
            if "audio tracks" in audio_check.stderr:
                return "Audio CD"
            return "Data CD/DVD"
        else:
            # Check for Video DVD
            video_check = subprocess.run(['dvdbackup', '--info', '-i', device], 
                                         capture_output=True, text=True)
            if "DVD-Video information" in video_check.stdout:
                return "Video/Music DVD"
            return "Unknown"
    except subprocess.CalledProcessError:
        return "Unknown"
    
def detect_dvd_devices():
    """Automatically detect available DVD drives."""
    dvd_devices = []
    for device in ["/dev/sr0", "/dev/sr1", "/dev/cdrom", "/dev/dvd"]:
        if os.path.exists(device):
            size = get_device_size(device)
            if size:
                dvd_devices.append(f"{device} ({size} MB)")
            else:
                dvd_devices.append(device)
    return dvd_devices or ["No DVD device found"]

def get_device_size(device):
    """Get the size of the DVD device in MB."""
    try:
        result = subprocess.run(['blockdev', '--getsize64', device], capture_output=True, text=True, check=True)
        size_bytes = int(result.stdout.strip())
        return size_bytes // (1024 * 1024)  # Convert to MB
    except Exception:
        return None
    
def get_output_path():
    """Get the full output path based on user selection."""
    base_path = output_path_var.get()
    if use_custom_filename_var.get():
        return base_path
    else:
        return os.path.join(base_path, generate_filename())
    
def prompt_insert_disc():
    """Prompt the user to insert a disc and retry."""
    return messagebox.askretrycancel("No media detected", "No media detected in the drive. Please insert a disc and try again.")

def create_iso():
    logging.debug("create_iso called")
    global process, stop_event
    stop_event.clear()
    
    output_path = get_output_path()
    output_directory = os.path.dirname(output_path)

    if not output_directory:
        messagebox.showerror("Error", "Please specify an output directory.")
        return

    if not os.path.isdir(output_directory):
        try:
            os.makedirs(output_directory)
        except OSError:
            messagebox.showerror("Error", "Failed to create output directory.")
            return

    if not check_writable_directory(output_directory):
        messagebox.showerror("Error", "The target directory is not writable. Please choose a different directory.")
        return

    if os.path.exists(output_path) and not c_option_var.get():
        if not messagebox.askyesno("File exists", f"The file {output_path} already exists. Do you want to overwrite it?"):
            return

    dvd_device = dvd_device_var.get().split()[0]  # Extract device name
    if dvd_device == "No DVD device found":
        messagebox.showerror("Error", "No DVD drive detected. Please check your hardware.")
        return

    # Check if media is present in the drive
    while not check_media_present(dvd_device):
        if not prompt_insert_disc():
            return

    media_type = detect_media_type(dvd_device)
    media_type_var.set(media_type)  # Update the GUI to reflect the detected media type
    update_gui_for_media_type()

    # Prepare command based on media type
    command = prepare_command(media_type, dvd_device, output_path)
    if command is None:
        return  # Error occurred in command preparation

    # Check for sufficient free space (assuming 8GB as max size for DVD)
    if not check_free_space(output_directory, 8 * 1024 * 1024 * 1024):
        messagebox.showerror("Error", "Insufficient free space in the output directory.")
        return

    handle_mapfile(output_path)  # Handle mapfile before starting the process

    disable_gui_elements()
    stop_button.config(state=tk.NORMAL, bg='red')

    log_text.delete(1.0, tk.END)  # Clear log before starting a new operation
    log_text.insert(tk.END, f"Executing command: {command}\n")

    app.after(0, disable_gui_elements)
    app.after(0, lambda: stop_button.config(state=tk.NORMAL, bg='red'))
    app.after(0, lambda: log_text.delete(1.0, tk.END))
    app.after(0, lambda: log_text.insert(tk.END, f"Executing command: {command}\n"))

    threading.Thread(target=run_command, args=(command, output_path, media_type, dvd_device), daemon=True).start()
    
def check_media_present(device):
    try:
        subprocess.run(['dd', 'if=' + device, 'of=/dev/null', 'count=1'], 
                       check=True, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

# Prepare command based on media type and selected options
def prepare_command(media_type, dvd_device, output_path):
    if media_type == "Data CD/DVD":
        return prepare_data_cd_dvd_command(dvd_device, output_path)
    elif media_type == "Audio CD":
        return prepare_audio_cd_command(dvd_device, output_path)
    elif media_type == "Video/Music DVD":
        return prepare_video_music_dvd_command(dvd_device, output_path)
    else:
        messagebox.showerror("Error", f"Unsupported media type: {media_type}")
        return None

def prepare_data_cd_dvd_command(dvd_device, output_path):
    method = method_var.get()
    if method == "ddrescue":
        if not check_tool_installed("ddrescue"):
            messagebox.showerror("Error", "ddrescue is not installed. Please install it and try again.")
            return None
        
        ddrescue_options = ['--force']
        if n_option_var.get():
            ddrescue_options.append("-n")
        if r3_option_var.get():
            ddrescue_options.append("-r3")
        if b_option_var.get():
            ddrescue_options.append("-b 2048")
        if d_option_var.get():
            ddrescue_options.append("-d")
        if c_option_var.get():
            ddrescue_options.append("-C")
        
        mapfile = f"{output_path}.map"
        return f"sudo ddrescue {' '.join(ddrescue_options)} {dvd_device} {output_path} {mapfile}"
    else:  # dd method
        return f"sudo dd if={dvd_device} of={output_path} bs=1M status=progress"

def prepare_audio_cd_command(dvd_device, output_path):
    """Prepare command for Audio CD extraction."""
    if not check_tool_installed("cdparanoia"):
        messagebox.showerror("Error", "cdparanoia is not installed. Please install it and try again.")
        return None
    return f"cdparanoia -B -d {dvd_device} -D 0 -Z {output_path}/track"

def prepare_video_music_dvd_command(dvd_device, output_path):
    """Prepare command for Video/Music DVD extraction."""
    if not check_tool_installed("dvdbackup"):
        messagebox.showerror("Error", "dvdbackup is not installed. Please install it and try again.")
        return None
    return f"dvdbackup -i {dvd_device} -o {output_path} -M"

def handle_mapfile(output_path):
    mapfile = f"{output_path}.map"
    if not c_option_var.get() and os.path.exists(mapfile):
        try:
            os.remove(mapfile)
            log_text.insert(tk.END, f"Existing mapfile removed: {mapfile}\n")
        except OSError as e:
            log_text.insert(tk.END, f"Error removing mapfile: {e}\n")

def run_command(command, output_path, media_type, dvd_device):
    """Execute the command and handle its output."""
    global process
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, preexec_fn=os.setsid)
        
        def read_output():
            output = process.stdout.readline()
            if output:
                app.after(0, lambda o=output: log_text.insert(tk.END, o))
                app.after(0, lambda: log_text.see(tk.END))
            if process.poll() is None:
                app.after(100, read_output)
            else:
                handle_process_completion()

        app.after(0, read_output)

    except Exception as e:
        app.after(0, lambda: log_text.insert(tk.END, f"Unexpected error: {e}\n"))
        app.after(0, lambda: messagebox.showerror("Error", "An unexpected error occurred. See log for details."))
    finally:
        app.after(0, reset_gui_state)

def handle_process_completion():
    if stop_event.is_set():
        app.after(0, lambda: log_text.insert(tk.END, "Process stopped.\n"))
    else:
        stderr_output = process.stderr.read().strip()
        if stderr_output:
            app.after(0, lambda s=stderr_output: log_text.insert(tk.END, f"Error output: {s}\n"))
        
        if process.returncode == 0:
            app.after(0, lambda: handle_successful_extraction(media_type, output_path, dvd_device))
        else:
            app.after(0, lambda: handle_command_error(subprocess.CalledProcessError(process.returncode, command)))      

def handle_command_error(error):
    """Handle specific command errors."""
    if "Input/output error" in str(error):
        log_text.insert(tk.END, "Error reading from the disc. The disc may be damaged or dirty.\n")
    elif "No medium found" in str(error):
        log_text.insert(tk.END, "No disc found in the drive. Please insert a disc and try again.\n")
    else:
        log_text.insert(tk.END, f"Command failed with error: {error}\n")
    messagebox.showerror("Error", f"Creation of ISO image or media extraction failed. See log for details.")

def check_free_space(directory, required_space):
    """Check if there's enough free space in the directory."""
    total, used, free = shutil.disk_usage(directory)
    return free > required_space

def handle_successful_extraction(media_type, output_path, dvd_device):
    """Handle successful extraction based on media type."""
    if media_type == "Data CD/DVD":
        if os.path.getsize(output_path) > 0:
            messagebox.showinfo("Success", f"ISO image successfully created at {output_path}")
        else:
            messagebox.showerror("Error", "The ISO file is 0 bytes. Please check the disc and try again.")
    elif media_type == "Audio CD":
        track_dir = os.path.dirname(output_path)
        if any(file.startswith("track") for file in os.listdir(track_dir)):
            messagebox.showinfo("Success", f"Audio tracks extracted to {track_dir}")
        else:
            messagebox.showerror("Error", "No audio tracks were extracted. Please check the disc and try again.")
    elif media_type == "Video/Music DVD":
        if os.path.isdir(output_path) and len(os.listdir(output_path)) > 0:
            messagebox.showinfo("Success", f"DVD content backed up to {output_path}")
        else:
            messagebox.showerror("Error", "No DVD content was backed up. Please check the disc and try again.")
    
    if messagebox.askyesno("Media extracted", "Media successfully extracted. Do you want to eject the disc?"):
        subprocess.run(["eject", dvd_device])

def check_writable_directory(path):
    """Check if the directory is writable."""
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except PermissionError:
            return False
    return os.access(directory, os.W_OK)

# Attempt to mount the ISO to verify its integrity
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
    """Attempt to recover or analyze the ISO file."""
    if check_tool_installed("dvdisaster"):
        recovery_command = f"dvdisaster -r -i {iso_path} -o {iso_path.replace('.iso', '-recovered.iso')}"
    else:
        messagebox.showwarning("dvdisaster not installed", "dvdisaster is not installed. Attempting recovery with iso-read instead.")
        recovery_command = f"iso-read -i {iso_path} -o {iso_path.replace('.iso', '-recovered.iso')}"
    
    try:
        log_text.insert(tk.END, f"Attempting ISO recovery with command: {recovery_command}\n")
        subprocess.run(recovery_command, shell=True, check=True)
        messagebox.showinfo("Recovery", "ISO recovery completed. Please check the recovered ISO.")
    except subprocess.CalledProcessError as e:
        log_text.insert(tk.END, f"ISO recovery failed with error: {e}\n")
        messagebox.showerror("Error", "ISO recovery failed. See log for details.")

def stop_process():
    logging.debug("stop_process called")
    global process, stop_event
    if process:
        stop_event.set()
        app.after(0, lambda: os.killpg(os.getpgid(process.pid), signal.SIGTERM))
        process = None
    app.after(0, reset_gui_state)
    
def disable_gui_elements():
    """Disable GUI elements during processing."""
    for widget in [dvd_device_combobox, media_type_combobox, method_combobox, 
                   n_option_checkbox, r3_option_checkbox, b_option_checkbox, 
                   d_option_checkbox, c_option_checkbox, output_path_entry, 
                   select_output_button, intact_button, damaged_button, 
                   irrecoverable_button, create_iso_button]:
        widget.config(state=tk.DISABLED)

def reset_gui_state():
    """Reset GUI state after processing."""
    global process
    process = None
    stop_button.config(state=tk.DISABLED, bg='light gray')
    create_iso_button.config(state=tk.NORMAL)
    dvd_device_combobox.config(state='readonly')
    media_type_combobox.config(state='readonly')
    method_combobox.config(state='readonly')
    for widget in [n_option_checkbox, r3_option_checkbox, b_option_checkbox, 
                   d_option_checkbox, c_option_checkbox, output_path_entry, 
                   select_output_button, intact_button, damaged_button, 
                   irrecoverable_button]:
        widget.config(state=tk.NORMAL)
    update_gui_for_media_type()
    app.update_idletasks()

# Apply preset configurations for different DVD conditions
def apply_preset(preset):
    presets = {
        "intact": {"method": "dd", "n": False, "r3": False, "b": True, "d": True},
        "damaged": {"method": "ddrescue", "n": False, "r3": True, "b": True, "d": True},
        "irrecoverable": {"method": "ddrescue", "n": True, "r3": True, "b": True, "d": True}
    }
    if preset in presets:
        method_var.set(presets[preset]["method"])
        n_option_var.set(presets[preset]["n"])
        r3_option_var.set(presets[preset]["r3"])
        b_option_var.set(presets[preset]["b"])
        d_option_var.set(presets[preset]["d"])

def update_gui_for_media_type(*args):
    """Update GUI elements based on selected media type and method."""
    media_type = media_type_var.get()
    method = method_var.get()
    
    if media_type == "Data CD/DVD":
        method_combobox.config(state='readonly')
        options_frame.pack(anchor=tk.W, fill="x", pady=5)
        
        # Show or hide ddrescue options based on the selected method
        if method == "ddrescue":
            for widget in [n_option_checkbox, r3_option_checkbox, b_option_checkbox, 
                           d_option_checkbox, c_option_checkbox]:
                widget.pack(anchor=tk.W)
        else:
            for widget in [n_option_checkbox, r3_option_checkbox, b_option_checkbox, 
                           d_option_checkbox, c_option_checkbox]:
                widget.pack_forget()
    elif media_type in ["Audio CD", "Video/Music DVD"]:
        method_var.set("cdparanoia" if media_type == "Audio CD" else "dvdbackup")
        method_combobox.config(state='disabled')
        options_frame.pack_forget()
    
    # Update the media type combobox
    media_type_combobox.set(media_type)

original_user = check_sudo()

# Initialize the main application window
app = tk.Tk()
app.title("Extended ISO Rescue GUI")

# Initialize GUI variables
use_custom_filename_var = tk.BooleanVar(value=False)
dvd_device_var = tk.StringVar(value="No DVD device found")
output_path_var = tk.StringVar(value=os.path.expanduser(f"~{original_user}"))
media_type_var = tk.StringVar(value="Data CD/DVD")
method_var = tk.StringVar(value="ddrescue")
n_option_var = tk.BooleanVar()
r3_option_var = tk.BooleanVar()
b_option_var = tk.BooleanVar(value=True)
d_option_var = tk.BooleanVar(value=True)
c_option_var = tk.BooleanVar(value=False)

frame = tk.Frame(app)
frame.pack(pady=10, padx=10)

# Media type selection
media_type_label = tk.Label(frame, text="Select Media Type:")
media_type_label.pack(anchor=tk.W)

media_type_combobox = ttk.Combobox(frame, textvariable=media_type_var, 
                                   values=["Data CD/DVD", "Audio CD", "Video/Music DVD"], 
                                   state='readonly')
media_type_combobox.pack(anchor=tk.W)
media_type_combobox.bind("<<ComboboxSelected>>", lambda _: update_gui_for_media_type())

label = tk.Label(frame, text="Create ISO image from CD/DVD")
label.pack(pady=10)

dvd_devices = detect_dvd_devices()
dvd_device_label = tk.Label(frame, text="Select DVD drive:")
dvd_device_label.pack(anchor=tk.W)

dvd_device_combobox = ttk.Combobox(frame, textvariable=dvd_device_var, values=dvd_devices, state='readonly')
dvd_device_combobox.pack(anchor=tk.W)
dvd_device_combobox.current(0)

method_label = tk.Label(frame, text="Select method for ISO creation:")
method_label.pack(anchor=tk.W)

method_combobox = ttk.Combobox(frame, textvariable=method_var, values=["dd", "ddrescue"], state='readonly')
method_combobox.pack(anchor=tk.W)

# Options for ddrescue
options_frame = tk.LabelFrame(frame, text="ddrescue Options")
options_frame.pack(anchor=tk.W, fill="x", pady=5)

n_option_checkbox = tk.Checkbutton(options_frame, text="Skip error correction pass (-n)", variable=n_option_var)
n_option_checkbox.pack(anchor=tk.W)

r3_option_checkbox = tk.Checkbutton(options_frame, text="Retry bad sectors 3 times (-r3)", variable=r3_option_var)
r3_option_checkbox.pack(anchor=tk.W)

b_option_checkbox = tk.Checkbutton(options_frame, text="Set block size to 2048 bytes (-b 2048)", variable=b_option_var)
b_option_checkbox.pack(anchor=tk.W)

d_option_checkbox = tk.Checkbutton(options_frame, text="Use direct access mode (-d)", variable=d_option_var)
d_option_checkbox.pack(anchor=tk.W)

c_option_checkbox = tk.Checkbutton(options_frame, text="Reading from partial copy (-C)", variable=c_option_var)
c_option_checkbox.pack(anchor=tk.W)

# Add presets
presets_frame = tk.LabelFrame(frame, text="Presets")
presets_frame.pack(anchor=tk.W, fill="x", pady=5)

intact_button = tk.Button(presets_frame, text="Intact DVD", command=lambda: apply_preset("intact"))
intact_button.pack(side=tk.LEFT, padx=5)

damaged_button = tk.Button(presets_frame, text="Damaged DVD", command=lambda: apply_preset("damaged"))
damaged_button.pack(side=tk.LEFT, padx=5)

irrecoverable_button = tk.Button(presets_frame, text="Irrecoverable DVD", command=lambda: apply_preset("irrecoverable"))
irrecoverable_button.pack(side=tk.LEFT, padx=5)

# Output selection
output_frame = tk.LabelFrame(frame, text="Output Settings")
output_frame.pack(anchor=tk.W, fill="x", pady=5)

use_custom_filename_checkbox = tk.Checkbutton(output_frame, text="Use custom filename", variable=use_custom_filename_var, command=lambda: select_output_button.config(text="Browse for file..." if use_custom_filename_var.get() else "Browse for directory..."))
use_custom_filename_checkbox.pack(anchor=tk.W)

output_path_label = tk.Label(output_frame, text="Output path:")
output_path_label.pack(anchor=tk.W)

output_path_entry = tk.Entry(output_frame, textvariable=output_path_var, width=50)
output_path_entry.pack(anchor=tk.W)

select_output_button = tk.Button(output_frame, text="Browse for directory...", command=select_output)
select_output_button.pack(anchor=tk.W, pady=5)

# Create a frame for buttons
button_frame = tk.Frame(frame)
button_frame.pack(fill=tk.X, pady=5)

create_iso_button = tk.Button(button_frame, text="Create ISO", command=create_iso)
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
    messagebox.showwarning("dvdisaster not installed", "dvdisaster is not installed. Some recovery options are disabled.")

# Update GUI for initial media type
update_gui_for_media_type()

app.mainloop()
