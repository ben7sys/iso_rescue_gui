import os
"""
This script provides a graphical user interface for creating ISO images from DVD devices.
It allows the user to select the DVD device, choose the method for creating the ISO image, and specify various options.
The ISO image can be created using either the 'ddrescue' tool or the 'dd' command.
The script also provides functionality for checking if a tool is installed, detecting available DVD drives, and checking if a directory is writable.
Additionally, it includes functions for mounting the ISO image to verify its integrity and attempting to recover or analyze the ISO file.
The GUI elements can be disabled during the ISO creation process, and a stop button is provided to terminate the process if needed.
"""
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk, font
import subprocess
import shutil
import sys
import signal
import threading

# Global variables
process = None
stop_event = threading.Event()

def check_sudo():
    """Check if the script is run with sudo privileges and get the original user."""
    if os.geteuid() != 0:
        messagebox.showerror("Error", "Dieses Script muss mit Root-Rechten ausgeführt werden. Bitte starten Sie es mit 'sudo'.")
        sys.exit(1)
    return os.environ.get('SUDO_USER') or os.environ.get('USER')

def check_tool_installed(tool_name):
    """Check if a tool is installed on the system."""
    return shutil.which(tool_name) is not None

def select_output_path():
    """Open a file dialog for selecting the output path."""
    iso_path = filedialog.asksaveasfilename(defaultextension=".iso", filetypes=[("ISO files", "*.iso")])
    if iso_path:
        output_path_var.set(iso_path)

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
    """Create an ISO image using the selected method and options."""
    global process, stop_event
    stop_event.clear()
    iso_path = output_path_var.get()
    if not iso_path:
        messagebox.showerror("Fehler", "Bitte geben Sie einen Ausgabepfad für die ISO-Datei an.")
        return

    if not check_writable_directory(iso_path):
        messagebox.showerror("Fehler", "Das Zielverzeichnis ist nicht beschreibbar. Bitte wählen Sie ein anderes Verzeichnis.")
        return

    if os.path.exists(iso_path):
        if not messagebox.askyesno("Überschreiben bestätigen", f"Die Datei {iso_path} existiert bereits. Überschreiben?"):
            return

    dvd_device = dvd_device_var.get().split()[0]  # Extract device name
    if dvd_device == "No DVD device found":
        messagebox.showerror("Fehler", "Kein DVD-Laufwerk erkannt. Bitte überprüfen Sie Ihre Hardware.")
        return

    method = method_var.get()
    use_n = n_option_var.get()
    use_r3 = r3_option_var.get()
    use_b = b_option_var.get()
    use_d = d_option_var.get()

    if method == "ddrescue" and not check_tool_installed("ddrescue"):
        messagebox.showerror("Fehler", "ddrescue ist nicht auf diesem System installiert. Bitte installieren Sie es und versuchen Sie es erneut.")
        return

    # Build the ddrescue command based on user selections
    ddrescue_options = ['--force']
    if use_n:
        ddrescue_options.append("-n")
    if use_r3:
        ddrescue_options.append("-r3")
    if use_b:
        ddrescue_options.append("-b 2048")
    if use_d:
        ddrescue_options.append("-d")
    
    # Generate a unique mapfile name based on the options
    mapfile = f"{iso_path}.map"
    
    ddrescue_command = f"sudo /usr/bin/ddrescue {' '.join(ddrescue_options)} {dvd_device} {iso_path} {mapfile}"
    dd_command = f"sudo dd if={dvd_device} of={iso_path} bs=1M status=progress"
    command = ddrescue_command if method == "ddrescue" else dd_command

    disable_gui_elements()
    stop_button.config(state=tk.NORMAL, bg='red')
    create_iso_button.config(state=tk.DISABLED)

    log_text.delete(1.0, tk.END)  # Clear log before starting a new operation
    log_text.insert(tk.END, f"Ausführender Befehl: {command}\n")

    def run_command():
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
                log_text.insert(tk.END, "Vorgang gestoppt.\n")
            else:
                stderr_output = process.stderr.read().strip()
                if stderr_output:
                    log_text.insert(tk.END, f"Fehlerausgabe: {stderr_output}\n")

                if process.returncode == 0:
                    if os.path.getsize(iso_path) > 0:
                        messagebox.showinfo("Erfolg", f"ISO-Image erfolgreich erstellt unter {iso_path}")
                        if messagebox.askyesno("ISO erstellt", "ISO erfolgreich erstellt. Möchten Sie die DVD auswerfen?"):
                            subprocess.run(["eject", dvd_device])
                    else:
                        messagebox.showerror("Fehler", "Die ISO-Datei ist 0 Bytes groß. Bitte überprüfen Sie die DVD und versuchen Sie es erneut.")
                else:
                    raise subprocess.CalledProcessError(process.returncode, command)

        except subprocess.CalledProcessError as e:
            log_text.insert(tk.END, f"Befehl fehlgeschlagen mit Fehler: {e}\n")
            messagebox.showerror("Fehler", f"Erstellung des ISO-Images fehlgeschlagen. Siehe Protokoll für Details.")
        except Exception as e:
            log_text.insert(tk.END, f"Unerwarteter Fehler: {e}\n")
            messagebox.showerror("Fehler", "Ein unerwarteter Fehler ist aufgetreten. Siehe Protokoll für Details.")
        finally:
            app.after(0, reset_gui_state)

    threading.Thread(target=run_command, daemon=True).start()

def check_writable_directory(path):
    """Check if the directory is writable."""
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except PermissionError:
            return False
    return os.access(directory, os.W_OK)

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
        messagebox.showwarning("dvdisaster nicht installiert", "dvdisaster ist nicht installiert. Versuche Wiederherstellung mit iso-read stattdessen.")
        recovery_command = f"iso-read -i {iso_path} -o {iso_path.replace('.iso', '-recovered.iso')}"
    
    try:
        log_text.insert(tk.END, f"Versuche ISO-Wiederherstellung mit Befehl: {recovery_command}\n")
        subprocess.run(recovery_command, shell=True, check=True)
        messagebox.showinfo("Wiederherstellung", "ISO-Wiederherstellung abgeschlossen. Überprüfen Sie die wiederhergestellte ISO.")
    except subprocess.CalledProcessError as e:
        log_text.insert(tk.END, f"ISO-Wiederherstellung fehlgeschlagen mit Fehler: {e}\n")
        messagebox.showerror("Fehler", "ISO-Wiederherstellung fehlgeschlagen. Siehe Protokoll für Details.")

def stop_process():
    """Stop the current ISO creation process."""
    global stop_event
    stop_event.set()

def disable_gui_elements():
    """Disable all GUI elements except the Stop button."""
    dvd_device_combobox.config(state=tk.DISABLED)
    method_combobox.config(state=tk.DISABLED)
    n_option_checkbox.config(state=tk.DISABLED)
    r3_option_checkbox.config(state=tk.DISABLED)
    b_option_checkbox.config(state=tk.DISABLED)
    d_option_checkbox.config(state=tk.DISABLED)
    output_path_entry.config(state=tk.DISABLED)
    select_output_button.config(state=tk.DISABLED)
    intact_button.config(state=tk.DISABLED)
    damaged_button.config(state=tk.DISABLED)
    irrecoverable_button.config(state=tk.DISABLED)
    create_iso_button.config(state=tk.DISABLED)

def reset_gui_state():
    """Reset the GUI state after process completion or termination."""
    global process
    process = None
    stop_button.config(state=tk.DISABLED, bg='light gray')
    create_iso_button.config(state=tk.NORMAL)
    # Re-enable all input fields and buttons
    dvd_device_combobox.config(state='readonly')
    method_combobox.config(state='readonly')
    n_option_checkbox.config(state=tk.NORMAL)
    r3_option_checkbox.config(state=tk.NORMAL)
    b_option_checkbox.config(state=tk.NORMAL)
    d_option_checkbox.config(state=tk.NORMAL)
    output_path_entry.config(state=tk.NORMAL)
    select_output_button.config(state=tk.NORMAL)
    intact_button.config(state=tk.NORMAL)
    damaged_button.config(state=tk.NORMAL)
    irrecoverable_button.config(state=tk.NORMAL)
    app.update_idletasks()

def apply_preset(preset):
    """Apply preset configurations for different DVD conditions."""
    if preset == "intact":
        method_var.set("dd")
        n_option_var.set(False)
        r3_option_var.set(False)
        b_option_var.set(True)
        d_option_var.set(True)
    elif preset == "damaged":
        method_var.set("ddrescue")
        n_option_var.set(False)
        r3_option_var.set(True)
        b_option_var.set(True)
        d_option_var.set(True)
    elif preset == "irrecoverable":
        method_var.set("ddrescue")
        n_option_var.set(True)
        r3_option_var.set(True)
        b_option_var.set(True)
        d_option_var.set(True)

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

b_option_var = tk.BooleanVar(value=True) # Default to True since DVDs typically use 2048 bytes sectors
b_option_checkbox = tk.Checkbutton(options_frame, text="Blockgröße auf 2048 Bytes setzen (-b 2048)", variable=b_option_var)
b_option_checkbox.pack(anchor=tk.W)

d_option_var = tk.BooleanVar(value=True)  # Option for using direct mode (-d)
d_option_checkbox = tk.Checkbutton(options_frame, text="Direkten Zugriffsmodus verwenden (-d)", variable=d_option_var)
d_option_checkbox.pack(anchor=tk.W)

# Add presets
presets_frame = tk.LabelFrame(frame, text="Voreinstellungen")
presets_frame.pack(anchor=tk.W, fill="x", pady=5)

intact_button = tk.Button(presets_frame, text="Intakte DVD", command=lambda: apply_preset("intact"))
intact_button.pack(side=tk.LEFT, padx=5)

damaged_button = tk.Button(presets_frame, text="Beschädigte DVD", command=lambda: apply_preset("damaged"))
damaged_button.pack(side=tk.LEFT, padx=5)

irrecoverable_button = tk.Button(presets_frame, text="Irreparable DVD", command=lambda: apply_preset("irrecoverable"))
irrecoverable_button.pack(side=tk.LEFT, padx=5)

# Set default output path to the original user's home directory
default_output_path = os.path.expanduser(f"~{original_user}/ddrescue.iso")
output_path_var = tk.StringVar(value=default_output_path)
output_path_label = tk.Label(frame, text="Ausgabepfad für ISO-Datei:")
output_path_label.pack(anchor=tk.W)

output_path_entry = tk.Entry(frame, textvariable=output_path_var, width=50)
output_path_entry.pack(anchor=tk.W)

select_output_button = tk.Button(frame, text="Durchsuchen...", command=select_output_path)
select_output_button.pack(anchor=tk.W, pady=5)

# Create a frame for buttons
button_frame = tk.Frame(frame)
button_frame.pack(fill=tk.X, pady=5)

create_iso_button = tk.Button(button_frame, text="ISO erstellen", command=create_iso)
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