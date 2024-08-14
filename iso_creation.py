import sys
import shutil
import os
import subprocess
import threading
from tkinter import messagebox
import signal
import tkinter as tk
from config import process, stop_event, DDRESCUE_DEFAULT_OPTIONS, DD_BS_SIZE, DDRESCUE_COMMAND_TEMPLATE, DD_COMMAND_TEMPLATE, NO_DVD_DEVICE, DDRESCUE_NOT_INSTALLED, ISO_CREATION_SUCCESS, EJECT_PROMPT
from core_functions import check_tool_installed, check_writable_directory
from gui_utils import disable_gui_elements, reset_gui_state, update_progress, update_log
from iso_utils import try_mount_iso, attempt_iso_recovery
from media_detection import detect_media_type, prepare_command

def handle_mapfile(iso_path):
    """Handle the mapfile for ddrescue before starting the process."""
    mapfile = iso_path + ".map"
    if os.path.exists(mapfile):
        try:
            os.remove(mapfile)
            print(f"Existing mapfile removed: {mapfile}")
        except OSError as e:
            print(f"Error removing mapfile: {e}")

def create_iso(dvd_device_var, output_path_var, method_var, n_option_var, r3_option_var, b_option_var, d_option_var, c_option_var, log_text, app, stop_button, progress_bar):
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

    if os.path.exists(iso_path):
        if not messagebox.askyesno("Confirm Overwrite", f"The file {iso_path} already exists. Overwrite?"):
            return

    dvd_device = dvd_device_var.get().split()[0]  # Extract device name
    if dvd_device == "No DVD device found":
        messagebox.showerror("Error", NO_DVD_DEVICE)
        return

    if not check_media_present(dvd_device):
        messagebox.showerror("Error", "No media detected in the drive. Please insert a disc and try again.")
        return

    media_type = detect_media_type(dvd_device)
    if media_type == "Unknown":
            messagebox.showerror("Error", "Unsupported or unknown media type detected.")
            return

    command = prepare_command(media_type, dvd_device, iso_path, 
                                n_option_var.get(), r3_option_var.get(), 
                                b_option_var.get(), d_option_var.get(), 
                                c_option_var.get())
    if command is None:
            return

    if not check_free_space(iso_path, 8 * 1024 * 1024 * 1024):
        messagebox.showerror("Error", "Insufficient free space in the output directory.")
        return

    handle_mapfile(iso_path)  # Handle mapfile before starting the process

    # Disable GUI elements and activate Stop button
    disable_gui_elements(app.winfo_children())
    stop_button.config(state=tk.NORMAL, bg='red')
    app.update_idletasks()  # Ensure the GUI updates after changes

    update_log(log_text, "Starting ISO creation process...")
    update_log(log_text, f"Executing command: {command}")

    # Start the command execution in a new thread
    threading.Thread(target=run_command, args=(command, log_text, app, iso_path, dvd_device, stop_button, progress_bar)).start()

def check_media_present(device):
    try:
        subprocess.run(['dd', 'if=' + device, 'of=/dev/null', 'count=1'], 
                       check=True, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def run_command(command, log_text, app, iso_path, dvd_device, stop_button, progress_bar):
    global process
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, preexec_fn=os.setsid)
        
        while process.poll() is None and not stop_event.is_set():
            output = process.stdout.readline()
            if output:
                # Extract progress from output (if available)
                if "%" in output:
                    try:
                        progress = float(output.split("%")[0].split()[-1])
                        update_progress(progress_bar, progress)
                    except ValueError:
                        pass
                
                update_log(log_text, output.strip())

        if stop_event.is_set():
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            update_log(log_text, "Operation stopped.")
            stop_button.config(state=tk.DISABLED)
        else:
            stderr_output = process.stderr.read().strip()
            if stderr_output:
                update_log(log_text, f"Error output: {stderr_output}")

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
        update_log(log_text, f"Command failed with error: {e}")
        messagebox.showerror("Error", "ISO creation failed. See the log for details.")
    except Exception as e:
        update_log(log_text, f"Unexpected error: {e}")
        messagebox.showerror("Error", "An unexpected error occurred. See the log for details.")
    finally:
        update_progress(progress_bar, 0)  # Reset progress bar
        app.after(0, lambda: reset_gui_state(app.winfo_children()))
        stop_button.config(state=tk.DISABLED)

def check_free_space(file_path, required_space):
    """Check if there's enough free space in the directory where the file will be created."""
    directory = os.path.dirname(file_path)
    
    if not directory:  # This handles cases where the file_path is just a filename without a directory
        directory = '.'
    
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except Exception as e:
            print(f"Error creating directory {directory}: {e}")
            return False
    
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
        update_log(log_text, f"Attempting ISO recovery with command: {recovery_command}")
        subprocess.run(recovery_command, shell=True, check=True)
        messagebox.showinfo("Recovery", "ISO recovery completed. Check the recovered ISO.")
    except subprocess.CalledProcessError as e:
        update_log(log_text, f"ISO recovery failed with error: {e}")
        messagebox.showerror("Error", "ISO recovery failed. See the log for details.")