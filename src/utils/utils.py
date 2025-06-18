import os
import subprocess
import sys
import json
import tkinter as tk
from tkinter import filedialog, messagebox
import pyautogui


def save_highres_gui_image(root, filename="/home/badar/0_PhD/pipeInSAR/src/gui_snapshot.png"):
    # Resize GUI to a large resolution
    offset = 30
    root.update_idletasks()
    # Get the position and size of the window
    x = root.winfo_rootx()
    y = root.winfo_rooty() - offset
    width = root.winfo_width()
    # Add the height of the title bar to the window height
    height = root.winfo_height()+ offset  # Adjust this value if needed to include the title bar height

    # Capture the screen region of the window (no need to raise or resize)
    screenshot = pyautogui.screenshot(region=(x, y, width, height))
    
    screenshot.save(filename)


CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
CONFIG_FILE_PART = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config_part.json")

# Function to run commands in parallel
def execute_command(command):
    # Execute bash command
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    return {'command': command, 'output': output, 'error': error}

def run_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr)
    return result.stdout.strip()
    
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
def update_console(console_text=None, message="", log_file_path=None):
    # Convert message to string or JSON-formatted string if it's a dictionary
    if isinstance(message, dict):
        message = json.dumps(message, indent=4)
    else:
        message = str(message)

    # Log the message if log_file_path is provided
    if log_file_path:
        log_message(log_file_path, message)

    # Update the console if console_text is provided
    if console_text:
        console_text.config(state=tk.NORMAL)
        console_text.insert(tk.END, message + "\n")
        console_text.config(state=tk.DISABLED)
        console_text.see(tk.END)
    else:
        # If no console_text is provided, print the message
        print(message)

def browse_file(entry_widget, key, file_types):
    """Browse for a file and insert the path into the entry widget."""
    initial_dir = os.path.dirname(entry_widget.get()) if os.path.isfile(entry_widget.get()) else None
    filepath = filedialog.askopenfilename(initialdir=initial_dir, filetypes=file_types)
    if filepath:
        entry_widget.delete(0, "end")
        entry_widget.insert(0, filepath)
        update_last_dir(key, filepath)


def browse_folder(entry_widget, key):
    """Browse for a folder and insert the path into the entry widget."""
    initial_dir = entry_widget.get() if os.path.isdir(entry_widget.get()) else None
    folder_path = filedialog.askdirectory(initialdir=initial_dir)
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

def load_config_part():
    """Load configuration from JSON file."""
    if os.path.exists(CONFIG_FILE_PART):
        with open(CONFIG_FILE_PART, "r") as f:
            return json.load(f)
    return {}

def save_config(config):
    """Save configuration to JSON file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def save_config_part(config):
    """Save/update configuration to JSON file, keeping existing values intact."""
    if os.path.exists(CONFIG_FILE_PART):
        with open(CONFIG_FILE_PART, "r") as f:
            existing_config = json.load(f)
    else:
        existing_config = {}

    # Update existing config with new values
    existing_config.update(config)

    with open(CONFIG_FILE_PART, "w") as f:
        json.dump(existing_config, f, indent=4)
    

def update_last_dir(key, path):
    """Update the last opened directory for a specific key."""
    config = load_config()
    config[key] = path
    save_config(config)

############################################################################################################
def read_file_lines(filename):
    """Read all lines from a file and return them as a list."""
    with open(filename, 'r') as f:
        return f.readlines()

def mkdir(indir):
    if not os.path.exists(indir):
        os.mkdir(indir)
        print(f"New folder created: {indir}")


def create_symlink(src, dest):
    # Check if the symbolic link already exists
    if not (os.path.islink(dest) and os.path.exists(dest)):        
        # If the symbolic link doesn't exist, create it
        try:
            subprocess.call(['ln', '-s', src, dest])
            # print(f"Symbolic link created: {dest} -> {src}")
        except Exception as e:
            print(f"Failed to create symbolic link: {e}")

def rm_symlink(file):
    if os.path.islink(file):
        os.unlink(file)

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text=self.text,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("tahoma", 10),
            anchor="w",              # Left align text
            justify="left"           # Left justify multi-line text
        )
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

def add_tooltip(widget, text):
    ToolTip(widget, text)
