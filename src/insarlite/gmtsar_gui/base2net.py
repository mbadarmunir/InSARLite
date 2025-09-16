import os
import threading
import tkinter as tk
import numpy as np
from tkinter import messagebox
# from datetime import datetime, timedelta
import json

from ..utils.utils import (
    connect_baseline_nodes,
    interactive_baseline_edges,
    plot_baseline_table,
)
from ..gmtsar_gui.baselines_gen import preprocess
from ..gmtsar_gui.masterselection import select_mst
import shutil

class BaselineGUI:
    def __init__(self, root, dem, paths=None, on_edges_exported=None):
        self.root = root
        self.dem_path = dem
        self.paths = paths
        self.on_edges_exported = on_edges_exported
        self.root.title("Plot Baselines and Generate IFG Pairs")

        # Plot-related attributes
        self.plot_frame = None
        self.canvas = None
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
        # Convert ndarray to list for JSON serialization
        if isinstance(marray, np.ndarray):
            conf["master_selection_cache"] = marray.tolist()
        else:
            conf["master_selection_cache"] = marray
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
        
        cache_imgs = [sublist[2].split('-SLC')[0] for sublist in marray]
        cache_imgs_set = set(cache_imgs)
        safe_dirs_set = set(safe_dirs)
        if (
            not marray
            or len(marray) != len(safe_dirs)
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

        tk.Label(self.alignment_frame, text="Baselines calc. & Align. Param.", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(5, 15))

        self.align_mode_var = tk.StringVar(value="esd")
        self.esd_mode_frame = None

        tk.Radiobutton(
            self.alignment_frame, text="Align with ESD", variable=self.align_mode_var, value="esd",
            command=lambda: self.show_esd_modes()
        ).grid(row=1, column=0, sticky="w", padx=5)
        tk.Radiobutton(
            self.alignment_frame, text="Align w/o ESD", variable=self.align_mode_var, value="no_esd",
            command=lambda: self.hide_esd_modes()
        ).grid(row=1, column=1, sticky="w", padx=5)

        self.esd_mode_var = tk.StringVar(value="2")
        self._add_plot_button(row=1)

        def create_esd_mode_frame():
            frame = tk.Frame(self.alignment_frame)
            tk.Label(frame, text="ESD Mode:").grid(row=0, column=0, sticky="w")
            tk.Radiobutton(frame, text="average", variable=self.esd_mode_var, value="0").grid(row=0, column=1, sticky="w")
            tk.Radiobutton(frame, text="median", variable=self.esd_mode_var, value="1").grid(row=0, column=2, sticky="w")
            tk.Radiobutton(frame, text="interpolation", variable=self.esd_mode_var, value="2").grid(row=0, column=3, sticky="w")
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

    # --- Baseline Plotting ---
    def on_plot_baselines(self):
        if not self.paths:
            print("No paths provided.")
            return
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
        if self.plot_frame:
            self.plot_frame.destroy()
        self.plot_frame, self.canvas, self.points, self.dates, self.perp_baselines = plot_baseline_table(
            self.root, baseline_table_path
        )

    # --- Master Selection UI ---
    def _show_master_ui(self, row=0, column=1):
        self._destroy_master_frame()
        frame = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        frame.grid(row=row, column=column, padx=10, pady=10, sticky="nw")
        self.root.master_frame = frame

        controls_frame = tk.Frame(frame)
        controls_frame.pack(side=tk.LEFT, fill=tk.X)
        tk.Label(controls_frame, text="Master Selection", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        self.select_mst_btn = tk.Button(controls_frame, text="Select Master", command=self._on_select_master)
        self.select_mst_btn.pack(side=tk.LEFT, padx=(0, 10))

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

            # xxxx write code to check if master cache has values pertaining to ddata entries
            
            cache_imgs = [sublist[2].split('-SLC')[0] for sublist in marray]            

            # Check if master cache is valid: length and content match (order disregarded)
            cache_imgs_set = set(cache_imgs)
            safe_dirs_set = set(safe_dirs)
            if (
                not marray
                or len(marray) != len(safe_dirs)
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
        array = sorted(array, key=lambda x: int(x[3]))
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

        columns_map = [3, 2, 0, 1]
        self._listbox_dates = []
        for row_data in array:
            row_text = "{:<8} {:<12} {:<12} {:<12}".format(
                str(row_data[columns_map[0]]),
                row_data[columns_map[1]][17:25],
                str(row_data[columns_map[2]]),
                str(row_data[columns_map[3]])
            )
            self.master_listbox.insert(tk.END, row_text)
            self._listbox_dates.append(row_data[columns_map[1]][17:25])

        self.master_listbox.selection_set(0)
        tk.Button(self.dropdown_frame, text="Confirm Selection", command=self._on_confirm_master).pack(side=tk.TOP, pady=10)
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
        if self._highlighted_point is not None:
            try:
                idx_prev = int(self._highlighted_point.replace("pt", ""))
                self.canvas.delete(self._highlighted_point)
                x_prev, y_prev = self.points[idx_prev]["x"], self.points[idx_prev]["y"]
                self.canvas.create_oval(x_prev - 2, y_prev - 2, x_prev + 2, y_prev + 2, fill="blue", tags=f"pt{idx_prev}")
            except Exception:
                pass
            self._highlighted_point = None

        try:
            idx = next(
                i for i, d in enumerate(self.dates)
                if d.strftime("%Y%m%d") == date_str.replace("-", "")
            )
        except StopIteration:
            return

        self.canvas.delete(f"pt{idx}")
        x, y = self.points[idx]["x"], self.points[idx]["y"]
        self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill="green", tags=f"pt{idx}")
        self._highlighted_point = f"pt{idx}"

    def _deselect_highlighted_point(self):
        if self._highlighted_point is not None:
            self.canvas.itemconfig(self._highlighted_point, fill="blue")
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

        tk.Label(frame, text="Baselines constraints", font=("Arial", 12, "bold")).pack(pady=(10, 5))
        self._add_constraint_entry(frame, "Perpendicular Baseline (m):", self.perp_var)
        self._add_constraint_entry(frame, "Temporal Baseline (days):", self.temp_var)
        tk.Button(frame, text="Plot Pairs", command=self._on_plot_pairs).pack(pady=10)
        self._add_export_edges_button(row=2, column=0)

    def _add_constraint_entry(self, frame, label_text, var):
        tk.Label(frame, text=label_text).pack(anchor="w", padx=10)
        tk.Entry(frame, textvariable=var, validate="key",
                 validatecommand=(self.root.register(lambda v: v.isdigit() or v == ""), "%P")
                 ).pack(fill=tk.X, padx=10, pady=(0, 10))

    def _on_plot_pairs(self):
        try:
            perp = float(self.perp_var.get())
            temp = int(self.temp_var.get())
        except ValueError:
            messagebox.showwarning("Input Error", "Please enter valid numeric thresholds.")
            return

        for e in self.edges:
            self.canvas.delete(e[0])
        self.edges.clear()

        self.edges = connect_baseline_nodes(self.canvas, self.points, self.dates, self.perp_baselines, perp, temp)
        self.original_edges = [(min(e[1], e[2]), max(e[1], e[2])) for e in self.edges]

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

    # --- Edit Graph Mode ---
    def _on_edit_graph_toggle(self):
        if self._highlighted_point is not None:
            self._deselect_highlighted_point()

        current_edges = self._get_sorted_edges(self.edges)
        original_edges = self._get_sorted_edges(self.original_edges)

        if self.edit_mode_var.get():
            self.edit_graph_check.config(fg="green")
            self.edit_graph_active = True
            self.edit_bindings = interactive_baseline_edges(self.canvas, self.points, self.edges)
        else:
            self.edit_graph_check.config(fg="black")
            self.edit_graph_active = False
            if hasattr(self, "edit_bindings"):
                if "reset" in self.edit_bindings:
                    self.edit_bindings["reset"]()
                self.canvas.unbind("<Button-1>")
                self.canvas.unbind_all("<Delete>")
            if current_edges != original_edges:
                self._show_edit_confirm_dialog(current_edges, original_edges)

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
            for e in self.edges:
                self.canvas.delete(e[0])
            self.edges.clear()
            for idx1, idx2 in original_edges:
                x1 = self.points[idx1]["x"]
                y1 = self.points[idx1]["y"]
                x2 = self.points[idx2]["x"]
                y2 = self.points[idx2]["y"]
                line_id = self.canvas.create_line(x1, y1, x2, y2, fill="green", width=2)
                self.edges.append((line_id, idx1, idx2))
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
            tk.Button(
                frame,
                text="Export Edge List & Save Plot",
                command=lambda: self._on_export_edges(primary_dir=valid_paths[0])
            ).pack(pady=10)

    def _on_export_edges(self, primary_dir=None):
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

        edge_list = []
        for edge in self.edges:
            if len(edge) == 3:
                _, idx1, idx2 = edge
            elif len(edge) == 2:
                idx1, idx2 = edge
            else:
                continue

            label1 = self.points[idx1].get('file_id', "") if idx1 < len(self.points) else ""
            label2 = self.points[idx2].get('file_id', "") if idx2 < len(self.points) else ""
            if not label1 and idx1 < len(self.dates):
                label1 = self.dates[idx1].strftime("%Y%m%d")
            if not label2 and idx2 < len(self.dates):
                label2 = self.dates[idx2].strftime("%Y%m%d")
            edge_list.append(f"{label1}:{label2}")

        intf_path = os.path.join(primary_dir, "intf.in")
        with open(intf_path, "w") as f:
            for pair in edge_list:
                f.write(pair + "\n")
        print(f"Edge list saved to {intf_path}")
        primary_key = edge_list[0][-2:] if edge_list else ""
        for key in ["pF1", "pF2", "pF3"]:
            dir_path = self.paths.get(key)
            if dir_path and os.path.exists(dir_path) and dir_path != primary_dir:
                other_path = os.path.join(dir_path, "intf.in")
                shutil.copy(intf_path, other_path)
                with open(other_path, 'r') as f:
                    lines = f.readlines()
                with open(other_path, 'w') as f:
                    for line in lines:
                        f.write(line.replace(primary_key, key[-2:]))

        for key in ["pF1", "pF2", "pF3"]:
            dir_path = self.paths.get(key)
            if dir_path and os.path.exists(dir_path):
                try:
                    ps_path = os.path.join(dir_path, "raw", "baseline_plot.ps")
                    os.makedirs(os.path.dirname(ps_path), exist_ok=True)
                    self.canvas.postscript(file=ps_path)
                    print(f"Plot saved as PostScript at {ps_path}")
                except Exception as e:
                    print(f"Error saving plot to {dir_path}: {e}")

        # Save config for next time
        # self._save_config()

        if self.on_edges_exported:
            self.on_edges_exported(self.mst, self.align_mode_var.get(), self.esd_mode_var.get())
            self._save_config()

        self.root.destroy()

def run_threaded(root, target, on_complete=None):
    def wrapper():
        target()
        if on_complete:
            root.after(0, on_complete)
    threading.Thread(target=wrapper).start()
