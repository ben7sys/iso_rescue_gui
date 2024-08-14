import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk, font
import subprocess
import shutil
import sys

def check_sudo():
    """Check if the script is run with sudo privileges."""
    if os.geteuid() != 0:
        messagebox.showerror("Error", "This script must be run as root. Please restart it with 'sudo'.")
        sys.exit(1)

def check_tool_installed(tool_name):
    """Check if a tool is installed on the system."""
    return shutil.which(tool_name) is not None

def select_output_path():
    """Open a file dialog for selecting the output path and update the entry widget."""
    iso_path = filedialog.asksaveasfilename(defaultextension=".iso", filetypes=[("ISO files", "*.iso")])
    if iso_path:
        output_path_var.set(iso_path)

def detect_dvd_devices():
    """Automatically detect available DVD drives, display their sizes, and populate the dropdown."""
    dvd_devices = []
    for device in ["/dev/sr0", "/dev/sr1", "/dev/cdrom", "/dev/dvd"]:
        if os.path.exists(device):
            size = get_device_size(device)
            if size:
                dvd_devices.append(f"{device} ({size} MB)")
            else:
                dvd_devices.append(device)
    if not dvd_devices:
        dvd_devices.append("No DVD device found")
    return dvd_devices

def get_device_size(device):
    """Get the size of the DVD device in MB."""
    try:
        result = subprocess.run(['blockdev', '--getsize64', device], capture_output=True, text=True, check=True)
        size_bytes = int(result.stdout.strip())
        return size_bytes // (1024 * 1024)  # Convert to MB
    except Exception:
        return None

def create_iso():
    """Create an ISO image using the selected method (dd or ddrescue) with selected options."""
    iso_path = output_path_var.get()
    if not iso_path:
        messagebox.showerror("Error", "Please specify an output path for the ISO file.")
        return

    if os.path.exists(iso_path):
        if not messagebox.askyesno("Overwrite Confirmation", f"The file {iso_path} already exists. Overwrite?"):
            return

    dvd_device = dvd_device_var.get().split()[0]  # Extract device name
    if dvd_device == "No DVD device found":
        messagebox.showerror("Error", "No DVD device detected. Please check your hardware.")
        return

    method = method_var.get()
    use_n = n_option_var.get()
    use_r3 = r3_option_var.get()
    use_b = b_option_var.get()
    use_d = d_option_var.get()

    if method == "ddrescue" and not check_tool_installed("ddrescue"):
        messagebox.showerror("Error", "ddrescue is not installed on this system. Please install it and try again.")
        return

    # Build the ddrescue command based on user selections
    ddrescue_options = []
    if use_n:
        ddrescue_options.append("-n")
    if use_r3:
        ddrescue_options.append("-r3")
    if use_b:
        ddrescue_options.append("-b 2048")
    if use_d:
        ddrescue_options.append("-d")
    
    ddrescue_command = f"sudo ddrescue {' '.join(ddrescue_options)} {dvd_device} {iso_path} {iso_path}.log"
    dd_command = f"sudo dd if={dvd_device} of={iso_path} bs=1M status=progress"
    command = ddrescue_command if method == "ddrescue" else dd_command

    try:
        log_text.delete(1.0, tk.END)  # Clear log before starting a new operation
        log_text.insert(tk.END, f"Running command: {command}\n")
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        for line in process.stdout:
            log_text.insert(tk.END, line)
            log_text.see(tk.END)
            app.update_idletasks()

        stderr_output = process.stderr.read().strip()
        if stderr_output:
            log_text.insert(tk.END, f"Error output: {stderr_output}\n")

        process.wait()  # Ensure process completes before checking return code

        if process.returncode == 0:
            # Check if the ISO file has data
            if os.path.getsize(iso_path) > 0:
                messagebox.showinfo("Success", f"ISO image created successfully at {iso_path}")
                # Option to open the directory or eject the DVD
                if messagebox.askyesno("ISO Created", "ISO created successfully. Would you like to eject the DVD?"):
                    subprocess.run(["eject", dvd_device])
            else:
                messagebox.showerror("Error", "The ISO file is 0 bytes. Please check the DVD and try again.")
        else:
            raise subprocess.CalledProcessError(process.returncode, command)

    except subprocess.CalledProcessError as e:
        log_text.insert(tk.END, f"Command failed with error: {e}\n")
        messagebox.showerror("Error", f"Failed to create ISO image. See log for details.")

    except Exception as e:
        log_text.insert(tk.END, f"Unexpected error: {e}\n")
        messagebox.showerror("Error", "An unexpected error occurred. See log for details.")

    # If the ISO is unreadable, attempt to recover or analyze the image
    if method == "ddrescue" and os.path.exists(iso_path) and os.path.getsize(iso_path) > 0:
        if not try_mount_iso(iso_path):
            messagebox.showerror("Error", "The ISO file seems to be corrupted or unreadable. Attempting recovery...")
            attempt_iso_recovery(iso_path)

def try_mount_iso(iso_path):
    """Attempt to mount the ISO to verify its integrity."""
    try:
        subprocess.run(['sudo', 'mount', '-o', 'loop', iso_path, '/mnt/iso'], check=True)
        subprocess.run(['sudo', 'umount', '/mnt/iso'], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def attempt_iso_recovery(iso_path):
    """Attempt to recover or analyze the ISO file."""
    if check_tool_installed("dvdisaster"):
        recovery_command = f"dvdisaster -r -i {iso_path} -o {iso_path.replace('.iso', '-recovered.iso')}"
    else:
        messagebox.showwarning("dvdisaster Not Installed", "dvdisaster is not installed. Attempting recovery with iso-read instead.")
        recovery_command = f"iso-read -i {iso_path} -o {iso_path.replace('.iso', '-recovered.iso')}"
    
    try:
        log_text.insert(tk.END, f"Attempting ISO recovery with command: {recovery_command}\n")
        subprocess.run(recovery_command, shell=True, check=True)
        messagebox.showinfo("Recovery", "ISO recovery completed. Check the recovered ISO.")
    except subprocess.CalledProcessError as e:
        log_text.insert(tk.END, f"ISO recovery failed with error: {e}\n")
        messagebox.showerror("Error", "ISO recovery failed. See log for details.")

# Initialize the main application window
app = tk.Tk()
app.title("ISO Image Creator")

# Check for sudo privileges
check_sudo()

frame = tk.Frame(app)
frame.pack(pady=10, padx=10)

label = tk.Label(frame, text="Create an ISO Image from a CD/DVD")
label.pack(pady=10)

dvd_device_var = tk.StringVar(value="No DVD device found")
dvd_devices = detect_dvd_devices()
dvd_device_label = tk.Label(frame, text="Select DVD Device:")
dvd_device_label.pack(anchor=tk.W)

dvd_device_combobox = ttk.Combobox(frame, textvariable=dvd_device_var, values=dvd_devices)
dvd_device_combobox.pack(anchor=tk.W)
dvd_device_combobox.current(0)

method_var = tk.StringVar(value="ddrescue")
method_label = tk.Label(frame, text="Select Method for ISO Creation:")
method_label.pack(anchor=tk.W)

method_combobox = ttk.Combobox(frame, textvariable=method_var, values=["dd", "ddrescue"])
method_combobox.pack(anchor=tk.W)

# Options for ddrescue
options_frame = tk.LabelFrame(frame, text="ddrescue Options")
options_frame.pack(anchor=tk.W, fill="x", pady=5)

n_option_var = tk.BooleanVar()
n_option_checkbox = tk.Checkbutton(options_frame, text="Skip error correction pass (-n)", variable=n_option_var)
n_option_checkbox.pack(anchor=tk.W)

r3_option_var = tk.BooleanVar()
r3_option_checkbox = tk.Checkbutton(options_frame, text="Retry reading bad sectors 3 times (-r3)", variable=r3_option_var)
r3_option_checkbox.pack(anchor=tk.W)

b_option_var = tk.BooleanVar(value=True)  # Default to True since DVDs typically use 2048 bytes sectors
b_option_checkbox = tk.Checkbutton(options_frame, text="Set block size to 2048 bytes (-b 2048)", variable=b_option_var)
b_option_checkbox.pack(anchor=tk.W)

d_option_var = tk.BooleanVar(value=True)  # Option for using direct mode (-d)
d_option_checkbox = tk.Checkbutton(options_frame, text="Use direct access mode (-d)", variable=d_option_var)
d_option_checkbox.pack(anchor=tk.W)

output_path_var = tk.StringVar(value=os.path.expanduser("/tmp/ddrescue.iso"))
output_path_label = tk.Label(frame, text="Output File Path for ISO:")
output_path_label.pack(anchor=tk.W)

output_path_entry = tk.Entry(frame, textvariable=output_path_var, width=50)
output_path_entry.pack(anchor=tk.W)
output_path_entry.insert(0, "")

select_output_button = tk.Button(frame, text="Browse...", command=select_output_path)
select_output_button.pack(anchor=tk.W, pady=5)

create_iso_button = tk.Button(frame, text="Create ISO", command=create_iso)
create_iso_button.pack(pady=10)

log_frame = tk.Frame(app)
log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Set a monospaced font for the log output
log_font = font.Font(family="Courier", size=10)
log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, font=log_font)
log_text.pack(fill=tk.BOTH, expand=True)

# Disable dvdisaster options if not installed
if not check_tool_installed("dvdisaster"):
    d_option_checkbox.config(state=tk.DISABLED)
    messagebox.showwarning("dvdisaster Not Installed", "dvdisaster is not installed. Some recovery options are disabled.")

app.mainloop()
