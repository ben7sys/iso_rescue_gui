import os
import subprocess
import threading
from tkinter import messagebox

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
        messagebox.showerror("Fehler", NO_DVD_DEVICE)
        return

    method = method_var.get()
    if method == "ddrescue" and not check_tool_installed("ddrescue"):
        messagebox.showerror("Fehler", DDRESCUE_NOT_INSTALLED)
        return

    # Build the command based on user selections
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

    disable_gui_elements(app.winfo_children())
    log_text.delete(1.0, tk.END)  # Clear log before starting a new operation
    log_text.insert(tk.END, f"Ausführender Befehl: {command}\n")

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
            log_text.insert(tk.END, "Vorgang gestoppt.\n")
        else:
            stderr_output = process.stderr.read().strip()
            if stderr_output:
                log_text.insert(tk.END, f"Fehlerausgabe: {stderr_output}\n")

            if process.returncode == 0:
                if os.path.getsize(iso_path) > 0:
                    messagebox.showinfo("Erfolg", ISO_CREATION_SUCCESS.format(iso_path))
                    if messagebox.askyesno("ISO erstellt", EJECT_PROMPT):
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
        app.after(0, lambda: reset_gui_state(app.winfo_children()))

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
        messagebox.showwarning("dvdisaster nicht installiert", "dvdisaster ist nicht installiert. Versuche Wiederherstellung mit iso-read stattdessen.")
        recovery_command = f"iso-read -i {iso_path} -o {iso_path.replace('.iso', '-recovered.iso')}"
    
    try:
        log_text.insert(tk.END, f"Versuche ISO-Wiederherstellung mit Befehl: {recovery_command}\n")
        subprocess.run(recovery_command, shell=True, check=True)
        messagebox.showinfo("Wiederherstellung", "ISO-Wiederherstellung abgeschlossen. Überprüfen Sie die wiederhergestellte ISO.")
    except subprocess.CalledProcessError as e:
        log_text.insert(tk.END, f"ISO-Wiederherstellung fehlgeschlagen mit Fehler: {e}\n")
        messagebox.showerror("Fehler", "ISO-Wiederherstellung fehlgeschlagen. Siehe Protokoll für Details.")