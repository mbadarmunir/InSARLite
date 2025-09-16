import os
import subprocess
import sys
import json
# import glob
import re
import tkinter as tk
from tkinter import filedialog, messagebox, font
from pykml import parser
from datetime import datetime, timedelta
import math
import base64
import requests
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import time
import numpy as np



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

def parse_kml(kml_file):
    # Parse the KML file
    with open(kml_file, 'r') as f:
        root = parser.parse(f).getroot()

    NAMESPACE = {'gx': 'http://www.google.com/kml/ext/2.2'}

    # Extract the gx:LatLonQuad coordinates using the correct namespace
    coordinates = root.xpath('.//gx:LatLonQuad//coordinates', namespaces=NAMESPACE)

    if coordinates:
        return coordinates        
    else:
        raise ValueError("No gx:LatLonQuad coordinates found in the KML file")        

def get_kml(indir):
    for root, _, files in os.walk(indir):
        for f in files:            
            if f == 'map-overlay.kml':
                kml_path = os.path.join(root, f)                
                return kml_path
    return None


def get_max_extent_from_kml_coords(coord_strings):
    """
    Given a list of coordinate strings (each string: "lon1,lat1 lon2,lat2 lon3,lat3 lon4,lat4"),
    determines the max extent quadrilateral by:
      - For each input, classify the 4 points as TL, BL, TR, BR using lat/lon values:
        - Top points: two with highest latitudes (if tie, use lon for tie-break)
        - Bottom points: two with lowest latitudes
        - For each pair, left/right by lon
      - For each logical corner (TL, BL, TR, BR), find the extreme values across all inputs:
        - TL: max lat, min lon
        - BL: min lat, min lon
        - TR: max lat, max lon
        - BR: min lat, max lon
    Returns a string with the same order as the first input string: "lon1,lat1 lon2,lat2 lon3,lat3 lon4,lat4"
    Also prints the order of points in terms of TL, BL, TR, BR.
    """

    def classify_corners(pts):
        # pts: list of (lon, lat), length 4
        # Sort by latitude descending
        sorted_by_lat = sorted(pts, key=lambda p: p[1], reverse=True)
        top2 = sorted_by_lat[:2]
        bottom2 = sorted_by_lat[2:]

        # For top points, TL is min lon, TR is max lon
        TL = min(top2, key=lambda p: p[0])
        TR = max(top2, key=lambda p: p[0])
        # For bottom points, BL is min lon, BR is max lon
        BL = min(bottom2, key=lambda p: p[0])
        BR = max(bottom2, key=lambda p: p[0])

        # Return mapping: logical corner -> actual point
        return {
            'TL': TL,
            'BL': BL,
            'TR': TR,
            'BR': BR
        }

    all_corner_pts = {'TL': [], 'BL': [], 'TR': [], 'BR': []}
    for coord_str in coord_strings:
        pts = [tuple(map(float, pt.split(','))) for pt in coord_str.split()]
        if len(pts) != 4:
            raise ValueError("Each coordinate string must have 4 points")
        mapping = classify_corners(pts)
        for corner in ['TL', 'BL', 'TR', 'BR']:
            all_corner_pts[corner].append(mapping[corner])

    # For each logical corner, find the extreme value
    # TL: max lat, min lon
    TL = max(all_corner_pts['TL'], key=lambda p: (p[1], -p[0]))
    # BL: min lat, min lon
    BL = min(all_corner_pts['BL'], key=lambda p: (p[1], p[0]))
    # TR: max lat, max lon
    TR = max(all_corner_pts['TR'], key=lambda p: (p[1], p[0]))
    # BR: min lat, max lon
    BR = min(all_corner_pts['BR'], key=lambda p: (p[1], -p[0]))

    # Map logical corners to their extreme values
    extreme_corners = {'TL': TL, 'BL': BL, 'TR': TR, 'BR': BR}

    # Use the order of the first input string to determine output order
    first_pts = [tuple(map(float, pt.split(','))) for pt in coord_strings[0].split()]
    first_mapping = classify_corners(first_pts)
    # Build a reverse mapping: actual point -> logical corner
    point_to_corner = {v: k for k, v in first_mapping.items()}

    # For each point in the first input, find its logical corner, and use the extreme value for that corner
    ordered_extreme_pts = []
    order_labels = []
    for pt in first_pts:
        corner = point_to_corner[pt]
        extreme_pt = extreme_corners[corner]
        ordered_extreme_pts.append(f"{extreme_pt[0]},{extreme_pt[1]}")
        order_labels.append(corner)

    # Determine flight direction based on latitude of BR and BL
    if extreme_corners['BR'][1] < extreme_corners['BL'][1]:
        flight_direction = "DESCENDING"
    else:
        flight_direction = "ASCENDING"

    return " ".join(ordered_extreme_pts), flight_direction


def extr_ext_TL(folder):
    """
    From sentinel-1 data folder, this function extracts and return the maximum extent of the data and period of acquisition."""
    
    # Get the list of all files in the directory
    # files = os.listdir(folder)

    # Filter for .SAFE directories
    safe_dirs = []
    for root, dirs, files in os.walk(folder):
        for d in dirs:
            if d.endswith('.SAFE'):
                safe_dirs.append(os.path.join(root, d))
    
    all_coords = []
    dates = []

    if not safe_dirs:
        return None, None
    else:
        for j in safe_dirs:
            kml = get_kml(j)
            if kml and os.path.isfile(kml):
                coordinates = parse_kml(kml)
                if coordinates:
                    all_coords.append(coordinates[0].text.strip())
            else:
                print(f"No map-overlay.kml found in {j}, skipping...")
                print(f"KML path: {kml}")
            # Extract date from directory name (n[17:25] = yyyymmdd)
            n = os.path.basename(j)
            if len(n) >= 25:
                date_str = n[17:25]
            try:
                date_obj = datetime.strptime(date_str, "%Y%m%d").date()
                dates.append(date_obj)
            except ValueError:
                pass  # Skip if not a valid date

    max_bounds, fdirection = get_max_extent_from_kml_coords(all_coords)
    sdate = min(dates) if dates else None
    edate = max(dates) if dates else None
    
    return max_bounds, sdate, edate, fdirection


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


def browse_folder(entry_widget, key=None):
    """Browse for a folder and insert the path into the entry widget."""
    initial_dir = entry_widget.get() if os.path.isdir(entry_widget.get()) else None
    folder_path = filedialog.askdirectory(initialdir=initial_dir)
    if folder_path:
        entry_widget.delete(0, "end")
        entry_widget.insert(0, folder_path)
        if key:
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

def configure_zooming_ui(root, min_font=8, max_font=50):
    def update_font_size(size):
        for name in ["TkDefaultFont", "TkTextFont", "TkFixedFont", "TkMenuFont", "TkHeadingFont"]:
            f = font.nametofont(name)
            f.configure(size=int(size * (1.1 if "Heading" in name else 1)))
        def recurse(w):
            try:
                w.configure(font=f)
            except:
                pass
            for child in w.winfo_children():
                recurse(child)
        recurse(root)

    def on_wheel(event):
        if event.state & 0x0004:  # Ctrl pressed
            if hasattr(event, 'delta') and event.delta != 0:
                delta = event.delta
            elif hasattr(event, 'num'):
                delta = 1 if event.num == 4 else -1
            else:
                delta = 0
            direction = 1 if delta > 0 else -1
            new_size = min(max(getattr(root, "font_size", 12) + direction, min_font), max_font)
            if new_size != getattr(root, "font_size", 12):
                root.font_size = new_size
                update_font_size(root.font_size)

    def on_key(event):
        if event.state & 0x0004:  # Ctrl pressed
            if event.keysym in ['plus', 'equal', 'KP_Add']:
                root.font_size = min(getattr(root, "font_size", 12) + 1, max_font)
            elif event.keysym in ['minus', 'KP_Subtract']:
                root.font_size = max(getattr(root, "font_size", 12) - 1, min_font)
            else:
                return
            update_font_size(root.font_size)

    # Only set font_size if not already set
    if not hasattr(root, "font_size"):
        root.font_size = 12

    root.bind_all("<MouseWheel>", on_wheel)
    root.bind_all("<Button-4>", on_wheel)     # Linux scroll up
    root.bind_all("<Button-5>", on_wheel)     # Linux scroll down
    for k in ["<Control-plus>", "<Control-equal>", "<Control-minus>", "<Control-KP_Add>", "<Control-KP_Subtract>"]:
        root.bind_all(k, on_key)

############################################################################################################
def subset_safe_dirs(safe_dirs, st, en):    
    # Filter safe_dirs based on the start and end dates
    filtered = []
    for d in safe_dirs:
        sdir = os.path.basename(d)
        date_str = sdir[17:25]
        try:
            date_obj = datetime.strptime(date_str, "%Y%m%d").date()
            st_date = datetime.strptime(st, "%Y-%m-%d").date()
            en_date = datetime.strptime(en, "%Y-%m-%d").date()
            if st_date <= date_obj <= en_date:
                filtered.append(d)
        except Exception:
            continue
    return filtered

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

#######################################################################################################
################ Functions to prepare and submit GACOS atmospheric correction requests ################
#######################################################################################################
def extract_times_from_folder(folder_name):
    """Extract startTime and stopTime from a folder name."""
    try:
        parts = folder_name.split("_")
        start_time = parts[5]
        stop_time = parts[6]

        # Parse to datetime objects
        start_datetime = datetime.strptime(start_time, "%Y%m%dT%H%M%S")
        stop_datetime = datetime.strptime(stop_time, "%Y%m%dT%H%M%S")

        # Calculate average time
        avg_datetime = start_datetime + (stop_datetime - start_datetime) / 2

        return start_datetime, stop_datetime, avg_datetime
    except Exception as e:
        print(f"Error processing folder {folder_name}: {e}")
        return None, None, None
            
def calculate_average_acquisition_time(directory):
    # Collect times from folder names
    start_times = []
    stop_times = []
    average_times = []
    dates = []

    for folder_name in os.listdir(directory):
        folder_path = os.path.join(directory, folder_name)
        if os.path.isdir(folder_path) and folder_name.startswith("S1"):
            start_time, stop_time, avg_time = extract_times_from_folder(folder_name)
            if avg_time:
                start_times.append(start_time)
                stop_times.append(stop_time)
                average_times.append(avg_time)
                dates.append(start_time.strftime("%Y%m%d"))

    if average_times:
        # Convert seconds back to time format for proper average calculation
        avg_total_seconds = sum(
            (t - t.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
            for t in average_times
        )
        avg_seconds = avg_total_seconds / len(average_times)
        overall_average_time = timedelta(seconds=avg_seconds)

        dates.sort()

        # Group dates in batches of 20
        grouped_dates = [dates[i:i + 20] for i in range(0, len(dates), 20)]

        # Extract hours and minutes from overall_average_time
        h, remainder = divmod(int(overall_average_time.total_seconds()), 3600)
        m = (remainder // 60)
        return grouped_dates, h, m

    return [], None

def estimate_s1_slc_frames(north, south, east, west):
    """
    Estimate how many Sentinel-1 IW SLC frames cover the given geographic extent.
    
    Parameters:
        north (float): Northern latitude in degrees
        south (float): Southern latitude in degrees
        east (float): Eastern longitude in degrees
        west (float): Western longitude in degrees

    Returns:
        dict: estimated frame size (deg), and number of frames N-S and E-W
    """
    # Average latitude of the extent (used for E-W frame size estimation)
    mean_lat = (north + south) / 2.0
    mean_lat_rad = math.radians(mean_lat)

    # Approximate IW frame size in degrees:
    # N–S is roughly constant at 2.2°
    frame_lat_deg = 2.2

    # E–W varies by latitude: ~250 km wide, so:
    # 1° longitude ≈ 111.32 * cos(latitude)
    km_per_deg_lon = 111.32 * math.cos(mean_lat_rad)
    frame_width_km = 250.0
    frame_lon_deg = frame_width_km / km_per_deg_lon if km_per_deg_lon > 0 else 360.0

    # Input extent size
    extent_lat = abs(north - south)
    extent_lon = abs(east - west)

    # Estimate number of frames
    n_frames_lat = math.ceil(extent_lat / frame_lat_deg)
    n_frames_lon = math.ceil(extent_lon / frame_lon_deg)

    return {
        "frame_lat_deg": round(frame_lat_deg, 3),
        "frame_lon_deg": round(frame_lon_deg, 3),
        "estimated_frames_N_S": n_frames_lat,
        "estimated_frames_E_W": n_frames_lon,
        "total_estimated_frames": n_frames_lat * n_frames_lon
    }


def submit_gacos_batch(indir, aoi, email, sleep_time_range=(30, 300)):
    """
    Submit GACOS requests for batches of dates, sleeping a random interval between requests.

    Args:
        indir (str): Directory containing data.
        aoi (tuple): Area of interest as (N, W, E, S).
        email (str): Email address for GACOS.
        sleep_time_range (tuple): Min and max seconds to sleep between requests.
    """
    dates, hh, mm = calculate_average_acquisition_time(indir)
    
    N, W, E, S = aoi
    
    for batch in dates:
        date_str = "\n".join(batch)

        post_data = {
            "N": float(N),
            "W": float(W),
            "S": float(S),
            "E": float(E),
            "H": int(hh),
            "M": int(mm),
            "date": date_str,
            "type": "1",
            "email": email,
        }

        url = "http://www.gacos.net/M/action_page.php"

        try:
            r = requests.post(url, data=post_data)
            print(r.text)
        except Exception as e:
            print(f"❌ Error during submission for {batch}: {e}")

        # Sleep a random interval between requests to avoid being rejected
        sleep_time = np.random.randint(*sleep_time_range)
        print(f"Sleeping for {sleep_time} seconds before next request...")
        time.sleep(sleep_time)

def create_ref_point_ra(topodir, outmean):
    print("Creating reference point RA file from mean coherence grid...")
    outmean_base = os.path.basename(outmean)
    output = subprocess.check_output(f"gmt grdinfo -M {outmean}", shell=True).decode().strip().split()

    if outmean_base in ["corr_stack.grd", "corr_stack"]:  # handle both with/without extension
        # Find v_max and get corresponding x and y
        try:
            v_max = output.index('v_max:')
            x = output[v_max + 5]
            y = output[v_max + 8]
        except ValueError:
            raise RuntimeError("v_max not found in grdinfo output.")
    elif outmean_base in ["std.grd", "std"]:
        # Find v_min and get corresponding x and y
        try:
            v_min = output.index('v_min:')
            x = output[v_min + 5]
            y = output[v_min + 8]
        except ValueError:
            raise RuntimeError("v_min not found in grdinfo output.")
    else:
        raise ValueError(f"Unknown grid file: {outmean_base}")

    with open(os.path.join(topodir, "ref_point.ra"), 'w') as f:
        f.write(f"{x} {y}\n")

    # with open(os.path.join(topodir, "ref_point.ll"), 'w') as f:
    #     f.write(f"{lon} {lat} 0\n")
    # print("Creating ref_point_2.ra file...")
    # os.chdir(topodir)
    # subprocess.run(f"SAT_llt2rat {os.path.join(topodir, 'master.PRM')} 0 < {os.path.join(topodir, 'ref_point.ll')} > {os.path.join(topodir, 'ref_point_2.ra')}", shell=True)

###################################
# Process completion status check #
###################################

def check_align_completion(subswathdir):    
    pfraw = os.path.join(subswathdir, "raw")
    pmerge =os.path.join(os.path.dirname(subswathdir), "merge")
    if not os.path.exists(pfraw):
        # print(f"❌ Missing directory for {subswathdir}")
        return False
    if os.path.exists(pmerge) and os.path.exists(os.path.join(pmerge, "trans.dat")):
        print(f"✅ {subswathdir} seems to be already aligned because the subswaths seem to be merged.")
        return True
    else:
        # List all files ending with .SLC in the ddata directory
        slc_files = [f for f in os.listdir(pfraw) if f.endswith('.SLC')]
        tif_files = [f for f in os.listdir(pfraw) if f.endswith('.tiff')]
        if not slc_files and not tif_files:
            # print(f"❌ No SLC files or TIFF files found in {subswathdir}")
            return False
        else:
            if len(slc_files) != len(tif_files):
                # print(f"❌ File count mismatch: {len(slc_files)} SLC files vs {len(tif_files)} TIFF files")
                # print(f"❌ Alignment not completed successfully for {subswathdir}")
                return False
            else:
                print(f"✅ Alignment completed successfully for {subswathdir}")
                return True    
        
def check_ifgs_completion(subswathdir):
    intf = os.path.join(subswathdir, "intf.in")
    ifg_dir = os.path.join(subswathdir, "intf_all")
    intf_count = None
    if not os.path.exists(ifg_dir):
        print(f"❌ No IFGs generated for {subswathdir}")
        return False
    if not os.path.exists(intf):
        print(f"❌ Missing {intf} for {subswathdir}")
        return False
    else:
        with open(intf, "r") as f:
            intf_count = sum(1 for _ in f)
        # List all subdirectories in ifg_dir
        subdirs = [d for d in os.listdir(ifg_dir) if os.path.isdir(os.path.join(ifg_dir, d))]
        if intf_count and len(subdirs) != intf_count:
            print(f"❌ Only {len(subdirs)} out of {intf_count} IFGs present for {subswathdir}")
            return False
        else:
            print(f"✅ All IFGs present for {subswathdir}")
            return True
        
def check_merge_completion(indir):
    intf = os.path.join(indir, "F2", "intf.in")
    pmerge = os.path.join(indir, "merge")
    if not os.path.exists(pmerge):
        print(f"❌ Merge directory not found in {indir}")
        return False
    intf_count = None
    if not os.path.exists(intf):
        print(f"❌ Missing {intf} for {indir}")
        return False
    else:
        with open(intf, "r") as f:
            intf_count = sum(1 for _ in f)
    # List all subdirectories in pmerge
    subdirs = [d for d in os.listdir(pmerge) if os.path.isdir(os.path.join(pmerge, d))]
    if intf_count and len(subdirs) != intf_count:
        print(f"❌ Only {len(subdirs)} out of {intf_count} merged IFGs present for {indir}")
        return False
    else:
        print(f"✅ All IFGs merged for {indir}")
        return True

###########################
# Baseline plot functions #
###########################

def plot_baseline_table(root, baseline_table_path, row=1, column=1):
    # Read and parse the baseline table
    dates = []
    perp_baselines = []
    file_ids = []
    with open(baseline_table_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            file_id = parts[0]
            date_str = file_id.split('_')[1]  # Extract yyyymmdd
            try:
                date = datetime.strptime(date_str, "%Y%m%d")
            except ValueError:
                continue
            perp_baseline = float(parts[4])
            dates.append(date)
            perp_baselines.append(perp_baseline)
            file_ids.append(file_id)

    # Remove previous plot_frame if exists
    if hasattr(root, "plot_frame") and root.plot_frame.winfo_exists():
        root.plot_frame.destroy()

    plot_frame = tk.Frame(root)
    plot_frame.grid(row=row, column=column, sticky="nsew", padx=10, pady=10)
    root.plot_frame = plot_frame

    canvas_width = 1280
    canvas_height = 720
    margin_left = 80
    margin_right = 40
    margin_top = 40
    margin_bottom = 80

    canvas = tk.Canvas(plot_frame, width=canvas_width, height=canvas_height, bg="white")
    canvas.pack(fill=tk.BOTH, expand=True)

    # Calculate min/max for scaling
    if not dates or not perp_baselines:
        tk.Label(root, text="No valid data to plot.").grid(row=row, column=column)
        return None, None, None

    min_date = min(dates)
    max_date = max(dates)
    min_baseline = min(perp_baselines)
    max_baseline = max(perp_baselines)

    # Y-axis ticks: interval of at least 50m, rounded
    baseline_tick_interval = max(50, round((max_baseline - min_baseline) / 6 / 50) * 50)
    min_baseline_tick = (int(min_baseline // baseline_tick_interval) * baseline_tick_interval) - baseline_tick_interval
    max_baseline_tick = ((int(max_baseline // baseline_tick_interval) + 1) * baseline_tick_interval)
    baseline_ticks = []
    tick = min_baseline_tick
    while tick <= max_baseline_tick:
        baseline_ticks.append(tick)
        tick += baseline_tick_interval

    min_baseline_plot = min_baseline_tick
    max_baseline_plot = max_baseline_tick

    date_range_days = (max_date - min_date).days
    date_offset_days = max(10, int(date_range_days * 0.05))
    min_date_plot = min_date - timedelta(days=date_offset_days)
    max_date_plot = max_date + timedelta(days=date_offset_days)

    def date_to_x(date):
        total_days = (max_date_plot - min_date_plot).days or 1
        return margin_left + ((date - min_date_plot).days / total_days) * (canvas_width - margin_left - margin_right)

    def baseline_to_y(baseline):
        baseline_range_plot = max_baseline_plot - min_baseline_plot or 1
        return canvas_height - margin_bottom - ((baseline - min_baseline_plot) / baseline_range_plot) * (canvas_height - margin_top - margin_bottom)

    # Draw axes
    x_axis_y = baseline_to_y(min_baseline_plot)
    canvas.create_line(margin_left, x_axis_y, canvas_width - margin_right, x_axis_y)
    canvas.create_line(margin_left, baseline_to_y(max_baseline_plot), margin_left, x_axis_y)

    # Draw axis labels
    canvas.create_text(canvas_width // 2, x_axis_y + margin_bottom // 2, text="Date (mm/yy)")
    canvas.create_text(margin_left // 2, canvas_height // 2, text="Baseline (m)", angle=90)

    # Draw y-axis ticks and labels
    for baseline in baseline_ticks:
        y = baseline_to_y(baseline)
        canvas.create_line(margin_left - 8, y, margin_left, y)
        canvas.create_text(margin_left - 12, y, text=f"{baseline:.1f}", anchor="e", font=("Arial", 8))

    # X-axis ticks: quarterly or yearly, show only mm/yy for first date of each month
    month_years = []
    current = min_date_plot.replace(day=1)
    while current <= max_date_plot:
        month_years.append(current)
        year = current.year + (current.month // 12)
        month = current.month % 12 + 1
        current = current.replace(year=year, month=month)
    if len(month_years) > 12:
        x_ticks = [d for d in month_years if d.month == 1]
        tick_label_fmt = "%m/%y"
    else:
        x_ticks = [d for d in month_years if d.month in [1, 4, 7, 10]]
        tick_label_fmt = "%m/%y"
    # Always include min_date and max_date as candidates
    if min_date not in x_ticks:
        x_ticks.insert(0, min_date)
    if max_date not in x_ticks:
        x_ticks.append(max_date)
    x_ticks = sorted(set(x_ticks))

    # Remove extreme ticks if they are too close to the next tick (avoid overlapping)
    min_tick_x = date_to_x(min_date)
    max_tick_x = date_to_x(max_date)
    # Find the next tick after min_date and before max_date
    min_dist = None
    max_dist = None
    for d in x_ticks:
        if d > min_date:
            min_dist = abs(date_to_x(d) - min_tick_x)
            break
    for d in reversed(x_ticks):
        if d < max_date:
            max_dist = abs(date_to_x(d) - max_tick_x)
            break
    min_label_spacing = 35  # pixels, adjust as needed
    # Remove min_date if too close to next
    if min_dist is not None and min_dist < min_label_spacing:
        x_ticks = [d for d in x_ticks if d != min_date]
    # Remove max_date if too close to previous
    if max_dist is not None and max_dist < min_label_spacing:
        x_ticks = [d for d in x_ticks if d != max_date]

    # Draw x-axis ticks and labels
    for tick_date in x_ticks:
        x = date_to_x(tick_date)
        canvas.create_line(x, x_axis_y, x, x_axis_y + 8)
        canvas.create_text(x, x_axis_y + 20, text=tick_date.strftime(tick_label_fmt), anchor="n", font=("Arial", 8))

    # Draw points and labels
    points = []
    for idx, (date, baseline, file_id) in enumerate(zip(dates, perp_baselines, file_ids)):
        x = date_to_x(date)
        y = baseline_to_y(baseline)
        pt_tag = f"pt{idx}"
        canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill="blue", tags=pt_tag)
        # Store all relevant attributes in a dict for each point
        points.append({
            "x": x,
            "y": y,
            "idx": idx,
            "date": date,
            "baseline": baseline,
            "file_id": file_id,
            "tag": pt_tag
        })
        canvas.create_text(x, y - 14, text=date.strftime("%d/%m"), font=("Verdana", 6), anchor="s")

    # Return plot_frame, canvas, points, and also dates/perp_baselines for later use
    return plot_frame, canvas, points, dates, perp_baselines

def connect_baseline_nodes(canvas, points, dates, perp_baselines, perp_constraint, temp_constraint):
    # Connect all nodes within constraints (no interactivity)
    edges = []
    n = len(points)
    for i in range(n):
        for j in range(i + 1, n):
            date1 = dates[i]
            date2 = dates[j]
            baseline1 = perp_baselines[i]
            baseline2 = perp_baselines[j]
            temp_diff = abs((date2 - date1).days)
            perp_diff = abs(baseline2 - baseline1)
            if temp_diff <= temp_constraint and perp_diff <= perp_constraint:
                x1, y1 = points[i]["x"], points[i]["y"]
                x2, y2 = points[j]["x"], points[j]["y"]
                line_id = canvas.create_line(x1, y1, x2, y2, fill="black", width=0.1)
                edges.append((line_id, i, j))
    return edges

def interactive_baseline_edges(canvas, points, edges):
    point_radius = 12
    edge_proximity = 8
    selected_points = []
    selected_edge = None

    def reset_point_colors():
        for idx in range(len(points)):
            canvas.delete(f"pt{idx}")
            x, y = points[idx]["x"], points[idx]["y"]
            canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill="blue", tags=f"pt{idx}")

    def reset_selection():
        nonlocal selected_points, selected_edge
        selected_points.clear()
        if selected_edge is not None:
            canvas.itemconfig(selected_edge, fill="black", width=1)
            selected_edge = None
        reset_point_colors()

    def on_canvas_click(event):
        nonlocal selected_edge
        for pt in points:
            x, y, idx = pt["x"], pt["y"], pt["idx"]
            if abs(event.x - x) <= point_radius and abs(event.y - y) <= point_radius:
                canvas.itemconfig(f"pt{idx}", fill="red")
                canvas.delete(f"pt{idx}")
                canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill="red", tags=f"pt{idx}")
                selected_points.append(idx)
                if len(selected_points) == 2:
                    idx1, idx2 = selected_points
                    x1, y1 = points[idx1]["x"], points[idx1]["y"]
                    x2, y2 = points[idx2]["x"], points[idx2]["y"]
                    if not any((e[1] == idx1 and e[2] == idx2) or (e[1] == idx2 and e[2] == idx1) for e in edges):
                        line_id = canvas.create_line(x1, y1, x2, y2, fill="black", width=0.1)
                        edges.append((line_id, idx1, idx2))
                    reset_point_colors()
                    selected_points.clear()
                return

        # Edge selection
        clicked_edge = None
        for line_id, idx1, idx2 in edges:
            coords = canvas.coords(line_id)
            if len(coords) == 4:
                x1, y1, x2, y2 = coords
                px, py = event.x, event.y
                dx, dy = x2 - x1, y2 - y1
                if dx == dy == 0:
                    continue
                t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
                nearest_x = x1 + t * dx
                nearest_y = y1 + t * dy
                dist = ((px - nearest_x) ** 2 + (py - nearest_y) ** 2) ** 0.5
                if dist < edge_proximity:
                    clicked_edge = line_id
                    break
        if clicked_edge is not None:
            if selected_edge == clicked_edge:
                canvas.itemconfig(selected_edge, fill="black", width=1)
                selected_edge = None
            else:
                if selected_edge is not None:
                    canvas.itemconfig(selected_edge, fill="black", width=1)
                selected_edge = clicked_edge
                canvas.itemconfig(selected_edge, fill="red", width=3)

    def on_delete(event):
        nonlocal selected_edge
        if selected_edge is not None:
            canvas.delete(selected_edge)
            edges_to_remove = [e for e in edges if e[0] == selected_edge]
            for e in edges_to_remove:
                try:
                    canvas.delete(e[0])
                except Exception:
                    pass
                edges.remove(e)
            selected_edge = None

    # Bind events
    canvas.bind("<Button-1>", on_canvas_click)
    canvas.bind_all("<Delete>", on_delete)

    return {
        "click": on_canvas_click,
        "delete": on_delete,
        "reset": reset_selection
    }
###########################################################################
############################## OUT TURN ###################################
###########################################################################
def velkml(indir):
    print(f'Converting vel grd to kml for {os.path.basename(indir)}')
    os.chdir(indir)
    maindir = os.path.dirname(indir)
    pmerge = os.path.join(maindir, "merge")
    IFGs = []
    g = None
    if os.path.exists(pmerge):
        intfdir = pmerge
        create_symlink(os.path.join(intfdir, 'trans.dat'), '.') 
        pF2intfdir = os.path.join(maindir, "F2", "intf_all")
        g = os.path.join(pF2intfdir, next(os.walk(pF2intfdir))[1][0], 'gauss_*')
        run_command(f'ln -s {g} .')
    else:
        for subswath in ["F1", "F2", "F3"]:
            dir_path = os.path.join(maindir, subswath)
            if os.path.exists(dir_path):
                intfdir = os.path.join(dir_path, "intf_all")
                create_symlink(os.path.join(dir_path, 'topo', 'trans.dat'), '.')
                IFGs = next(os.walk(intfdir))[1]
                g = os.path.join(intfdir, IFGs[0], 'gauss_*')
                run_command(f'ln -s {g} .')
                break   
      

    if not os.path.exists('vel_ll.grd'):
        # Convert vel.grd to geographic coordinates using proj_ra2ll.csh
        run_command("proj_ra2ll.csh trans.dat vel.grd vel_ll.grd")

        # Generate a color palette table (CPT) for the grid
        run_command("gmt grd2cpt vel_ll.grd -T= -Z -Cjet > vel_ll.cpt")


        # Generate the KML file from the .grd file
        run_command("grd2kml.csh vel_ll vel_ll.cpt")
        '''gmt grd2cpt: This is a command from the Generic Mapping Tools (GMT) suite that generates a color palette table (CPT) based on the data in a grid file.
    vel_ll.grd: The input grid file containing your raster data (e.g., velocity values).
    -T=: Specifies that the CPT should be scaled automatically to cover the range of the grid. The = means GMT will choose limits based on the data's actual min/max values.
    -Z: Ensures that the CPT is continuous, without discrete color bands. This produces a gradient effect across the color scale.
    -Cjet: Specifies the color scheme to use, in this case, jet, which is a popular color scale that transitions through blue, cyan, green, yellow, and red.
    > vel_ll.cpt: Redirects the output to a file named vel_ll.cpt, which stores the generated CPT.'''

        # Add a legend to the KML file
        run_command(
            "gmt psscale -Cvel_ll.cpt -Dx1i/0.5i+w5i/0.25i -Bx5f5+l\"Velocity (mm/yr)\" -By+f\"%.2f\" > legend.ps")
        '''gmt psscale: This command creates a color scale (legend) based on a given CPT file.
    -Cvel_ll.cpt: Specifies the CPT file to use (vel_ll.cpt), which was generated by grd2cpt.
    -Dx1i/0.5i+w5i/0.25i: Sets the position and size of the scale bar.
        -D indicates that a scale bar is to be drawn.
        x1i/0.5i sets the reference point of the scale (1 inch from the left and 0.5 inches from the bottom).
        w5i/0.25i specifies the width (5 inches) and height (0.25 inches) of the scale bar.
    -Bx5f5+l"Velocity (mm/yr)":
        -Bx5f5 specifies the annotations on the x-axis. The 5 means major ticks are labeled every 5 units, and f5 adds minor ticks every 5 units.
        +l"Velocity (mm/yr)" adds a label to the x-axis.
    -By+f"%.2f": Formats the numbers on the scale to show only two decimal places (%.2f).
    > legend.ps: Redirects the output to a PostScript file named legend.ps, which contains the visual representation of the legend.'''

        run_command("gmt psconvert legend.ps -A -Tg -W+k+l100/100 > legend.png")
        '''gmt psconvert: This is a GMT command used to convert PostScript (PS) files to other formats, such as PNG, PDF, or JPG.
legend.ps: The input file in PostScript format that you want to convert (in this case, the legend generated by the psscale command).
-A: Trims the output by removing any surrounding white space around the content. This makes the output image more compact and eliminates unnecessary margins.
-Tg: Specifies the output format, with g indicating PNG format (e.g., -Tg means the output will be legend.png).
-W+k+l100/100:

    -W: Applies anti-aliasing to improve the appearance of the image.
    +k: Ensures that the background color is kept in the output.
    +l100/100: Controls the DPI (dots per inch) for the output image, where 100/100 sets the horizontal and vertical DPI to 100. This affects the resolution and quality of the resulting image.'''

        # Assuming the KML file was named `vel_ll.kml`:
        with open('vel_ll.kml', 'r') as file:
            kml_data = file.read()

        legend_overlay = """
		<ScreenOverlay>
			<name>Legend</name>
			<Icon>
				<href>legend.png</href>
			</Icon>
			<overlayXY x="0" y="0" xunits="fraction" yunits="fraction"/>
			<screenXY x="0.05" y="0.05" xunits="fraction" yunits="fraction"/>
			<rotationXY x="0" y="0" xunits="fraction" yunits="fraction"/>
			<size x="0.05" y="0.5" xunits="fraction" yunits="fraction"/>
		</ScreenOverlay>
		"""

        # Insert the legend inside the <Document> tag
        if '<Document>' in kml_data:
            kml_data = kml_data.replace('<Document>', '<Document>' + legend_overlay)
        else:
            print("Error: No <Document> or <Folder> tag found in KML file.")

        # Insert the legend overlay before the closing tag
        # kml_data = kml_data.replace("</kml>", legend_overlay)

        # Write the updated KML data back to the file
        with open('vel_ll_with_legend.kml', 'w') as file:
            file.write(kml_data)

        print('Created KML file')


def projgrd(indir):
    print(f'Projecting for {indir}')
    os.chdir(indir)
    # Regex pattern: disp_<7digits>.grd
    pattern = re.compile(r"^disp_\d{7}\.grd$")
    grds =  [os.path.join(indir, f) for f in os.listdir(indir) if pattern.match(f)]
    grdsout = [x.replace('.grd', '_ll.grd') for x in grds]
    for i in range(0, len(grds)):
        print(f'{i} Projecting {os.path.basename(grds[i])}')
        run_command(f'proj_ra2ll.csh trans.dat {grds[i]} {grdsout[i]}')