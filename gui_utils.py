import tkinter as tk
from tkinter import ttk

def disable_gui_elements(elements):
    """Disable all GUI elements except the Stop button."""
    for element in elements:
        if isinstance(element, (tk.Button, tk.Entry, tk.Text, ttk.Combobox)):
            if isinstance(element, tk.Button) and element['text'] == "Stop":
                element.config(state=tk.NORMAL, bg='red')
            else:
                element.config(state=tk.DISABLED)

def reset_gui_state(elements):
    """Reset the GUI state after process completion or termination."""
    for element in elements:
        if isinstance(element, tk.Button):
            if element['text'] == "Stop":
                element.config(state=tk.DISABLED, bg='light gray')
            else:
                element.config(state=tk.NORMAL)
        elif isinstance(element, tk.Entry):
            element.config(state=tk.NORMAL)
        elif isinstance(element, ttk.Combobox):
            element.config(state='readonly')
        else:
            element.config(state=tk.NORMAL)

def apply_preset(preset, method_var, n_option_var, r3_option_var, b_option_var, d_option_var):
    """Apply preset configurations for different DVD conditions."""
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

# Update the GUI based on the selected media type
def update_gui_for_media_type(media_type_var, method_var, elements):
    """Update the GUI based on the selected media type."""
    media_type = media_type_var.get()
    method = method_var.get()
    
    # Show or hide elements based on media type and method
    if media_type == "Data CD/DVD":
        enable_ddrescue_options(elements)
    elif media_type in ["Audio CD", "Video/Music DVD"]:
        disable_ddrescue_options(elements)
        method_var.set("cdparanoia" if media_type == "Audio CD" else "dvdbackup")

def enable_ddrescue_options(elements):
    """Enable ddrescue-specific options in the GUI."""
    for element in elements:
        if isinstance(element, (tk.Checkbutton, ttk.Combobox)):
            element.config(state='normal')

def disable_ddrescue_options(elements):
    """Disable ddrescue-specific options in the GUI."""
    for element in elements:
        if isinstance(element, (tk.Checkbutton, ttk.Combobox)):
            element.config(state='disabled')

# Other helper functions related to GUI management can be added here.
