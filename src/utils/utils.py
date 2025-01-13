import os
import sys
import json
import time
import tkinter as tk
from tkinter import filedialog, messagebox


CONFIG_FILE = "config.json"


def toggle_gacos_folder(atm_option, folder2_entry, browse_button3):
    """
    Enable or disable folder2_entry and browse_button3 based on the selected atmospheric correction option.

    Args:
        atm_option (tk.StringVar): The StringVar containing the selected option.
        folder2_entry (tk.Entry): The Entry widget for the GACOS folder.
        browse_button3 (tk.Button): The Browse button for the GACOS folder.
    """
    if atm_option.get() == "GACOS Atmospheric correction":
        folder2_entry.config(state="normal")
        browse_button3.config(state="normal")
    else:
        folder2_entry.config(state="disabled")
        browse_button3.config(state="disabled")


# Function to format time output
def format_time(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    mins, secs = divmod(remainder, 60)

    # Create a list to hold non-zero parts
    parts = []
    if days > 0:
        parts.append(f"{int(days)}d")
    if hours > 0:
        parts.append(f"{int(hours)}h")
    if mins > 0:
        parts.append(f"{int(mins)}m")
    if (
        secs > 0 or not parts
    ):  # Always include seconds, even if zero when it's the only value
        parts.append(f"{secs:.2f}s")

    return " ".join(parts)


# Function to exit the program on specified condition if false
def exitGUI(root, condition, message="Critical Error. Exiting..."):
    """
    Displays a pop-up message, closes the GUI, and exits the program if the condition is not met.

    Parameters:
    root (Tk): The root Tkinter window object.
    condition (bool): The condition to check. If False, the program will exit.
    message (str): Optional. Message to display in the pop-up before exiting.
    """
    if not condition:
        # Show the pop-up message
        messagebox.showerror("Error", message)

        # Close the Tkinter window
        root.destroy()

        # Exit the entire program
        sys.exit()


# Function to log messages to a log file
def log_message(log_file_path, message):
    with open(log_file_path, "a") as log_file:
        log_file.write(message + "\n")


# Function to log messages with timing details
def update_console(console_text, message, track_time=False):
    global last_true_time

    # Convert message to string or JSON-formatted string if it's a dictionary
    if isinstance(message, dict):
        message = json.dumps(message, indent=4)
    else:
        message = str(message)

    # Track step time if 'track_time' is True
    if track_time:
        current_time = time.time()
        if last_true_time is not None:
            time_taken = current_time - last_true_time
            formatted_time_taken = format_time(time_taken)
            message += f"\nTime taken: {formatted_time_taken}"
        last_true_time = current_time  # Update last_true_time with current timestamp

    log_message(message)  # This function is assumed to handle actual logging

    # Update the console (assuming you have a Tkinter text widget named `console_text`)
    console_text.config(state=tk.NORMAL)
    console_text.insert(tk.END, message + "\n")
    console_text.config(state=tk.DISABLED)
    console_text.see(tk.END)


def browse_file(entry_widget, key, file_types):
    """Browse for a file and insert the path into the entry widget."""
    filepath = filedialog.askopenfilename(filetypes=file_types)
    if filepath:
        entry_widget.delete(0, "end")
        entry_widget.insert(0, filepath)
        update_last_dir(key, os.path.dirname(filepath))


def browse_folder(entry_widget, key):
    """Browse for a folder and insert the path into the entry widget."""
    folder_path = filedialog.askdirectory()
    if folder_path:
        entry_widget.delete(0, "end")
        entry_widget.insert(0, folder_path)
        update_last_dir(key, folder_path)


def load_config():
    """Load configuration from JSON file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_config(config):
    """Save configuration to JSON file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


def update_last_dir(key, path):
    """Update the last opened directory for a specific key."""
    config = load_config()
    config[key] = path
    save_config(config)
