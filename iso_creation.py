import os
import subprocess
import threading
from tkinter import messagebox
import signal
import tkinter as tk

from config import (
    process, stop_event, DDRESCUE_DEFAULT_OPTIONS, DD_BS_SIZE,
    DDRESCUE_COMMAND_TEMPLATE, DD_COMMAND_TEMPLATE,
    NO_DVD_DEVICE, DDRESCUE_NOT_INSTALLED, ISO_CREATION_SUCCESS, EJECT_PROMPT
)
from core_functions import check_tool_installed, check_writable_directory
from gui_utils import disable_gui_elements, reset_gui_state

def create_iso(dvd_device_var, output_path_var, method_var, n_option_var, r3_option_var, b_option_var, d_option_var, log_text, app):
    """Create an ISO image using the selected method and options."""
    global process, stop_event
    stop_event = threading.Event()

    # Check output path
    iso_path = output_path_var.get()
    if not iso_path:
        messagebox.showerror("Error", "Please specify an output path for the ISO file.")
        return

    if not check_writable_directory(iso_path):
        messagebox.showerror("Error", "The target directory is not writable. Please choose a different directory.")
        return

    # Check for overwrite confirmation
    if os.path.exists(iso_path):
        if not messagebox.askyesno("Confirm Overwrite", f"The file {iso_path} already exists. Overwrite?"):
            return

    # Check DVD device
    dvd_device = dvd_device_var.get().split()[0]  # Extract device name
    if dvd_device == "No DVD device found":
        messagebox.showerror("Error", NO_DVD_DEVICE)
        return

    # Check method and tool availability
    method = method_var.get()
    if method == "ddrescue" and not check_tool_installed("ddrescue"):
        messagebox.showerror("Error", DDRESCUE_NOT_INSTALLED)
        return

    # Build and execute command based on method and user options
    if method == "ddrescue":
        ddrescue_options = DDRESCUE_DEFAULT_OPTIONS.copy()
        if n_option_var.get():
            ddrescue_options.append("-n")
        if r3_option_var.get():
            ddrescue_options.append("-r3")
        if b_option_var.get():
            ddrescue_options.append("-b 2048")
        if d_option_var.get():
            ddrescue_options.append("-d")
        
        mapfile = f"{iso_path}.map"
        command = DDRESCUE_COMMAND_TEMPLATE.format(
            options=' '.join(ddrescue_options),
            device=dvd_device,
            iso_path=iso_path,
            mapfile=mapfile
        )
    else:  # dd method
        command = DD_COMMAND_TEMPLATE.format(
            device=dvd_device,
            iso_path=iso_path,
            bs_size=DD_BS_SIZE
        )

    # Disable GUI elements and log command
    disable_gui_elements(app.winfo_children())
    log_text.delete(1.0, tk.END)  # Clear log before starting a new operation
    log_text.insert(tk.END, f"Executing command: {command}\n")

    # Start the command execution in a new thread
    threading.Thread(target=run_command, args=(command, log_text, app, iso_path, dvd_device)).start()


def run_command(command, log_text, app, iso_path, dvd_device):
    """Run the ISO creation command in a separate thread."""
    global process
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, preexec_fn=os.setsid)
        
        while process.poll() is None and not stop_event.is_set():
            output = process.stdout.readline()
            if output:
                log_text.insert(tk.END, output)
                log_text.see(tk.END)
                app.update_idletasks()

        if stop_event.is_set():
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            log_text.insert(tk.END, "Operation stopped.\n")
        else:
            stderr_output = process.stderr.read().strip()
            if stderr_output:
                log_text.insert(tk.END, f"Error output: {stderr_output}\n")

            if process.returncode == 0:
                if os.path.getsize(iso_path) > 0:
                    messagebox.showinfo("Success", ISO_CREATION_SUCCESS.format(iso_path))
                    if messagebox.askyesno("ISO Created", EJECT_PROMPT):
                        subprocess.run(["eject", dvd_device])
                else:
                    messagebox.showerror("Error", "The ISO file is 0 bytes in size. Please check the DVD and try again.")
            else:
                raise subprocess.CalledProcessError(process.returncode, command)

    except subprocess.CalledProcessError as e:
        log_text.insert(tk.END, f"Command failed with error: {e}\n")
        messagebox.showerror("Error", "ISO creation failed. See the log for details.")
    except Exception as e:
        log_text.insert(tk.END, f"Unexpected error: {e}\n")
        messagebox.showerror("Error", "An unexpected error occurred. See the log for details.")
    finally:
        app.after(0, lambda: reset_gui_state(app.winfo_children()))

def check_free_space(directory, required_space):
    """Check if there's enough free space in the directory."""
    total, used, free = shutil.disk_usage(directory)
    return free > required_space

def stop_process():
    """Stop the current ISO creation process."""
    global stop_event
    if stop_event:
        stop_event.set()

def attempt_iso_recovery(iso_path, log_text):
    """Attempt to recover or analyze the ISO file."""
    if check_tool_installed("dvdisaster"):
        recovery_command = f"dvdisaster -r -i {iso_path} -o {iso_path.replace('.iso', '-recovered.iso')}"
    else:
        messagebox.showwarning("dvdisaster not installed", "dvdisaster is not installed. Attempting recovery with iso-read instead.")
        recovery_command = f"iso-read -i {iso_path} -o {iso_path.replace('.iso', '-recovered.iso')}"
    
    try:
        log_text.insert(tk.END, f"Attempting ISO recovery with command: {recovery_command}\n")
        subprocess.run(recovery_command, shell=True, check=True)
        messagebox.showinfo("Recovery", "ISO recovery completed. Check the recovered ISO.")
    except subprocess.CalledProcessError as e:
        log_text.insert(tk.END, f"ISO recovery failed with error: {e}\n")
        messagebox.showerror("Error", "ISO recovery failed. See the log for details.")
