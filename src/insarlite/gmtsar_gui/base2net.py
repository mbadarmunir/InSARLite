import os
import threading
import tkinter as tk
import numpy as np
from tkinter import messagebox
import shutil
# from datetime import datetime, timedelta
import json

from ..utils.utils import (
    add_tooltip,
    process_logger,
)
from ..utils.matplotlib_baseline_plotter import create_interactive_baseline_plot
from ..gmtsar_gui.baselines_gen import preprocess
from ..gmtsar_gui.masterselection import select_mst
import shutil

class BaselineGUI:
    def __init__(self, root, dem, paths=None, on_edges_exported=None, log_file=None):
        self.root = root
        self.dem_path = dem
        self.paths = paths
        self.on_edges_exported = on_edges_exported
        self.log_file = log_file
        self.root.title("Plot Baselines and Generate IFG Pairs")

        # Plot-related attributes
        self.plot_frame = None
        self.plotter = None  # New matplotlib plotter instance
        self.points = []
        self.dates = []
        self.perp_baselines = []
        self.edges = []
        self.original_edges = []
        self.edit_graph_active = False

        # Master selection UI
        self.select_mst_btn = None
        self.master_listbox = None
        self.selected_master_idx = tk.IntVar(value=0)
        self._listbox_dates = []
        self._highlighted_point = None

        # Constraints UI
        self.perp_var = tk.StringVar()
        self.temp_var = tk.StringVar()
        self.edit_mode_var = tk.BooleanVar(value=False)
        self.edit_graph_check = None

        # Config file path - use project-specific config
        self.conf_path = self._get_project_config_path()
        self.mst = None

        self._init_ui()
        self._check_previous_config()

    # --- Config Handling ---
    def _get_project_config_path(self):
        """Get project-specific config path from paths dictionary."""
        if self.paths:
            for key in ['pF1', 'pF2', 'pF3']:
                path = self.paths.get(key)
                if path:
                    # Path is like /project/asc/F1, go up two levels to /project
                    flight_dir = os.path.dirname(path)  # /project/asc
                    project_root = os.path.dirname(flight_dir)  # /project
                    return os.path.join(project_root, '.config.json')
        # Fallback to home directory if paths not available
        return os.path.join(os.path.expanduser('~'), ".config.json")
    
    def _load_config(self):
        conf = {}
        if os.path.exists(self.conf_path):
            try:
                with open(self.conf_path, "r") as f:
                    conf = json.load(f)
            except Exception:
                conf = {}
        return conf

    def _save_config(self):
        """Save alignment configuration and baseline constraints only if changed."""
        conf = self._load_config()
        
        # New values to save (including baseline constraints)
        new_values = {
            "mst": self.mst,
            "align_mode": self.align_mode_var.get(),
            "esd_mode": self.esd_mode_var.get(),
            "perpendicular_baseline_constraint": self.perp_var.get() if hasattr(self, 'perp_var') else None,
            "temporal_baseline_constraint": self.temp_var.get() if hasattr(self, 'temp_var') else None
        }
        
        # Check if any value has changed
        changed = False
        for key, new_val in new_values.items():
            if new_val is not None and conf.get(key) != new_val:
                changed = True
                break
        
        # Only write if something changed
        if changed:
            conf.update({k: v for k, v in new_values.items() if v is not None})
            try:
                with open(self.conf_path, "w") as f:
                    json.dump(conf, f, indent=2)
                print(f"Updated config: {', '.join(f'{k}={v}' for k, v in new_values.items() if v is not None)}")
            except Exception as e:
                print(f"Could not save config: {e}")
        else:
            print("Config unchanged, skipping save")

    def _save_master_selection_cache(self, marray):
        """Save master selection cache only if changed."""
        conf = self._load_config()
        
        # Convert array to JSON-serializable format
        new_cache_data = None
        try:
            if isinstance(marray, np.ndarray):
                new_cache_data = marray.tolist()
            elif hasattr(marray, '__iter__'):
                # Convert S1Product objects or other complex objects to simple lists
                cache_data = []
                for item in marray:
                    if hasattr(item, 'properties'):
                        # S1Product object - extract key properties (ASF method - 4 elements)
                        cache_data.append([
                            float(item.properties.get('temporalBaseline', 0)),
                            float(item.properties.get('perpendicularBaseline', 0)),
                            str(item.properties.get('fileID', '')),
                            0.0,  # No avg_baseline for ASF method
                            int(item.properties.get('frameNumber', 0))  # rank
                        ])
                    elif isinstance(item, (list, tuple, np.ndarray)) and len(item) >= 5:
                        # Local method format: [temporal_bl, perpendicular_bl, image_id, avg_baseline, rank]
                        cache_data.append([
                            float(item[0]),
                            float(item[1]),
                            str(item[2]),
                            float(item[3]),
                            int(item[4])
                        ])
                    elif isinstance(item, (list, tuple, np.ndarray)) and len(item) >= 4:
                        # Legacy format: [temporal_bl, perpendicular_bl, fileID, rank] - convert to 5 elements
                        cache_data.append([
                            float(item[0]),
                            float(item[1]),
                            str(item[2]),
                            0.0,  # No avg_baseline
                            int(item[3])
                        ])
                    else:
                        # Convert other iterables to list
                        cache_data.append(list(item))
                new_cache_data = cache_data
            else:
                new_cache_data = marray
        except Exception as e:
            print(f"Could not convert master selection data for caching: {e}")
            new_cache_data = []
        
        # Check if cache data has changed
        existing_cache = conf.get("master_selection_cache", [])
        if existing_cache != new_cache_data:
            conf["master_selection_cache"] = new_cache_data
            try:
                with open(self.conf_path, "w") as f:
                    json.dump(conf, f, indent=2)
                print(f"Updated master selection cache ({len(new_cache_data)} entries)")
            except Exception as e:
                print(f"Could not save master selection cache: {e}")
        else:
            print("Master selection cache unchanged, skipping save")
    
    def _save_removed_images(self, removed_dates):
        """Save list of removed unconnected images to config and ask user about future handling."""
        if not removed_dates:
            return
        
        conf = self._load_config()
        # Convert set to sorted list for consistent storage
        removed_list = sorted(list(removed_dates))
        
        # Check if it changed
        prev_removed = conf.get("removed_unconnected_images", [])
        if removed_list == prev_removed:
            return
        
        # Ask user how to handle removed images in future runs
        from tkinter import messagebox
        msg = (
            f"🗑️  Removed {len(removed_list)} unconnected image(s) from network:\n"
            f"{', '.join([f'{d[:4]}-{d[4:6]}-{d[6:8]}' for d in removed_list[:5]])}"
            f"{'...' if len(removed_list) > 5 else ''}\n\n"
            f"How should these be handled in future runs?\n\n"
            f"• Yes: Ignore these images (don't count as 'missing' in baseline checks)\n"
            f"  Recommended if you intentionally removed low-quality images\n\n"
            f"• No: Treat as mismatch (trigger regeneration if files recreated)\n"
            f"  Use this if you might re-download/add these images later"
        )
        
        ignore_removed = messagebox.askyesno(
            "Unconnected Images Removed",
            msg,
            icon="question"
        )
        
        conf["removed_unconnected_images"] = removed_list
        conf["ignore_removed_in_validation"] = ignore_removed
        
        try:
            with open(self.conf_path, "w") as f:
                json.dump(conf, f, indent=2)
            action = "will be ignored" if ignore_removed else "will trigger mismatch"
            print(f"✅ Saved {len(removed_list)} removed image(s) to config ({action} in future validations)")
        except Exception as e:
            print(f"Warning: Could not save removed images to config: {e}")

    def _load_master_selection_cache(self):
        conf = self._load_config()
        return conf.get("master_selection_cache", [])

    def _get_current_ui_params(self):
        """
        Collect current UI parameter values for logging and config saving.
        
        Returns:
            dict: Dictionary of current UI parameter values
        """
        ui_params = {
            'alignment_mode': self.align_mode_var.get(),
            'esd_mode': self.esd_mode_var.get(),
        }
        
        # Add baseline constraints if available from plotter
        if hasattr(self, 'plotter') and self.plotter:
            try:
                constraints = self.plotter.get_constraints()
                ui_params.update({
                    'perpendicular_baseline_constraint': constraints.get('perp_constraint'),
                    'temporal_baseline_constraint': constraints.get('temp_constraint'),
                })
            except:
                pass  # Plotter might not have constraints method yet
        
        # Add manual constraints from UI variables
        try:
            if self.perp_var.get():
                ui_params['perpendicular_baseline_constraint'] = self.perp_var.get()
            if self.temp_var.get():
                ui_params['temporal_baseline_constraint'] = self.temp_var.get()
        except:
            pass
            
        # Add master selection if available
        if hasattr(self, 'mst') and self.mst:
            ui_params['master_image'] = self.mst
            
        # Add network information if available
        if hasattr(self, 'edges') and self.edges:
            ui_params['network_edges_count'] = len(self.edges)
            
        return ui_params

    def _save_step_config(self, step_name, additional_params=None):
        """
        Save current step configuration to project config file.
        
        Args:
            step_name (str): Name of the processing step
            additional_params (dict): Additional parameters to save
        """
        try:
            from ..utils.utils import save_config_to_json
            
            ui_params = self._get_current_ui_params()
            
            if additional_params:
                ui_params.update(additional_params)
            
            # Save to project config file
            if hasattr(self, 'paths') and self.paths:
                # Try to find project config from paths
                for key in ['pF1', 'pF2', 'pF3']:
                    path = self.paths.get(key)
                    if path:
                        # Navigate up from F1/F2/F3 to project root (two levels)
                        # Path is like /project/asc/F1, go up two levels to /project
                        flight_dir = os.path.dirname(path)  # /project/asc
                        project_root = os.path.dirname(flight_dir)  # /project
                        config_path = os.path.join(project_root, '.config.json')
                        save_config_to_json(config_path, ui_params, step_name)
                        break
                        
        except Exception as e:
            print(f"Warning: Could not save step configuration: {e}")

    def _check_previous_config(self):
        conf = self._load_config()
        prev_mst = conf.get("mst")
        prev_align = conf.get("align_mode")
        prev_esd = conf.get("esd_mode")
        
        # Store for later use
        self._prev_mst = prev_mst
        self._prev_align = prev_align
        self._prev_esd = prev_esd
        
        # Check if SLC files exist and if alignment parameters have changed
        slc_exists, alignment_changed = self._check_alignment_status(prev_align, prev_esd)
        
        # Set self.pF1raw, self.pF2raw, self.pF3raw if present in self.paths
        valid_pfraw = True
        for key in ["pF1raw", "pF2raw", "pF3raw"]:
            pfraw_path = getattr(self, key, None)
            if pfraw_path and os.path.exists(pfraw_path):
                prm_files = [f for f in os.listdir(pfraw_path) if f.endswith(".PRM")]
                led_files = [f for f in os.listdir(pfraw_path) if f.endswith(".LED")]
                tif_files = [f for f in os.listdir(pfraw_path) if f.endswith(".tiff")]
                if not prm_files:
                    print(f"No .PRM files found in {pfraw_path}")
                if not led_files:
                    print(f"No .LED files found in {pfraw_path}")
                if not tif_files:
                    print(f"No .tiff files found in {pfraw_path}")
                if not (
                    (prm_files and led_files and tif_files and len(prm_files) == len(led_files) == len(tif_files))
                    or
                    (len(prm_files) == len(led_files) == 2 * len(tif_files) and len(tif_files) > 0)
                ):
                    print(f"File count mismatch or missing files in {pfraw_path}: "
                    f"{len(prm_files)} .PRM, {len(led_files)} .LED, {len(tif_files)} .tiff")
                    valid_pfraw = False
                    break
                else:
                    print(f"All required files found in {pfraw_path}: "
                    f"{len(prm_files)} .PRM, {len(led_files)} .LED, {len(tif_files)} .tiff")

        # Additional check for master selection cache validity
        print("additional check for master selection cache validity")
        ddata = self.paths.get("pdata")
        
        # Get SAFE directories
        safe_dirs = [safe_dir.split('.SAFE')[0] for root, dirs, files in os.walk(ddata) for safe_dir in dirs if safe_dir.endswith(".SAFE")]
        marray = self._load_master_selection_cache()
        
        try:
            # Handle both old and new cache formats - extract dates for comparison
            cache_dates = []
            for item in marray:
                if isinstance(item, (list, tuple)) and len(item) >= 3:
                    # Extract the fileID (GMTSAR format: S1_YYYYMMDD_ALL_F*)
                    file_id = str(item[2])
                    # Extract date from GMTSAR format
                    if '_' in file_id:
                        parts = file_id.split('_')
                        if len(parts) >= 2 and len(parts[1]) == 8:
                            cache_dates.append(parts[1])  # YYYYMMDD
                elif hasattr(item, 'properties'):
                    # S1Product object
                    file_id = str(item.properties.get('fileID', ''))
                    if '_' in file_id:
                        parts = file_id.split('_')
                        if len(parts) >= 2 and len(parts[1]) == 8:
                            cache_dates.append(parts[1])  # YYYYMMDD
            
            # Extract dates from SAFE directories (format: S1A_IW_SLC__1SDV_YYYYMMDDTHHMMSS_...)
            safe_dates = []
            for safe_dir in safe_dirs:
                if len(safe_dir) >= 25:
                    date_str = safe_dir[17:25]  # YYYYMMDD
                    safe_dates.append(date_str)
                    
            cache_dates_set = set(cache_dates)
            safe_dates_set = set(safe_dates)
        except Exception as e:
            print(f"Error processing master selection cache: {e}")
            cache_dates_set = set()
            safe_dates_set = set(safe_dates) if safe_dirs else set()
            
        # Check if master selection cache matches current SAFE directories
        # Note: Image list may differ slightly (some added/removed) - this is OK
        # What matters is whether master-related config (mst, align_mode, esd_mode) is valid
        if (
            not marray
            or len(cache_dates) != len(safe_dates)
            or cache_dates_set != safe_dates_set
        ):
            print("Master selection cache is invalid or does not match SAFE directories.")
            print("ℹ️  This is expected if images were added/removed - will regenerate baselines.")
            valid_pfraw = False

        # Store valid_pfraw for later use
        self._valid_pfraw = valid_pfraw
        
        # Additional check: prev_mst must match one of the SAFE directory dates
        if prev_mst:
            # Extract dates from SAFE directories (format: YYYYMMDD)
            safe_dates = [safe_dir[17:25] for safe_dir in safe_dirs if len(safe_dir) >= 25]
            # Normalize prev_mst to YYYYMMDD format (remove dashes)
            prev_mst_normalized = prev_mst.replace('-', '')
            if prev_mst_normalized not in safe_dates:
                print(f"Previous master {prev_mst} not found in SAFE directory dates.")
                valid_pfraw = False

        # Handle different scenarios based on SLC existence and parameter changes
        if prev_mst and prev_align and prev_esd and valid_pfraw:
            if slc_exists and alignment_changed:
                # SLC files exist but alignment parameters changed - need confirmation
                print("SLC files exist but alignment parameters have changed. Prompting for confirmation.")
                self._prompt_alignment_method_change(prev_mst, prev_align, prev_esd)
                return
            else:
                print("Previous config found and all pfraw checks passed. Prompting user to use previous config.")
                self._prompt_use_previous_config(prev_mst, prev_align, prev_esd)
                return
        elif prev_mst and prev_align and prev_esd and not valid_pfraw:
            # Master config exists but image list has changed
            print("Master config found but image list differs from cache.")
            self._prompt_image_list_change(prev_mst, prev_align, prev_esd, cache_dates_set, safe_dates_set)
            return
        else:
            # Master config incomplete or missing
            if not prev_mst:
                print("No previous master (mst) found in config.")
            if not prev_align:
                print("No previous align_mode found in config.")
            if not prev_esd:
                print("No previous esd_mode found in config.")
            
            # Check if baseline files exist
            baseline_files_exist = self._check_baseline_files_exist()
            if baseline_files_exist:
                print("Master configuration missing but baseline files exist.")
                self._prompt_master_config_invalid(baseline_files_exist)
                return
      
        # If not using previous config, proceed as normal

    def _check_baseline_files_exist(self):
        """Check if baseline LED/PRM files already exist."""
        for key in ["pF1", "pF2", "pF3"]:
            subswath_path = self.paths.get(key)
            if subswath_path and os.path.exists(subswath_path):
                raw_path = os.path.join(subswath_path, "raw")
                if os.path.exists(raw_path):
                    prm_files = [f for f in os.listdir(raw_path) if f.endswith(".PRM")]
                    led_files = [f for f in os.listdir(raw_path) if f.endswith(".LED")]
                    if len(prm_files) > 0 and len(led_files) > 0:
                        return True
        return False
    
    def _check_alignment_status(self, prev_align, prev_esd):
        """Check if SLC files exist and if alignment parameters have changed."""
        slc_exists = False
        alignment_changed = False
        
        # Check if SLC files exist in any subswath
        for key in ["pF1", "pF2", "pF3"]:
            subswath_path = self.paths.get(key)
            if subswath_path and os.path.exists(subswath_path):
                raw_path = os.path.join(subswath_path, "raw")
                if os.path.exists(raw_path):
                    slc_files = [f for f in os.listdir(raw_path) if f.endswith('.SLC')]
                    if len(slc_files) > 0:
                        slc_exists = True
                        break
        
        # Check if alignment parameters have changed
        current_align = self.align_mode_var.get()
        current_esd = self.esd_mode_var.get()
        
        if prev_align and prev_esd:
            if current_align != prev_align or current_esd != prev_esd:
                alignment_changed = True
        
        return slc_exists, alignment_changed

    def _backup_existing_slc_files(self):
        """Backup existing SLC files to 'previous_aligned' folder instead of deleting them."""
        backup_created = False
        
        for key in ["pF1", "pF2", "pF3"]:
            subswath_path = self.paths.get(key)
            if subswath_path and os.path.exists(subswath_path):
                raw_path = os.path.join(subswath_path, "raw")
                if os.path.exists(raw_path):
                    slc_files = [f for f in os.listdir(raw_path) if f.endswith('.SLC')]
                    
                    if len(slc_files) > 0:
                        # Create backup directory
                        backup_dir = os.path.join(raw_path, "previous_aligned")
                        if not os.path.exists(backup_dir):
                            os.makedirs(backup_dir)
                        
                        # Move SLC files to backup
                        for slc_file in slc_files:
                            src = os.path.join(raw_path, slc_file)
                            dst = os.path.join(backup_dir, slc_file)
                            try:
                                shutil.move(src, dst)
                                print(f"Backed up {slc_file} to previous_aligned folder")
                            except Exception as e:
                                print(f"Warning: Could not backup {slc_file}: {e}")
                        
                        backup_created = True
        
        if backup_created:
            print("✅ Existing aligned SLC files have been backed up to 'previous_aligned' folders")
        
        return backup_created

    def _prompt_master_config_invalid(self, baseline_files_exist):
        """Prompt user when master configuration is missing/invalid but baseline files exist."""
        from tkinter import messagebox
        
        msg = (
            "Master configuration (mst, align_mode, esd_mode) is incomplete or missing.\n\n"
            "However, baseline LED/PRM files were found in the project.\n\n"
            "Do you want to:\n"
            "• Yes: Regenerate baseline files (recommended if project parameters changed)\n"
            "• No: Use existing baseline files and proceed to plotting"
        )
        
        result = messagebox.askyesno(
            "Master Configuration Invalid",
            msg,
            icon="warning"
        )
        
        if result:
            # User chose to regenerate - proceed with plotting which will regenerate
            print("User chose to regenerate baseline files")
            self._plot_baselines()
        else:
            # User chose to use existing files - proceed to plotting
            print("User chose to use existing baseline files")
            self._on_preprocess_done()
    
    def _prompt_image_list_change(self, prev_mst, prev_align, prev_esd, cache_dates_set, safe_dates_set):
        """Prompt user when image list has changed from cached version."""
        from tkinter import messagebox
        
        added = safe_dates_set - cache_dates_set
        removed = cache_dates_set - safe_dates_set
        
        # Convert dates to readable format (YYYY-MM-DD)
        def format_date(date_str):
            """Convert YYYYMMDD to YYYY-MM-DD."""
            if len(date_str) == 8:
                return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            return date_str
        
        change_details = ""
        if added:
            added_formatted = [format_date(d) for d in sorted(added)[:3]]
            change_details += f"\nAdded images ({len(added)}): {', '.join(added_formatted)}{'...' if len(added) > 3 else ''}"
        if removed:
            removed_formatted = [format_date(d) for d in sorted(removed)[:3]]
            change_details += f"\nRemoved images ({len(removed)}): {', '.join(removed_formatted)}{'...' if len(removed) > 3 else ''}"
        
        msg = (
            f"Image list has changed since last baseline generation:\n"
            f"Previous: {len(cache_dates_set)} images\n"
            f"Current: {len(safe_dates_set)} images"
            f"{change_details}\n\n"
            "This is acceptable if you intentionally added/removed data.\n\n"
            "Do you want to:\n"
            "• Yes: Regenerate baseline files with current image list\n"
            "• No: Use existing baseline files (may cause issues if images changed significantly)"
        )
        
        result = messagebox.askyesno(
            "Image List Changed",
            msg,
            icon="question"
        )
        
        if result:
            # User confirmed regeneration
            print(f"User confirmed image list change - regenerating baselines")
            self._plot_baselines()
        else:
            # User chose to use existing files
            print("User chose to use existing baseline files despite image list change")
            self._on_preprocess_done()
    
    def _prompt_alignment_method_change(self, prev_mst, prev_align, prev_esd):
        """Prompt user when alignment method/mode has changed and SLC files exist."""
        current_align = self.align_mode_var.get()
        current_esd = self.esd_mode_var.get()
        
        def use_existing():
            # Revert to previous settings and use existing alignment
            self.align_mode_var.set(prev_align)
            self.esd_mode_var.set(prev_esd)
            self._update_ui_for_alignment_mode()
            
            if self.on_edges_exported:
                self.on_edges_exported(prev_mst, prev_align, prev_esd)
            self.root.destroy()

        def backup_and_realign():
            # Backup existing SLC files and proceed with new alignment
            self._backup_existing_slc_files()
            prompt.destroy()
            # Continue with normal flow for new alignment - the alignment function 
            # will automatically detect the method change and handle SLC protection

        def cancel_operation():
            # Close the baseline window and return to main interface
            self.root.destroy()

        prompt = tk.Toplevel(self.root)
        prompt.title("Alignment Method Changed")
        prompt.transient(self.root)
        prompt.lift()
        prompt.attributes('-topmost', True)
        
        # Create a more detailed message
        changes = []
        if current_align != prev_align:
            changes.append(f"Alignment mode: {prev_align} → {current_align}")
        if current_esd != prev_esd:
            esd_modes = {"0": "average", "1": "median", "2": "interpolation"}
            prev_esd_name = esd_modes.get(prev_esd, prev_esd)
            current_esd_name = esd_modes.get(current_esd, current_esd)
            changes.append(f"ESD mode: {prev_esd_name} → {current_esd_name}")
        
        msg = (
            f"⚠️  Alignment Parameters Changed\n\n"
            f"Existing aligned SLC files were found, but you have selected different alignment parameters:\n\n"
            + "\n".join(f"• {change}" for change in changes) + "\n\n"
            f"Re-alignment is required when using different parameters.\n"
            f"Existing aligned images will NEVER be deleted.\n\n"
            f"Options:\n"
            f"• Use Existing: Keep current aligned images with previous settings\n"
            f"• Backup & Re-align: Move existing images to 'previous_aligned' folder and re-align with new settings\n"
            f"• Cancel: Return to main interface"
        )
        
        tk.Label(prompt, text=msg, justify="left", wraplength=500).pack(padx=20, pady=10)
        
        btn_frame = tk.Frame(prompt)
        btn_frame.pack(pady=(0, 10))
        
        tk.Button(btn_frame, text="Use Existing", width=15, bg="lightgreen", command=use_existing).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Backup & Re-align", width=15, bg="lightblue", command=backup_and_realign).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", width=15, bg="lightcoral", command=cancel_operation).pack(side=tk.LEFT, padx=5)

        def center_window(win, parent):
            win.update_idletasks()
            x = parent.winfo_rootx() + (parent.winfo_width() - win.winfo_width()) // 2
            y = parent.winfo_rooty() + (parent.winfo_height() - win.winfo_height()) // 2
            win.geometry(f"+{x}+{y}")

        prompt.after_idle(lambda: center_window(prompt, self.root))
        prompt.grab_set()

    def _update_ui_for_alignment_mode(self):
        """Update UI elements when alignment mode is changed programmatically."""
        if self.align_mode_var.get() == "esd":
            self.show_esd_modes()
        else:
            self.hide_esd_modes()

    def _prompt_use_previous_config(self, prev_mst, prev_align, prev_esd):
        def use_previous():
            if self.on_edges_exported:
                self.on_edges_exported(prev_mst, prev_align, prev_esd)
            self.root.destroy()

        def redo():
            prompt.destroy()

        prompt = tk.Toplevel(self.root)
        prompt.title("Previous Configuration Found")
        prompt.transient(self.root)
        prompt.lift()
        prompt.attributes('-topmost', True)
        msg = (
            f"Use previous configuration?\n\n"
            f"Master: {prev_mst}\n"
            f"Align mode: {prev_align}\n"
            f"ESD mode: {prev_esd}\n"
        )
        tk.Label(prompt, text=msg, justify="left").pack(padx=20, pady=10)
        btn_frame = tk.Frame(prompt)
        btn_frame.pack(pady=(0, 10))
        tk.Button(btn_frame, text="Use Previous", width=12, command=use_previous).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Redo", width=12, command=redo).pack(side=tk.LEFT, padx=5)

        def center_window(win, parent):
            win.update_idletasks()
            x = parent.winfo_rootx() + (parent.winfo_width() - win.winfo_width()) // 2
            y = parent.winfo_rooty() + (parent.winfo_height() - win.winfo_height()) // 2
            win.geometry(f"+{x}+{y}")

        prompt.after_idle(lambda: center_window(prompt, self.root))
        prompt.grab_set()

    # --- UI Initialization ---
    def _init_ui(self):
        self.alignment_frame = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        self.alignment_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nw")

        title_label = tk.Label(self.alignment_frame, text="Baselines calc. & Align. Param.", font=("Arial", 12, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(5, 15))
        add_tooltip(title_label, "Configure baseline calculation and image alignment parameters")

        self.align_mode_var = tk.StringVar(value="esd")
        self.esd_mode_frame = None

        esd_radio = tk.Radiobutton(
            self.alignment_frame, text="Align with ESD", variable=self.align_mode_var, value="esd",
            command=lambda: self.show_esd_modes()
        )
        esd_radio.grid(row=1, column=0, sticky="w", padx=5)
        add_tooltip(esd_radio, "Enhanced Spectral Diversity (ESD) alignment\nMore accurate but slower processing\nRecommended for most applications")
        
        no_esd_radio = tk.Radiobutton(
            self.alignment_frame, text="Align w/o ESD", variable=self.align_mode_var, value="no_esd",
            command=lambda: self.hide_esd_modes()
        )
        no_esd_radio.grid(row=1, column=1, sticky="w", padx=5)
        add_tooltip(no_esd_radio, "Standard alignment without ESD\nFaster processing but less accurate\nUse only for quick testing")

        self.esd_mode_var = tk.StringVar(value="2")
        self._add_plot_button(row=1)

        def create_esd_mode_frame():
            frame = tk.Frame(self.alignment_frame)
            esd_label = tk.Label(frame, text="ESD Mode:")
            esd_label.grid(row=0, column=0, sticky="w")
            add_tooltip(esd_label, "ESD calculation method for improved alignment accuracy")
            
            avg_radio = tk.Radiobutton(frame, text="average", variable=self.esd_mode_var, value="0")
            avg_radio.grid(row=0, column=1, sticky="w")
            add_tooltip(avg_radio, "Average ESD method\nUses mean spectral diversity estimates")
            
            median_radio = tk.Radiobutton(frame, text="median", variable=self.esd_mode_var, value="1")
            median_radio.grid(row=0, column=2, sticky="w")
            add_tooltip(median_radio, "Median ESD method\nRobust to outliers in spectral diversity")
            
            interp_radio = tk.Radiobutton(frame, text="interpolation", variable=self.esd_mode_var, value="2")
            interp_radio.grid(row=0, column=3, sticky="w")
            add_tooltip(interp_radio, "Interpolation ESD method (recommended)\nMost accurate spectral diversity estimation")
            
            return frame

        def show_esd_modes():
            if self.esd_mode_frame is None:
                self.esd_mode_frame = create_esd_mode_frame()
                self.esd_mode_frame.grid(row=2, column=0, columnspan=2, pady=(5, 5), sticky="w")
        def hide_esd_modes():
            if self.esd_mode_frame is not None:
                self.esd_mode_frame.destroy()
                self.esd_mode_frame = None

        self.show_esd_modes = show_esd_modes
        self.hide_esd_modes = hide_esd_modes
        self.show_esd_modes()

    def _add_plot_button(self, row=0):
        self.plot_button = tk.Button(self.root, text="Plot Baselines", command=self.on_plot_baselines)
        self.plot_button.grid(row=row, column=0, pady=20, sticky="w")
        add_tooltip(self.plot_button, "Generate baseline plot and calculate temporal/perpendicular baselines\nShows time vs perpendicular baseline chart")

    # --- Baseline Plotting ---
    def on_plot_baselines(self):
        if not self.paths:
            print("No paths provided.")
            return
            
        # Collect UI parameters for logging
        ui_params = self._get_current_ui_params()
            
        # Log the start of actual baseline processing with UI parameters
        if self.log_file:
            process_logger(process_num=1, log_file=self.log_file, 
                         message="Starting baseline analysis and network design...", 
                         mode="start", ui_params=ui_params)
            
        # Save configuration for this step
        self._save_step_config("baseline_analysis")
            
        if self.plot_frame and self.plot_frame.winfo_exists():
            self.plot_frame.destroy()
        self._destroy_master_frame()
        if hasattr(self.root, "baselines_frame") and self.root.baselines_frame.winfo_exists():
            self.root.baselines_frame.destroy()
        if hasattr(self.root, "export_frame") and self.root.export_frame is not None and self.root.export_frame.winfo_exists():
            self.root.export_frame.destroy()
        run_threaded(
            self.root,
            target=lambda: preprocess(self.paths, self.dem_path, self.align_mode_var.get(), self.esd_mode_var.get(), force_regenerate=False),
            on_complete=self._on_preprocess_done
        )

    def _on_preprocess_done(self):
        for key in ['pF1', 'pF2', 'pF3']:
            pfx = self.paths.get(key)
            if not pfx:
                continue
            baseline_table_path = os.path.join(pfx, "baseline_table.dat")
            if os.path.exists(baseline_table_path):
                self._plot_baseline_table(baseline_table_path)
                self._show_master_ui()
                return
        messagebox.showerror("Error", "No valid baseline_table.dat found.")

    def _plot_baseline_table(self, baseline_table_path):
        """Create interactive matplotlib baseline plot."""
        if self.plot_frame:
            self.plot_frame.destroy()
            
        # Create new plot frame
        self.plot_frame = tk.Frame(self.root)
        self.plot_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        
        # Configure grid weights for resizing
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        
        try:
            # Force reload of matplotlib baseline plotter to ensure latest version
            import importlib
            from ..utils import matplotlib_baseline_plotter
            importlib.reload(matplotlib_baseline_plotter)
            
            # Create the interactive matplotlib plotter
            self.plotter = matplotlib_baseline_plotter.create_interactive_baseline_plot(self.plot_frame, baseline_table_path)
            
            # Set up callbacks
            self.plotter.on_edge_changed = self._on_edges_changed
            
            # Extract data for compatibility with existing code
            self.points = self.plotter.points
            self.dates = self.plotter.dates  
            self.perp_baselines = self.plotter.perp_baselines
            
            print(f"Loaded {len(self.points)} baseline points successfully")
            
        except Exception as e:
            print(f"Error creating baseline plot: {e}")
            # Fallback to simple message
            tk.Label(self.plot_frame, text=f"Error loading baseline plot: {e}").pack()
            
    def _on_edges_changed(self, edges):
        """Callback when edges are modified in the plotter."""
        # Update internal edges list for compatibility
        self.edges = edges
        print(f"Network updated: {len(edges)} connections")

    # --- Master Selection UI ---
    def _show_master_ui(self, row=0, column=1):
        self._destroy_master_frame()
        frame = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        frame.grid(row=row, column=column, padx=10, pady=10, sticky="nw")
        self.root.master_frame = frame

        controls_frame = tk.Frame(frame)
        controls_frame.pack(side=tk.LEFT, fill=tk.X)
        
        master_label = tk.Label(controls_frame, text="Master Selection", font=("Arial", 12, "bold"))
        master_label.pack(side=tk.LEFT, padx=(0, 10))
        add_tooltip(master_label, "Select the master (reference) image for interferometric processing")
        
        self.select_mst_btn = tk.Button(controls_frame, text="Select Master", command=self._on_select_master)
        self.select_mst_btn.pack(side=tk.LEFT, padx=(0, 10))
        add_tooltip(self.select_mst_btn, "Calculate master selection criteria and display candidate images\nMaster image should have good temporal and spatial baselines")

        self.master_listbox = None
        self._listbox_dates = []
        self.dropdown_frame = None

    def _destroy_master_frame(self):
        if hasattr(self.root, "master_frame") and self.root.master_frame is not None and self.root.master_frame.winfo_exists():
            self.root.master_frame.destroy()
            self.root.master_frame = None

    def _on_select_master(self):
        self.select_mst_btn.config(state=tk.DISABLED)
        if hasattr(self, "plot_button"):
            self.plot_button.config(state=tk.DISABLED)

        def task(use_fallback=False):
            ddata = self.paths.get("pdata")
            safe_dirs = [safe_dir.split('.SAFE')[0] for root, dirs, files in os.walk(ddata) for safe_dir in dirs if safe_dir.endswith(".SAFE")]
            marray = self._load_master_selection_cache()

            # Check if master cache has values pertaining to ddata entries
            try:
                # Handle both old and new cache formats
                cache_imgs = []
                for item in marray:
                    if isinstance(item, (list, tuple)) and len(item) >= 3:
                        # Extract the fileID and remove '-SLC' suffix
                        file_id = str(item[2])
                        cache_imgs.append(file_id.split('-SLC')[0])
                    elif hasattr(item, 'properties'):
                        # S1Product object
                        file_id = str(item.properties.get('fileID', ''))
                        cache_imgs.append(file_id.split('-SLC')[0])
                        
                cache_imgs_set = set(cache_imgs)
                safe_dirs_set = set(safe_dirs)
            except Exception as e:
                print(f"Error processing master selection cache: {e}")
                cache_imgs_set = set()
                safe_dirs_set = set(safe_dirs)

            # Check if master cache is valid: length and content match (order disregarded)
            if (
                not marray
                or len(cache_imgs) != len(safe_dirs)
                or cache_imgs_set != safe_dirs_set
            ):
                # Need to perform master selection
                attempt = 0
                max_attempts = 10  # Allow user to retry up to 10 times
                
                while attempt < max_attempts:
                    try:
                        marray = select_mst(ddata, use_fallback=use_fallback)
                        # Success - save cache and break
                        if len(marray) > 0:
                            self._save_master_selection_cache(marray)
                        break
                    except Exception as e:
                        attempt += 1
                        print(f"Master selection attempt {attempt} failed: {e}")
                        
                        # Show user prompt for retry or fallback
                        user_choice = self._prompt_asf_failure(str(e), attempt)
                        
                        if user_choice == "retry":
                            continue  # Try again with same settings
                        elif user_choice == "fallback":
                            use_fallback = True
                            continue  # Try again with fallback enabled
                        else:  # cancel
                            # User cancelled - re-enable buttons and exit
                            self.root.after(0, self._on_select_master_done)
                            return
                
                if attempt >= max_attempts:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Error", 
                        "Maximum retry attempts reached. Please check your EarthData credentials or use fallback method."
                    ))
                    self.root.after(0, self._on_select_master_done)
                    return
                    
            self.root.after(0, lambda: self._populate_master_listbox(marray))
            self.root.after(0, self._on_select_master_done)

        threading.Thread(target=task).start()
    
    def _prompt_asf_failure(self, error_msg, attempt_num):
        """
        Prompt user when ASF search fails, asking if they want to retry or use fallback.
        Returns: "retry", "fallback", or "cancel"
        """
        result = {"choice": "cancel"}  # Default to cancel
        
        def on_retry():
            result["choice"] = "retry"
            prompt.destroy()
        
        def on_fallback():
            result["choice"] = "fallback"
            prompt.destroy()
        
        def on_cancel():
            result["choice"] = "cancel"
            prompt.destroy()
        
        # Create prompt on main thread
        prompt = tk.Toplevel(self.root)
        prompt.title("ASF Search Failed")
        prompt.transient(self.root)
        prompt.lift()
        prompt.attributes('-topmost', True)
        
        msg = (
            f"❌ ASF Search Authentication Failed (Attempt {attempt_num})\n\n"
            f"Error: {error_msg}\n\n"
            f"This usually means:\n"
            f"• Your EarthData credentials may be incorrect or expired\n"
            f"• Network connectivity issues\n"
            f"• ASF service temporarily unavailable\n\n"
            f"Options:\n"
            f"• Try Again: Re-attempt ASF search with EarthData authentication\n"
            f"• Use Fallback: Calculate baselines from local files only (no ASF metadata)\n"
            f"• Cancel: Return to previous step\n\n"
            f"Note: Fallback method uses only local SAFE directory information\n"
            f"and may have limited baseline accuracy."
        )
        
        tk.Label(prompt, text=msg, justify="left", wraplength=500).pack(padx=20, pady=10)
        
        btn_frame = tk.Frame(prompt)
        btn_frame.pack(pady=(0, 10))
        
        tk.Button(btn_frame, text="Try Again", width=12, bg="lightblue", command=on_retry).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Use Fallback", width=12, bg="lightyellow", command=on_fallback).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", width=12, bg="lightcoral", command=on_cancel).pack(side=tk.LEFT, padx=5)

        def center_window(win, parent):
            win.update_idletasks()
            x = parent.winfo_rootx() + (parent.winfo_width() - win.winfo_width()) // 2
            y = parent.winfo_rooty() + (parent.winfo_height() - win.winfo_height()) // 2
            win.geometry(f"+{x}+{y}")

        prompt.after_idle(lambda: center_window(prompt, self.root))
        
        # Wait for user to make a choice
        prompt.wait_window()
        
        return result["choice"]

    def _populate_master_listbox(self, array):
        # Handle both S1Product objects and simple arrays
        processed_array = []
        for item in array:
            if hasattr(item, 'properties'):
                # S1Product object - extract properties (ASF method)
                # Format: [temporal_bl, perpendicular_bl, fileID, rank]
                file_id = str(item.properties.get('fileID', ''))
                processed_array.append([
                    float(item.properties.get('temporalBaseline', 0)),
                    float(item.properties.get('perpendicularBaseline', 0)),
                    file_id,
                    0.0,  # No avg_baseline for ASF method
                    int(item.properties.get('frameNumber', 0))  # This becomes rank position
                ])
            elif isinstance(item, (list, tuple, np.ndarray)) and len(item) >= 5:
                # Local baseline method format: [temporal_bl, perpendicular_bl, image_id, avg_total_bl, rank]
                processed_array.append([
                    float(item[0]) if item[0] is not None else 0.0,
                    float(item[1]) if item[1] is not None else 0.0,
                    str(item[2]) if item[2] is not None else '',
                    float(item[3]) if item[3] is not None else 0.0,  # avg_baseline
                    int(item[4]) if item[4] is not None else 0  # rank
                ])
            elif isinstance(item, (list, tuple, np.ndarray)) and len(item) >= 4:
                # Legacy format: [temporal_bl, perpendicular_bl, fileID, rank]
                processed_array.append([
                    float(item[0]) if item[0] is not None else 0.0,
                    float(item[1]) if item[1] is not None else 0.0,
                    str(item[2]) if item[2] is not None else '',
                    0.0,  # No avg_baseline
                    int(item[3]) if item[3] is not None else 0
                ])
            else:
                print(f"Warning: Unexpected item format in master array: {type(item)}")
                continue
        
        # Sort by rank (index 4)
        try:
            processed_array = sorted(processed_array, key=lambda x: int(x[4]))
        except (ValueError, TypeError, IndexError) as e:
            print(f"Warning: Could not sort master array by rank: {e}")
            # Continue without sorting
        
        if self.select_mst_btn:
            self.select_mst_btn.pack_forget()
        if self.dropdown_frame and self.dropdown_frame.winfo_exists():
            self.dropdown_frame.destroy()
        self.dropdown_frame = tk.Frame(self.root.master_frame)
        self.dropdown_frame.pack(side=tk.LEFT, padx=10)

        # Determine if we have avg_baseline data (local method)
        has_avg_baseline = any(row[3] != 0.0 for row in processed_array)
        
        header = tk.Frame(self.dropdown_frame)
        header.pack(side=tk.TOP, fill=tk.X)
        
        # Column headers
        if has_avg_baseline:
            headers = ["Rank", "Date", "Btemp (days)", "Bperp (m)", "Avg BL"]
            widths = [6, 12, 13, 12, 12]
        else:
            headers = ["Rank", "Date", "Btemp (days)", "Bperp (m)"]
            widths = [6, 12, 13, 12]
        
        for idx, (text, width) in enumerate(zip(headers, widths)):
            tk.Label(header, text=text, width=width, anchor="w", font=("Arial", 10, "bold")).grid(row=0, column=idx, sticky="w")

        listbox_frame = tk.Frame(self.dropdown_frame)
        listbox_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Adjust listbox width based on columns
        listbox_width = 55 if has_avg_baseline else 48
        self.master_listbox = tk.Listbox(listbox_frame, height=3, width=listbox_width, exportselection=False, font=("Courier New", 10))
        self.master_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.master_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.master_listbox.config(yscrollcommand=scrollbar.set)

        self._listbox_dates = []
        for row_data in processed_array:
            try:
                # row_data format: [temporal_bl, perpendicular_bl, file_id, avg_baseline, rank]
                file_id = str(row_data[2])
                rank = int(row_data[4])
                temporal_bl = int(row_data[0])  # Convert to int
                perpendicular_bl = float(row_data[1])
                avg_baseline = float(row_data[3])
                
                # Extract and format date from file_id
                # Format: S1_20170319_ALL_F1 -> 2017-03-19
                date_str = None
                if '_' in file_id:
                    # Try to find 8-digit date pattern (YYYYMMDD)
                    parts = file_id.split('_')
                    for part in parts:
                        if len(part) == 8 and part.isdigit():
                            # Found date: YYYYMMDD -> YYYY-MM-DD
                            date_str = f"{part[0:4]}-{part[4:6]}-{part[6:8]}"
                            break
                
                # Fallback: try extracting from position 17:25 (old logic)
                if not date_str and len(file_id) > 25:
                    date_part = file_id[17:25]
                    if date_part.isdigit():
                        date_str = f"{date_part[0:4]}-{date_part[4:6]}-{date_part[6:8]}"
                
                # Final fallback: try first 8 characters
                if not date_str and len(file_id) >= 8:
                    date_part = file_id[:8]
                    if date_part.isdigit():
                        date_str = f"{date_part[0:4]}-{date_part[4:6]}-{date_part[6:8]}"
                
                # Last resort: use file_id as is
                if not date_str:
                    date_str = file_id[:12]  # Truncate if too long
                
                # Format the row
                if has_avg_baseline:
                    row_text = f"{rank:<6} {date_str:<12} {temporal_bl:<13} {perpendicular_bl:<12.2f} {avg_baseline:<12.2f}"
                else:
                    row_text = f"{rank:<6} {date_str:<12} {temporal_bl:<13} {perpendicular_bl:<12.2f}"
                
                self.master_listbox.insert(tk.END, row_text)
                
                # Store date in YYYYMMDD format for point highlighting
                date_yyyymmdd = date_str.replace('-', '')
                self._listbox_dates.append(date_yyyymmdd)
                
            except (IndexError, TypeError, ValueError) as e:
                print(f"Warning: Could not process row data {row_data}: {e}")
                continue

        if self.master_listbox.size() > 0:
            self.master_listbox.selection_set(0)
        confirm_btn = tk.Button(self.dropdown_frame, text="Confirm Selection", command=self._on_confirm_master)
        confirm_btn.pack(side=tk.TOP, pady=10)
        add_tooltip(confirm_btn, "Confirm the selected master image\nThis image will be used as reference for all interferograms")
        self.master_listbox.bind("<<ListboxSelect>>", self._on_listbox_select)
        if self._listbox_dates:
            self._highlight_point_by_date(self._listbox_dates[0])

    def _on_listbox_select(self, _event):
        selection = self.master_listbox.curselection()
        if selection:
            self.selected_master_idx.set(selection[0])
            date_str = self._listbox_dates[selection[0]]
            self._highlight_point_by_date(date_str)

    def _highlight_point_by_date(self, date_str):
        """Highlight a point by date using matplotlib plotter."""
        if self._highlighted_point is not None:
            self._deselect_highlighted_point()

        if not self.plotter or not self.dates:
            return

        try:
            idx = next(
                i for i, d in enumerate(self.dates)
                if d.strftime("%Y%m%d") == date_str.replace("-", "")
            )
        except StopIteration:
            return

        # Use matplotlib plotter to highlight the point
        if idx < len(self.plotter.points):
            # Store the highlighted point info
            self._highlighted_point = idx
            
            # Update point colors to highlight the selected one
            colors = []
            sizes = []
            for i, point in enumerate(self.plotter.points):
                if i == idx:
                    colors.append('green')  # Highlight color
                    sizes.append(80)       # Larger size for highlight
                elif point['selected']:
                    colors.append('red')
                    sizes.append(70)
                else:
                    colors.append('steelblue')
                    sizes.append(50)
            
            self.plotter.point_scatter.set_color(colors)
            self.plotter.point_scatter.set_sizes(sizes)
            self.plotter.canvas.draw_idle()

    def _deselect_highlighted_point(self):
        """Deselect the highlighted point using matplotlib plotter."""
        if self._highlighted_point is not None and self.plotter:
            # Reset to normal colors
            self.plotter._update_point_colors()
            self._highlighted_point = None

    def _on_select_master_done(self):
        self.select_mst_btn.config(state=tk.NORMAL)
        if hasattr(self, "plot_button"):
            self.plot_button.config(state=tk.NORMAL)

    def _on_confirm_master(self):
        idx = self.selected_master_idx.get()
        selected_row = self.master_listbox.get(idx)
        columns = selected_row.split()
        self.mst = columns[1] if len(columns) >= 2 else None
        self._destroy_master_frame()
        self._show_constraints_ui()

    # --- Constraints UI ---
    def _show_constraints_ui(self, row=1, column=0):
        if hasattr(self.root, "baselines_frame") and self.root.baselines_frame.winfo_exists():
            self.root.baselines_frame.destroy()
        frame = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        frame.grid(row=row, column=column, padx=10, pady=10, sticky="nw")
        self.root.baselines_frame = frame

        constraints_label = tk.Label(frame, text="Baselines constraints", font=("Arial", 12, "bold"))
        constraints_label.pack(pady=(10, 5))
        add_tooltip(constraints_label, "Set thresholds for interferometric pair selection\nPairs exceeding these limits will be excluded")
        
        self._add_constraint_entry(frame, "Perpendicular Baseline (m):", self.perp_var)
        self._add_constraint_entry(frame, "Temporal Baseline (days):", self.temp_var)
        
        plot_pairs_btn = tk.Button(frame, text="Plot Pairs", command=self._on_plot_pairs)
        plot_pairs_btn.pack(pady=10)
        add_tooltip(plot_pairs_btn, "Generate interferometric pairs based on baseline constraints\nDisplays connections between compatible image pairs")
        
        self._add_export_edges_button(row=2, column=0)

    def _add_constraint_entry(self, frame, label_text, var):
        label = tk.Label(frame, text=label_text)
        label.pack(anchor="w", padx=10)
        
        # Add specific tooltips based on the constraint type
        if "Perpendicular" in label_text:
            add_tooltip(label, "Maximum perpendicular baseline in meters\nTypical range: 100-400m\nSmaller values = better coherence, fewer pairs")
        elif "Temporal" in label_text:
            add_tooltip(label, "Maximum temporal baseline in days\nTypical range: 50-365 days\nSmaller values = better coherence, fewer pairs")
        
        entry = tk.Entry(frame, textvariable=var, validate="key",
                 validatecommand=(self.root.register(lambda v: v.isdigit() or v == ""), "%P")
                 )
        entry.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        if "Perpendicular" in label_text:
            add_tooltip(entry, "Enter maximum perpendicular baseline in meters\nRecommended: 200-300m for good results")
        elif "Temporal" in label_text:
            add_tooltip(entry, "Enter maximum temporal separation in days\nRecommended: 100-200 days for SBAS analysis")

    def _on_plot_pairs(self):
        """Plot interferometric pairs based on constraints using matplotlib plotter."""
        try:
            perp = float(self.perp_var.get())
            temp = int(self.temp_var.get())
        except ValueError:
            messagebox.showwarning("Input Error", "Please enter valid numeric thresholds.")
            return

        if not self.plotter:
            messagebox.showerror("Error", "No baseline plot available. Please plot baselines first.")
            return
        
        # Clear existing edges and create new connections
        self.plotter.clear_edges()
        self.plotter.connect_baseline_nodes(perp, temp)
        
        # Show constraint visualization
        self.plotter.show_constraints(perp, temp)
        
        # Update internal edges for compatibility
        self.edges = self.plotter.edges
        self.original_edges = [(e['idx1'], e['idx2']) for e in self.edges]

        # Create edit mode checkbox
        if self.edit_graph_check and self.edit_graph_check.winfo_exists():
            self.edit_graph_check.destroy()
        self.edit_graph_check = tk.Checkbutton(
            self.root.baselines_frame,
            text="Edit Mode",
            variable=self.edit_mode_var,
            indicatoron=True,
            command=self._on_edit_graph_toggle
        )
        self.edit_graph_check.pack(pady=10)
        add_tooltip(self.edit_graph_check, 
                   "Enable interactive editing of baseline network\n"
                   "• Click points to add connections\n"
                   "• Click edges to select/delete\n" 
                   "• Press Delete to remove selected edge\n"
                   "• Use mouse wheel to zoom, drag to pan")
        
        # Display network statistics
        stats = self.plotter.get_statistics()
        stats_text = (f"Network: {stats['total_points']} images, {stats['total_edges']} pairs\n"
                     f"Avg temporal: {stats['avg_temporal_baseline']:.1f} days\n"
                     f"Avg perpendicular: {stats['avg_perp_baseline']:.1f} m")
        print(stats_text)

    # --- Edit Graph Mode ---
    def _on_edit_graph_toggle(self):
        """Toggle edit mode for the matplotlib plotter."""
        if not self.plotter:
            return
            
        if self._highlighted_point is not None:
            self._deselect_highlighted_point()

        # Get current and original edge lists for comparison
        current_edges = self._get_sorted_edges_from_plotter()
        original_edges = sorted(self.original_edges) if self.original_edges else []

        if self.edit_mode_var.get():
            # Enable edit mode
            self.edit_graph_check.config(fg="green")
            self.edit_graph_active = True
            self.plotter.set_edit_mode(True)
        else:
            # Disable edit mode
            self.edit_graph_check.config(fg="black")
            self.edit_graph_active = False
            self.plotter.set_edit_mode(False)
            
            # Check if changes were made
            if current_edges != original_edges:
                self._show_edit_confirm_dialog(current_edges, original_edges)
                
    def _get_sorted_edges_from_plotter(self):
        """Get sorted edge list from matplotlib plotter."""
        if not self.plotter or not self.plotter.edges:
            return []
        edges = []
        for edge in self.plotter.edges:
            idx1, idx2 = edge['idx1'], edge['idx2']
            edges.append((min(idx1, idx2), max(idx1, idx2)))
        return sorted(edges)

    def _get_sorted_edges(self, edges):
        sorted_edges = []
        for e in edges:
            if len(e) == 3:
                _, i, j = e
            elif len(e) == 2:
                i, j = e
            else:
                continue
            sorted_edges.append((min(i, j), max(i, j)))
        return sorted(sorted_edges)

    def _show_edit_confirm_dialog(self, current_edges, original_edges):
        """Show confirmation dialog for graph edits."""
        confirm = tk.Toplevel(self.root)
        confirm.transient(self.root)
        confirm.title("Graph Edited")
        tk.Label(confirm, text="You have made changes to the graph.\nRetain changes?").pack(padx=20, pady=10)
        btn_frame = tk.Frame(confirm)
        btn_frame.pack(pady=(0, 10))

        def retain():
            self.original_edges = current_edges
            confirm.destroy()

        def discard():
            if not self.plotter:
                confirm.destroy()
                return
                
            # Restore original edges in matplotlib plotter
            self.plotter.clear_edges()
            
            # Recreate original edges
            for idx1, idx2 in original_edges:
                if idx1 < len(self.points) and idx2 < len(self.points):
                    self.plotter._create_edge(idx1, idx2)
                    
            # Update internal edges
            self.edges = self.plotter.edges
            confirm.destroy()

        tk.Button(btn_frame, text="Yes", width=8, command=retain).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="No", width=8, command=discard).pack(side=tk.LEFT, padx=5)

        def center_window(win, parent):
            win.update_idletasks()
            x = parent.winfo_rootx() + (parent.winfo_width() - win.winfo_width()) // 2
            y = parent.winfo_rooty() + (parent.winfo_height() - win.winfo_height()) // 2
            win.geometry(f"+{x}+{y}")

        def finalize_dialog():
            center_window(confirm, self.root)
            if confirm.winfo_exists():
                confirm.after(10, lambda: confirm.grab_set())

        confirm.after_idle(finalize_dialog)

    def _add_export_edges_button(self, row=2, column=0):
        if hasattr(self.root, "export_frame") and self.root.export_frame is not None and self.root.export_frame.winfo_exists():
            return

        frame = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        frame.grid(row=row, column=column, padx=10, pady=10, sticky="nw")
        self.root.export_frame = frame

        valid_paths = [self.paths.get(k) for k in ['pF1', 'pF2', 'pF3'] if self.paths.get(k) and os.path.exists(self.paths.get(k))]
        if valid_paths:
            export_btn = tk.Button(
                frame,
                text="Export Edge List & Save Plot",
                command=lambda: self._on_export_edges(primary_dir=valid_paths[0])
            )
            export_btn.pack(pady=10)
            add_tooltip(export_btn, "Save interferometric pairs to intf.in files\nExports baseline plot and completes network design\nClick when satisfied with pair selection")

    def _save_baseline_plot(self, primary_dir):
        """Save baseline plot in both PNG and vector formats."""
        if not self.plotter:
            return
            
        # Save the matplotlib plot (PNG and vector formats)
        plot_path = os.path.join(primary_dir, "baseline_network_plot.png")
        
        try:
            # Use the plotter's enhanced save method with vector support
            self.plotter.save_plot(plot_path, dpi=300, save_vector=True)
            print(f"Baseline plots saved to {primary_dir}")
                    
        except Exception as e:
            print(f"Warning: Could not save plot: {e}")

    def _on_export_edges(self, primary_dir=None):
        """Export edge list and save plot using matplotlib plotter."""
        
        # Always save the plot first
        if self.plotter:
            self._save_baseline_plot(primary_dir)
        
        # Check if config and baseline constraints unchanged, skip writing intf.in if so
        conf = self._load_config()
        prev_mst = conf.get("mst")
        prev_align = conf.get("align_mode")
        prev_esd = conf.get("esd_mode")
        prev_perp = conf.get("perpendicular_baseline_constraint")
        prev_temp = conf.get("temporal_baseline_constraint")
        
        current_perp = self.perp_var.get() if hasattr(self, 'perp_var') else None
        current_temp = self.temp_var.get() if hasattr(self, 'temp_var') else None
        
        if (
            self.mst == prev_mst
            and self.align_mode_var.get() == prev_align
            and self.esd_mode_var.get() == prev_esd
            and current_perp == prev_perp
            and current_temp == prev_temp            
        ):
            # Config and constraints unchanged - still need to check for unconnected images
            print(f"✅ Network config unchanged (master, alignment, and baseline constraints)")
            intf_path = os.path.join(primary_dir, "intf.in")
            raw_dir = os.path.join(primary_dir, "raw")
            data_in_path = os.path.join(raw_dir, "data.in")
            if os.path.exists(data_in_path) and os.path.exists(intf_path):
                from ..gmtsar_gui.pair_generation import remove_unconnected_images
                removed_dates = remove_unconnected_images(intf_path, data_in_path)
                if removed_dates:
                    self._save_removed_images(removed_dates)
            
            # Only call callback and close, skip writing intf.in (plot already saved above)
            if self.on_edges_exported:
                self.on_edges_exported(self.mst, self.align_mode_var.get(), self.esd_mode_var.get())
                self._save_config()
            self.root.destroy()
            return
        
        # If we reach here, something changed - regenerate intf.in
        if current_perp != prev_perp or current_temp != prev_temp:
            print(f"🔄 Baseline constraints changed: perp {prev_perp}->{current_perp}, temp {prev_temp}->{current_temp}")

        if not self.plotter:
            messagebox.showerror("Error", "No baseline plot available for export.")
            return
            
        # Get edge list from matplotlib plotter
        edge_data = self.plotter.get_edge_list()
        edge_list = [f"{pair[0]}:{pair[1]}" for pair in edge_data]

        # Always save interferometric pairs to intf.in (even if config unchanged)
        intf_path = os.path.join(primary_dir, "intf.in")
        with open(intf_path, "w") as f:
            for pair in edge_list:
                f.write(pair + "\n")
        print(f"Edge list saved to {intf_path}")
        
        # Remove unconnected images from data.in and clean up symlinks
        from ..gmtsar_gui.pair_generation import remove_unconnected_images
        raw_dir = os.path.join(primary_dir, "raw")
        data_in_path = os.path.join(raw_dir, "data.in")
        removed_dates = set()
        if os.path.exists(data_in_path):
            removed_dates = remove_unconnected_images(intf_path, data_in_path)
            if removed_dates:
                self._save_removed_images(removed_dates)
        
        # Save the matplotlib plot (already called above, but call again in case primary_dir changed)
        self._save_baseline_plot(primary_dir)
            
        # Display final statistics
        stats = self.plotter.get_statistics()
        stats_message = (
            f"Network Export Complete!\n\n"
            f"Total images: {stats['total_points']}\n"
            f"Interferometric pairs: {stats['total_edges']}\n"
            f"Average temporal baseline: {stats['avg_temporal_baseline']:.1f} days\n"
            f"Average perpendicular baseline: {stats['avg_perp_baseline']:.1f} m\n"
            f"Network connectivity: {stats['connectivity']:.2%}"
        )
        messagebox.showinfo("Export Complete", stats_message)

        # Copy to other subswaths and clean up unconnected images
        from ..gmtsar_gui.pair_generation import remove_unconnected_images
        
        # Extract primary subswath number from primary_dir (e.g., /path/to/F1 -> "1")
        primary_subswath = os.path.basename(primary_dir)[-1] if primary_dir else "1"
        
        for key in ["pF1", "pF2", "pF3"]:
            dir_path = self.paths.get(key)
            if dir_path and os.path.exists(dir_path) and dir_path != primary_dir:
                try:
                    # Get target subswath number
                    target_subswath = os.path.basename(dir_path)[-1]
                    
                    # Copy and modify intf.in with correct subswath references
                    subswath_intf = os.path.join(dir_path, "intf.in")
                    shutil.copy2(intf_path, subswath_intf)
                    
                    # Modify subswath references in the copied file
                    with open(subswath_intf, 'r') as f:
                        lines = f.readlines()
                    with open(subswath_intf, 'w') as f:
                        for line in lines:
                            # Replace _ALL_F1 with _ALL_F2, etc.
                            modified_line = line.replace(f'_ALL_F{primary_subswath}', f'_ALL_F{target_subswath}')
                            f.write(modified_line)
                    
                    print(f"Copied and modified intf.in to {dir_path} (F{primary_subswath} -> F{target_subswath})")
                    
                    # Also remove unconnected images for this subswath
                    subswath_raw = os.path.join(dir_path, "raw")
                    subswath_data_in = os.path.join(subswath_raw, "data.in")
                    if os.path.exists(subswath_data_in):
                        remove_unconnected_images(subswath_intf, subswath_data_in)
                except Exception as e:
                    print(f"Warning: Could not copy to {dir_path}: {e}")

        # Call callback and close
        if self.on_edges_exported:
            # Log completion of the entire baseline workflow
            if self.log_file:
                process_logger(process_num=1, log_file=self.log_file, message="Baseline analysis and network design completed.", mode="end")
            self.on_edges_exported(self.mst, self.align_mode_var.get(), self.esd_mode_var.get())
            self._save_config()
        self.root.destroy()


def run_threaded(root, target, on_complete=None):
    def wrapper():
        target()
        if on_complete:
            root.after(0, on_complete)
    threading.Thread(target=wrapper).start()
