import tkinter as tk

def disable_gui_elements(elements):
    """Disable all GUI elements except the Stop button."""
    for element in elements:
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
        else:
            element.config(state='readonly' if isinstance(element, tk.ttk.Combobox) else tk.NORMAL)

def apply_preset(preset, method_var, n_option_var, r3_option_var, b_option_var, d_option_var):
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