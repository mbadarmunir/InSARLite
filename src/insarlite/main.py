import os
import math
import threading
import datetime
import tkinter as tk
from tkinter import messagebox
import platform

# WSL/Linux detection for calendar widget compatibility
def is_wsl_or_problematic_env():
    """Detect if running in WSL where calendar popups might not work properly"""
    try:
        # Check specifically for WSL (not general Linux)
        if 'microsoft' in platform.uname().release.lower():
            return True
        # Check for WSL2 specifically
        if 'Microsoft' in platform.uname().release:
            return True
        # Check for specific WSL environment variables
        if 'WSL_DISTRO_NAME' in os.environ:
            return True
        return False
    except:
        return False

# Conditional import of DateEntry
USE_CALENDAR_WIDGET = not is_wsl_or_problematic_env()

if USE_CALENDAR_WIDGET:
    try:
        from tkcalendar import DateEntry
    except ImportError:
        USE_CALENDAR_WIDGET = False
        print("⚠️  tkcalendar not available, using text entry fields for dates")

if not USE_CALENDAR_WIDGET:
    print("📅 Using text entry fields for dates (calendar widgets disabled for compatibility)")

from tkintermapview import TkinterMapView
import glob
from .utils.utils import (
    browse_folder, browse_file, extr_ext_TL, configure_zooming_ui,
    submit_gacos_batch, estimate_s1_slc_frames,
    check_alignment_completion_status, check_ifgs_completion, check_merge_completion, process_logger, add_tooltip
)
from .utils.file_operations import (
    clamp, get_safe_and_zip_files, are_files_identical,
    extract_extent_from_zip_manifests, extract_zip_files_with_progress,
    summarize_polarizations_from_files
)
from .utils.gui_helpers import (
    validate_float, validate_dates_gentle, enforce_extent_limits,
    try_draw_from_entries, validate_path_syntax, clear_entry_focus,
    validate_dates_strict, enforce_date_limits, update_data_query_btn_state,
    draw_rectangle_on_map, update_extent_entries_from_map, on_map_click_with_limits,
    disable_extent_editing, enable_extent_editing, set_default_date_range_if_empty,
    display_extent_labels, set_extent_entry_values, get_aoi_wkt
)
from .utils.data_handlers import DataHandlers
from .utils.config_manager import config_manager
from .utils.gmtsar_installer import check_and_install_gmtsar
from .gmtsar_gui.data_dwn import search_sentinel1_acquisitions, download_sentinel1_acquisitions
from .gmtsar_gui.dem_dwn import make_dem
from .gmtsar_gui.structuring import orchestrate_structure_and_copy
from .gmtsar_gui.orbitsdownload import process_files
from .gmtsar_gui.base2net import BaselineGUI
from .gmtsar_gui.align_genIFGs import GenIfg
from .gmtsar_gui.sbas04 import SBASApp
from .gmtsar_gui.unwrap import UnwrapApp
import time
import re
import subprocess
import json
import inspect

class InSARLiteApp:
    LABELS = ["Elapsed", "Downloaded", "Speed", "Mean", "Completion", "ETA"]
    POLY_COLORS = ["green", "yellow", "black"]

    def __init__(self, root):
        self.root = root
        self.mst = None
        self.root.title("InSARLite Workflow Studio")
        add_tooltip(self.root, "InSARLite: Complete InSAR Time Series Processing Workflow\nSupports Sentinel-1 data processing from download to deformation analysis")
        
        self.DEFAULT_BROWSE_BG = self.root.cget("bg")
        self._global_pause_event = threading.Event()
        configure_zooming_ui(self.root)
        
        # Check GMTSAR availability on every startup
        self._check_gmtsar_installation()
        
        self._init_state()
        self._row = 0
        self._row_map = {}
        self._create_widgets()
        self._bind_events()
        self._try_auto_draw()
        self._update_data_query_btn_state_wrapper()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        # self._add_pause_button()

    def _on_close(self):
        # Cancel any pending validation timer
        if hasattr(self, '_date_validation_timer') and self._date_validation_timer:
            self.root.after_cancel(self._date_validation_timer)
        self._set_global_pause_flag(False)
        self.root.destroy()
        os._exit(0)

    def _check_gmtsar_installation(self):
        """Check if GMTSAR is available using projects file optimization."""
        # Get projects file path from config_manager
        projects_file = config_manager.projects_file
        
        # Use optimized check that first looks for projects file
        success = check_and_install_gmtsar(projects_file)
        
        if success == "close_app":
            # GMTSAR was installed, but app needs to close for environment variables to take effect
            try:
                messagebox.showinfo(
                    "Installation Complete", 
                    "GMTSAR installation completed!\n\n"
                    "InSARLite will now close so you can restart your terminal.\n"
                    "Please restart your terminal and launch InSARLite again."
                )
            except:
                print("GMTSAR installation completed!")
                print("Please restart your terminal and launch InSARLite again.")
            
            self.root.destroy()
            import sys
            sys.exit(0)
        elif not success:
            # Show error and exit - InSARLite cannot work without GMTSAR
            try:
                messagebox.showerror(
                    "GMTSAR Required", 
                    "InSARLite cannot function without GMTSAR.\n"
                    "Please install GMTSAR manually and restart the application."
                )
            except:
                print("ERROR: InSARLite cannot function without GMTSAR.")
                print("Please install GMTSAR manually and restart the application.")
            
            self.root.destroy()
            import sys
            sys.exit(1)

    def _set_global_pause_flag(self, value):
        if value:
            self._global_pause_event.set()
        else:
            self._global_pause_event.clear()

    def is_paused(self):
        return self._global_pause_event.is_set()

    def _add_pause_button(self, row=0):
        if not hasattr(self, "pause_btn") or self.pause_btn is None:
            self.pause_btn = tk.Button(
                self.root, text="Pause", command=self._toggle_pause,
                bg="orange", activebackground="orange"
            )
            add_tooltip(self.pause_btn, "Pause/Resume download process\nPauses active downloads temporarily\nButton color indicates state:\n• Orange: Ready to pause\n• Yellow: Paused, click to resume")
        self.pause_btn.grid(row=row, column=5, padx=10, pady=5, sticky="e")

    def _toggle_pause(self):
        if self.is_paused():
            self._set_global_pause_flag(False)
            self.pause_btn.config(text="Pause", bg="orange", activebackground="orange")
        else:
            self._set_global_pause_flag(True)
            self.pause_btn.config(text="Resume", bg="yellow", activebackground="yellow")

    def _show_pause_button(self, row=0):
        """Show the pause button during download."""
        if not hasattr(self, "pause_btn") or not self.pause_btn:
            self._add_pause_button(row)
        else:
            self.pause_btn.grid(row=row, column=5, padx=10, pady=5, sticky="e")

    def _hide_pause_button(self):
        """Hide the pause button when download is not in progress."""
        if hasattr(self, "pause_btn") and self.pause_btn and self.pause_btn.winfo_exists():
            self.pause_btn.grid_remove()
            # Optionally destroy the button to free resources
            self.pause_btn.destroy()
            self.pause_btn = None

    def _next_row(self, key=None):
        row = self._row
        self._row += 1
        if key:
            self._row_map[key] = row
        return row

    def _get_row(self, key):
        return self._row_map.get(key, None)

    def _init_state(self):
        self.extent_limits = dict.fromkeys("swne")
        self.date_limits = {"sdate": None, "edate": None}
        self.rect_shape = [None]
        self.legend_items = []
        self.legend_selected_idx = [None]
        self.on_data_query = type("on_data_query", (), {})()
        self.on_data_query.polygons = []
        self.on_data_query.last_result = None
        self.selected_files_info = None
        self.total_expected_size = None
        self.custom_shape = None
        self.safe_dirs_label = None
        self.download_stats_labels = {}
        self.conf_path = None  # Will be set dynamically
        self._date_validation_timer = None  # For debounced date validation
        self._zip_derived_values = False  # Flag to prevent config overwriting zip-derived values
        self.pause_btn = None  # Initialize pause button as None

    def _create_widgets(self):
        self._row = 0
        self._create_extent_widgets()
        self._create_map_widget()
        self._create_legend_frame()
        self._create_date_widgets()
        self._create_flight_dir_widgets()
        self._create_data_folder_widgets()
        self._create_action_buttons()
        self._set_controls_state("disabled" if not self.data_folder_entry.get().strip() else "normal")        
        self._show_project_selection_popup()
        

    def _show_project_selection_popup(self):
        """Show project selection popup using config manager."""
        # Get valid projects from config manager
        valid_projects = config_manager.get_valid_projects()
        
        # Show popup if any valid projects
        popup = tk.Toplevel(self.root)
        popup.title("Select Project")
        add_tooltip(popup, "Choose from existing projects or start new\nPrevious projects are automatically validated")
        
        tk.Label(popup, text="Select a previous project or start a new one:").pack(padx=20, pady=10)
        listbox = tk.Listbox(popup, width=60, height=min(12, len(valid_projects)+1))
        for entry in valid_projects:
            out_folder = entry.get("output_folder", "")
            proj_name = entry.get("project_name", "")
            listbox.insert(tk.END, f"{out_folder} > {proj_name}")
        listbox.pack(padx=20, pady=5)

        btn_frame = tk.Frame(popup)
        btn_frame.pack(pady=10)

        def on_select():
            idx = listbox.curselection()
            if idx:
                entry = valid_projects[idx[0]]
                config_manager.set_config_path(
                    entry.get("output_folder", ""), entry.get("project_name", "")
                )
                popup.destroy()
                self._load_config()
            else:
                messagebox.showinfo("Select Project", "Please select a project from the list.")

        def on_new():
            popup.destroy()

        tk.Button(btn_frame, text="Load Selected", command=on_select, width=14).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Start New Project", command=on_new, width=14).pack(side="left", padx=8)

        popup.transient(self.root)
        popup.grab_set()

        # Instead of blocking with wait_window(), use a callback
        def on_popup_close():
            if popup.winfo_exists():
                popup.destroy()
            self._refresh_map_widget()  # refresh after popup closes

        popup.protocol("WM_DELETE_WINDOW", on_popup_close)

    def _refresh_map_widget(self):
        """Refresh the map widget if it exists."""
        if hasattr(self, "map_widget") and self.map_widget is not None:
            try:
                self.map_widget.set_zoom(self.map_widget.zoom + 1)
                self.map_widget.set_zoom(self.map_widget.zoom - 1)
                self.map_widget.set_position(20, 0)
            except Exception:
                pass

    def _save_config(self):
        """Save configuration using config manager."""
        # Only save if output controls exist
        if not (hasattr(self, "output_folder_entry") and hasattr(self, "project_name_entry")):
            messagebox.showwarning("Save Config", "Cannot save configuration: output controls not available.")
            return
            
        out_folder_val = self.output_folder_entry.get().strip()
        proj_name_val = self.project_name_entry.get().strip()
        
        if not out_folder_val or not proj_name_val:
            messagebox.showwarning("Save Config", "Please specify both output folder and project name.")
            return
        
        # Set config path and add to projects list
        config_manager.set_config_path(out_folder_val, proj_name_val)
        config_manager.add_project_to_list(out_folder_val, proj_name_val)
        
        # Create configuration data
        extent_entries = {
            "n": self.n_entry.get(),
            "s": self.s_entry.get(),
            "e": self.e_entry.get(),
            "w": self.w_entry.get()
        }
        
        date_vars = {
            "start": self.start_var.get(),
            "end": self.end_var.get()
        }
        
        config_data = config_manager.create_config_from_gui_state(
            extent_entries=extent_entries,
            extent_limits=self.extent_limits,
            date_vars=date_vars,
            date_limits=self.date_limits,
            flight_direction=self.flight_dir_var.get(),
            data_folder=self.data_folder_entry.get().strip(),
            polarization=self._get_pol_controls_state(),
            subswaths=self.get_selected_subswaths(),
            dem_file=self.dem_entry.get().strip() if hasattr(self, "dem_entry") else "",
            output_folder=out_folder_val,
            project_name=proj_name_val,
            gacos_folder=self.gacos_data_path if hasattr(self, "gacos_data_path") else ""
        )
        
        config_manager.save_config(config_data)

    def _load_config(self):
        """Load configuration using config manager following proper workflow."""
        # Set config path if not already set (only when output controls exist)
        if hasattr(self, "output_folder_entry") and hasattr(self, "project_name_entry"):
            out_folder_val = self.output_folder_entry.get().strip()
            proj_name_val = self.project_name_entry.get().strip()
            config_manager.set_config_path(out_folder_val, proj_name_val)
        # If output controls don't exist, config path should already be set by project selection
        
        # Load configuration
        config = config_manager.load_config()
        if not config:
            messagebox.showinfo("Load Config", f"No previous configuration found.")
            return
        
        # Set flag to indicate we're loading config (allows output controls creation)
        self._loading_config = True
        
        # Store config for later use
        self._pending_config = config
        
        # Step 1: Load data folder first (this should trigger data Load button green and create DEM controls)
        data_folder = config.get("data_folder", "")
        if data_folder:
            self.data_folder_entry.delete(0, 'end')
            self.data_folder_entry.insert(0, data_folder)
            # Trigger data folder change to create DEM controls
            self._on_data_folder_change()
            
            # Use root.after to continue the config loading after GUI updates
            self.root.after(100, self._load_config_step2)
        else:
            messagebox.showwarning("Load Config", "No data folder found in configuration.")
            self._loading_config = False
    
    def _load_config_step2(self):
        """Continue loading config after data folder is set and DEM controls are created."""
        if not hasattr(self, '_pending_config'):
            return
            
        config = self._pending_config
        
        # Force DEM controls creation if not created yet (e.g., when data folder has SAFE dirs)
        if not hasattr(self, 'dem_entry') or self.dem_entry is None:
            # Check if data folder contains SAFE directories
            data_folder = config.get("data_folder", "")
            if data_folder and os.path.exists(data_folder):
                from .utils.file_operations import get_safe_and_zip_files
                safe_dirs, zip_files = get_safe_and_zip_files(data_folder)
                if safe_dirs:
                    # Force create DEM controls by calling the same function used in workflow
                    self._show_dem_entry_and_browse()
                    print("✓ Created DEM controls for configuration loading")
        
        # Step 2: Set extent and dates if not zip-derived
        skip_zip_derived = getattr(self, '_zip_derived_values', False)
        if not skip_zip_derived:
            # Update extent entries
            ext = config.get("extent_entries", {})
            for coord, entry in [("n", self.n_entry), ("s", self.s_entry), ("e", self.e_entry), ("w", self.w_entry)]:
                if coord in ext:
                    entry.delete(0, 'end')
                    entry.insert(0, ext[coord])
            
            # Update date entries
            dates = config.get("dates_entries", {})
            if "start" in dates:
                self.start_var.set(dates["start"])
            if "end" in dates:
                self.end_var.set(dates["end"])
        
        # Step 3: Set other controls that should exist by now
        if hasattr(self, "flight_dir_var") and self.flight_dir_var:
            self.flight_dir_var.set(config.get("flight_direction", "DESCENDING"))
        
        if hasattr(self, "pol_var") and self.pol_var:
            self.pol_var.set(config.get("polarization", "VV").upper())
        
        # Update subswaths if they exist
        subswaths = config.get("subswaths", [])
        if hasattr(self, "subswath_vars") and self.subswath_vars:
            for i, var in enumerate(self.subswath_vars):
                if var:  # Check if var is not None
                    var.set(1 if (i+1) in subswaths else 0)
        
        # Step 4: Set DEM file (this should trigger DEM Load button green and create output controls)
        dem_file = config.get("dem_file", "")
        if dem_file and os.path.exists(dem_file) and hasattr(self, "dem_entry") and self.dem_entry:
            self.dem_entry.delete(0, 'end')
            self.dem_entry.insert(0, dem_file)
            
            # Remove Download DEM button if it exists (since we're loading a DEM from config)
            if hasattr(self, "dwn_dem") and self.dwn_dem and self.dwn_dem.winfo_exists():
                self.dwn_dem.destroy()
            
            # Trigger DEM update to create output controls
            self.update_dem_controls()
            
            # Use root.after to continue after output controls are created
            self.root.after(100, self._load_config_step3)
        else:
            # No DEM file or DEM controls don't exist yet, but still try to create output controls if needed
            output_folder = config.get("output_folder", "")
            project_name = config.get("project_name", "")
            if output_folder and project_name:
                # Force create output controls if we have the required data
                if not hasattr(self, 'output_folder_entry') or self.output_folder_entry is None:
                    self._show_output_folder_and_project_controls()
                    print("✓ Created output controls for configuration loading")
                self.root.after(100, self._load_config_step3)
            else:
                self._load_config_finish()
    
    def _load_config_step3(self):
        """Final step: set output control values after they are created."""
        if not hasattr(self, '_pending_config'):
            return
            
        config = self._pending_config
        
        # Step 5: Set output controls if they exist now
        if hasattr(self, "output_folder_entry") and self.output_folder_entry:
            output_folder = config.get("output_folder", "")
            if output_folder:
                self.output_folder_entry.delete(0, 'end')
                self.output_folder_entry.insert(0, output_folder)
        
        if hasattr(self, "project_name_entry") and self.project_name_entry:
            project_name = config.get("project_name", "")
            if project_name:
                self.project_name_entry.delete(0, 'end')
                self.project_name_entry.insert(0, project_name)
        
        # Set GACOS folder if specified
        gacos_folder = config.get("gacos_folder", "")
        if gacos_folder:
            self.gacos_data_path = gacos_folder
            if hasattr(self, "_set_gacos_btn_state"):
                self._set_gacos_btn_state()
        
        self._load_config_finish()
    
    def _load_config_finish(self):
        """Finish loading configuration and clean up."""
        # Store current DEM path before clearing config loading flag
        current_dem_path = ""
        if hasattr(self, 'dem_entry') and self.dem_entry:
            current_dem_path = self.dem_entry.get().strip()
        
        # Clear the config loading flag
        self._loading_config = False
        
        if hasattr(self, '_pending_config'):
            config = self._pending_config
            delattr(self, '_pending_config')
            
            # Call final update callback
            self._on_config_loaded(config)
            
            # Restore DEM path if it was cleared during callback
            if current_dem_path and hasattr(self, 'dem_entry') and self.dem_entry:
                if not self.dem_entry.get().strip():
                    print(f"Restoring DEM path that was cleared: {current_dem_path}")
                    self.dem_entry.delete(0, 'end')
                    self.dem_entry.insert(0, current_dem_path)
                    self.update_dem_controls()
            
            messagebox.showinfo("Load Config", "Configuration loaded successfully!")
        
    def _on_dem_loaded(self):
        """Handle DEM file loading completion."""
        # Don't interfere with DEM controls during configuration loading
        if getattr(self, '_loading_config', False):
            return
            
        if hasattr(self, "dwn_dem"):
            self.dwn_dem.destroy()
            self.update_dem_controls()
            self._show_output_folder_and_project_controls()
    
    def _on_config_loaded(self, config):
        """Handle configuration loading completion."""
        # Update GACOS folder
        self.gacos_data_path = config.get("gacos_folder", "")
        
        # Handle polarization controls state
        if hasattr(self, "pol_controls"):
            enabled_pols = [pol for pol, ctrl in self.pol_controls.items() if ctrl is not None]
            if len(enabled_pols) == 1:
                pol = enabled_pols[0]
                ctrl = self.pol_controls[pol]
                if ctrl and "rb" in ctrl and ctrl["rb"].winfo_exists():
                    ctrl["rb"].config(state="disabled")
                    self.pol_var.set(pol)
            else:
                for ctrl in self.pol_controls.values():
                    if ctrl and "rb" in ctrl and ctrl["rb"].winfo_exists():
                        ctrl["rb"].config(state="normal")
        
        # Validate dates
        validate_dates_strict(self.start_var, self.end_var, self.start_date, self.root)
        self._enforce_date_wrapper()

        self.show_confirm_btn_if_ready()

        # 5. Set GACOS data entry if exists
        self.gacos_data_path = config.get("gacos_folder", "")
        self._set_gacos_btn_state()
        messagebox.showinfo("Config Loaded", "Previous configuration successfully retrieved.")

    def _create_extent_widgets(self):
        row = self._next_row("extent")
        extent_label = tk.Label(self.root, text="Extent:")
        extent_label.grid(row=row, column=0, padx=10, pady=5)
        add_tooltip(extent_label, "Define the geographic bounds of your Area of Interest (AOI)")
        
        coord_info_label = tk.Label(self.root, text="(Lat/Lon in °)")
        coord_info_label.grid(row=row, column=0, padx=10, pady=30, sticky="s")
        add_tooltip(
            coord_info_label,
            (
            "Latitude/Longitude in decimal degrees.\n"
            "You need to define the bounds of your AOI.\n"
            "This AOI is represented in the map as a red rectangle. This is initially used to query and download S1 images and DEM.\n"
            "You can also draw a custom AOI by clicking and dragging on the map.\n"
            "The extent values will be updated accordingly.\n"
            "You can also manually edit the values here and the rectangle on the map will be updated accordingly.\n"
            "The overall extent is clamped and shown as green labels. User can also define a smaller extent for a given project configuration. "
            "This smaller extent will be used to limit processing to that smaller extent for a few Time Series analysis steps later."
            )
        )
        self.extent_frame = tk.Frame(self.root)
        self.extent_frame.grid(row=row, column=1, columnspan=2, padx=10, pady=5, sticky="w")
        vcmd = (self.root.register(validate_float), "%P")
        self.n_entry, self.s_entry, self.e_entry, self.w_entry = self._make_extent_entries(self.extent_frame, vcmd)
        add_tooltip(self.n_entry, "Northern Latitude boundary in decimal degrees\n(Maximum latitude value)")
        add_tooltip(self.s_entry, "Southern Latitude boundary in decimal degrees\n(Minimum latitude value)")
        add_tooltip(self.e_entry, "Eastern Longitude boundary in decimal degrees\n(Maximum longitude value)")
        add_tooltip(self.w_entry, "Western Longitude boundary in decimal degrees\n(Minimum longitude value)")

    def _make_extent_entries(self, frame, vcmd):
        def entry(label, row, col, sticky, tooltip_text):
            lbl = tk.Label(frame, text=label)
            lbl.grid(row=row, column=col, padx=2, pady=2, sticky=sticky)
            add_tooltip(lbl, tooltip_text)
            e = tk.Entry(frame, width=8, validate="key", validatecommand=vcmd)
            e.grid(row=row, column=col+1, padx=2, pady=2, sticky=sticky)
            return e
        n = entry("N", 0, 2, "s", "North latitude boundary (maximum latitude)")
        s = entry("S", 2, 2, "n", "South latitude boundary (minimum latitude)")
        w = entry("W", 1, 0, "e", "West longitude boundary (minimum longitude)")
        e = entry("E", 1, 4, "w", "East longitude boundary (maximum longitude)")
        return n, s, e, w

    def _create_map_widget(self):
        row = self._get_row("extent")
        self.map_frame = tk.Frame(self.root)
        self.map_frame.grid(row=row, column=3, padx=10, pady=5, sticky="nsew")
        add_tooltip(self.map_frame, "Interactive map for visualizing and defining Area of Interest (AOI).\n• Click and drag to define rectangular extent\n• Red rectangle shows current AOI\n• Green polygons show available data coverage\n• Colored polygons show query results")
        
        for i in range(2): self.root.grid_columnconfigure(i, weight=0)
        self.root.grid_columnconfigure(3, weight=1)
        self.root.grid_rowconfigure(row, weight=1)
        self.map_frame.grid_rowconfigure(0, weight=1)
        self.map_frame.grid_columnconfigure(0, weight=1)
        map_container = tk.Frame(self.map_frame)
        map_container.grid(row=0, column=0, sticky="nsew")
        map_container.grid_rowconfigure(0, weight=1)
        map_container.grid_columnconfigure(0, weight=1)
        
        try:
            self.map_widget = TkinterMapView(map_container, corner_radius=0)
            self.map_widget.grid(row=0, column=0, sticky="nsew")
            self.map_widget.set_zoom(1)
            self.map_widget.set_position(20, 0)
            map_container.bind("<Configure>", lambda event: self.map_widget.config(width=event.width, height=event.height))
            
            # Test map click binding with error handling
            try:
                self.map_widget.add_left_click_map_command(self._on_map_click_with_limits_and_update)
                print("✅ Map click handler successfully bound")
            except Exception as click_error:
                print(f"⚠️ Warning: Could not bind map click handler: {click_error}")
                print("   Map clicking will not work - please use extent text boxes")
                # Create fallback message overlay
                error_label = tk.Label(map_container, 
                                     text="Map clicking disabled\nUse extent text boxes instead\n\nTo fix: pip install --upgrade tkintermapview",
                                     bg="lightyellow", fg="orange", 
                                     justify="center", padx=10, pady=5,
                                     relief="raised", borderwidth=2)
                error_label.place(relx=0.5, rely=0.05, anchor="center")
                
        except Exception as map_error:
            print(f"❌ Error creating map widget: {map_error}")
            print("   Creating fallback map display")
            # Create fallback widget
            fallback_frame = tk.Frame(map_container, bg="lightgray")
            fallback_frame.grid(row=0, column=0, sticky="nsew")
            error_msg = tk.Label(fallback_frame, 
                                text="Map Widget Error\nPlease use extent text boxes\n\nInstall missing dependencies:\npip install --upgrade tkintermapview pillow",
                                bg="lightgray", fg="red", 
                                justify="center", padx=20, pady=20)
            error_msg.pack(expand=True)
            return

        # Securely refresh the map once everything is loaded
        def refresh_map():
            try:
                # Pan and zoom to force refresh
                self.map_widget.set_zoom(self.map_widget.zoom + 1)
                self.map_widget.set_zoom(self.map_widget.zoom - 1)
                self.map_widget.set_position(20, 0)
                print("✅ Map widget refreshed successfully")
            except Exception as refresh_error:
                print(f"⚠️ Warning: Could not refresh map: {refresh_error}")

        # Bind to root's initial idle event after window is shown
        self.root.after(500, refresh_map)

    def _create_legend_frame(self):
        self.legend_display_frame = tk.Frame(self.map_frame)
        self.legend_display_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=(5, 0))

    def _create_date_widgets(self):
        today = datetime.date.today()
        row = self._next_row("date")
        date_label = tk.Label(self.root, text="Start/End Date (YYYY-MM-DD):")
        date_label.grid(row=row, column=0, padx=10, pady=5)
        add_tooltip(date_label, "Specify the temporal range for satellite data acquisition.\nDates should be in YYYY-MM-DD format.")
        
        self.date_frame = tk.Frame(self.root)
        self.date_frame.grid(row=row, column=1, columnspan=6, padx=20, pady=5, sticky="w")
        self.start_var, self.end_var, self.start_date, self.end_date = self._make_date_entries(self.date_frame, today)

    def _make_date_entries(self, frame, today):
        start_label = tk.Label(frame, text="Start")
        start_label.grid(row=0, column=0, padx=(0, 2))
        add_tooltip(start_label, "Start date for data acquisition period")
        
        start_var = tk.StringVar()
        
        if USE_CALENDAR_WIDGET:
            # Use DateEntry with calendar popup
            start_date = DateEntry(
                frame, 
                textvariable=start_var, 
                date_pattern="yyyy-mm-dd", 
                width=12, 
                maxdate=today,
                state="normal",  # Allow manual editing
                validate="none"  # Don't validate on every keystroke
            )
            add_tooltip(start_date, "Enter date as YYYY-MM-DD or click calendar icon.\nType directly in the field or use calendar picker.")
        else:
            # Use simple text entry (WSL/Linux fallback)
            start_date = tk.Entry(
                frame,
                textvariable=start_var,
                width=12,
                validate="none"
            )
            add_tooltip(start_date, "Enter date as YYYY-MM-DD format.\nExample: 2024-01-15")
        
        start_date.grid(row=0, column=1, padx=(0, 8))
        
        end_label = tk.Label(frame, text="End")
        end_label.grid(row=0, column=4, padx=(0, 2))
        add_tooltip(end_label, "End date for data acquisition period")
        
        end_var = tk.StringVar()
        
        if USE_CALENDAR_WIDGET:
            # Use DateEntry with calendar popup
            end_date = DateEntry(
                frame, 
                textvariable=end_var, 
                date_pattern="yyyy-mm-dd", 
                width=12, 
                maxdate=today,
                state="normal",  # Allow manual editing
                validate="none"  # Don't validate on every keystroke
            )
            add_tooltip(end_date, "Enter date as YYYY-MM-DD or click calendar icon.\nMust be after start date and not in the future.")
        else:
            # Use simple text entry (WSL/Linux fallback)
            end_date = tk.Entry(
                frame,
                textvariable=end_var,
                width=12,
                validate="none"
            )
            add_tooltip(end_date, "Enter date as YYYY-MM-DD format.\nExample: 2024-12-31\nMust be after start date.")
        
        end_date.grid(row=0, column=5, padx=(0, 2))
        
        start_var.set("")
        end_var.set("")
        return start_var, end_var, start_date, end_date

    def _create_flight_dir_widgets(self):
        row = self._next_row("flight_dir")
        self.flight_dir_var = tk.StringVar(value="DESCENDING")
        flight_dir_label = tk.Label(self.root, text="Flight Direction:")
        flight_dir_label.grid(row=row, column=0, padx=10, pady=5, sticky="w")
        add_tooltip(flight_dir_label, "Satellite orbit direction during image acquisition")
        
        flight_dir_frame = tk.Frame(self.root)
        flight_dir_frame.grid(row=row, column=1, columnspan=2, padx=10, pady=5, sticky="w")
        
        self.ascending_rb = tk.Radiobutton(flight_dir_frame, text="Ascending", variable=self.flight_dir_var, value="ASCENDING")
        self.ascending_rb.pack(side="left", padx=(0, 10))
        add_tooltip(self.ascending_rb, "Satellite travels from South to North\n(typically evening passes for Sentinel-1)")
        
        self.descending_rb = tk.Radiobutton(flight_dir_frame, text="Descending", variable=self.flight_dir_var, value="DESCENDING")
        self.descending_rb.pack(side="left")
        add_tooltip(self.descending_rb, "Satellite travels from North to South\n(typically morning passes for Sentinel-1)")
        
        self.flight_dir_frame = flight_dir_frame

    def _detect_and_set_flight_direction(self, safe_dirs, zip_files):
        """
        Detect flight direction from manifest.safe files and update UI accordingly.
        
        Args:
            safe_dirs (list): List of SAFE directory paths
            zip_files (list): List of ZIP file paths
        """
        from .utils.utils import analyze_flight_directions
        
        # Skip if no data files to analyze
        if not (safe_dirs or zip_files):
            self._enable_flight_direction_controls()
            return
            
        try:
            analysis = analyze_flight_directions(safe_dirs, zip_files)
            
            if analysis['uniform'] and analysis['direction']:
                # All files have the same flight direction
                direction = analysis['direction']
                print(f"Detected uniform flight direction: {direction}")
                
                # Set the flight direction
                self.flight_dir_var.set(direction)
                
                # Disable the controls since direction is auto-detected
                self._disable_flight_direction_controls()
                
                # Update tooltip to show auto-detection
                self._update_flight_direction_tooltip(f"Auto-detected from manifest files: {direction}")
                
            elif len(analysis['directions']) > 1:
                # Mixed flight directions found
                directions = list(analysis['directions'])
                print(f"Mixed flight directions found: {directions}")
                
                # Show warning to user
                from tkinter import messagebox
                messagebox.showwarning(
                    "Mixed Flight Directions", 
                    f"The selected data folder contains files with different flight directions:\n"
                    f"{', '.join(directions)}\n\n"
                    f"For proper InSAR processing, all images should have the same flight direction.\n"
                    f"Please select a folder containing only ascending OR descending data."
                )
                
                # Enable controls for manual selection
                self._enable_flight_direction_controls()
                self._update_flight_direction_tooltip("Manual selection required due to mixed directions")
                
            else:
                # No flight direction detected (no manifest files or parsing errors)
                print("No flight direction detected from manifest files")
                
                # Enable controls for manual selection
                self._enable_flight_direction_controls()
                self._update_flight_direction_tooltip("Manual selection - could not auto-detect from manifest files")
                
        except Exception as e:
            print(f"Error detecting flight direction: {e}")
            # Fallback to manual selection
            self._enable_flight_direction_controls()
            self._update_flight_direction_tooltip("Manual selection - error during auto-detection")

    def _disable_flight_direction_controls(self):
        """Disable flight direction radio buttons."""
        if hasattr(self, 'ascending_rb') and self.ascending_rb:
            self.ascending_rb.config(state='disabled')
        if hasattr(self, 'descending_rb') and self.descending_rb:
            self.descending_rb.config(state='disabled')

    def _enable_flight_direction_controls(self):
        """Enable flight direction radio buttons."""
        if hasattr(self, 'ascending_rb') and self.ascending_rb:
            self.ascending_rb.config(state='normal')
        if hasattr(self, 'descending_rb') and self.descending_rb:
            self.descending_rb.config(state='normal')

    def _update_flight_direction_tooltip(self, message):
        """Update tooltip for flight direction controls."""
        if hasattr(self, 'ascending_rb') and self.ascending_rb:
            add_tooltip(self.ascending_rb, f"Satellite travels from South to North\n(typically evening passes for Sentinel-1)\n\n{message}")
        if hasattr(self, 'descending_rb') and self.descending_rb:
            add_tooltip(self.descending_rb, f"Satellite travels from North to South\n(typically morning passes for Sentinel-1)\n\n{message}")

    def _create_data_folder_widgets(self):
        row = self._next_row("data_folder")
        data_folder_label = tk.Label(self.root, text="Select Data Folder:")
        data_folder_label.grid(row=row, column=0, padx=10, pady=5)
        add_tooltip(data_folder_label, "Choose folder containing Sentinel-1 data (ZIP files or SAFE directories)")
        
        self.data_folder_entry = tk.Entry(self.root, width=50)
        self.data_folder_entry.grid(row=row, column=1, padx=10, pady=5)
        add_tooltip(self.data_folder_entry, "Path to folder containing Sentinel-1 SLC data.\nSupports both ZIP archives and extracted SAFE directories.")
        
        self.data_browse = tk.Button(self.root, text="Load", command=self._load_and_update)
        self.data_browse.grid(row=row, column=2, padx=10, pady=5)
        add_tooltip(self.data_browse, "Browse and select the data folder.\nButton color indicates status:\n• Default: No folder selected\n• Red: Valid folder, ready for data query\n• Yellow: ZIP files found, extraction needed\n• Green: Data loaded successfully")
        
        self.data_folder_entry.bind("<KeyRelease>", self._validate_path_syntax)
        self.data_folder_entry.bind("<FocusOut>", self._validate_path_syntax)
        self._validate_path_syntax()

    def _create_action_buttons(self):
        def start_download_thread():
            thread = threading.Thread(target=self._run_data_download)
            thread.start()
        self.data_download_btn = tk.Button(
            self.root, text="Data Download",
            command=start_download_thread,
            state="disabled"
        )
        add_tooltip(self.data_download_btn, "Download selected Sentinel-1 data from Copernicus Hub.\nAppears after successful data query and selection.")
        
        self.data_query_btn = tk.Button(
            self.root, text="Data Query",
            command=self._on_data_query_callback,
            state="disabled"
        )
        add_tooltip(self.data_query_btn, "Search for available Sentinel-1 data in the specified area and time range.\nRequires valid extent coordinates to be enabled.")
        
        self._action_btn_row = self._next_row("action_btns")

    def _bind_events(self):
        for entry in (self.n_entry, self.s_entry, self.e_entry, self.w_entry):
            for event in ("<KeyRelease>", "<FocusOut>", "<Return>", "<Tab>", "<Shift-Tab>"):
                entry.bind(event, self._try_draw_wrapper, add="+")
                entry.bind(event, self._enforce_extent_wrapper, add="+")
                entry.bind(event, lambda e: self._update_data_query_btn_state_wrapper(), add="+")
        self.root.bind_all("<Button-1>", self._enforce_extent_wrapper, add="+")
        self.root.bind_all("<Button-1>", self._try_draw_wrapper, add="+")
        # Bind date entry events with improved logic
        for widget in (self.start_date, self.end_date):
            if USE_CALENDAR_WIDGET:
                # Calendar widget event bindings
                for event in ("<<DateEntrySelected>>", "<FocusOut>"):
                    widget.bind(event, self._validate_dates_gentle_wrapper, add="+")
                
                # Only enforce limits when calendar is used (not when typing)
                widget.bind("<<DateEntrySelected>>", self._enforce_date_wrapper, add="+")
                
                # For Enter and Tab, validate but don't trigger folder change
                for event in ("<Return>", "<Tab>", "<Shift-Tab>"):
                    widget.bind(event, self._on_date_entry_complete, add="+")
                
                # For typing, use debounced validation (delayed)
                widget.bind("<KeyRelease>", self._on_date_key_release, add="+")
            else:
                # Text entry widget event bindings (WSL/Linux fallback)
                for event in ("<FocusOut>", "<Return>", "<Tab>", "<Shift-Tab>"):
                    widget.bind(event, self._validate_dates_gentle_wrapper, add="+")
                    widget.bind(event, self._on_date_entry_complete, add="+")
                
                # For typing, use debounced validation (delayed)
                widget.bind("<KeyRelease>", self._on_date_key_release, add="+")
        
        for event in ("<Return>", "<Tab>", "<Shift-Tab>"):
            self.data_folder_entry.bind(event, self._on_data_folder_change_wrapper, add="+")
        self.root.after(200, self._try_auto_draw)
        self.root.after(100, lambda: self._update_data_query_btn_state_wrapper())

    def _on_date_entry_complete(self, event=None):
        """Handle when user completes date entry (Enter/Tab)."""
        # Validate gently - this won't auto-correct during typing
        self._validate_dates_gentle_wrapper(event)
        # Only enforce limits if query button is not active
        # (the enforce wrapper now has this logic built-in)

    def _on_date_key_release(self, event=None):
        """Handle keystrokes in date entries with debouncing."""
        # Cancel any existing validation timer
        if hasattr(self, '_date_validation_timer') and self._date_validation_timer:
            self.root.after_cancel(self._date_validation_timer)
        
        # Set a new timer for delayed validation (1 second after user stops typing)
        self._date_validation_timer = self.root.after(1000, self._on_date_validation_timeout)

    def _on_data_folder_change_wrapper(self, event=None):
        """Wrapper to handle focus management before calling the main function."""
        # Schedule the actual function to run after current event processing
        self.root.after_idle(lambda: self._on_data_folder_change(event))

    # --- Validation and Entry Helpers ---
    def _validate_path_syntax(self, *_):
        folder = self.data_folder_entry.get().strip()
        validate_path_syntax(self.data_folder_entry, folder)
        self.data_browse.config(state="normal")

    # --- Event Handlers using external utilities ---
    def _try_draw_wrapper(self, event=None):
        """Wrapper for try_draw_from_entries function."""
        if hasattr(self, 'map_widget') and hasattr(self, 'rect_shape'):
            def draw_callback(s, w, n, e):
                draw_rectangle_on_map(self.map_widget, self.rect_shape, self.data_browse, s, w, n, e)
            try_draw_from_entries(self.n_entry, self.s_entry, self.e_entry, self.w_entry, draw_callback)
    
    def _enforce_extent_wrapper(self, event=None):
        """Wrapper for enforce_extent_limits function."""
        enforce_extent_limits(self.n_entry, self.s_entry, self.e_entry, self.w_entry, self.extent_limits)
    
    def _enforce_date_wrapper(self, event=None):
        """Wrapper for enforce_date_limits function."""
        if hasattr(self, 'date_limits') and hasattr(self, 'start_var') and hasattr(self, 'end_var'):
            # Check if query button is active (visible and enabled)
            query_btn_active = (
                hasattr(self, 'data_query_btn') and 
                self.data_query_btn is not None and 
                self.data_query_btn.winfo_exists() and
                self.data_query_btn.winfo_viewable() and
                str(self.data_query_btn['state']) != 'disabled'
            )
            
            # Only enforce date limits when query button is NOT active
            if not query_btn_active:
                enforce_date_limits(self.start_var, self.end_var, self.date_limits)
    
    def _validate_dates_gentle_wrapper(self, event=None):
        """Wrapper for validate_dates_gentle function."""
        if hasattr(self, 'start_var') and hasattr(self, 'end_var') and hasattr(self, 'start_date') and hasattr(self, 'root'):
            # Check if query button is active (visible and enabled)
            query_btn_active = (
                hasattr(self, 'data_query_btn') and 
                self.data_query_btn is not None and 
                self.data_query_btn.winfo_exists() and
                self.data_query_btn.winfo_viewable() and
                str(self.data_query_btn['state']) != 'disabled'
            )
            
            validate_dates_gentle(
                self.start_var, 
                self.end_var, 
                self.start_date, 
                self.root,
                self.date_limits if hasattr(self, 'date_limits') else {},
                query_btn_active
            )
    
    def _update_data_query_btn_state_wrapper(self, state=None):
        """Wrapper for update_data_query_btn_state function."""
        if hasattr(self, 'data_query_btn') and hasattr(self, 'data_browse'):
            update_data_query_btn_state(
                self.n_entry, self.s_entry, self.e_entry, self.w_entry,
                self.data_query_btn, self.data_browse,
                self.show_query_btn, self.hide_query_btn
            )

    def _try_auto_draw(self):
        if all(entry.get() for entry in (self.n_entry, self.s_entry, self.e_entry, self.w_entry)):
            self._try_draw_wrapper()

    def _on_date_validation_timeout(self):
        """Called after user stops typing in date fields."""
        # Only do gentle validation that doesn't auto-correct while typing
        self._validate_dates_gentle_wrapper()
        # Don't trigger folder change during typing - only on explicit completion

    # --- Map and Polygon Helpers ---
    def _on_map_click_with_limits_and_update(self, coords):
        try:
            print(f"🖱️ Map clicked at coordinates: {coords}")
            
            # Check if we have a pending first click
            has_pending_click = hasattr(self.map_widget, "_map_click_start")
            print(f"🔍 Pending first click: {has_pending_click}")
            
            if has_pending_click:
                first_coords = getattr(self.map_widget, "_map_click_start")
                print(f"📍 Completing rectangle from {first_coords} to {coords}")
            
            result = on_map_click_with_limits(coords, self.extent_limits, self.map_widget, "_map_click_start")
            
            if result:
                print(f"✅ Rectangle completed: {result}")
                # Update extent entries with the completed rectangle
                s, w, n, e = result
                
                # Clear any existing rectangle first
                try:
                    if self.rect_shape[0]:
                        print("🗑️ Clearing previous rectangle")
                        self.rect_shape[0].delete()
                        self.rect_shape[0] = None
                except Exception as e:
                    print(f"⚠️ Warning clearing previous rectangle: {e}")
                
                # Update entries and draw new rectangle
                update_extent_entries_from_map((s, w, n, e), self.n_entry, self.s_entry, self.w_entry, self.e_entry, 
                                               lambda s, w, n, e: draw_rectangle_on_map(self.map_widget, self.rect_shape, self.data_browse, s, w, n, e))
                print(f"📝 Extent entries updated with: N={n}, S={s}, E={e}, W={w}")
                
                # Force map refresh and verify rectangle is drawn
                try:
                    if hasattr(self.map_widget, 'update'):
                        self.map_widget.update()
                    if self.rect_shape[0]:
                        print("🎯 Rectangle successfully drawn and visible")
                    else:
                        print("❌ Warning: Rectangle not visible after drawing")
                except Exception as e:
                    print(f"⚠️ Warning during map refresh: {e}")
                    
            else:
                print("📍 First click registered, waiting for second click")
                
            # Check final state
            still_pending = hasattr(self.map_widget, "_map_click_start")
            print(f"🔍 After processing - still pending: {still_pending}")
            
            # Add rectangle verification
            if self.rect_shape[0]:
                print("🎯 Current rectangle status: ACTIVE")
            else:
                print("🎯 Current rectangle status: NONE")
            
            self.root.after(200, lambda: self._update_data_query_btn_state_wrapper())
        except Exception as e:
            print(f"❌ Error in map click handler: {e}")
            import traceback
            traceback.print_exc()

    def test_rectangle_drawing(self, test_coords=(40.0, 35.0, 42.0, 39.0)):
        """Test method to manually draw a rectangle for debugging."""
        try:
            s, w, n, e = test_coords
            print(f"🧪 Testing rectangle drawing with coords: S={s}, W={w}, N={n}, E={e}")
            
            # Clear existing rectangle
            if self.rect_shape[0]:
                self.rect_shape[0].delete()
                self.rect_shape[0] = None
                print("🗑️ Cleared existing test rectangle")
            
            # Draw test rectangle
            draw_rectangle_on_map(self.map_widget, self.rect_shape, self.data_browse, s, w, n, e)
            
            if self.rect_shape[0]:
                print("✅ Test rectangle drawn successfully")
                return True
            else:
                print("❌ Test rectangle failed to draw")
                return False
        except Exception as e:
            print(f"❌ Test rectangle error: {e}")
            return False

    # --- Legend and Polygon Display ---
    def _clear_legend(self):
        for widget in self.legend_items:
            widget.destroy()
        self.legend_items.clear()
        self.legend_selected_idx[0] = None

    def _clear_extent_and_date_labels(self):
        attrs = [
            "n_label", "s_label", "e_label", "w_label",
            "sdate_label", "edate_label", "safe_dirs_label"
        ]
        for attr in attrs:
            widget = getattr(self, attr, None)
            if widget:
                widget.destroy()
                setattr(self, attr, None)

    def _highlight_polygon(self, idx):
        # Remove existing polygons
        for poly in getattr(self.on_data_query, "polygons", []):
            poly.delete()
        new_polys = []
        result = getattr(self.on_data_query, "last_result", None)
        if result is None:
            result = search_sentinel1_acquisitions(
                self._get_aoi_wkt(),
                self.start_var.get(),
                self.end_var.get(),
                self.flight_dir_var.get()
            )
            self.on_data_query.last_result = result
        for i, item in enumerate(result[:3]):
            geom = item.get("geometry", {})
            coords = geom.get("coordinates", [])
            if coords and geom.get("type") == "Polygon":
                points = [(lat, lon) for lon, lat in coords[0]]
                outline_color = "cyan" if i == idx else self.POLY_COLORS[i]
                border_width = 4 if i == idx else 2
                poly = self.map_widget.set_polygon(
                    points,
                    outline_color=outline_color,
                    fill_color="",
                    border_width=border_width
                )
                new_polys.append(poly)
        self.on_data_query.polygons = new_polys

    def _on_legend_item_click(self, idx):
        for i, frame in enumerate(self.legend_items):
            frame.config(bg="#cceeff" if i == idx else self.legend_display_frame.cget("bg"))
        self.legend_selected_idx[0] = idx
        # Schedule polygon highlighting safely without creating unnecessary threads
        try:
            if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                self.root.after(0, self._highlight_polygon, idx)
        except Exception as e:
            print(f"Warning: Could not schedule polygon highlight: {e}")
        result = getattr(self.on_data_query, "last_result", None)
        if result and idx < len(result):
            self.selected_files_info = result[idx].get('files_info')
            self.total_expected_size = result[idx].get('total_expected_size')
        else:
            self.selected_files_info = None
            self.total_expected_size = None

    def _on_data_query_callback(self):
        def run_query():
            result = search_sentinel1_acquisitions(
                self._get_aoi_wkt(),
                self.start_var.get(),
                self.end_var.get(),
                self.flight_dir_var.get()
            )
            self.on_data_query.last_result = result
            for poly in getattr(self.on_data_query, "polygons", []):
                poly.delete()
            self.on_data_query.polygons = []

            def update_gui():
                self._clear_legend()
                for idx, item in enumerate(result[:3]):
                    geom = item.get("geometry", {})
                    coords = geom.get("coordinates", [])
                    if coords and geom.get("type") == "Polygon":
                        points = [(lat, lon) for lon, lat in coords[0]]
                        poly = self.map_widget.set_polygon(
                            points,
                            outline_color=self.POLY_COLORS[idx],
                            fill_color="",
                            border_width=2
                        )
                        self.on_data_query.polygons.append(poly)
                        text = f"Acqs={item['num_acquisitions']}, Coverage={round(item['percent_coverage'], 1)}%"
                        frame = tk.Frame(self.legend_display_frame, bd=1, relief="flat")
                        color_box = tk.Canvas(frame, width=18, height=18, highlightthickness=0, bg=frame.cget("bg"))
                        color_box.create_rectangle(2, 2, 16, 16, outline=self.POLY_COLORS[idx], width=2, fill="")
                        color_box.pack(side="left", padx=(0, 4))
                        label = tk.Label(frame, text=text, anchor="w")
                        label.pack(side="left", fill="x", expand=True)
                        frame.pack(side="left", padx=5, pady=2)
                        for widget in (frame, color_box, label):
                            widget.bind("<Button-1>", lambda _, i=idx: self._on_legend_item_click(i))
                        self.legend_items.append(frame)
                if self.on_data_query.polygons:
                    self._on_legend_item_click(0)
                self._show_data_download_btn()
            # Schedule GUI update safely
            try:
                if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                    self.root.after(0, update_gui)
            except Exception as e:
                print(f"Warning: Could not schedule GUI update: {e}")
        threading.Thread(target=run_query).start()

    def _show_data_download_btn(self):
        self.show_download_btn()
        if self.data_browse.cget("bg") != "green":
            self.data_download_btn.config(state="normal")
        else:
            self.data_download_btn.config(state="disabled")

    def _get_aoi_wkt(self):
        """Use external function for AOI WKT generation."""
        return get_aoi_wkt(self.n_entry, self.s_entry, self.e_entry, self.w_entry)

    def _run_data_download(self):
        self.download_in_progress = True
        files_info = self.selected_files_info if self.selected_files_info is not None else []
        folder = self.data_folder_entry.get().strip()
        total_expected_size = self.total_expected_size if self.total_expected_size is not None else 0
        if not files_info:
            messagebox.showinfo("Download", "No files selected for download.")
            return

        # Disable controls and remove query/download buttons
        self._set_controls_state("disabled")
        if hasattr(self, "data_query_btn") and self.data_query_btn is not None and self.data_query_btn.winfo_exists():
            self.data_query_btn.grid_remove()
            self.data_query_btn.destroy()
        self.hide_download_btn()
        # Hide extraction button during download
        if hasattr(self, 'hide_extract_btn'):
            self.hide_extract_btn()
        # Also hide the zip extraction button if it exists
        if hasattr(self, '_extract_btn') and self._extract_btn and self._extract_btn.winfo_exists():
            self._extract_btn.grid_remove()
        # Show pause button during download
        pause_row = getattr(self, '_action_btn_row', 10) - 2  # Use row 8 as default if not set
        self._show_pause_button(pause_row)
        for btn_attr in ["data_browse", "browse_dem", "dwn_dem", "output_folder_browse",
                            "output_folder_entry", "project_name_entry", "data_folder_entry", "dem_entry"]:
            btn = getattr(self, btn_attr, None)
            if btn and btn.winfo_exists():
                btn.config(state="disabled")
        if hasattr(self, "subswath_cbs"):
            for cb in self.subswath_cbs:
                if cb and cb.winfo_exists():
                    cb.config(state="disabled")
        if hasattr(self, "pol_controls"):
            for pol in self.pol_controls.values():
                if pol and "rb" in pol and pol["rb"] and pol["rb"].winfo_exists():
                    pol["rb"].config(state="disabled")
        # Hide DEM controls during download
        for attr in ["dem_entry", "dem_label", "browse_dem", "dwn_dem"]:
            widget = getattr(self, attr, None)
            if widget and widget.winfo_exists():
                widget.grid_remove()

        self._init_download_stats_labels()
        self._download_completed = False
        self._download_error = None
        self._last_stats = {}

        def update_stats(stats):
            try:
                if not stats or not isinstance(stats, dict):
                    return  # Skip invalid stats
                    
                def format_time(seconds):
                    if not isinstance(seconds, (int, float)) or math.isnan(seconds) or math.isinf(seconds):
                        return "inf"
                    seconds = int(seconds)
                    hours = seconds // 3600
                    minutes = (seconds % 3600) // 60
                    secs = seconds % 60
                    return f"{hours:02}h:{minutes:02}m:{secs:02}s" if hours > 0 else f"{minutes:02}m:{secs:02}s"
                def format_bytes(num_bytes):
                    num_bytes = float(num_bytes)
                    if num_bytes < 1024**2:
                        return f"{num_bytes/1024:.1f} KB"
                    elif num_bytes < 1024**3:
                        return f"{num_bytes/1024**2:.1f} MB"
                    else:
                        return f"{num_bytes/1024**3:.2f} GB"
                def format_speed(bytes_per_sec):
                    bytes_per_sec = float(bytes_per_sec)
                    if bytes_per_sec < 1024:
                        return f"{bytes_per_sec:.0f} B/s"
                    elif bytes_per_sec < 1024**2:
                        return f"{bytes_per_sec/1024:.1f} KB/s"
                    elif bytes_per_sec < 1024**3:
                        return f"{bytes_per_sec/1024**2:.1f} MB/s"
                    else:
                        return f"{bytes_per_sec/1024**3:.2f} GB/s"
                
                # Throttle UI updates to prevent jitter (max once per second)
                now = time.time()
                if not hasattr(update_stats, 'last_update_time'):
                    update_stats.last_update_time = 0
                
                if now - update_stats.last_update_time < 1.0:
                    # Too soon since last update, skip this one
                    self._last_stats = stats
                    return
                
                update_stats.last_update_time = now
                
                if isinstance(stats, dict):
                    percent_complete = stats.get('percent_complete')
                    total_expected_size = self.total_expected_size if self.total_expected_size is not None else 0
                    if percent_complete is None:
                        total_downloaded = stats.get('total_downloaded', 0)
                        percent_complete = 100.0 * total_downloaded / total_expected_size if total_expected_size else 0.0
                    eta_seconds = stats.get('eta_seconds')
                    if eta_seconds is None:
                        current_speed = stats.get('current_speed', 0)
                        total_downloaded = stats.get('total_downloaded', 0)
                        eta_seconds = (total_expected_size - total_downloaded) / current_speed if current_speed > 0 and total_expected_size > 0 else 0
                    formatted = {
                        "Elapsed": format_time(stats.get("elapsed", 0)),
                        "Downloaded": f"{format_bytes(stats.get('total_downloaded', 0))}/{format_bytes(stats.get('total_expected_size', total_expected_size))}",
                        "Speed": format_speed(stats.get("current_speed", 0)),
                        "Mean": format_speed(stats.get("mean_speed", 0)),
                        "Completion": f"{percent_complete:.1f}%",
                        "ETA": format_time(eta_seconds),
                    }
                    # Ensure labels exist before updating
                    if hasattr(self, "download_stats_labels") and self.download_stats_labels:
                        for key, value in formatted.items():
                            label = self.download_stats_labels.get(key)
                            if label and hasattr(label, "config"):
                                label.config(text=value)
                    self._last_stats = stats
            except Exception as e:
                print(f"Warning: Stats update error: {e}")
                # Don't crash on stats update failures

        def run_download():
            error = None
            self._download_completed = False
            self._download_error = None
            self._last_stats = {}

            def progress_callback(stats):
                # Ensure we capture the stats data and avoid lambda closure issues
                stats_copy = dict(stats) if stats else {}
                try:
                    # Add extra defensive checks for thread safety
                    if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                        self.root.after(0, lambda s=stats_copy: update_stats(s))
                    self._last_stats = stats_copy
                except Exception as e:
                    print(f"Warning: Progress callback error: {e}")
                    # Don't crash on UI update failures

            try:
                download_sentinel1_acquisitions(
                    files_info, folder, total_expected_size,
                    progress_callback=progress_callback,
                    pause_event=self._global_pause_event
                )
            except Exception as e:
                error = str(e)

            def after_download():
                self.download_in_progress = False
                percent = self._last_stats.get("percent_complete", 0)
                if not percent and "total_downloaded" in self._last_stats and total_expected_size:
                    percent = 100.0 * self._last_stats["total_downloaded"] / total_expected_size
                if error or percent < 99.9:
                    for f in os.listdir(folder):
                        if f.lower().endswith(".zip"):
                            try:
                                os.remove(os.path.join(folder, f))
                            except Exception:
                                pass
                    self.hide_download_stats()
                    self.data_folder_entry.config(state="normal")
                    self.data_browse.config(state="normal")
                    self._set_controls_state("normal")
                    self.show_download_btn()
                    # Hide pause button when download fails
                    self._hide_pause_button()
                    messagebox.showerror("Download Failed", f"Download failed or incomplete. All downloaded zip files have been deleted.\n\n{error if error else 'Incomplete download.'}")
                else:
                    self.data_folder_entry.config(state="normal")
                    self.data_browse.config(state="normal")
                    self._on_data_folder_change()
                    self.hide_download_stats()
                    # Hide pause button when download completes successfully
                    self._hide_pause_button()
                    # Show extraction button after successful download (100%)
                    if hasattr(self, 'show_extract_btn'):
                        self.show_extract_btn()
                    # Also show the zip extraction button if zip files exist
                    elif hasattr(self, '_extract_btn'):
                        # Re-show the zip extraction button for downloaded files
                        self._show_zip_extraction_controls()
            # Schedule after_download callback safely
            try:
                if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                    self.root.after(0, after_download)
            except Exception as e:
                print(f"Warning: Could not schedule after_download callback: {e}")

        self.download_thread = threading.Thread(target=run_download, daemon=True)
        self.download_thread.start()

    def _init_download_stats_labels(self):
        base_row = self._action_btn_row-2
        if hasattr(self, "download_stats_frame") and self.download_stats_frame:
            self.download_stats_frame.destroy()
        # Note: Pause button is now managed explicitly by _show_pause_button/_hide_pause_button
        # and only shown during active downloads
        self.download_stats_frame = tk.Frame(self.root)
        self.download_stats_frame.grid(row=base_row, column=6, columnspan=2, sticky="w", padx=5, pady=5)
        self.download_stats_labels = {}
        for name in self.LABELS:
            row_frame = tk.Frame(self.download_stats_frame)
            row_frame.pack(anchor="w", pady=0)
            tk.Label(row_frame, text=f"{name}:", anchor="e", width=10).pack(side="left")
            label = tk.Label(row_frame, text="", anchor="w", width=20)
            label.pack(side="left")
            self.download_stats_labels[name] = label

    def show_download_stats(self):
        if hasattr(self, "download_stats_frame") and self.download_stats_frame:
            self.download_stats_frame.grid()

    def hide_download_stats(self):
        if hasattr(self, "download_stats_frame") and self.download_stats_frame:
            self.download_stats_frame.grid_remove()

    def _set_controls_state(self, state):
        for entry in (self.n_entry, self.s_entry, self.e_entry, self.w_entry):
            entry.config(state=state)
        self.start_date.config(state=state)
        self.end_date.config(state=state)
        # Note: Flight direction controls are managed separately by _detect_and_set_flight_direction

    def show_query_btn(self):
        row = self._action_btn_row - 1
        if not hasattr(self, "data_query_btn") or not self.data_query_btn.winfo_exists():
            self.data_query_btn = tk.Button(
                self.root, text="Data Query",
                command=self._on_data_query_callback,
                state="normal"
            )
        self.data_query_btn.grid(row=row, column=3, padx=10, pady=5)
        self.data_query_btn.lift()

    def hide_query_btn(self):
        if hasattr(self, "data_query_btn") and self.data_query_btn.winfo_exists():
            self.data_query_btn.grid_remove()

    def show_download_btn(self):
        row = self._action_btn_row - 1
        if not hasattr(self, "data_download_btn") or not self.data_download_btn.winfo_exists():
            def start_download_thread():
                threading.Thread(target=self._run_data_download).start()
            self.data_download_btn = tk.Button(
                self.root, text="Data Download",
                command=start_download_thread,
                state="normal"
            )
        self.data_download_btn.grid(row=row, column=4, padx=10, pady=5)
        self.data_download_btn.lift()

    def hide_download_btn(self):
        if hasattr(self, "data_download_btn") and self.data_download_btn and self.data_download_btn.winfo_exists():
            self.data_download_btn.grid_remove()
            self.data_download_btn.destroy()

    def fail_prompt(self):
        messagebox.showerror("Extraction Failed", "Extraction did not succeed. Please check the zip files or select another folder.")
        self.data_folder_entry.delete(0, tk.END)
        self.data_browse.config(state="normal", bg=self.DEFAULT_BROWSE_BG, activebackground=self.DEFAULT_BROWSE_BG)
        setattr(self, "zip_prompted", False)

    # --- Data Folder Change Handler ---

    def _on_data_folder_change(self, _=None):
        if getattr(self, "download_in_progress", False):
            return
        
        # Clear focus from entry widgets to prevent interference with map widget
        clear_entry_focus(self)
        
        self._clear_dynamic_widgets_and_shapes()
        folder = self.data_folder_entry.get().strip()
        bg = self.DEFAULT_BROWSE_BG

        # Clean up all dynamic widgets and shapes
        self._clear_dynamic_widgets_and_shapes()

        # 1. Default background: nothing selected
        if not folder:
            self._set_data_browse_bg(bg)
            self._set_controls_state("disabled")
            self.hide_query_btn()
            self.hide_download_btn()
            return

        # Create folder if not exists (treat non-existent paths as valid empty folders)
        if not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except Exception as e:
                # If folder creation fails, still proceed as if it's valid
                # This allows the user to work with the path and handle permission issues manually
                print(f"Warning: Could not create folder {folder}: {e}")
                # Continue with the function - treat as empty folder

        safe_dirs, zip_files = get_safe_and_zip_files(folder)
        safe_dirs_tiff = []
        for safe_dir in safe_dirs:
            measurement_dir = os.path.join(safe_dir, "measurement")
            if os.path.isdir(measurement_dir):
                tiff_files = [
                    os.path.join(measurement_dir, f)
                    for f in os.listdir(measurement_dir)
                    if f.lower().endswith(".tiff") and os.path.exists(os.path.join(measurement_dir, f))
                ]
                safe_dirs_tiff.extend(tiff_files)
        safe_dirs_tiff = list(dict.fromkeys(safe_dirs_tiff))
        dir_pol_summary = self._summarize_polarizations_from_files(safe_dirs_tiff)
        zip_pol_summary = self._summarize_polarizations_from_files(zip_files)

        # Detect and set flight direction from manifest files
        self._detect_and_set_flight_direction(safe_dirs, zip_files)

        # Handle case where both ZIP files and SAFE directories are found
        if safe_dirs and zip_files:
            DataHandlers.handle_mixed_safe_and_zip_files(self, folder, safe_dirs, zip_files, dir_pol_summary, zip_pol_summary)
            return

        if safe_dirs:
            DataHandlers.handle_safe_dirs_found(self, folder, safe_dirs, dir_pol_summary, zip_pol_summary)
            return

        if zip_files and not safe_dirs:
            DataHandlers.handle_zip_files_found(self, folder, zip_files, zip_pol_summary)
            return

        self.zip_prompted = False

        if not safe_dirs and not zip_files:
            # Enable flight direction controls for manual selection when no data files
            self._enable_flight_direction_controls()
            
            self._set_data_browse_bg("red")
            self.show_query_btn()
            self._update_data_query_btn_state_wrapper()
            self._set_controls_state("normal")
            self._clear_extent_and_date_labels()
            self.hide_download_btn()
            # Hide extraction button when no data files are found
            if hasattr(self, 'hide_extract_btn'):
                self.hide_extract_btn()
            self._clear_dynamic_widgets_and_shapes()
            self._setup_subswath_controls(None, None)
            self._setup_polarization_controls(None, None)
            self._show_output_folder_and_project_controls()
            
            # Ensure focus is properly cleared from the entry widget
            clear_entry_focus(self)

    # --- Helper Methods for _on_data_folder_change ---

    def _setup_subswath_controls(self, safe_dirs, zip_files):
        if hasattr(self, "subswath_frame") and self.subswath_frame:
            self.subswath_frame.destroy()
            self.subswath_frame = None

        if not (safe_dirs or zip_files):
            self.subswath_vars = None
            return

        row = self._get_row("data_folder") + 1
        self.subswath_frame = tk.Frame(self.root)
        self.subswath_frame.grid(row=row, column=2, columnspan=2, padx=10, pady=5, sticky="w")
        
        subswath_label = tk.Label(self.subswath_frame, text="Subswaths:")
        subswath_label.pack(side="left", padx=(0, 6))
        add_tooltip(subswath_label, "Sentinel-1 IW mode acquires data in 3 parallel subswaths.\nSelect which subswaths to process.")

        subswath_found = set()
        if safe_dirs:
            for safe_dir in safe_dirs:
                measurement_dir = os.path.join(safe_dir, "measurement")
                if os.path.isdir(measurement_dir):
                    for fname in os.listdir(measurement_dir):
                        if fname.lower().endswith(".tiff"):
                            try:
                                subswath_idx = int(fname[6:7])
                                if subswath_idx in [1, 2, 3]:
                                    subswath_found.add(subswath_idx)
                            except Exception:
                                continue
        elif zip_files:
            subswath_found = {1, 2, 3}

        self.subswath_vars = []
        self.subswath_cbs = []
        for i in range(3):
            var = tk.IntVar(value=1 if (i+1) in subswath_found else 0)
            state = "normal" if len(subswath_found) > 1 and (i+1) in subswath_found else "disabled"
            cb = tk.Checkbutton(
                self.subswath_frame,
                text=f"Subswath-{i+1}",
                variable=var,
                state=state,
                command=self._on_subswath_selection_change
            )
            cb.pack(side="left", padx=(0, 4))
            
            # Add tooltips for each subswath
            if i == 0:
                add_tooltip(cb, "Subswath 1 (IW1): Westernmost subswath\nCovers approximately 250km swath width")
            elif i == 1:
                add_tooltip(cb, "Subswath 2 (IW2): Central subswath\nRecommended for most processing workflows")
            else:
                add_tooltip(cb, "Subswath 3 (IW3): Easternmost subswath\nCovers approximately 250km swath width")
                
            self.subswath_vars.append(var)
            self.subswath_cbs.append(cb)

        self._on_subswath_selection_change()

    def _on_subswath_selection_change(self):
        selected = [i for i, var in enumerate(self.subswath_vars) if var.get()]
        if len(selected) == 2:
            if 1 not in selected:
                self.subswath_vars[1].set(1)
                self.subswath_vars[0].set(0)
                self.subswath_vars[2].set(0)
        if not selected:
            self.subswath_vars[1].set(1)

    def get_selected_subswaths(self):
        if not hasattr(self, "subswath_vars") or self.subswath_vars is None:
            return []
        return [i+1 for i, var in enumerate(self.subswath_vars) if var.get()]

    def _clear_dynamic_widgets_and_shapes(self):
        attrs = [
            "n_label", "s_label", "e_label", "w_label",
            "sdate_label", "edate_label", "safe_dirs_label", "lbl",
            "total_imgs_label", "sub_imgs_label", "dem_entry", "dwn_dem", "browse_dem", "dem_label",
            "_extract_btn"  # Include extraction button in cleanup
        ]
        for attr in attrs:
            widget = getattr(self, attr, None)
            if widget is not None and hasattr(widget, "destroy") and widget.winfo_exists():
                try:
                    widget.destroy()
                except Exception:
                    pass  # Ignore destruction errors
            setattr(self, attr, None)
        
        # Safely clear shapes with error handling
        try:
            if self.custom_shape:
                self.custom_shape.delete()
                self.custom_shape = None
        except Exception:
            self.custom_shape = None
            
        try:
            if self.rect_shape[0]:
                self.rect_shape[0].delete()
                self.rect_shape[0] = None
        except Exception:
            self.rect_shape[0] = None
            
        try:
            for poly in getattr(self.on_data_query, "polygons", []):
                poly.delete()
            self.on_data_query.polygons = []
        except Exception:
            self.on_data_query.polygons = []
            
        self.extent_limits.update(dict.fromkeys("swne"))
        self.date_limits.update({"sdate": None, "edate": None})

    def _set_data_browse_bg(self, color):
        self.data_browse.config(bg=color, activebackground=color)

    def _summarize_polarizations_from_files(self, file_list):
        """Use external function from file_operations."""
        return summarize_polarizations_from_files(file_list)

    def _draw_custom_shape_and_labels(self, max_bounds):
        points = [tuple(map(float, pair.split(','))) for pair in max_bounds.strip().split()]
        if len(points) == 4:
            polygon_points = [(lat, lon) for lon, lat in points] + [(points[0][1], points[0][0])]
            self.custom_shape = self.map_widget.set_polygon(
                polygon_points, outline_color="green", fill_color="", border_width=2
            )
            lats, lons = zip(*[(lat, lon) for lat, lon in polygon_points[:-1]])
            s, n = min(lats), max(lats)
            w, e = min(lons), max(lons)
            self.n_label = tk.Label(self.extent_frame, text=n, fg="green")
            self.n_label.grid(row=0, column=4, sticky="w", padx=(4, 0))
            self.s_label = tk.Label(self.extent_frame, text=s, fg="green")
            self.s_label.grid(row=2, column=4, sticky="w", padx=(4, 0))
            self.e_label = tk.Label(self.extent_frame, text=e, fg="green")
            self.e_label.grid(row=1, column=6, sticky="w", padx=(4, 0))
            self.w_label = tk.Label(self.extent_frame, text=w, fg="green")
            self.w_label.grid(row=1, column=2, sticky="w", padx=(4, 0))
            self.extent_limits.update({"s": s, "w": w, "n": n, "e": e})
            def draw_callback(s, w, n, e):
                draw_rectangle_on_map(self.map_widget, self.rect_shape, self.data_browse, s, w, n, e)
            update_extent_entries_from_map((s, w, n, e), self.n_entry, self.s_entry, self.w_entry, self.e_entry, draw_callback)

    def update_dem_controls(self, *_):
        dem_path = self.dem_entry.get().strip()
        if not dem_path:
            self.browse_dem.config(background=self.DEFAULT_BROWSE_BG, activebackground=self.DEFAULT_BROWSE_BG)
            if not hasattr(self, "dwn_dem") or not self.dwn_dem.winfo_exists():
                row = self._get_row("dem")
                self.dwn_dem = tk.Button(
                    self.root,
                    text="Download",
                    command=self.on_dem_download
                )
                self.dwn_dem.grid(row=row, column=3, padx=10, pady=5, sticky="w")
            else:
                self.dwn_dem.config(state="normal")
            if hasattr(self, "output_controls_frame") and self.output_controls_frame:
                self.output_controls_frame.destroy()
                self.output_controls_frame = None
        else:
            if os.path.exists(dem_path):
                self.browse_dem.config(background="green", activebackground="green")
                if hasattr(self, "dwn_dem") and self.dwn_dem.winfo_exists():
                    self.dwn_dem.config(state="disabled")
                # Show output controls when DEM Load button turns green
                self._show_output_folder_and_project_controls()
            else:
                self.browse_dem.config(background=self.DEFAULT_BROWSE_BG, activebackground=self.DEFAULT_BROWSE_BG)
                if hasattr(self, "dwn_dem") and self.dwn_dem.winfo_exists():
                    self.dwn_dem.config(state="normal")

    def _setup_polarization_controls(self, dir_pol_summary=None, zip_pol_summary=None):
        # If SAFE directories exist (extracted data), always use their polarization summary
        # This reflects the actual files available, not what's in unextracted ZIPs
        if dir_pol_summary:
            zip_pol_summary = None  # Ignore ZIP files when SAFE dirs exist
        
        if not dir_pol_summary and not zip_pol_summary:
            # If we only have zip_pol_summary, use it
            pass  # Continue with zip_pol_summary
                
        row = self._get_row("data_folder") + 1

        # Remove existing controls first
        self._remove_pol_controls()

        # If no summary, just return
        if not dir_pol_summary and not zip_pol_summary:
            return

        # Get polarization counts from the selected summary (not sum)
        pol_counts = {}
        if dir_pol_summary:
            pol_counts = {pol: dir_pol_summary.get(pol, 0) for pol in ["VV", "VH", "HH", "HV"]}
        elif zip_pol_summary:
            pol_counts = {pol: zip_pol_summary.get(pol, 0) for pol in ["VV", "VH", "HH", "HV"]}
            
        enabled_pols = [pol for pol, count in pol_counts.items() if count > 0]

        # Create new controls
        self._create_pol_controls(enabled_pols, pol_counts, row)

    def _remove_pol_controls(self):
        if hasattr(self, "pol_frame") and self.pol_frame and self.pol_frame.winfo_exists():
            self.pol_frame.destroy()
            self.pol_frame = None
        if hasattr(self, "lbl") and self.lbl and self.lbl.winfo_exists():
            self.lbl.destroy()
            self.lbl = None
        if hasattr(self, "pol_controls") and self.pol_controls:
            for pol in self.pol_controls.values():
                if pol and "frame" in pol and pol["frame"] and pol["frame"].winfo_exists():
                    pol["frame"].destroy()
        self.pol_controls = {}

    def _create_pol_controls(self, enabled_pols, pol_counts, row):
        self.pol_controls = {}
        self.pol_frame = tk.Frame(self.root)
        self.pol_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        
        pol_label = tk.Label(self.pol_frame, text="Polarization:")
        pol_label.pack(side="left", padx=(0, 6))
        add_tooltip(pol_label, "Radar polarization mode.\nDifferent polarizations provide different surface scattering information.")
        
        # Always create a new StringVar for polarization selection
        self.pol_var = tk.StringVar(value=enabled_pols[0] if enabled_pols else "VV")
        # If only one polarization is available, show it as disabled
        if len(enabled_pols) == 1:
            pol = enabled_pols[0]
            frame = tk.Frame(self.pol_frame)
            rb = tk.Radiobutton(frame, text=pol, variable=self.pol_var, value=pol, state="disabled")
            rb.pack(side="left")
            
            # Add polarization-specific tooltips
            if pol == "VV":
                add_tooltip(rb, "VV Polarization: Vertical transmit, Vertical receive\nSensitive to volume scattering and surface roughness")
            elif pol == "VH":
                add_tooltip(rb, "VH Polarization: Vertical transmit, Horizontal receive\nCross-polarization, sensitive to vegetation and volume scattering")
            elif pol == "HH":
                add_tooltip(rb, "HH Polarization: Horizontal transmit, Horizontal receive\nSimilar to VV but different sensitivity to surface orientation")
            elif pol == "HV":
                add_tooltip(rb, "HV Polarization: Horizontal transmit, Vertical receive\nCross-polarization, useful for vegetation studies")
            
            lbl = tk.Label(frame, text=f"{pol_counts[pol]} imgs found", fg="green")
            lbl.pack(side="left", padx=(2, 8))
            frame.pack(side="left")
            self.pol_controls[pol] = {"frame": frame, "rb": rb, "label": lbl}
            self.pol_var.set(pol)  # Ensure selection is set even if disabled
            self.lbl = lbl
            # Set other pols to None for consistency
            for other_pol in ["VV", "VH", "HH", "HV"]:
                if other_pol != pol:
                    self.pol_controls[other_pol] = None
        else:
            # Multiple polarizations: show enabled radiobuttons
            for pol in ["VV", "VH", "HH", "HV"]:
                if pol in enabled_pols:
                    frame = tk.Frame(self.pol_frame)
                    rb = tk.Radiobutton(frame, text=pol, variable=self.pol_var, value=pol)
                    rb.pack(side="left")
                    
                    # Add polarization-specific tooltips
                    if pol == "VV":
                        add_tooltip(rb, "VV Polarization: Vertical transmit, Vertical receive\nSensitive to volume scattering and surface roughness")
                    elif pol == "VH":
                        add_tooltip(rb, "VH Polarization: Vertical transmit, Horizontal receive\nCross-polarization, sensitive to vegetation and volume scattering")
                    elif pol == "HH":
                        add_tooltip(rb, "HH Polarization: Horizontal transmit, Horizontal receive\nSimilar to VV but different sensitivity to surface orientation")
                    elif pol == "HV":
                        add_tooltip(rb, "HV Polarization: Horizontal transmit, Vertical receive\nCross-polarization, useful for vegetation studies")
                    
                    lbl = tk.Label(frame, text=f"{pol_counts[pol]} imgs found", fg="green")
                    lbl.pack(side="left", padx=(2, 8))
                    frame.pack(side="left")
                    self.pol_controls[pol] = {"frame": frame, "rb": rb, "label": lbl}
                else:
                    self.pol_controls[pol] = None
            # Set lbl to None since multiple pols are shown
            self.lbl = None
        # Helper to set state of all pol controls
        self.set_pol_controls_state = self._set_pol_controls_state

    def _set_pol_controls_state(self, state):
        for pol in self.pol_controls.values():
            if pol and "rb" in pol and pol["rb"]:
                pol["rb"].config(state=state)

    def start_dem_download(self, mode, west, east, south, north, outdir):
        print(f"Starting DEM download with mode {mode} for bounds: {west}, {east}, {south}, {north} to {outdir}")
        self.dwn_dem.config(state="disabled")
        self.browse_dem.config(state="disabled")
        try:
            make_dem(west, east, south, north, outdir, mode=mode)
            dem_path = os.path.join(outdir, "dem.grd")
            if os.path.exists(dem_path):
                self.dem_entry.delete(0, tk.END)
                self.dem_entry.insert(0, dem_path)
                self.dem_path = dem_path
                self.dem_entry.config(state="disabled")
                self.dwn_dem.destroy()
                self.browse_dem.config(state="disabled")
                self.browse_dem.config(background="green", activebackground="green")
                self._show_output_folder_and_project_controls()
                self.update_dem_controls()
            messagebox.showinfo("DEM Download", "DEM download completed.")
        except Exception as e:
            messagebox.showerror("DEM Download Failed", str(e))
            self.dwn_dem.config(state="normal")
            self.browse_dem.config(state="normal")
        else:
            pass

    def on_dem_download(self):
        self.dwn_dem.config(state="disabled")
        self.browse_dem.config(state="disabled")
        try:
            west = clamp(self.w_entry.get(), None, None)
            east = clamp(self.e_entry.get(), None, None)
            south = clamp(self.s_entry.get(), None, None)
            north = clamp(self.n_entry.get(), None, None)
        except Exception:
            messagebox.showerror("Error", "Invalid extent values for DEM download.")
            self.dwn_dem.config(state="normal")
            self.browse_dem.config(state="normal")
            return
        outdir = self.data_folder_entry.get().strip()
        if not outdir or not os.path.exists(outdir):
            messagebox.showerror("Error", "Could not find the data folder to download DEM.")
            self.dwn_dem.config(state="normal")
            self.browse_dem.config(state="normal")
            return

        prompt = tk.Toplevel(self.root)
        prompt.title("Select DEM Type")
        tk.Label(prompt, text="Choose DEM type:").pack(padx=20, pady=10)
        btn_frame = tk.Frame(prompt)
        btn_frame.pack(pady=10)
        def start_srtm30_download():
            prompt.destroy()
            t = threading.Thread(target=self.start_dem_download, args=(1, west, east, south, north, outdir), daemon=True)
            t.start()
            # t.join()

        tk.Button(
            btn_frame,
            text="SRTM-30m",
            width=12,
            command=start_srtm30_download
        ).pack(side="left", padx=5)
        def start_srtm90_download():
            prompt.destroy()
            t = threading.Thread(target=self.start_dem_download, args=(2, west, east, south, north, outdir), daemon=True)
            t.start()
            # t.join()

        tk.Button(
            btn_frame,
            text="SRTM-90m",
            width=12,
            command=start_srtm90_download
        ).pack(side="left", padx=5)
        prompt.transient(self.root)
        prompt.grab_set()
        prompt.wait_window()

    def _get_pol_controls_state(self):
        if hasattr(self, "pol_var") and self.pol_var is not None:
            return self.pol_var.get().lower()
        return ""
    
    def prompt_btconfig(self):
        prompt = tk.Toplevel(self.root)
        prompt.title("Locate batch_tops.config")
        tk.Label(prompt, text="Unable to automatically locate batch_tops.config.\nPlease specify the full path and name:").pack(padx=20, pady=10)
        entry = tk.Entry(prompt, width=60)
        entry.pack(padx=20, pady=5)
        entry.insert(0, "")
        def on_ok():
            val = entry.get().strip()
            if not os.path.isfile(val):
                messagebox.showerror("File Not Found", "The specified file does not exist. Please try again.")
                return
            self.btconfig_path = val
            prompt.destroy()
        tk.Button(prompt, text="OK", command=on_ok).pack(pady=10)
        prompt.transient(self.root)
        prompt.grab_set()
        prompt.wait_window()
    
    def on_browse_dem(self):
        browse_file(
            self.dem_entry, "dem_file", [("DEM files", "dem.grd")]
        )
        dem_path = self.dem_entry.get().strip()
        if dem_path and os.path.exists(dem_path):
            self.browse_dem.config(state="normal")
            self.browse_dem.config(background="green", activebackground="green")
            self._show_output_folder_and_project_controls()
            self.update_dem_controls()
            self.dwn_dem.destroy()

    def _show_dem_entry_and_browse(self):
        row = self._next_row("dem")
        self.dem_entry = tk.Entry(self.root, width=50)
        
        self.dem_label = tk.Label(self.root, text="DEM File:")
        self.dem_label.grid(row=row, column=0, padx=(10, 0), pady=5, sticky="w")
        add_tooltip(self.dem_label, "Digital Elevation Model for topographic phase correction")
        
        self.dem_entry.grid(row=row, column=1, padx=10, pady=5, sticky="w")
        add_tooltip(self.dem_entry, "Path to DEM file (dem.grd format).\nUsed for removing topographic phase from interferograms.")

        self.browse_dem = tk.Button(
            self.root,
            text="Load",
            command=self.on_browse_dem,
        )
        self.browse_dem.grid(row=row, column=2, padx=10, pady=5, sticky="w")
        add_tooltip(self.browse_dem, "Browse for existing DEM file.\nButton color indicates status:\n• Default: No DEM selected\n• Green: Valid DEM file loaded")

        self.dwn_dem = tk.Button(
            self.root,
            text="Download",
            command=self.on_dem_download
        )
        self.dwn_dem.grid(row=row, column=3, padx=10, pady=5, sticky="w")
        add_tooltip(self.dwn_dem, "Download DEM data for the specified area.\nChoose between SRTM 30m or 90m resolution.")

        # Bind dem_entry changes to update controls
        self.dem_entry.bind("<KeyRelease>", self.update_dem_controls)
        self.dem_entry.bind("<FocusOut>", self.update_dem_controls)
        self.update_dem_controls()

    def show_confirm_btn_if_ready(self, event=None):
        # Check if output controls exist before accessing them
        if not (hasattr(self, "output_folder_entry") and hasattr(self, "project_name_entry")):
            return
            
        out_folder = self.output_folder_entry.get().strip()
        proj_name = self.project_name_entry.get().strip()
        
        # Validate that output_folder is not same as or within data_folder
        if out_folder and proj_name:
            data_folder = self.data_folder_entry.get().strip() if hasattr(self, "data_folder_entry") else ""
            if data_folder and out_folder:
                # Normalize paths for comparison
                try:
                    data_folder_abs = os.path.abspath(data_folder)
                    out_folder_abs = os.path.abspath(out_folder)
                    
                    # Check if output_folder is same as or within data_folder
                    try:
                        rel_path = os.path.relpath(out_folder_abs, data_folder_abs)
                        if not rel_path.startswith('..'):
                            messagebox.showerror(
                                "Invalid Output Folder",
                                "Output folder cannot be the same as or inside the data folder.\n\n"
                                f"Data Folder: {data_folder_abs}\n"
                                f"Output Folder: {out_folder_abs}\n\n"
                                "Please choose a different output location."
                            )
                            if hasattr(self, "confirm_config_btn"):
                                self.confirm_config_btn.grid_remove()
                            if hasattr(self, "gacos_btn"):
                                self.gacos_btn.grid_remove()
                            return
                    except ValueError:
                        # Different drives on Windows, no conflict
                        pass
                        
                except Exception:
                    # If path validation fails, allow it to proceed
                    pass
            
            if hasattr(self, "confirm_config_btn"):
                self.confirm_config_btn.config(state="normal")
                self.confirm_config_btn.grid()
            if hasattr(self, "gacos_btn"):
                self.gacos_btn.config(state="normal")
                self.gacos_btn.grid()
        else:
            if hasattr(self, "confirm_config_btn"):
                self.confirm_config_btn.grid_remove()
            if hasattr(self, "gacos_btn"):
                self.gacos_btn.grid_remove()


    def _show_output_folder_and_project_controls(self):
        # Destroy output_controls_frame if dem_entry does not exist
        if not hasattr(self, "dem_entry") or self.dem_entry is None:
            if hasattr(self, "output_controls_frame") and self.output_controls_frame:
                self.output_controls_frame.destroy()
                self.output_controls_frame = None
            return

        # Only show if DEM entry is valid or DEM Load button is green or during config loading
        dem_path = self.dem_entry.get().strip()
        self.dem_path = dem_path
        dem_valid = dem_path and os.path.exists(dem_path)
        dem_load_green = hasattr(self, "browse_dem") and self.browse_dem is not None and self.browse_dem.cget("background") == "green"
        config_loading = getattr(self, '_loading_config', False)
        
        if not (dem_valid or dem_load_green or config_loading):
            if hasattr(self, "output_controls_frame") and self.output_controls_frame:
                self.output_controls_frame.destroy()
                self.output_controls_frame = None
            return
        if hasattr(self, "output_controls_frame") and self.output_controls_frame:
            self.output_controls_frame.destroy()
        row = self._next_row("project_controls")
        self.output_controls_frame = tk.Frame(self.root)
        self.output_controls_frame.grid(row=row, column=0, columnspan=5, padx=10, pady=5, sticky="w")
        
        # Output Folder
        output_folder_label = tk.Label(self.output_controls_frame, text="Output Folder:")
        output_folder_label.grid(row=0, column=0, padx=(0, 4), sticky="w")
        add_tooltip(output_folder_label, "Directory where processing results will be saved")
        
        self.output_folder_entry = tk.Entry(self.output_controls_frame, width=30)
        self.output_folder_entry.grid(row=0, column=1, padx=(0, 4), sticky="w")
        add_tooltip(self.output_folder_entry, "Path to output directory.\nProject folder will be created inside this directory.")
        
        def browse_output_folder():
            browse_folder(self.output_folder_entry, "output_folder")
        
        self.output_folder_browse = tk.Button(
            self.output_controls_frame, text="Browse", 
            command=browse_output_folder
        )
        self.output_folder_browse.grid(row=0, column=2, padx=(0, 8), sticky="w")
        add_tooltip(self.output_folder_browse, "Browse and select output directory")
        
        # Project Name
        project_name_label = tk.Label(self.output_controls_frame, text="Project Name:")
        project_name_label.grid(row=0, column=3, padx=(0, 4), sticky="w")
        add_tooltip(project_name_label, "Unique name for this InSAR processing project")
        
        self.project_name_entry = tk.Entry(self.output_controls_frame, width=20)
        self.project_name_entry.grid(row=0, column=4, padx=(0, 4), sticky="w")
        add_tooltip(self.project_name_entry, "Enter a descriptive name for your project.\nThis will be used as the main project folder name.")

        # GACOS Data button (red by default), placed next to DEM controls
        if not hasattr(self, "gacos_btn") or not self.gacos_btn.winfo_exists():
            self.gacos_btn = tk.Button(
            self.output_controls_frame,
            text="GACOS Data",
            width=16,
            command=self.on_gacos_data_intermediate,
            bg="red",
            activebackground="red"
            )
            self.gacos_btn.grid(row=0, column=5, padx=10, pady=5, sticky="w")
            self.gacos_btn.grid_remove()
            add_tooltip(self.gacos_btn, "GACOS atmospheric correction data.\nButton color indicates status:\n• Red: No GACOS data configured\n• Green: GACOS data path set and validated\n\nGACOS provides zenith total delay estimates for atmospheric correction.")

        # Confirm Configuration button (initially hidden)
        self.confirm_config_btn = tk.Button(
            self.output_controls_frame,
            text="Confirm Configuration",
            command=lambda: self._on_confirm_configuration(),
            state="disabled"
        )
        self.confirm_config_btn.grid(row=0, column=6, padx=(8, 0), sticky="w")
        self.confirm_config_btn.grid_remove()
        add_tooltip(self.confirm_config_btn, "Confirm all settings and create project structure.\nEnabled when both output folder and project name are specified.")
        
        # Bind only Tab and Enter keys to show_confirm_btn_if_ready
        for entry in [self.output_folder_entry, self.project_name_entry]:
            entry.bind("<Tab>", self.show_confirm_btn_if_ready)
            entry.bind("<Return>", self.show_confirm_btn_if_ready)
    
    def on_gacos_data_intermediate(self):
        # Intermediate popup with Request Data and Load Data buttons
        intermediate_popup = tk.Toplevel(self.root)
        intermediate_popup.title("GACOS Data Options")
        tk.Label(intermediate_popup, text="Choose GACOS Data Option:").pack(padx=20, pady=10)
        btn_frame = tk.Frame(intermediate_popup)
        btn_frame.pack(pady=10)

        def on_request_data():            
            intermediate_popup.destroy()
            # Check if output controls exist before accessing them
            if not (hasattr(self, "output_folder_entry") and hasattr(self, "project_name_entry")):
                messagebox.showwarning("Request Data", "Cannot request data: output controls not available. Please ensure DEM is loaded first.")
                return
                
            outdir = self.output_folder_entry.get().strip()
            project_name = self.project_name_entry.get().strip()
            
            if not outdir or not project_name:
                messagebox.showwarning("Request Data", "Please specify both output folder and project name.")
                return
                
            indir = os.path.join(outdir, project_name, os.listdir(outdir)[0],"raw")
            if os.path.exists(indir):
                print(f"Looking for metadata in {indir}")
            else:
                indir = self.data_folder_entry.get().strip()
            # Use label values if they exist, otherwise use entry values
            n = self.n_label.cget("text") if hasattr(self, "n_label") and self.n_label else self.n_entry.get().strip()
            w = self.w_label.cget("text") if hasattr(self, "w_label") and self.w_label else self.w_entry.get().strip()
            e = self.e_label.cget("text") if hasattr(self, "e_label") and self.e_label else self.e_entry.get().strip()
            s = self.s_label.cget("text") if hasattr(self, "s_label") and self.s_label else self.s_entry.get().strip()
            aoi = (n, w, e, s)
            # Prompt user for email address in a popup
            email_popup = tk.Toplevel(self.root)
            email_popup.title("Enter Email Address")
            tk.Label(email_popup, text="Enter your email address:").pack(padx=20, pady=10)
            email_entry = tk.Entry(email_popup, width=40)
            email_entry.pack(padx=20, pady=5)
            email_entry.focus_set()

            def on_email_submit():
                email = email_entry.get().strip()
                if not email or "@" not in email:
                    messagebox.showerror("Invalid Email", "Please enter a valid email address.")
                    return
                email_popup.destroy()
                print(f"Submitting GACOS batch request for AOI {aoi} to {indir} with email {email}")
                # submit_gacos_batch(aoi, hh, mm, dates, email)
                submit_gacos_batch(indir, aoi, email)

            submit_btn = tk.Button(email_popup, text="Submit", command=on_email_submit)
            submit_btn.pack(pady=10)
            email_popup.transient(self.root)
            email_popup.grab_set()
            email_popup.wait_window()


        def on_load_data():
            intermediate_popup.destroy()
            self.on_gacos_data()

        tk.Button(btn_frame, text="Request Data", width=14, command=on_request_data).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Load Data", width=14, command=on_load_data).pack(side="left", padx=8)
        intermediate_popup.transient(self.root)
        intermediate_popup.grab_set()
        intermediate_popup.wait_window()

    def _on_confirm_configuration(self):
        # Check if output controls exist before accessing them
        if not (hasattr(self, "output_folder_entry") and hasattr(self, "project_name_entry")):
            messagebox.showwarning("Configuration", "Output controls not available. Please ensure DEM is loaded first.")
            return
            
        self._create_TS_steps_buttons()
        out_folder = self.output_folder_entry.get().strip()
        proj_name = self.project_name_entry.get().strip()
        
        if not out_folder or not proj_name:
            messagebox.showwarning("Configuration", "Please specify both output folder and project name.")
            return
        
        # Validate that output_folder is not same as or within data_folder
        data_folder = self.data_folder_entry.get().strip() if hasattr(self, "data_folder_entry") else ""
        if data_folder and out_folder:
            try:
                data_folder_abs = os.path.abspath(data_folder)
                out_folder_abs = os.path.abspath(out_folder)
                
                # Check if output_folder is same as or within data_folder
                try:
                    rel_path = os.path.relpath(out_folder_abs, data_folder_abs)
                    if not rel_path.startswith('..'):
                        messagebox.showerror(
                            "Invalid Output Folder",
                            "Output folder cannot be the same as or inside the data folder.\n\n"
                            f"Data Folder: {data_folder_abs}\n"
                            f"Output Folder: {out_folder_abs}\n\n"
                            "Please choose a different output location."
                        )
                        return
                except ValueError:
                    pass  # Different drives on Windows
            except Exception:
                pass  # Allow to proceed if validation fails
            
        self.log_file = None
        
        if out_folder and proj_name:
            full_path = os.path.join(out_folder, proj_name)
            try:
                os.makedirs(full_path, exist_ok=True)
            except Exception:
                return
            self.confirm_config_btn.config(state="disabled")
            now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = os.path.join(full_path, f"{proj_name}_{now}.log")
            # structuring
            # 1. Clamped extents
            n = self.n_label.cget("text") if hasattr(self, "n_label") and self.n_label else self.n_entry.get().strip()
            w = self.w_label.cget("text") if hasattr(self, "w_label") and self.w_label else self.w_entry.get().strip()
            e = self.e_label.cget("text") if hasattr(self, "e_label") and self.e_label else self.e_entry.get().strip()
            s = self.s_label.cget("text") if hasattr(self, "s_label") and self.s_label else self.s_entry.get().strip()
            print("Clamped extents:", {"n": n, "s": s, "e": e, "w": w})

            # 2. Textbox extents
            print("Textbox extents:", {
                "n": self.n_entry.get(),
                "s": self.s_entry.get(),
                "e": self.e_entry.get(),
                "w": self.w_entry.get()
            })

            # 3. Textbox dates
            stdate = self.start_var.get()
            endate = self.end_var.get()
            

            # 4. Flight direction selection value
            print("Flight direction selection value:", self.flight_dir_var.get())

            # 5. data_entry (data folder)
            print("data_entry:", self.data_folder_entry.get().strip())

            # 6. Selected polarization
            print("Selected polarization:", self._get_pol_controls_state())

            # 7. Subswaths
            print("subswaths:", self.get_selected_subswaths())

            # 8. dem_entry
            dem_val = self.dem_entry.get().strip() if hasattr(self, "dem_entry") else ""
            print("dem_entry:", dem_val)

            # 9. Output_folder
            out_folder_val = self.output_folder_entry.get().strip() if hasattr(self, "output_folder_entry") else ""
            print("Output_folder:", out_folder_val)

            # 10. Project Name
            proj_name_val = self.project_name_entry.get().strip() if hasattr(self, "project_name_entry") else ""
            print("Project Name:", proj_name_val)

            # 11. Pin file
            pin_file = os.path.join(self.data_folder_entry.get().strip(), "pins.II")
            # Write pin_file based on extents and flight direction
            try:
                E = float(self.e_entry.get())
                N = float(self.n_entry.get())
                W = float(self.w_entry.get())
                S = float(self.s_entry.get())
                fd = self.flight_dir_var.get().strip().lower()
                with open(pin_file, "w") as f:
                    if fd == "descending":
                        f.write(f"{E} {N}\n{W} {S}")
                    elif fd == "ascending":
                        f.write(f"{E} {S}\n{W} {N}")
                    else:
                        raise ValueError(f"Problem creating pin file at {pin_file}.")
            except Exception as e:
                print(f"Failed to write pin_file: {e}")
            
            # 12. BTConfig
            share_dir = subprocess.getoutput("gmtsar_sharedir.csh").strip()
            # Determine btconfig path based on share_dir
            btconfig = ""
            

            # Try to determine btconfig path
            self.btconfig_path = ""
            if share_dir:
                # Typical location: .../gmtsar/csh/batch_tops.config
                btconfig_guess = os.path.join(os.path.dirname(os.path.dirname(share_dir)), "gmtsar", "csh", "batch_tops.config")
                if os.path.isfile(btconfig_guess):
                    self.btconfig_path = btconfig_guess
                else:
                    self.prompt_btconfig()
            else:
                self.prompt_btconfig()
            btconfig = self.btconfig_path

            # 13. polarization
            pol = self._get_pol_controls_state()

            process_logger(process_num=0.1, log_file=self.log_file, message="Creating project structure and copying data...", mode="start")

            # Call orchestrate_structure_and_copy and store results as instance variables
            self.paths, self.structure = orchestrate_structure_and_copy(
                out_folder_val,
                proj_name_val,
                self.flight_dir_var.get(),
                self.get_selected_subswaths(),
                self.dem_entry.get().strip(),
                pin_file,
                self.data_folder_entry.get().strip(),
                btconfig,
                pol.lower(),
                stdate,
                endate
            )
            self._save_config()
            if isinstance(self.paths, dict):
                self.paths["log_file_path"] = self.log_file
            process_logger(process_num=0.1, log_file=self.log_file, message="Project structure created and data copied.", mode="end")

    def on_gacos_data(self):
        # Popup for GACOS data entry
        popup = tk.Toplevel(self.root)
        popup.title("GACOS Data")
        tk.Label(popup, text="GACOS Data Path:").grid(row=0, column=0, padx=10, pady=10)
        self.gacos_data_entry = tk.Entry(popup, width=40)
        self.gacos_data_entry.grid(row=0, column=1, padx=10, pady=10)

        def browse_gacos():
            browse_folder(self.gacos_data_entry)

        browse_btn = tk.Button(popup, text="Browse", command=browse_gacos)
        browse_btn.grid(row=0, column=2, padx=10, pady=10)

        def on_close():
            self.gacos_data_path = self.gacos_data_entry.get().strip()
            self._set_gacos_btn_state()
            popup.destroy()
            
        close_btn = tk.Button(popup, text="Close", command=on_close)
        close_btn.grid(row=1, column=1, pady=10)
        popup.transient(self.root)
        popup.grab_set()
        popup.wait_window()

    def _set_gacos_btn_state(self):
        if hasattr(self, "gacos_btn") and self.gacos_btn.winfo_exists():
            if hasattr(self, "gacos_data_path") and self.gacos_data_path:                
                ztd_files = [os.path.join(root, f) for root, _, files in os.walk(self.gacos_data_path) for f in files if f.lower().endswith('.ztd')]                
                safe_dirs = [os.path.join(root, f) for root, dirs, _ in os.walk(self.data_folder_entry.get().strip()) for f in dirs if f.endswith('.SAFE')]
                print(f"Found {len(ztd_files)} GACOS ZTD files and {len(safe_dirs)} SAFE directories.")
                if ztd_files and safe_dirs:
                    if not len(ztd_files) < len(safe_dirs):
                        
                        messagebox.showinfo("GACOS Data", "Number of GACOS files equal or exceed S1 files but user has to ensure if the GACOS files are correct.")
                        self.gacos_btn.config(bg="green", activebackground="green")                                  
            else:
                self.gacos_btn.config(bg="red", activebackground="red")
          

    def on_next_step(self):        
        # Check if output controls exist before accessing them
        if not (hasattr(self, "output_folder_entry") and hasattr(self, "project_name_entry")):
            messagebox.showwarning("Next Step", "Cannot proceed: output controls not available. Please ensure DEM is loaded first.")
            return
            
        outdir = os.path.join(self.output_folder_entry.get().strip(), self.project_name_entry.get().strip())
        
        if not outdir.strip():
            messagebox.showwarning("Next Step", "Please specify both output folder and project name before proceeding.")
            return
            
        flight_dir = self.flight_dir_var.get().lower()
        if flight_dir == "descending":
            xdir = "des"
        elif flight_dir == "ascending":
            xdir = "asc"
        maindir = os.path.join(outdir, xdir)
        def process_files_thread():        
            process_logger(process_num=0.2, log_file=self.log_file, message="Downloading orbit files...", mode="start")
            print(f"Downloading orbit files to {os.path.join(maindir, 'data')}")    
            
            if hasattr(self, "download_orbit_btn") and self.download_orbit_btn.winfo_exists():
                self.download_orbit_btn.config(state="disabled")
            # if hasattr(self, "ts_analysis_btn") and self.ts_analysis_btn.winfo_exists():
            #     self.ts_analysis_btn.config(state="disabled")            
            if self.paths:            
                for key in ['pF1', 'pF2', 'pF3']:
                    pfx = self.paths.get(key)
                    if pfx:
                        pfxraw = os.path.join(pfx, "raw")
                        data_in = os.path.join(pfx, "raw", "data.in")
                        data_in_lines = sum(1 for _ in open(data_in, "r")) if os.path.exists(data_in) else None
                        # Count *.tiff files in pfxraw
                        tiff_files = [f.split('.')[0] for f in os.listdir(pfxraw) if f.lower().endswith(".tiff")] if os.path.exists(pfxraw) else []
                                                
                        ddata = self.paths.get("pdata", "")
                        indata = self.data_folder_entry.get().strip()
                        in_safe = [os.path.join(root, d) for root, dirs, _ in os.walk(indata) for d in dirs if d.endswith(".SAFE")]

                        if os.path.exists(pfxraw) and data_in_lines is not None and data_in_lines == len(tiff_files):
                            print("Orbits already downloaded.")
                            if hasattr(self, "download_orbit_btn") and self.download_orbit_btn.winfo_exists():
                                self.download_orbit_btn.config(state="disabled", bg="green", activebackground="green")
                        else:
                            # Try up to 4 times to process_files in case of connection problems
                            max_attempts = 4
                            for attempt in range(1, max_attempts + 1):
                                try:
                                    process_files(os.path.join(maindir, "data"), maindir)
                                    break  # Success, exit the retry loop
                                except Exception as e:
                                    print(f"Attempt {attempt} to download orbit files failed: {e}")
                                    if attempt == max_attempts:
                                        messagebox.showerror(
                                            "Orbit Download Failed",
                                            f"Failed to download orbit files after {max_attempts} attempts.\n\nError: {e}"
                                        )
                            data_in_tiffs = [f.split(':')[0] for f in open(data_in, "r")]
                            din_dates = [t[15:23] for t in data_in_tiffs]
                            if len(data_in_tiffs) != len(tiff_files):
                                print("Removing tiff files having no orbits available.")
                                for tiff in tiff_files:
                                    if tiff not in data_in_tiffs:
                                        try:
                                            os.unlink(os.path.join(pfxraw, tiff + ".tiff"))
                                            os.unlink(os.path.join(pfxraw, tiff + ".xml"))
                                
                                        except Exception as e:
                                            print(f"Error removing {tiff}: {e}")
                                if ddata and os.path.exists(ddata):
                                    print(f"Removing SAFE directories in {ddata} having no orbits available.")
                                    # Remove SAFE directories that do not have corresponding tiff dates
                                    
                                    for sf in os.listdir(ddata):
                                        # print(sf, din_dates[0])
                                        if sf.endswith(".SAFE") and sf[17:25] not in din_dates:
                                            
                                            try:
                                                print(f"Removing {sf} from {ddata}")
                                                os.unlink(os.path.join(ddata, sf))
                                                for sf_org in in_safe:
                                                    if os.path.basename(sf_org) == sf:
                                                        print(f"Also removing {sf_org} from {indata}")
                                                        os.rename(sf_org, sf_org + ".NO_ORBITS")
                                            except Exception as e:
                                                print(f"Error removing {sf}: {e}")

                            print("Orbit file download completed.")
            if hasattr(self, "baselines_btn") and self.baselines_btn.winfo_exists():
                self.baselines_btn.config(state="normal")
            if hasattr(self, "download_orbit_btn") and self.download_orbit_btn.winfo_exists():
                self.download_orbit_btn.config(state="disabled", bg="green", activebackground="green")
                process_logger(process_num=0.2, log_file=self.log_file, message="Orbit files downloaded.", mode="end")            
            
        thread_process = threading.Thread(target=process_files_thread)
        thread_process.start()
        # thread_process.join()  # Wait for the thread to finish before returning        

        # Disable all available UI controls
        self._set_controls_state("disabled")
        if hasattr(self, "data_browse") and self.data_browse.winfo_exists():
            self.data_browse.config(state="disabled")
        if hasattr(self, "browse_dem") and self.browse_dem.winfo_exists():
            self.browse_dem.config(state="disabled")
        if hasattr(self, "dwn_dem") and self.dwn_dem.winfo_exists():
            self.dwn_dem.config(state="disabled")
        if hasattr(self, "output_folder_browse") and self.output_folder_browse.winfo_exists():
            self.output_folder_browse.config(state="disabled")
        if hasattr(self, "output_folder_entry") and self.output_folder_entry.winfo_exists():
            self.output_folder_entry.config(state="disabled")
        if hasattr(self, "project_name_entry") and self.project_name_entry.winfo_exists():
            self.project_name_entry.config(state="disabled")
        if hasattr(self, "data_folder_entry") and self.data_folder_entry.winfo_exists():
            self.data_folder_entry.config(state="disabled")
        if hasattr(self, "dem_entry") and self.dem_entry.winfo_exists():
            self.dem_entry.config(state="disabled")
        if hasattr(self, "data_query_btn") and self.data_query_btn.winfo_exists():
            self.data_query_btn.config(state="disabled")
        if hasattr(self, "data_download_btn") and self.data_download_btn.winfo_exists():
            self.data_download_btn.config(state="disabled")
        if hasattr(self, "subswath_cbs"):
            for cb in self.subswath_cbs:
                if cb.winfo_exists():
                    cb.config(state="disabled")
        if hasattr(self, "pol_controls"):
            for pol in self.pol_controls.values():
                if pol and "rb" in pol and pol["rb"].winfo_exists():
                    pol["rb"].config(state="disabled")
        if hasattr(self, "gacos_btn") and self.gacos_btn.winfo_exists():
            self.gacos_btn.config(state="disabled")        

    def on_baselines_btn_click(self):
        # Validate data.in files before opening Base2Net GUI
        validation_passed = self._validate_data_in_files()
        
        if not validation_passed:
            return  # User chose to abort or validation failed
            
        # Create a new Toplevel window for BaselineGUI
        baseline_window = tk.Toplevel(self.root)

        # Define the callback function to receive the result from the child
        def on_edges_exported(result, align_method, esd_mode):
            self.mst = result
            self.align_mode = align_method
            self.esd_mode = esd_mode
            print("Selected master:", result)   # Use the returned value here
            baseline_window.destroy()          # Close the child window
            if self.mst:
                # Enable the next button in the main window
                if hasattr(self, "align_intf_gen_btn") and self.align_intf_gen_btn.winfo_exists():
                    self.align_intf_gen_btn.config(state="normal")
                if hasattr(self, "baselines_btn") and self.baselines_btn.winfo_exists():
                    self.baselines_btn.config(state="disabled", bg="green", activebackground="green")
                

        # Create BaselineGUI and pass the callback with log_file
        BaselineGUI(baseline_window, self.dem_path, self.paths, on_edges_exported=on_edges_exported, log_file=self.log_file)

    def _validate_data_in_files(self):
        """
        Validate data.in files against TIFF and EOF files in each subswath.
        
        Returns:
            bool: True if validation passes or user chooses to continue, False if user aborts
        """
        from .utils.utils import validate_data_in_vs_files
        
        validation_issues = []
        
        # Check each subswath directory
        for key in ['pF1', 'pF2', 'pF3']:
            if key not in self.paths:
                continue
                
            subswath_path = self.paths[key]
            if not os.path.exists(subswath_path):
                continue
                
            praw = os.path.join(subswath_path, "raw")
            
            if not os.path.exists(praw):
                validation_issues.append(f"Raw directory not found for {key}: {praw}")
                continue
                
            # Validate this subswath's data.in file
            validation = validate_data_in_vs_files(praw)
            
            if not validation['valid']:
                issue_details = [f"Subswath {key}:"]
                
                if 'error' in validation:
                    issue_details.append(f"  Error: {validation['error']}")
                else:
                    issue_details.append(f"  data.in entries: {validation['data_in_count']}")
                    issue_details.append(f"  TIFF files found: {validation['tiff_count']}")
                    issue_details.append(f"  EOF files found: {validation['eof_count']}")
                    
                    if validation['missing_tiff']:
                        issue_details.append(f"  Missing TIFF files: {len(validation['missing_tiff'])}")
                    if validation['missing_eof']:
                        issue_details.append(f"  Missing EOF files: {len(validation['missing_eof'])}")
                    if validation['extra_tiff']:
                        issue_details.append(f"  Extra TIFF files: {len(validation['extra_tiff'])}")
                    if validation['extra_eof']:
                        issue_details.append(f"  Extra EOF files: {len(validation['extra_eof'])}")
                
                validation_issues.append("\n".join(issue_details))
        
        # If there are validation issues, show prompt
        if validation_issues:
            message = "⚠️  Data.in File Validation Issues Detected\n\n"
            message += "\n\n".join(validation_issues)
            message += "\n\nThis may indicate missing files or incomplete data extraction."
            message += "\nDo you want to continue with baseline analysis anyway?"
            
            result = messagebox.askyesno(
                "Data Validation Warning",
                message,
                icon='warning'
            )
            
            if not result:
                print("User aborted baseline analysis due to data validation issues")
                return False
            else:
                print("User chose to continue despite validation issues")
                
        return True

    def _create_TS_steps_buttons(self):
        """Create buttons for TS steps after orbits download."""
        row = self._next_row("ts_steps_frame")

        # Create a frame to hold all 4 buttons in a single row, side by side
        ts_steps_frame = tk.Frame(self.root)
        ts_steps_frame.grid(row=row, column=0, columnspan=8, padx=10, pady=10, sticky="w")
        add_tooltip(ts_steps_frame, "InSAR Time Series Processing Workflow\nFollow these steps in sequence for complete processing")

        
        self.download_orbit_btn = tk.Button(
            ts_steps_frame, 
            text="00_Download Orbit Files", 
            width=16, 
            command=self.on_next_step
        )
        self.download_orbit_btn.pack(side="left", padx=8)
        add_tooltip(self.download_orbit_btn, "Step 0: Download precise orbit files\nRequired for accurate geocoding and coregistration\nButton turns green when completed")

        # Disable all available UI controls
        self._set_controls_state("disabled")
        if hasattr(self, "data_browse") and self.data_browse.winfo_exists():
            self.data_browse.config(state="disabled")
        if hasattr(self, "browse_dem") and self.browse_dem.winfo_exists():
            self.browse_dem.config(state="disabled")
        if hasattr(self, "dwn_dem") and self.dwn_dem.winfo_exists():
            self.dwn_dem.config(state="disabled")
        if hasattr(self, "output_folder_browse") and self.output_folder_browse.winfo_exists():
            self.output_folder_browse.config(state="disabled")
        if hasattr(self, "output_folder_entry") and self.output_folder_entry.winfo_exists():
            self.output_folder_entry.config(state="disabled")
        if hasattr(self, "project_name_entry") and self.project_name_entry.winfo_exists():
            self.project_name_entry.config(state="disabled")
        if hasattr(self, "data_folder_entry") and self.data_folder_entry.winfo_exists():
            self.data_folder_entry.config(state="disabled")
        if hasattr(self, "dem_entry") and self.dem_entry.winfo_exists():
            self.dem_entry.config(state="disabled")
        if hasattr(self, "data_query_btn") and self.data_query_btn.winfo_exists():
            self.data_query_btn.config(state="disabled")
        if hasattr(self, "data_download_btn") and self.data_download_btn.winfo_exists():
            self.data_download_btn.config(state="disabled")
        if hasattr(self, "subswath_cbs"):
            for cb in self.subswath_cbs:
                if cb.winfo_exists():
                    cb.config(state="disabled")
        if hasattr(self, "pol_controls"):
            for pol in self.pol_controls.values():
                if pol and "rb" in pol and pol["rb"].winfo_exists():
                    pol["rb"].config(state="disabled")
        if hasattr(self, "gacos_btn") and self.gacos_btn.winfo_exists():
            self.gacos_btn.config(state="disabled")
        
        self.baselines_btn = tk.Button(
            ts_steps_frame,
            text="01_Base2Net",
            state="disabled",
            command=self.on_baselines_btn_click
        )
        add_tooltip(self.baselines_btn, "Step 1: Baseline analysis and network design\nAnalyze temporal and perpendicular baselines\nSelect master image and interferometric pairs")
        
        self.align_intf_gen_btn = tk.Button(
            ts_steps_frame,
            text="02_Align imgs & Gen. INTFs",
            state="disabled",
            command=self._process_02
        )
        add_tooltip(self.align_intf_gen_btn, "Step 2: Image alignment and interferogram generation\nAlign slave images to master\nGenerate interferograms from image pairs")
        
        self.unwrap_btn = tk.Button(
            ts_steps_frame,
            text="03_Unwrap INTFs",
            state="disabled",
            command=self._show_unwrap_app
        )
        add_tooltip(self.unwrap_btn, "Step 3: Phase unwrapping\nUnwrap interferometric phase\nApply atmospheric corrections if available")
        
        self.inversion_btn = tk.Button(
            ts_steps_frame,
            text="04_SBAS",
            state="disabled",
            command=self._show_sbas_app
        )
        add_tooltip(self.inversion_btn, "Step 4: Small Baseline Subset (SBAS) inversion\nEstimate time series deformation\nGenerate velocity and displacement maps")

        # Pack all buttons side by side
        self.baselines_btn.pack(side="left", padx=8)
        self.align_intf_gen_btn.pack(side="left", padx=8)
        self.unwrap_btn.pack(side="left", padx=8)
        self.inversion_btn.pack(side="left", padx=8)

    def _process_02(self):
        """Process step 02: Align images and generate interferograms."""
        if not hasattr(self, "paths") or not self.paths:
            print("No paths found. Cannot proceed with alignment.")
            return
        if not hasattr(self, "mst") or not self.mst:
            print("No master image selected. Cannot proceed with alignment.")
            return

        process_logger(process_num=2, log_file=self.log_file, message="Starting image alignment and interferogram generation...", mode="start")

        if hasattr(self, "align_intf_gen_btn") and self.align_intf_gen_btn.winfo_exists():
            self.align_intf_gen_btn.config(state="disabled")

        align_Ifggen_window = tk.Toplevel(self.root)

        # Define the callback to be called when GenIfg completes
        def on_gen_ifg_done(*args, **kwargs):
            print("on_gen_ifg_done is called")
            pF1 = self.paths.get("pF1")
            pF2 = self.paths.get("pF2")
            pF3 = self.paths.get("pF3")
            pmerge = self.paths.get("pmerge")
            if pF1 and os.path.exists(pF1):
                self.pF1 = pF1
            else:
                self.pF1 = None
            if pF2 and os.path.exists(pF2):
                self.pF2 = pF2
            else:
                self.pF2 = None
            if pF3 and os.path.exists(pF3):
                self.pF3 = pF3
            else:
                self.pF3 = None
            if pmerge and os.path.exists(pmerge):
                self.pmerge = pmerge
            else:
                self.pmerge = None
            
            for subswath in [self.pF1, self.pF2, self.pF3]:
                if subswath and os.path.exists(subswath):
                    raw_folder = os.path.join(subswath, "raw")
                    if os.path.exists(raw_folder):
                        status_info = check_alignment_completion_status(raw_folder)
                        if status_info['status'] == 'complete':
                            print(f"Alignment completed successfully for {subswath} ({status_info['aligned_images']}/{status_info['total_images']} images)")
                        else:
                            print(f"Alignment not completed successfully for {subswath} ({status_info['aligned_images']}/{status_info['total_images']} images)")
                            return
                    else:
                        print(f"Raw folder not found for {subswath}")
                        return
                    if check_ifgs_completion(subswath):
                        print(f"IFG generation completed successfully for {subswath}")
                    else:
                        print(f"IFG generation not completed successfully for {subswath}")
                        return
            if self.pmerge and os.path.exists(self.pmerge):
                if check_merge_completion(os.path.dirname(self.pmerge)):
                    print(f"Merge completed successfully for {self.pmerge}")
                else:
                    print(f"Merge not completed successfully for {self.pmerge}")
                    return

            process_logger(process_num=2, log_file=self.log_file, message="Image alignment and interferogram generation completed.", mode="end")

            if hasattr(self, "unwrap_btn") and self.unwrap_btn.winfo_exists():
                self.unwrap_btn.config(state="normal")
            if hasattr(self, "align_intf_gen_btn") and self.align_intf_gen_btn.winfo_exists():
                self.align_intf_gen_btn.config(state="disabled", bg="green", activebackground="green")
            if align_Ifggen_window.winfo_exists():
                align_Ifggen_window.destroy()

        # Run GenIfg, then call on_gen_ifg_done after it completes
        def run_gen_ifg_and_callback():
            GenIfg(align_Ifggen_window, self.paths, self.mst, self.dem_path, self.align_mode, self.esd_mode, on_done=lambda: self.root.after(0, on_gen_ifg_done))
            

        threading.Thread(target=run_gen_ifg_and_callback, daemon=True).start()

        # Prevent user from closing the window manually during processing
        align_Ifggen_window.protocol("WM_DELETE_WINDOW", lambda: None)
        align_Ifggen_window.transient(self.root)
        align_Ifggen_window.grab_set()

    # Store subswath paths for use by other methods
    def _store_subswath_paths(self):
        """Store subswath paths as instance variables for later use."""
        for key in ['pF1', 'pF2', 'pF3', 'pmerge']:
            path = self.paths.get(key)
            if path and os.path.exists(path):
                setattr(self, key, path)
            else:
                setattr(self, key, None)


    def _show_unwrap_app(self):
        intfdir = None
        IFGs = []
        # Determine ifgsroot from self.paths if available

        if self.pmerge and os.path.exists(self.pmerge):
            IFGs = [d for d in next(os.walk(self.pmerge))[1] if not os.path.exists(os.path.join(self.pmerge, d, "unwrap.grd"))]
            intfdir = self.pmerge
        else:
            for dir_path in [self.pF1, self.pF2, self.pF3]:
                if dir_path and os.path.exists(dir_path):
                    intfdir = os.path.join(dir_path, "intf_all")
                    IFGs = [d for d in next(os.walk(intfdir))[1] if not os.path.exists(os.path.join(intfdir, d, "unwrap.grd"))]                
                    break
        
        self.ifgsroot = intfdir
        self.IFGs = IFGs        

        # Import UnwrapApp dynamically to avoid circular import
        # Only create a new unwrap_window if one is not already open
        if hasattr(self, "unwrap_window") and self.unwrap_window.winfo_exists():
            self.unwrap_window.lift()
            self.unwrap_window.focus_force()
            return
        self.unwrap_window = tk.Toplevel(self.root)        

        UnwrapApp(self.unwrap_window, self.ifgsroot, self.IFGs, self.gacos_data_path, log_file=self.log_file)
        # Wait until the window is destroyed, then print the command
        self.unwrap_window.wait_window()
        
        # Set 03_Unwrap button to green and disabled
        if hasattr(self, "unwrap_btn") and self.unwrap_btn.winfo_exists():
            self.unwrap_btn.config(state="disabled", bg="green", activebackground="green")
        # Enable 04_SBAS button
        if hasattr(self, "inversion_btn") and self.inversion_btn.winfo_exists():
            self.inversion_btn.config(state="normal")        

    def _show_sbas_app(self):
        # Only create a new sbas_window if one is not already open
        if hasattr(self, "sbas_window") and self.sbas_window.winfo_exists():
            self.sbas_window.lift()
            self.sbas_window.focus_force()
            return
        
        # Use the same IFGs and ifgsroot as in unwrap
        ifgsroot = getattr(self, "ifgsroot", None)
        IFGs = getattr(self, "IFGs", [])
        gacosdir = getattr(self, "gacos_data_path", "")
        
        try:
            self.sbas_window = tk.Toplevel(self.root)
            SBASApp(self.sbas_window, self.paths, ifgsroot, IFGs, gacosdir, log_file=self.log_file)
            
            # Wait until the window is destroyed, then set button states
            self.sbas_window.wait_window()
            
            # Set 04_SBAS button to green and disabled after window closes
            if hasattr(self, "inversion_btn") and self.inversion_btn.winfo_exists():
                self.inversion_btn.config(state="disabled", bg="green", activebackground="green")
                
        except Exception as e:
            print(f"Error creating SBAS window: {e}")
            # If error occurred, don't change button state
            if hasattr(self, "sbas_window"):
                try:
                    self.sbas_window.destroy()
                except:
                    pass
                delattr(self, "sbas_window")

    # def _handle_zip_files_found_with_query_option(self, folder, zip_files, zip_pol_summary):
    #     """
    #     Handle zip files found in folder with option to query for additional data.
    #     Shows extent from zip files but allows querying for more data.
    #     """
    #     # Derive extent from ALL zip files and show red bounding box
    #     extent_from_zips = self._get_extent_from_zip_files(zip_files)
    #     extent_extraction_successful = extent_from_zips is not None
        
    #     # Derive date range from ALL zip files  
    #     dates_from_zips = self._get_dates_from_zip_files(zip_files)
        
    #     # Set flag to prevent config from overwriting zip-derived values
    #     self._zip_derived_values = True
        
    #     if extent_extraction_successful:
    #         # Set the extent limits from zip files
    #         self.extent_limits.update(extent_from_zips)            
    #         # Display extent and draw red bounding box
    #         self._display_extent_labels(extent_from_zips)
    #         self._draw_extent_rectangle(extent_from_zips)
    #         # Disable extent editing (user can't modify the extent derived from zip files)
    #         disable_extent_editing(self.n_entry, self.s_entry, self.e_entry, self.w_entry)
    #     else:
    #         # If extent extraction failed (invalid zip files), re-enable extent editing
    #         enable_extent_editing(self.n_entry, self.s_entry, self.e_entry, self.w_entry)
    #         print("Warning: Could not extract extent from zip files, extent editing enabled")
        
    #     # Set dates from zip files if extracted successfully
    #     if dates_from_zips:
    #         self.start_var.set(dates_from_zips['start'])
    #         self.end_var.set(dates_from_zips['end'])
    #         print(f"Set date range from zip files: {dates_from_zips['start']} to {dates_from_zips['end']}")
        
    #     # Set red background to indicate querying is possible
    #     self._set_data_browse_bg("red")
        
    #     # Enable query functionality 
    #     self.show_query_btn()
    #     update_data_query_btn_state(self, "normal")
    #     self._set_controls_state("normal")
        
    #     # Set default date range if not already set (especially important when zip extraction fails)
    #     set_default_date_range_if_empty(self)
        
    #     # Setup controls for zip file extraction
    #     self._setup_polarization_controls(dir_pol_summary=None, zip_pol_summary=zip_pol_summary)
    #     self._setup_subswath_controls(safe_dirs=None, zip_files=zip_files)
    #     self._show_output_folder_and_project_controls()
        
    #     # Show extraction button
    #     self._show_zip_extraction_controls()
        
    #     # Hide download button initially (will appear after query)
    #     self.hide_download_btn()

    def _get_extent_from_zip_files(self, zip_files):
        """Extract geographical extent from zip files metadata."""
        try:
            extents = []
            for zip_file in zip_files:
                # Parse the filename to extract extent information
                # S1A_IW_SLC__1SDV_20210101T050000_20210101T050030_036123_043C8A_1234.zip
                basename = os.path.basename(zip_file)
                if basename.startswith('S1') and '_IW_SLC_' in basename:
                    # For now, return a general extent - this could be enhanced
                    # to parse actual metadata from the zip files
                    pass
            
            # If we can't derive extent from filenames, try to read manifest files from zip
            return extract_extent_from_zip_manifests(zip_files)
            
        except Exception as e:
            print(f"Warning: Could not derive extent from zip files: {e}")
            return None

    def _get_dates_from_zip_files(self, zip_files):
        """Extract date range from zip files based on their filenames."""
        try:
            import re
            from datetime import datetime
            
            dates = []
            for zip_file in zip_files:
                basename = os.path.basename(zip_file)
                # Extract date from Sentinel-1 filename pattern
                # S1A_IW_SLC__1SDV_20210101T050000_20210101T050030_036123_043C8A_1234.zip
                if basename.startswith('S1') and '_IW_SLC_' in basename:
                    match = re.search(r'_(\d{8})T\d{6}_(\d{8})T\d{6}_', basename)
                    if match:
                        start_date = match.group(1)  # YYYYMMDD
                        end_date = match.group(2)    # YYYYMMDD
                        try:
                            # Convert to datetime for proper comparison
                            start_dt = datetime.strptime(start_date, '%Y%m%d')
                            end_dt = datetime.strptime(end_date, '%Y%m%d')
                            dates.extend([start_dt, end_dt])
                        except ValueError:
                            continue
            
            if dates:
                # Get the overall date range
                min_date = min(dates)
                max_date = max(dates)
                return {
                    'start': min_date.strftime('%Y-%m-%d'),
                    'end': max_date.strftime('%Y-%m-%d')
                }
        except Exception as e:
            print(f"Warning: Could not extract dates from zip files: {e}")
        
        return None

    def _show_zip_extraction_controls(self):
        """Show controls for zip file extraction."""
        # This will create an extraction button in a non-conflicting position
        # Use column 5 to avoid conflicts with Query (col 3) and Download (col 4) buttons
        
        row = self._get_row("data_folder")
        if hasattr(self, "_extract_btn") and self._extract_btn:
            self._extract_btn.destroy()
            
        self._extract_btn = tk.Button(
            self.root, 
            text="Extract Zip Files", 
            command=self._start_zip_extraction,
            bg="orange", 
            activebackground="orange"
        )
        self._extract_btn.grid(row=row, column=5, padx=5, pady=5, sticky="w")
        add_tooltip(self._extract_btn, 
                   "Extract selected zip files with chosen subswaths and polarization\n"
                   "Smart extraction: skips files that already exist and are identical\n"
                   "Progress will be displayed on the button\n"
                   "Failed extractions will be reported with cleanup options")

    def _start_zip_extraction(self):
        """Start the zip extraction process."""
        # Get current folder and settings
        folder = self.data_folder_entry.get().strip()
        if not folder:
            messagebox.showerror("Error", "Please specify a data folder first")
            return
            
        # Get selected subswaths and polarization
        selected_subswaths = self.get_selected_subswaths()
        if not selected_subswaths:
            messagebox.showerror("Error", "Please select at least one subswath")
            return
            
        selected_pol = getattr(self, 'pol_var', None)
        if not selected_pol or not selected_pol.get():
            messagebox.showerror("Error", "Please select a polarization")
            return
            
        # Show confirmation dialog
        result = messagebox.askyesno(
            "Confirm Extraction",
            f"Extract zip files to: {folder}\n"
            f"Subswaths: {', '.join(map(str, selected_subswaths))}\n"
            f"Polarization: {selected_pol.get()}\n\n"
            f"This will extract the selected data. Continue?"
        )
        
        if result:
            # Disable controls during extraction
            self._extract_btn.config(state="disabled", text="Extracting 1/...")
            self.data_folder_entry.config(state="disabled")
            
            # Start extraction in thread
            threading.Thread(
                target=DataHandlers.perform_zip_extraction_optimized,
                args=(self, folder, selected_subswaths, selected_pol.get().lower()),
                daemon=True
            ).start()

    def _display_extent_labels(self, extent):
        """Use external function for displaying extent labels."""
        if not extent or not hasattr(self, 'extent_frame'):
            return
        
        # Clear existing labels first
        self._clear_extent_and_date_labels()
        
        # Create a labels dictionary for the external function
        labels_dict = {}
        
        # Use the external function
        display_extent_labels(extent, self.extent_frame, labels_dict)
        
        # Store the labels for cleanup later
        self.n_label = labels_dict.get('n_label')
        self.s_label = labels_dict.get('s_label') 
        self.e_label = labels_dict.get('e_label')
        self.w_label = labels_dict.get('w_label')
        
        # Set extent entry values using external function
        set_extent_entry_values(extent, self.n_entry, self.s_entry, self.e_entry, self.w_entry)

    def _draw_extent_rectangle(self, extent):
        """Draw a red rectangle on the map for the given extent."""
        if not extent:
            return
        
        draw_rectangle_on_map(
            self.map_widget, self.rect_shape, self.data_browse,
            extent['s'], extent['w'], 
            extent['n'], extent['e']
        )

    def _load_and_update(self):
        # Reset flag when user manually browses to allow config loading
        self._zip_derived_values = False
        
        # Hide pause button when user browses to new folder (no download in progress)
        self._hide_pause_button()
        
        if self.rect_shape[0]:
            self.rect_shape[0].delete()
            self.rect_shape[0] = None
        for poly in getattr(self.on_data_query, "polygons", []):
            poly.delete()
        self.on_data_query.polygons = []
        if self.custom_shape:
            self.custom_shape.delete()
            self.custom_shape = None
        browse_folder(self.data_folder_entry, "in_data_dir")
        self._on_data_folder_change()
        validate_dates_strict(self.start_var, self.end_var, self.start_date, self.root)  # Ensure dates are validated and UI updated
        enforce_date_limits(self.start_var, self.end_var, self.date_limits)  # Ensure dates are clamped to limits

def main():
    """Main entry point for InSARLite application."""
    root = tk.Tk()
    app = InSARLiteApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
