import os
import threading
import tkinter as tk
import numpy as np
from tkinter import messagebox
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

        # Config file path
        self.conf_path = os.path.join(os.path.expanduser('~'), ".config.json")
        self.mst = None

        self._init_ui()
        self._check_previous_config()

    # --- Config Handling ---
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
        # Only update/append the relevant keys, preserving others
        conf = self._load_config()
        updates = {
            "mst": self.mst,
            "align_mode": self.align_mode_var.get(),
            "esd_mode": self.esd_mode_var.get()
        }
        
        conf.update({k: v for k, v in updates.items() if v is not None})
        
        try:
            with open(self.conf_path, "w") as f:
                json.dump(conf, f, indent=2)
        except Exception as e:
            print(f"Could not save config: {e}")

    def _save_master_selection_cache(self, marray):
        # Only update/append the master_selection_cache key        
        conf = self._load_config()
        # Convert array to JSON-serializable format
        try:
            if isinstance(marray, np.ndarray):
                conf["master_selection_cache"] = marray.tolist()
            elif hasattr(marray, '__iter__'):
                # Convert S1Product objects or other complex objects to simple lists
                cache_data = []
                for item in marray:
                    if hasattr(item, 'properties'):
                        # S1Product object - extract key properties
                        cache_data.append([
                            float(item.properties.get('temporalBaseline', 0)),
                            float(item.properties.get('perpendicularBaseline', 0)),
                            str(item.properties.get('fileID', '')),
                            int(item.properties.get('frameNumber', 0))
                        ])
                    elif isinstance(item, (list, tuple)) and len(item) >= 4:
                        # Already a list/tuple format
                        cache_data.append(list(item))
                    else:
                        # Convert other iterables to list
                        cache_data.append(list(item))
                conf["master_selection_cache"] = cache_data
            else:
                conf["master_selection_cache"] = marray
        except Exception as e:
            print(f"Could not convert master selection data for caching: {e}")
            # Fallback: don't cache complex objects
            conf["master_selection_cache"] = []
            
        try:
            with open(self.conf_path, "w") as f:
                json.dump(conf, f, indent=2)
        except Exception as e:
            print(f"Could not save master selection cache: {e}")

    def _load_master_selection_cache(self):
        conf = self._load_config()
        return conf.get("master_selection_cache", [])

    def _check_previous_config(self):
        conf = self._load_config()
        prev_mst = conf.get("mst")
        prev_align = conf.get("align_mode")
        prev_esd = conf.get("esd_mode")
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
        
        safe_dirs = [safe_dir.split('.SAFE')[0] for root, dirs, files in os.walk(ddata) for safe_dir in dirs if safe_dir.endswith(".SAFE")]
        marray = self._load_master_selection_cache()
        
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
            
        if (
            not marray
            or len(cache_imgs) != len(safe_dirs)
            or cache_imgs_set != safe_dirs_set
        ):
            print("Master selection cache is invalid or does not match SAFE directories.")
            valid_pfraw = False

        # Additional check: prev_mst must match one of the SAFE directory dates
        if prev_mst:
            safe_dates = [safe_dir[17:25] for safe_dir in safe_dirs if len(safe_dir) >= 25]
            if prev_mst not in safe_dates:
                print(f"Previous master {prev_mst} not found in SAFE directory dates.")
                valid_pfraw = False

        if prev_mst and prev_align and prev_esd and valid_pfraw:
            print("Previous config found and all pfraw checks passed. Prompting user to use previous config.")
            self._prompt_use_previous_config(prev_mst, prev_align, prev_esd)
            return
        else:
            if not prev_mst:
                print("No previous master (mst) found in config.")
            if not prev_align:
                print("No previous align_mode found in config.")
            if not prev_esd:
                print("No previous esd_mode found in config.")
            if not valid_pfraw:
                print("Images are different than saved in the config.")
      
        # If not using previous config, proceed as normal

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
            
        # Log the start of actual baseline processing
        if self.log_file:
            process_logger(process_num=1, log_file=self.log_file, message="Starting baseline analysis and network design...", mode="start")
            
        if self.plot_frame and self.plot_frame.winfo_exists():
            self.plot_frame.destroy()
        self._destroy_master_frame()
        if hasattr(self.root, "baselines_frame") and self.root.baselines_frame.winfo_exists():
            self.root.baselines_frame.destroy()
        if hasattr(self.root, "export_frame") and self.root.export_frame is not None and self.root.export_frame.winfo_exists():
            self.root.export_frame.destroy()
        run_threaded(
            self.root,
            target=lambda: preprocess(self.paths, self.dem_path, self.align_mode_var.get(), self.esd_mode_var.get()),
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
            # Create the interactive matplotlib plotter
            self.plotter = create_interactive_baseline_plot(self.plot_frame, baseline_table_path)
            
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

        def task():
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
                for attempt in range(4):
                    try:
                        marray = select_mst(ddata)
                        break
                    except Exception as e:
                        print(f"Attempt {attempt+1} failed: {e}")
                if len(marray) > 0:
                    self._save_master_selection_cache(marray)
            self.root.after(0, lambda: self._populate_master_listbox(marray))
            self.root.after(0, self._on_select_master_done)

        threading.Thread(target=task).start()

    def _populate_master_listbox(self, array):
        # Handle both S1Product objects and simple arrays
        processed_array = []
        for item in array:
            if hasattr(item, 'properties'):
                # S1Product object - extract properties
                processed_array.append([
                    float(item.properties.get('temporalBaseline', 0)),
                    float(item.properties.get('perpendicularBaseline', 0)),
                    str(item.properties.get('fileID', '')),
                    int(item.properties.get('frameNumber', 0))
                ])
            elif isinstance(item, (list, tuple, np.ndarray)) and len(item) >= 4:
                # Already in array format
                processed_array.append([
                    float(item[0]) if item[0] is not None else 0.0,
                    float(item[1]) if item[1] is not None else 0.0,
                    str(item[2]) if item[2] is not None else '',
                    int(item[3]) if item[3] is not None else 0
                ])
            else:
                print(f"Warning: Unexpected item format in master array: {type(item)}")
                continue
        
        # Sort by rank (index 3)
        try:
            processed_array = sorted(processed_array, key=lambda x: int(x[3]))
        except (ValueError, TypeError, IndexError) as e:
            print(f"Warning: Could not sort master array by rank: {e}")
            # Continue without sorting
        
        if self.select_mst_btn:
            self.select_mst_btn.pack_forget()
        if self.dropdown_frame and self.dropdown_frame.winfo_exists():
            self.dropdown_frame.destroy()
        self.dropdown_frame = tk.Frame(self.root.master_frame)
        self.dropdown_frame.pack(side=tk.LEFT, padx=10)

        header = tk.Frame(self.dropdown_frame)
        header.pack(side=tk.TOP, fill=tk.X)
        for idx, text in enumerate(["Rank", "Date", "Btemp (days)", "Bperp (m)"]):
            tk.Label(header, text=text, width=12, anchor="w", font=("Arial", 10, "bold")).grid(row=0, column=idx, sticky="w")

        listbox_frame = tk.Frame(self.dropdown_frame)
        listbox_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.master_listbox = tk.Listbox(listbox_frame, height=3, width=48, exportselection=False, font=("Courier New", 10))
        self.master_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.master_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.master_listbox.config(yscrollcommand=scrollbar.set)

        columns_map = [3, 2, 0, 1]  # [rank, fileID, temporal_baseline, perpendicular_baseline]
        self._listbox_dates = []
        for row_data in processed_array:
            try:
                # Extract date from fileID (position 17:25)
                file_id = str(row_data[columns_map[1]])
                date_str = file_id[17:25] if len(file_id) > 25 else file_id[:8]
                
                row_text = "{:<8} {:<12} {:<12} {:<12}".format(
                    str(row_data[columns_map[0]]),  # rank
                    date_str,                        # date
                    str(row_data[columns_map[2]]),   # temporal baseline
                    str(row_data[columns_map[3]])    # perpendicular baseline
                )
                self.master_listbox.insert(tk.END, row_text)
                self._listbox_dates.append(date_str)
            except (IndexError, TypeError) as e:
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

    def _on_export_edges(self, primary_dir=None):
        """Export edge list and save plot using matplotlib plotter."""
        # If user chose to use previous config, skip writing intf.in
        conf = self._load_config()
        prev_mst = conf.get("mst")
        prev_align = conf.get("align_mode")
        prev_esd = conf.get("esd_mode")
        if (
            self.mst == prev_mst
            and self.align_mode_var.get() == prev_align
            and self.esd_mode_var.get() == prev_esd
            and os.path.exists(os.path.join(primary_dir, "intf.in"))
        ):
            # Only call callback and close, skip writing intf.in and plot
            if self.on_edges_exported:
                self.on_edges_exported(self.mst, self.align_mode_var.get(), self.esd_mode_var.get())
                self._save_config()
            self.root.destroy()
            return

        if not self.plotter:
            messagebox.showerror("Error", "No baseline plot available for export.")
            return
            
        # Get edge list from matplotlib plotter
        edge_data = self.plotter.get_edge_list()
        edge_list = [f"{pair[0]}:{pair[1]}" for pair in edge_data]

        # Save interferometric pairs to intf.in
        intf_path = os.path.join(primary_dir, "intf.in")
        with open(intf_path, "w") as f:
            for pair in edge_list:
                f.write(pair + "\n")
        print(f"Edge list saved to {intf_path}")
        
        # Save the matplotlib plot
        plot_path = os.path.join(primary_dir, "baseline_network_plot.png")
        try:
            self.plotter.save_plot(plot_path, dpi=300)
            print(f"Baseline plot saved to {plot_path}")
        except Exception as e:
            print(f"Warning: Could not save plot: {e}")
            
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

        # Copy to other subswaths
        primary_key = edge_list[0][-2:] if edge_list else ""
        for key in ["pF1", "pF2", "pF3"]:
            dir_path = self.paths.get(key)
            if dir_path and os.path.exists(dir_path) and dir_path != primary_dir:
                try:
                    shutil.copy2(intf_path, dir_path)
                    print(f"Copied intf.in to {dir_path}")
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
