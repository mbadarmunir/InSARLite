"""
UI Factory module for InSARLite.
Contains widget creation and layout functions to reduce main.py complexity.
"""

import os
import tkinter as tk
import datetime
from tkintermapview import TkinterMapView
from ..utils.utils import add_tooltip, browse_folder, browse_file
from .gui_helpers import validate_float

# WSL detection for calendar widget compatibility
def is_wsl_or_problematic_env():
    """Detect if running in WSL where calendar popups might not work properly"""
    # Check for WSL-specific environment variables
    wsl_env_vars = ['WSL_DISTRO_NAME', 'WSL_INTEROP', 'WSLENV']
    if any(os.environ.get(var) for var in wsl_env_vars):
        return True
    
    # Check /proc/version for Microsoft/WSL indicators
    try:
        with open('/proc/version', 'r') as f:
            version = f.read().lower()
            if 'microsoft' in version or 'wsl' in version:
                return True
    except:
        pass
    
    return False

# Conditional import of DateEntry
USE_CALENDAR_WIDGET = not is_wsl_or_problematic_env()

if USE_CALENDAR_WIDGET:
    try:
        from tkcalendar import DateEntry
    except ImportError:
        USE_CALENDAR_WIDGET = False
        print("Warning: tkcalendar not available, using text entry fields for dates")

if not USE_CALENDAR_WIDGET:
    print("Using text entry fields for dates (calendar widgets disabled for compatibility)")
    # Create a fallback DateEntry-like class
    class DateEntry(tk.Entry):
        def __init__(self, parent, textvariable=None, date_pattern='yyyy-mm-dd', **kwargs):
            # Remove calendar-specific kwargs that Entry doesn't understand
            kwargs.pop('background', None)
            kwargs.pop('foreground', None) 
            kwargs.pop('borderwidth', None)
            kwargs.pop('validate', None)
            super().__init__(parent, textvariable=textvariable, **kwargs)
            self.date_pattern = date_pattern
            
        def set_date(self, date_obj):
            """Set date using date object"""
            if hasattr(date_obj, 'strftime'):
                self.delete(0, tk.END)
                self.insert(0, date_obj.strftime('%Y-%m-%d'))
        
        def get_date(self):
            """Get date as string"""
            return self.get()


class UIFactory:
    """Factory class for creating UI widgets and layouts."""
    
    @staticmethod
    def create_extent_widgets(parent, root):
        """Create extent input widgets."""
        extent_frame = tk.Frame(parent)
        extent_frame.grid(row=1, column=0, columnspan=6, sticky="ew", padx=5, pady=5)
        add_tooltip(extent_frame, "Area of Interest (AOI) Definition\nSpecify geographical boundaries for data search and processing")
        
        # Validation command for float entries
        vcmd = (root.register(validate_float), "%P")
        
        def entry(label, row, col, sticky, tooltip_text):
            lbl = tk.Label(extent_frame, text=label)
            lbl.grid(row=row, column=col, padx=2, pady=2, sticky=sticky)
            add_tooltip(lbl, tooltip_text)
            e = tk.Entry(extent_frame, width=8, validate="key", validatecommand=vcmd)
            e.grid(row=row, column=col+1, padx=2, pady=2, sticky=sticky)
            return e
        
        n_entry = entry("N", 0, 2, "s", "North latitude boundary (maximum latitude)")
        s_entry = entry("S", 2, 2, "n", "South latitude boundary (minimum latitude)")
        w_entry = entry("W", 1, 0, "e", "West longitude boundary (minimum longitude)")
        e_entry = entry("E", 1, 4, "w", "East longitude boundary (maximum longitude)")
        
        return extent_frame, n_entry, s_entry, e_entry, w_entry

    @staticmethod
    def create_map_widget(parent):
        """Create the interactive map widget."""
        map_widget = TkinterMapView(parent, width=800, height=400, corner_radius=0)
        map_widget.grid(row=2, column=0, columnspan=6, sticky="nsew", padx=5, pady=5)
        map_widget.set_position(20, 0)
        map_widget.set_zoom(2)
        add_tooltip(map_widget, "Interactive Map\nClick and drag to select area of interest\nUse mouse wheel to zoom\nRight-click for context menu")
        return map_widget

    @staticmethod
    def create_legend_frame(parent):
        """Create the legend frame for map symbols."""
        legend_frame = tk.Frame(parent)
        legend_frame.grid(row=3, column=0, columnspan=6, sticky="ew", padx=5, pady=2)
        add_tooltip(legend_frame, "Map Legend\nShows available data coverage and selection status")
        return legend_frame

    @staticmethod
    def create_date_widgets(parent):
        """Create date selection widgets."""
        date_frame = tk.Frame(parent)
        date_frame.grid(row=4, column=0, columnspan=6, sticky="ew", padx=5, pady=5)
        add_tooltip(date_frame, "Temporal Range Selection\nSpecify time period for data search and processing")
        
        today = datetime.date.today()
        default_start = today - datetime.timedelta(days=30)
        
        # Start date
        start_label = tk.Label(date_frame, text="Start Date:")
        start_label.grid(row=0, column=0, sticky="e", padx=(0, 5))
        add_tooltip(start_label, "Start date for data acquisition period\nFormat: YYYY-MM-DD")
        
        start_var = tk.StringVar()
        
        if USE_CALENDAR_WIDGET:
            # Use DateEntry with calendar popup
            start_date = DateEntry(
                date_frame,
                textvariable=start_var,
                width=12,
                background='darkblue',
                foreground='white',
                borderwidth=2,
                date_pattern='yyyy-mm-dd',
                validate="none"  # Don't validate on every keystroke
            )
            add_tooltip(start_date, "Click to open calendar picker\nOr type date in YYYY-MM-DD format")
        else:
            # Use simple text entry
            start_date = DateEntry(
                date_frame,
                textvariable=start_var,
                width=12,
                date_pattern='yyyy-mm-dd'
            )
            add_tooltip(start_date, "Enter date in YYYY-MM-DD format")
            
        start_date.grid(row=0, column=1, sticky="w", padx=(0, 10))
        start_date.set_date(default_start)
        
        # End date
        end_label = tk.Label(date_frame, text="End Date:")
        end_label.grid(row=0, column=4, sticky="e", padx=(10, 5))
        add_tooltip(end_label, "End date for data acquisition period\nFormat: YYYY-MM-DD")
        
        end_var = tk.StringVar()
        
        if USE_CALENDAR_WIDGET:
            # Use DateEntry with calendar popup
            end_date = DateEntry(
                date_frame,
                textvariable=end_var,
                width=12,
                background='darkblue',
                foreground='white',
                borderwidth=2,
                date_pattern='yyyy-mm-dd',
                validate="none"  # Don't validate on every keystroke
            )
            add_tooltip(end_date, "Click to open calendar picker\nOr type date in YYYY-MM-DD format")
        else:
            # Use simple text entry
            end_date = DateEntry(
                date_frame,
                textvariable=end_var,
                width=12,
                date_pattern='yyyy-mm-dd'
            )
            add_tooltip(end_date, "Enter date in YYYY-MM-DD format")
        
        end_date.grid(row=0, column=5, sticky="w")
        end_date.set_date(today)
        
        return date_frame, start_var, end_var, start_date, end_date

    @staticmethod
    def create_flight_dir_widgets(parent):
        """Create flight direction selection widgets."""
        flight_dir_frame = tk.Frame(parent)
        flight_dir_frame.grid(row=5, column=0, columnspan=6, sticky="ew", padx=5, pady=5)
        add_tooltip(flight_dir_frame, "Satellite Flight Direction\nSentinel-1 orbit direction affects data characteristics")
        
        flight_dir_label = tk.Label(flight_dir_frame, text="Flight Direction:")
        flight_dir_label.pack(side="left", padx=(0, 10))
        add_tooltip(flight_dir_label, "Choose satellite orbital direction:\nAscending: South to North\nDescending: North to South")
        
        flight_dir_var = tk.StringVar(value="Descending")
        
        ascending_rb = tk.Radiobutton(flight_dir_frame, text="Ascending", variable=flight_dir_var, value="Ascending")
        ascending_rb.pack(side="left", padx=(0, 10))
        add_tooltip(ascending_rb, "Ascending orbit: Satellite moves from South to North\nTypically acquired in the evening")
        
        descending_rb = tk.Radiobutton(flight_dir_frame, text="Descending", variable=flight_dir_var, value="Descending")
        descending_rb.pack(side="left")
        add_tooltip(descending_rb, "Descending orbit: Satellite moves from North to South\nTypically acquired in the morning")
        
        return flight_dir_frame, flight_dir_var, ascending_rb, descending_rb

    @staticmethod
    def create_data_folder_widgets(parent, on_data_folder_change, validate_path_syntax):
        """Create data folder selection widgets."""
        data_folder_frame = tk.Frame(parent)
        data_folder_frame.grid(row=6, column=0, columnspan=6, sticky="ew", padx=5, pady=5)
        add_tooltip(data_folder_frame, "Data Directory Selection\nChoose folder containing Sentinel-1 data (ZIP files or extracted SAFE directories)")
        
        data_folder_label = tk.Label(data_folder_frame, text="Data Folder:")
        data_folder_label.grid(row=0, column=0, sticky="e", padx=(0, 5))
        add_tooltip(data_folder_label, "Path to folder containing Sentinel-1 SLC data\nSupports both ZIP archives and extracted SAFE directories")
        
        data_folder_entry = tk.Entry(data_folder_frame, width=60)
        data_folder_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        data_folder_frame.columnconfigure(1, weight=1)
        add_tooltip(data_folder_entry, "Enter or browse to select data folder\nShould contain S1*.zip files or S1*.SAFE directories")
        
        data_browse = tk.Button(
            data_folder_frame, 
            text="Load", 
            command=lambda: browse_folder(data_folder_entry, "in_data_dir")
        )
        data_browse.grid(row=0, column=2, padx=(5, 0))
        add_tooltip(data_browse, "Browse and select data folder\nButton color indicates data status:\nGreen: Valid data found\nYellow: ZIP files need extraction\nRed: No valid data found")
        
        # Bind events
        data_folder_entry.bind("<KeyRelease>", validate_path_syntax)
        data_folder_entry.bind("<FocusOut>", on_data_folder_change)
        
        return data_folder_frame, data_folder_entry, data_browse

    @staticmethod
    def create_action_buttons(parent):
        """Create main action buttons."""
        button_frame = tk.Frame(parent)
        button_frame.grid(row=7, column=0, columnspan=6, sticky="ew", padx=5, pady=10)
        add_tooltip(button_frame, "Main Action Buttons\nPrimary controls for data search and download")
        
        # Data Query button (initially hidden)
        data_query_btn = tk.Button(button_frame, text="Search Data", state="disabled")
        add_tooltip(data_query_btn, "Search for available Sentinel-1 data\nRequires valid extent and date range")
        
        # Data Download button (initially hidden)  
        data_download_btn = tk.Button(button_frame, text="Start Download", state="disabled")
        add_tooltip(data_download_btn, "Download selected Sentinel-1 acquisitions\nRequires completed data search")
        
        return button_frame, data_query_btn, data_download_btn

    @staticmethod
    def create_subswath_controls(parent, safe_dirs, zip_files, row_func):
        """Create subswath selection controls."""
        if safe_dirs:
            # Get unique subswaths from SAFE directories
            subswaths = set()
            for safe_dir in safe_dirs:
                measurement_dir = os.path.join(safe_dir, "measurement")
                if os.path.isdir(measurement_dir):
                    for f in os.listdir(measurement_dir):
                        if f.lower().endswith(".tiff"):
                            parts = f.split('-')
                            if len(parts) >= 2 and parts[1].startswith('iw'):
                                try:
                                    sw_num = int(parts[1][2])
                                    if 1 <= sw_num <= 3:
                                        subswaths.add(sw_num)
                                except (ValueError, IndexError):
                                    continue
        elif zip_files:
            # For now, assume all subswaths are available in ZIP files
            subswaths = {1, 2, 3}
        else:
            subswaths = set()
        
        if subswaths:
            # Create subswath frame
            subswath_frame = tk.Frame(parent)
            subswath_frame.grid(row=row_func("subswath"), column=0, columnspan=6, sticky="ew", padx=5, pady=5)
            
            subswath_label = tk.Label(subswath_frame, text="Subswaths:")
            subswath_label.pack(side="left", padx=(0, 10))
            add_tooltip(subswath_label, "Select Sentinel-1 subswaths to process\nIW1, IW2, IW3 correspond to different swath positions")
            
            subswath_vars = {}
            checkboxes = {}
            
            for i in sorted(subswaths):
                var = tk.BooleanVar()
                var.set(True)  # Default to selected
                cb = tk.Checkbutton(subswath_frame, text=f"IW{i}", variable=var)
                cb.pack(side="left", padx=(0, 10))
                add_tooltip(cb, f"Interferometric Wide swath {i}\nEach subswath covers different ground area")
                
                subswath_vars[i] = var
                checkboxes[i] = cb
            
            return subswath_frame, subswath_vars, checkboxes
        
        return None, {}, {}

    @staticmethod
    def create_polarization_controls(parent, dir_pol_summary, zip_pol_summary, row_func):
        """Create polarization selection controls."""
        # Combine polarization info from both sources
        combined_summary = {}
        if dir_pol_summary:
            combined_summary.update(dir_pol_summary)
        if zip_pol_summary:
            for pol, count in zip_pol_summary.items():
                combined_summary[pol] = combined_summary.get(pol, 0) + count
        
        if combined_summary:
            pol_frame = tk.Frame(parent)
            pol_frame.grid(row=row_func("polarization"), column=0, columnspan=6, sticky="ew", padx=5, pady=5)
            
            pol_label = tk.Label(pol_frame, text="Polarization:")
            pol_label.pack(side="left", padx=(0, 10))
            add_tooltip(pol_label, "Select radar polarization mode\nDifferent polarizations provide different information about targets")
            
            pol_var = tk.StringVar()
            
            # Set default polarization
            available_pols = list(combined_summary.keys())
            if 'VV' in available_pols:
                pol_var.set('VV')
            else:
                pol_var.set(available_pols[0])
            
            pol_controls = {}
            for pol in available_pols:
                count = combined_summary[pol]
                rb = tk.Radiobutton(pol_frame, text=f"{pol} ({count})", variable=pol_var, value=pol)
                rb.pack(side="left", padx=(0, 10))
                
                tooltip_text = {
                    'VV': "Vertical transmit, Vertical receive\nGood for surface roughness and vegetation",
                    'VH': "Vertical transmit, Horizontal receive\nSensitive to volume scattering",
                    'HH': "Horizontal transmit, Horizontal receive\nGood for surface features",
                    'HV': "Horizontal transmit, Vertical receive\nSensitive to vegetation structure"
                }.get(pol, f"{pol} polarization")
                
                add_tooltip(rb, f"{tooltip_text}\n{count} images available")
                pol_controls[pol] = rb
            
            return pol_frame, pol_var, pol_controls
        
        return None, None, {}