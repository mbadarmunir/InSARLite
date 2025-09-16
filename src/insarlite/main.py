import os
import math
import threading
import datetime
import tkinter as tk
from tkinter import messagebox
from tkcalendar import DateEntry
from tkintermapview import TkinterMapView
from .utils.utils import (
    browse_folder, browse_file, extr_ext_TL, configure_zooming_ui,
    subset_safe_dirs, submit_gacos_batch, estimate_s1_slc_frames,
    check_align_completion, check_ifgs_completion, check_merge_completion
)
from .gmtsar_gui.data_dwn import search_sentinel1_acquisitions, download_sentinel1_acquisitions
from .gmtsar_gui.dem_dwn import make_dem
from .gmtsar_gui.structuring import orchestrate_structure_and_copy
from .gmtsar_gui.orbitsdownload import process_files
from .gmtsar_gui.base2net import BaselineGUI
from .gmtsar_gui.align_genIFGs import GenIfg
from .gmtsar_gui.sbas04 import SBASApp
from .gmtsar_gui.unwrap import UnwrapApp
import time
import fnmatch
import zipfile
import shutil
import re
import subprocess
import json
import inspect

def clamp(val, minval, maxval):
    try:
        val = float(val)
        if minval is not None:
            val = max(val, minval)
        if maxval is not None:
            val = min(val, maxval)
        return val
    except Exception:
        return val

class InSARLiteApp:
    LABELS = ["Elapsed", "Downloaded", "Speed", "Mean", "Completion", "ETA"]
    POLY_COLORS = ["green", "yellow", "black"]

    def __init__(self, root):
        self.root = root
        self.mst = None
        self.root.title("InSARLite Workflow Studio")
        self.DEFAULT_BROWSE_BG = self.root.cget("bg")
        self._global_pause_event = threading.Event()
        configure_zooming_ui(self.root)
        self._init_state()
        self._row = 0
        self._row_map = {}
        self._create_widgets()
        self._bind_events()
        self._try_auto_draw()
        self._update_data_query_btn_state()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        # self._add_pause_button()

    def _on_close(self):
        self._set_global_pause_flag(False)
        self.root.destroy()
        os._exit(0)

    def _set_global_pause_flag(self, value):
        if value:
            self._global_pause_event.set()
        else:
            self._global_pause_event.clear()

    def is_paused(self):
        return self._global_pause_event.is_set()

    def _add_pause_button(self, row=0):
        if not hasattr(self, "pause_btn"):
            self.pause_btn = tk.Button(
                self.root, text="Pause", command=self._toggle_pause,
                bg="orange", activebackground="orange"
            )
        self.pause_btn.grid(row=row, column=5, padx=10, pady=5, sticky="e")

    def _toggle_pause(self):
        if self.is_paused():
            self._set_global_pause_flag(False)
            self.pause_btn.config(text="Pause", bg="orange", activebackground="orange")
        else:
            self._set_global_pause_flag(True)
            self.pause_btn.config(text="Resume", bg="yellow", activebackground="yellow")

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
        self.selected_urls = None
        self.total_expected_size = None
        self.custom_shape = None
        self.safe_dirs_label = None
        self.download_stats_labels = {}
        self.conf_path = None  # Will be set dynamically

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
        proj_json = os.path.join(os.path.expanduser('~'), ".projs.json")
        projects = []
        # Load previous projects
        if os.path.exists(proj_json):
            try:
                with open(proj_json, "r") as f:
                    projects = json.load(f)
            except Exception:
                projects = []
        # Validate existence of each project and its config
        valid_projects = []
        for entry in projects:
            out_folder = entry.get("output_folder", "")
            proj_name = entry.get("project_name", "")
            conf_path = os.path.join(out_folder, proj_name, ".config.json")
            if os.path.isdir(os.path.join(out_folder, proj_name)) and os.path.isfile(conf_path):
                valid_projects.append(entry)
        # Remove non-existent entries from .projs.json
        if valid_projects != projects:
            try:
                with open(proj_json, "w") as f:
                    json.dump(valid_projects, f, indent=2)
            except Exception:
                pass
        # Show popup if any valid projects
        popup = tk.Toplevel(self.root)
        popup.title("Select Project")
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
                self.conf_path = os.path.join(
                    entry.get("output_folder", ""), entry.get("project_name", ""), ".config.json"
                )
                popup.destroy()
                self._load_config()
            else:
                messagebox.showinfo("Select Project", "Please select a project from the list.")

        def on_new():
            popup.destroy()
            self.conf_path = None

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
        # Save config to project-specific location
        out_folder_val = self.output_folder_entry.get().strip()
        proj_name_val = self.project_name_entry.get().strip()
        self.conf_path = os.path.join(out_folder_val, proj_name_val, ".config.json")
        print(f"Saving config to {self.conf_path}")

        # Save project entry to .projs.json
        proj_json = os.path.join(os.path.expanduser('~'), ".projs.json")
        entry = {"output_folder": out_folder_val, "project_name": proj_name_val}
        projects = []
        if os.path.exists(proj_json):
            try:
                with open(proj_json, "r") as f:
                    projects = json.load(f)
            except Exception:
                projects = []
        # Add or update entry
        found = False
        for i, e in enumerate(projects):
            if e["output_folder"] == out_folder_val and e["project_name"] == proj_name_val:
                projects[i] = entry
                found = True
                break
        if not found:
            projects.append(entry)
        try:
            with open(proj_json, "w") as f:
                json.dump(projects, f, indent=2)
        except Exception as e:
            print(f"Failed to update .projs.json: {e}")

        # Clamp extent values
        try:
            n = clamp(self.n_entry.get(), self.extent_limits.get("s"), self.extent_limits.get("n"))
            s = clamp(self.s_entry.get(), self.extent_limits.get("s"), self.extent_limits.get("n"))
            e = clamp(self.e_entry.get(), self.extent_limits.get("w"), self.extent_limits.get("e"))
            w = clamp(self.w_entry.get(), self.extent_limits.get("w"), self.extent_limits.get("e"))
        except Exception:
            n = self.n_entry.get()
            s = self.s_entry.get()
            e = self.e_entry.get()
            w = self.w_entry.get()
        # Clamp dates
        try:
            st = self.start_var.get()
            en = self.end_var.get()
            sdate = clamp(st, self.date_limits.get("sdate"), self.date_limits.get("edate"))
            edate = clamp(en, self.date_limits.get("sdate"), self.date_limits.get("edate"))
        except Exception:
            sdate = self.start_var.get()
            edate = self.end_var.get()

        config = {}
        if os.path.exists(self.conf_path):
            try:
                with open(self.conf_path, "r") as f:
                    config = json.load(f)
            except Exception:
                config = {}

        config.update({
            "extent_clamped": {"n": n, "s": s, "e": e, "w": w},
            "extent_entries": {
                "n": self.n_entry.get(),
                "s": self.s_entry.get(),
                "e": self.e_entry.get(),
                "w": self.w_entry.get()
            },
            "dates_clamped": {"start": sdate, "end": edate},
            "dates_entries": {
                "start": self.start_var.get(),
                "end": self.end_var.get()
            },
            "flight_direction": self.flight_dir_var.get(),
            "data_folder": self.data_folder_entry.get().strip(),
            "polarization": self._get_pol_controls_state(),
            "subswaths": self.get_selected_subswaths(),
            "dem_file": self.dem_entry.get().strip() if hasattr(self, "dem_entry") else "",
            "output_folder": out_folder_val,
            "project_name": proj_name_val,
            "gacos_folder": self.gacos_data_path if hasattr(self, "gacos_data_path") else ""
        })
        try:
            os.makedirs(os.path.join(out_folder_val, proj_name_val), exist_ok=True)
            with open(self.conf_path, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def _load_config(self):
        # Load config from project-specific location
        if not self.conf_path:
            out_folder_val = self.output_folder_entry.get().strip()
            proj_name_val = self.project_name_entry.get().strip()
            self.conf_path = os.path.join(out_folder_val, proj_name_val, ".config.json")
        if not os.path.exists(self.conf_path):
            messagebox.showinfo("Load Config", f"No previous configuration found at {self.conf_path}.")
            return
        try:
            with open(self.conf_path, "r") as f:
                config = json.load(f)
        except Exception as e:
            messagebox.showinfo("Load Config", f"Failed to load configuration.\n\n{e}")
            return

        # 2.0 Set the stored date entries (not clamped)
        self.start_var.set(config.get("dates_entries", {}).get("start", ""))
        self.end_var.set(config.get("dates_entries", {}).get("end", ""))
        self._validate_dates()  # Ensure dates are validated and UI updated
        self._enforce_date_limits()  # Ensure dates are clamped to limits

        # 1. Set the value of data_folder_entry
        data_folder = config.get("data_folder", "")
        self.data_folder_entry.delete(0, tk.END)
        self.data_folder_entry.insert(0, data_folder)
        self._on_data_folder_change()  # This should trigger the UI to update and controls to appear

        # Wait for the UI to update (since controls are dynamic)
        self.root.update_idletasks()

        # Update clamped values in config and set extent/date entries to stored ones
        ext = config.get("extent_entries", {})
        self.n_entry.delete(0, tk.END)
        self.n_entry.insert(0, ext.get("n", ""))
        self.s_entry.delete(0, tk.END)
        self.s_entry.insert(0, ext.get("s", ""))
        self.e_entry.delete(0, tk.END)
        self.e_entry.insert(0, ext.get("e", ""))
        self.w_entry.delete(0, tk.END)
        self.w_entry.insert(0, ext.get("w", ""))
        dates = config.get("dates_entries", {})
        self.start_var.set(dates.get("start", ""))
        self.end_var.set(dates.get("end", ""))
        if hasattr(self, "pol_var"):
            self.pol_var.set(config.get("polarization", "VV").upper())
        # Ensure the correct polarization radio button is selected and disabled if only one is available
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

        if hasattr(self, "flight_dir_var"):
            self.flight_dir_var.set(config.get("flight_direction", "DESCENDING"))
        # Set subswaths
        if hasattr(self, "subswath_vars"):
            for i, var in enumerate(self.subswath_vars):
                var.set(1 if (i+1) in config.get("subswaths", []) else 0)

        # 3. Set DEM entry if file exists, else error popup
        dem_file = config.get("dem_file", "")
        if dem_file:
            if os.path.exists(dem_file):
                if hasattr(self, "dem_entry"):
                    self.dem_entry.config(state="normal")
                    self.dem_entry.delete(0, tk.END)
                    self.dem_entry.insert(0, dem_file)
                    self.dem_entry.config(state="disabled")
                    self.dwn_dem.destroy()
                    self.update_dem_controls()
                    self._show_output_folder_and_project_controls()
            else:
                messagebox.showerror("DEM File Error", "DEM file has been changed/moved. Load aborted!")
                return

        # 4. Set output folder and project name
        if hasattr(self, "output_folder_entry"):
            self.output_folder_entry.config(state="normal")
            self.output_folder_entry.delete(0, tk.END)
            self.output_folder_entry.insert(0, config.get("output_folder", ""))
        if hasattr(self, "project_name_entry"):
            self.project_name_entry.config(state="normal")
            self.project_name_entry.delete(0, tk.END)
            self.project_name_entry.insert(0, config.get("project_name", ""))

        self.show_confirm_btn_if_ready()

        # 5. Set GACOS data entry if exists
        self.gacos_data_path = config.get("gacos_folder", "")
        self._set_gacos_btn_state()
        messagebox.showinfo("Config Loaded", "Previous configuration successfully retrieved.")

    def _create_extent_widgets(self):
        row = self._next_row("extent")
        tk.Label(self.root, text="Extent:").grid(row=row, column=0, padx=10, pady=5)
        self.extent_frame = tk.Frame(self.root)
        self.extent_frame.grid(row=row, column=1, columnspan=2, padx=10, pady=5, sticky="w")
        vcmd = (self.root.register(self._validate_float), "%P")
        self.n_entry, self.s_entry, self.e_entry, self.w_entry = self._make_extent_entries(self.extent_frame, vcmd)

    def _make_extent_entries(self, frame, vcmd):
        def entry(label, row, col, sticky):
            tk.Label(frame, text=label).grid(row=row, column=col, padx=2, pady=2, sticky=sticky)
            e = tk.Entry(frame, width=8, validate="key", validatecommand=vcmd)
            e.grid(row=row, column=col+1, padx=2, pady=2, sticky=sticky)
            return e
        n = entry("N", 0, 2, "s")
        s = entry("S", 2, 2, "n")
        w = entry("W", 1, 0, "e")
        e = entry("E", 1, 4, "w")
        return n, s, e, w

    def _create_map_widget(self):
        row = self._get_row("extent")
        self.map_frame = tk.Frame(self.root)
        self.map_frame.grid(row=row, column=3, padx=10, pady=5, sticky="nsew")
        for i in range(2): self.root.grid_columnconfigure(i, weight=0)
        self.root.grid_columnconfigure(3, weight=1)
        self.root.grid_rowconfigure(row, weight=1)
        self.map_frame.grid_rowconfigure(0, weight=1)
        self.map_frame.grid_columnconfigure(0, weight=1)
        map_container = tk.Frame(self.map_frame)
        map_container.grid(row=0, column=0, sticky="nsew")
        map_container.grid_rowconfigure(0, weight=1)
        map_container.grid_columnconfigure(0, weight=1)
        self.map_widget = TkinterMapView(map_container, corner_radius=0)
        self.map_widget.grid(row=0, column=0, sticky="nsew")
        self.map_widget.set_zoom(1)
        self.map_widget.set_position(20, 0)
        map_container.bind("<Configure>", lambda event: self.map_widget.config(width=event.width, height=event.height))
        self.map_widget.add_left_click_map_command(self._on_map_click_with_limits_and_update)

        # Securely refresh the map once everything is loaded
        def refresh_map():
            try:
                # Pan and zoom to force refresh
                self.map_widget.set_zoom(self.map_widget.zoom + 1)
                self.map_widget.set_zoom(self.map_widget.zoom - 1)
                self.map_widget.set_position(20, 0)
            except Exception:
                pass

        # Bind to root's initial idle event after window is shown
        self.root.after(500, refresh_map)

    def _create_legend_frame(self):
        self.legend_display_frame = tk.Frame(self.map_frame)
        self.legend_display_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=(5, 0))

    def _create_date_widgets(self):
        today = datetime.date.today()
        row = self._next_row("date")
        tk.Label(self.root, text="Start/End Date (YYYY-MM-DD):").grid(row=row, column=0, padx=10, pady=5)
        self.date_frame = tk.Frame(self.root)
        self.date_frame.grid(row=row, column=1, columnspan=6, padx=20, pady=5, sticky="w")
        self.start_var, self.end_var, self.start_date, self.end_date = self._make_date_entries(self.date_frame, today)

    def _make_date_entries(self, frame, today):
        tk.Label(frame, text="Start").grid(row=0, column=0, padx=(0, 2))
        start_var = tk.StringVar()
        start_date = DateEntry(frame, textvariable=start_var, date_pattern="yyyy-mm-dd", width=12, maxdate=today)
        start_date.grid(row=0, column=1, padx=(0, 8))
        tk.Label(frame, text="End").grid(row=0, column=4, padx=(0, 2))
        end_var = tk.StringVar()
        end_date = DateEntry(frame, textvariable=end_var, date_pattern="yyyy-mm-dd", width=12, maxdate=today)
        end_date.grid(row=0, column=5, padx=(0, 2))
        start_var.set("")
        end_var.set("")
        return start_var, end_var, start_date, end_date

    def _create_flight_dir_widgets(self):
        row = self._next_row("flight_dir")
        self.flight_dir_var = tk.StringVar(value="DESCENDING")
        tk.Label(self.root, text="Flight Direction:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
        flight_dir_frame = tk.Frame(self.root)
        flight_dir_frame.grid(row=row, column=1, columnspan=2, padx=10, pady=5, sticky="w")
        self.ascending_rb = tk.Radiobutton(flight_dir_frame, text="Ascending", variable=self.flight_dir_var, value="ASCENDING")
        self.ascending_rb.pack(side="left", padx=(0, 10))
        self.descending_rb = tk.Radiobutton(flight_dir_frame, text="Descending", variable=self.flight_dir_var, value="DESCENDING")
        self.descending_rb.pack(side="left")
        self.flight_dir_frame = flight_dir_frame

    def _create_data_folder_widgets(self):
        row = self._next_row("data_folder")
        tk.Label(self.root, text="Select Data Folder:").grid(row=row, column=0, padx=10, pady=5)
        self.data_folder_entry = tk.Entry(self.root, width=50)
        self.data_folder_entry.grid(row=row, column=1, padx=10, pady=5)
        self.data_browse = tk.Button(self.root, text="Load", command=self._load_and_update)
        self.data_browse.grid(row=row, column=2, padx=10, pady=5)
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
        self.data_query_btn = tk.Button(
            self.root, text="Data Query",
            command=self._on_data_query_callback,
            state="disabled"
        )
        self._action_btn_row = self._next_row("action_btns")

    def _bind_events(self):
        for entry in (self.n_entry, self.s_entry, self.e_entry, self.w_entry):
            for event in ("<KeyRelease>", "<FocusOut>", "<Return>", "<Tab>", "<Shift-Tab>"):
                entry.bind(event, self._try_draw_from_entries, add="+")
                entry.bind(event, self._enforce_extent_limits, add="+")
                entry.bind(event, self._update_data_query_btn_state, add="+")
        self.root.bind_all("<Button-1>", self._enforce_extent_limits, add="+")
        self.root.bind_all("<Button-1>", self._try_draw_from_entries, add="+")
        for widget in (self.start_date, self.end_date):
            for event in ("<<DateEntrySelected>>", "<FocusOut>", "<Return>","<KeyRelease>", "<Tab>", "<Shift-Tab>"):
                widget.bind(event, self._validate_dates, add="+")
                widget.bind(event, self._enforce_date_limits, add="+")
                widget.bind(event, self._on_data_folder_change, add="+")
        for event in ("<Return>", "<Tab>", "<Shift-Tab>"):
            self.data_folder_entry.bind(event, self._on_data_folder_change, add="+")
        self.root.after(200, self._try_auto_draw)
        self.root.after(100, self._update_data_query_btn_state)

    # --- Validation and Entry Helpers ---
    def _validate_float(self, P):
        if P in ("", "-", "."): return True
        try: float(P); return True
        except ValueError: return False

    def _validate_path_syntax(self, *_):
        folder = self.data_folder_entry.get().strip()
        self.data_browse.config(state="normal")
        if folder and not os.path.exists(folder):
            self.data_folder_entry.config(bg="#ffcccc")
        else:
            self.data_folder_entry.config(bg="white")

    def _try_draw_from_entries(self, _=None):
        try:
            n, s, e, w = map(float, (self.n_entry.get(), self.s_entry.get(), self.e_entry.get(), self.w_entry.get()))
            if n > s and e > w:
                self._draw_rectangle_on_map(s, w, n, e)
        except ValueError:
            pass

    def _try_auto_draw(self):
        if all(entry.get() for entry in (self.n_entry, self.s_entry, self.e_entry, self.w_entry)):
            self._try_draw_from_entries()

    def _validate_dates(self, _=None):
        today = datetime.date.today()
        default_start = today - datetime.timedelta(days=30)
        st, en = self.start_var.get(), self.end_var.get()
        try: st = datetime.datetime.strptime(st, "%Y-%m-%d").date()
        except ValueError: st = default_start; self.start_var.set(st.strftime("%Y-%m-%d"))
        try: en = datetime.datetime.strptime(en, "%Y-%m-%d").date()
        except ValueError: en = today; self.end_var.set(en.strftime("%Y-%m-%d"))
        if st > today: st = today; self.start_var.set(st.strftime("%Y-%m-%d"))
        if en > today: en = today; self.end_var.set(en.strftime("%Y-%m-%d"))
        if st > en:
            widget = self.root.focus_get()
            if widget == self.start_date: en = st; self.end_var.set(en.strftime("%Y-%m-%d"))
            else: st = en; self.start_var.set(st.strftime("%Y-%m-%d"))

    def _enforce_extent_limits(self, _=None):
        if all(v is not None for v in self.extent_limits.values()):
            try:
                n = clamp(self.n_entry.get(), self.extent_limits["s"], self.extent_limits["n"])
                s = clamp(self.s_entry.get(), self.extent_limits["s"], self.extent_limits["n"])
                e = clamp(self.e_entry.get(), self.extent_limits["w"], self.extent_limits["e"])
                w = clamp(self.w_entry.get(), self.extent_limits["w"], self.extent_limits["e"])
                if n < s: n, s = s, n
                if e < w: e, w = w, e
                for entry, val in zip([self.n_entry, self.s_entry, self.e_entry, self.w_entry], [n, s, e, w]):
                    entry.delete(0, tk.END)
                    entry.insert(0, str(round(val, 6)))
            except Exception:
                pass

    def _enforce_date_limits(self, _=None):
        sdate = self.date_limits.get("sdate")
        edate = self.date_limits.get("edate")
        if sdate and edate:
            if self.start_var.get():
                st = datetime.datetime.strptime(self.start_var.get(), "%Y-%m-%d").date()
            else:
                st = sdate
            if self.end_var.get():
                en = datetime.datetime.strptime(self.end_var.get(), "%Y-%m-%d").date()
            else:
                en = edate
            if st < sdate: st = sdate
            if st > edate: st = edate
            if en < sdate: en = sdate
            if en > edate: en = edate
            if st > en: st = en
            self.start_var.set(st.strftime("%Y-%m-%d"))
            self.end_var.set(en.strftime("%Y-%m-%d"))

    def _update_data_query_btn_state(self, *_):
        entries = [self.n_entry.get(), self.s_entry.get(), self.e_entry.get(), self.w_entry.get()]
        valid = False
        if all(entries):
            try:
                n, s, e, w = map(float, entries)
                valid = (n > s) and (e > w)
            except ValueError:
                pass
        if self.data_query_btn is not None and self.data_query_btn.winfo_exists():
            if self.data_browse.cget("bg") == "red":
                self.data_query_btn.config(state="normal" if valid else "disabled")
                self.show_query_btn()
            else:
                self.hide_query_btn()

    # --- Map and Polygon Helpers ---
    def _draw_rectangle_on_map(self, s, w, n, e):
        if self.rect_shape[0]:
            self.rect_shape[0].delete()
        self.rect_shape[0] = self.map_widget.set_path(
            [(n, w), (n, e), (s, e), (s, w), (n, w)], color="red", width=2
        )
        if not hasattr(self, "_red_rect_zoomed") or self.data_browse.cget("bg") != "red":
            self.map_widget.set_position((n + s) / 2, (e + w) / 2)
            max_diff = max(abs(n - s), abs(e - w))
            zoom = 15 if max_diff < 0.0001 else int(max(2, min(15, 8 - math.log(max_diff + 1e-6, 2))))
            self.map_widget.set_zoom(zoom)
            if self.data_browse.cget("bg") == "red":
                self._red_rect_zoomed = True
        elif self.data_browse.cget("bg") != "red":
            if hasattr(self, "_red_rect_zoomed"):
                del self._red_rect_zoomed

    def _update_extent_entries_from_map(self, bounds):
        s, w, n, e = bounds
        for entry, val in zip([self.n_entry, self.s_entry, self.w_entry, self.e_entry], [n, s, w, e]):
            entry.delete(0, tk.END)
            entry.insert(0, str(round(val, 6)))
        self._draw_rectangle_on_map(s, w, n, e)

    def _on_map_click_with_limits(self, coords):
        lat, lon = coords
        if all(v is not None for v in self.extent_limits.values()):
            lat = min(max(lat, self.extent_limits["s"]), self.extent_limits["n"])
            lon = min(max(lon, self.extent_limits["w"]), self.extent_limits["e"])
        if not hasattr(self, "_map_click_start"):
            self._map_click_start = (lat, lon)
        else:
            lat0, lon0 = self._map_click_start
            lat1, lon1 = lat, lon
            if all(v is not None for v in self.extent_limits.values()):
                lat0 = min(max(lat0, self.extent_limits["s"]), self.extent_limits["n"])
                lon0 = min(max(lon0, self.extent_limits["w"]), self.extent_limits["e"])
                lat1 = min(max(lat1, self.extent_limits["s"]), self.extent_limits["n"])
                lon1 = min(max(lon1, self.extent_limits["w"]), self.extent_limits["e"])
            n, s = max(lat0, lat1), min(lat0, lat1)
            e, w = max(lon0, lon1), min(lon0, lon1)
            self._update_extent_entries_from_map((s, w, n, e))
            del self._map_click_start

    def _on_map_click_with_limits_and_update(self, coords):
        self._on_map_click_with_limits(coords)
        self.root.after(200, self._update_data_query_btn_state)

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
        threading.Thread(target=lambda: self.root.after(0, self._highlight_polygon, idx)).start()
        result = getattr(self.on_data_query, "last_result", None)
        if result and idx < len(result):
            self.selected_urls = result[idx].get('urls')
            self.total_expected_size = result[idx].get('total_expected_size')
        else:
            self.selected_urls = None
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
            self.root.after(0, update_gui)
        threading.Thread(target=run_query).start()

    def _show_data_download_btn(self):
        self.show_download_btn()
        if self.data_browse.cget("bg") != "green":
            self.data_download_btn.config(state="normal")
        else:
            self.data_download_btn.config(state="disabled")

    def _get_aoi_wkt(self):
        try:
            n, s, e, w = map(float, (self.n_entry.get(), self.s_entry.get(), self.e_entry.get(), self.w_entry.get()))
            coords = [(w, s), (e, s), (e, n), (w, n), (w, s)]
            return "POLYGON((" + ",".join(f"{x} {y}" for x, y in coords) + "))"
        except Exception:
            return None

    def _run_data_download(self):
        self.download_in_progress = True
        urls = self.selected_urls if self.selected_urls is not None else []
        folder = self.data_folder_entry.get().strip()
        total_expected_size = self.total_expected_size if self.total_expected_size is not None else 0
        if not urls:
            messagebox.showinfo("Download", "No files selected for download.")
            return

        # Disable controls and remove query/download buttons
        self._set_controls_state("disabled")
        if hasattr(self, "data_query_btn") and self.data_query_btn is not None and self.data_query_btn.winfo_exists():
            self.data_query_btn.grid_remove()
            self.data_query_btn.destroy()
        self.hide_download_btn()
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
                    return f"{num_bytes/1024:.2f} KB"
                elif num_bytes < 1024**3:
                    return f"{num_bytes/1024**2:.2f} MB"
                else:
                    return f"{num_bytes/1024**3:.2f} GB"
            def format_speed(bytes_per_sec):
                bytes_per_sec = float(bytes_per_sec)
                if bytes_per_sec < 1024:
                    return f"{bytes_per_sec:.2f} B/s"
                elif bytes_per_sec < 1024**2:
                    return f"{bytes_per_sec/1024:.2f} KB/s"
                elif bytes_per_sec < 1024**3:
                    return f"{bytes_per_sec/1024**2:.2f} MB/s"
                else:
                    return f"{bytes_per_sec/1024**3:.2f} GB/s"
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
                    "Downloaded": format_bytes(stats.get("total_downloaded", 0)),
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

        def run_download():
            error = None
            self._download_completed = False
            self._download_error = None
            self._last_stats = {}

            def progress_callback(stats):
                self.root.after(0, lambda: update_stats(stats))
                self._last_stats = stats

            try:
                download_sentinel1_acquisitions(
                    urls, folder, total_expected_size,
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
                    messagebox.showerror("Download Failed", f"Download failed or incomplete. All downloaded zip files have been deleted.\n\n{error if error else 'Incomplete download.'}")
                else:
                    self.data_folder_entry.config(state="normal")
                    self.data_browse.config(state="normal")
                    self._on_data_folder_change()
                    self.hide_download_stats()
            self.root.after(0, after_download)

        self.download_thread = threading.Thread(target=run_download, daemon=True)
        self.download_thread.start()

    def _init_download_stats_labels(self):
        base_row = self._action_btn_row-2
        if hasattr(self, "download_stats_frame") and self.download_stats_frame:
            self.download_stats_frame.destroy()
        if not hasattr(self, "pause_btn") or not self.pause_btn:
            self._add_pause_button(base_row)
        else:
            # If it exists, just re-grid it (don't destroy/recreate)
            self.pause_btn.grid(row=base_row, column=5, padx=10, pady=5, sticky="e")
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
        self.ascending_rb.config(state=state)
        self.descending_rb.config(state=state)

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

        # Try to create folder if not exists
        if not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create folder: {e}")
                self._set_data_browse_bg(bg)
                self._set_controls_state("disabled")
                self.hide_query_btn()
                self.hide_download_btn()
                return

        safe_dirs, zip_files = self._get_safe_and_zip_files(folder)
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

        if safe_dirs:
            self._handle_safe_dirs_found(folder, safe_dirs, dir_pol_summary, zip_pol_summary)
            return

        if zip_files and not safe_dirs and not getattr(self, "zip_prompted", False):
            self._handle_zip_files_found(folder, zip_files, zip_pol_summary)
            return

        self.zip_prompted = False

        if not safe_dirs and not zip_files:
            self._set_data_browse_bg("red")
            self.show_query_btn()
            self._update_data_query_btn_state("normal")
            self._set_controls_state("normal")
            self._clear_extent_and_date_labels()
            self.hide_download_btn()
            self._clear_dynamic_widgets_and_shapes()
            self._setup_subswath_controls(None, None)
            self._setup_polarization_controls(None, None)
            self._show_output_folder_and_project_controls()

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
        tk.Label(self.subswath_frame, text="Subswaths:").pack(side="left", padx=(0, 6))

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
            "total_imgs_label", "sub_imgs_label", "dem_entry", "dwn_dem", "browse_dem", "dem_label"
        ]
        for attr in attrs:
            widget = getattr(self, attr, None)
            if widget is not None and hasattr(widget, "destroy") and widget.winfo_exists():
                widget.destroy()
            setattr(self, attr, None)
        if self.custom_shape:
            self.custom_shape.delete()
            self.custom_shape = None
        if self.rect_shape[0]:
            self.rect_shape[0].delete()
            self.rect_shape[0] = None
        for poly in getattr(self.on_data_query, "polygons", []):
            poly.delete()
        self.on_data_query.polygons = []
        self.extent_limits.update(dict.fromkeys("swne"))
        self.date_limits.update({"sdate": None, "edate": None})

    def _set_data_browse_bg(self, color):
        self.data_browse.config(bg=color, activebackground=color)

    def _get_safe_and_zip_files(self, folder):
        pattern = "S1*_IW_SLC__1S*_*"
        safe_dirs = [
            os.path.join(root, d)
            for root, dirs, _ in os.walk(folder)
            for d in dirs
            if d.endswith('.SAFE') and fnmatch.fnmatch(d, pattern)
        ]
        zip_files = [
            os.path.join(root, f)
            for root, _, files in os.walk(folder)
            for f in files
            if f.lower().endswith('.zip') and fnmatch.fnmatch(f, pattern)
        ]
        exclude_pol = {"HH", "VV", "VH", "HV"}
        safe_dirs = [x for x in safe_dirs if len(os.path.basename(x)) < 16 or os.path.basename(x)[14:16] not in exclude_pol]
        zip_files = [x for x in zip_files if len(os.path.basename(x)) < 16 or os.path.basename(x)[14:16] not in exclude_pol]
        return safe_dirs, zip_files

    def _summarize_polarizations_from_files(self, file_list):
        pol_map = {
            'SV': ['VV'],
            'DV': ['VV', 'VH'],
            'DH': ['HH', 'HV'],
            'SH': ['HH']
        }
        summary = {'VV': 0, 'VH': 0, 'HH': 0, 'HV': 0}
        type2_found = False
        pol_dir_groups = {}
        for x in file_list:
            base = os.path.basename(x)
            dir_path = os.path.dirname(x)
            if len(base) >= 15 and base[12:14] in ['vv', 'vh', 'hh', 'hv']:
                type2_found = True
                pol = base[12:14].upper()
                key = dir_path
                pol_dir_groups.setdefault(key, set()).add(pol)
        if type2_found:
            for pol_set in pol_dir_groups.values():
                for pol in pol_set:
                    if pol in summary:
                        summary[pol] += 1
            summary = {k: v for k, v in summary.items() if v != 0}
            return summary
        for x in file_list:
            base = os.path.basename(x)
            if len(base) >= 16 and base[14:16] in pol_map:
                pol = base[14:16]
                for p in pol_map.get(pol, []):
                    summary[p] += 1
        summary = {k: v for k, v in summary.items() if v != 0}
        return summary

    def _handle_safe_dirs_found(self, folder, safe_dirs, dir_pol_summary, zip_pol_summary):
        self._set_data_browse_bg("green")
        self._set_controls_state("normal")
        self._setup_subswath_controls(safe_dirs, zip_files=None)
        self._setup_polarization_controls(dir_pol_summary, zip_pol_summary)
        if hasattr(self, "data_query_btn") and self.data_query_btn is not None and self.data_query_btn.winfo_exists():
            self.hide_query_btn()
        self.hide_download_btn()

        max_bounds, sdate, edate, fdirection = extr_ext_TL(folder)
        if max_bounds:
            self._draw_custom_shape_and_labels(max_bounds)
        if sdate:
            self.date_limits["sdate"] = sdate
            self.sdate_label = tk.Label(self.date_frame, text=sdate, fg="green")
            self.sdate_label.grid(row=0, column=2, sticky="w", padx=(4, 0))
        if edate:
            self.date_limits["edate"] = edate
            self.edate_label = tk.Label(self.date_frame, text=edate, fg="green")
            self.edate_label.grid(row=0, column=6, sticky="w", padx=(4, 0))
        if fdirection:
            self.flight_dir_var.set(fdirection)
            self.ascending_rb.config(state="disabled")
            self.descending_rb.config(state="disabled")
        self.safe_dirs_label = tk.Label(self.root, text=f"{len(safe_dirs)} imgs found", fg="green")
        self.safe_dirs_label.grid(row=self._get_row("data_folder"), column=3, sticky="w", padx=(0, 2))

        if sdate and edate:
            self.total_imgs_label = tk.Label(self.date_frame, text=f"Total IMGs: {len(safe_dirs)}", fg="green")
            self.total_imgs_label.grid(row=0, column=7, sticky="w", padx=(8, 0))

        stack = inspect.stack()
        called_from_browse = any("self._load_and_update" in frame.function or "load_and_update" in frame.function for frame in stack)

        if called_from_browse and sdate and edate:
            self.start_var.set(sdate)
            self.end_var.set(edate)
            st = sdate
            en = edate
        else:
            st = self.start_var.get()
            en = self.end_var.get()

        if st and en:
            st = str(st)
            en = str(en)
            sub_safe_dirs = subset_safe_dirs(safe_dirs, st, en)
            self.sub_imgs_label = tk.Label(self.date_frame, text=f"Total IMGs: {len(sub_safe_dirs)}", fg="black")
            self.sub_imgs_label.grid(row=0, column=8, sticky="w", padx=(8, 0))

        if not hasattr(self, "dem_entry") or self.dem_entry is None:
            self._show_dem_entry_and_browse()

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
            self._update_extent_entries_from_map((s, w, n, e))

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
            else:
                self.browse_dem.config(background=self.DEFAULT_BROWSE_BG, activebackground=self.DEFAULT_BROWSE_BG)
                if hasattr(self, "dwn_dem") and self.dwn_dem.winfo_exists():
                    self.dwn_dem.config(state="normal")

    def _setup_polarization_controls(self, dir_pol_summary=None, zip_pol_summary=None):
        if dir_pol_summary and zip_pol_summary:
            zip_pol_summary = None
        row = self._get_row("data_folder") + 1

        # Remove existing controls first
        self._remove_pol_controls()

        # If no summary, just return
        if not dir_pol_summary and not zip_pol_summary:
            return

        # Get polarization counts from either summary
        pol_counts = {pol: (dir_pol_summary.get(pol, 0) if dir_pol_summary else 0) or (zip_pol_summary.get(pol, 0) if zip_pol_summary else 0) for pol in ["VV", "VH", "HH", "HV"]}
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
        tk.Label(self.pol_frame, text="Polarization:").pack(side="left", padx=(0, 6))
        # Always create a new StringVar for polarization selection
        self.pol_var = tk.StringVar(value=enabled_pols[0] if enabled_pols else "VV")
        # If only one polarization is available, show it as disabled
        if len(enabled_pols) == 1:
            pol = enabled_pols[0]
            frame = tk.Frame(self.pol_frame)
            rb = tk.Radiobutton(frame, text=pol, variable=self.pol_var, value=pol, state="disabled")
            rb.pack(side="left")
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
        self.dem_entry.grid(row=row, column=1, padx=10, pady=5, sticky="w") 

        self.browse_dem = tk.Button(
            self.root,
            text="Load",
            command=self.on_browse_dem,
        )
        self.browse_dem.grid(row=row, column=2, padx=10, pady=5, sticky="w")

        self.dwn_dem = tk.Button(
            self.root,
            text="Download",
            command=self.on_dem_download
        )
        self.dwn_dem.grid(row=row, column=3, padx=10, pady=5, sticky="w")        

        # Bind dem_entry changes to update controls
        self.dem_entry.bind("<KeyRelease>", self.update_dem_controls)
        self.dem_entry.bind("<FocusOut>", self.update_dem_controls)
        self.update_dem_controls()

    def show_confirm_btn_if_ready(self, event=None):
        out_folder = self.output_folder_entry.get().strip()
        proj_name = self.project_name_entry.get().strip()
        if out_folder and proj_name:
            self.confirm_config_btn.config(state="normal")
            self.confirm_config_btn.grid()
            self.gacos_btn.config(state="normal")
            self.gacos_btn.grid()
        else:
            self.confirm_config_btn.grid_remove()
            self.gacos_btn.grid_remove()


    def _show_output_folder_and_project_controls(self):
        # Destroy output_controls_frame if dem_entry does not exist
        if not hasattr(self, "dem_entry") or self.dem_entry is None:
            if hasattr(self, "output_controls_frame") and self.output_controls_frame:
                self.output_controls_frame.destroy()
                self.output_controls_frame = None
            return

        # Only show if DEM entry is valid or Load button is green
        dem_path = self.dem_entry.get().strip()
        self.dem_path = dem_path
        dem_valid = dem_path and os.path.exists(dem_path)
        load_green = hasattr(self, "browse_dem") and self.browse_dem is not None and self.browse_dem.cget("background") == "green"
        if not (dem_valid or load_green):
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
        tk.Label(self.output_controls_frame, text="Output Folder:").grid(row=0, column=0, padx=(0, 4), sticky="w")
        self.output_folder_entry = tk.Entry(self.output_controls_frame, width=30)
        self.output_folder_entry.grid(row=0, column=1, padx=(0, 4), sticky="w")
        def on_browse_output():
            browse_folder(self.output_folder_entry, "output_folder")
        self.output_folder_browse = tk.Button(
            self.output_controls_frame, text="Browse", command=on_browse_output
        )
        self.output_folder_browse.grid(row=0, column=2, padx=(0, 8), sticky="w")
        # Project Name
        tk.Label(self.output_controls_frame, text="Project Name:").grid(row=0, column=3, padx=(0, 4), sticky="w")
        self.project_name_entry = tk.Entry(self.output_controls_frame, width=20)
        self.project_name_entry.grid(row=0, column=4, padx=(0, 4), sticky="w")

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

        # Confirm Configuration button (initially hidden)
        self.confirm_config_btn = tk.Button(
            self.output_controls_frame,
            text="Confirm Configuration",
            command=lambda: self._on_confirm_configuration(),
            state="disabled"
        )
        self.confirm_config_btn.grid(row=0, column=6, padx=(8, 0), sticky="w")
        self.confirm_config_btn.grid_remove()
        
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
            outdir = self.output_folder_entry.get().strip()
            indir = os.path.join(outdir, self.project_name_entry.get().strip(), os.listdir(outdir)[0],"raw")
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
        self._create_TS_steps_buttons()
        out_folder = self.output_folder_entry.get().strip()
        proj_name = self.project_name_entry.get().strip()
        if out_folder and proj_name:
            full_path = os.path.join(out_folder, proj_name)
            try:
                os.makedirs(full_path, exist_ok=True)
            except Exception:
                return            
            self.confirm_config_btn.config(state="disabled")
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
        outdir = os.path.join(self.output_folder_entry.get().strip(), self.project_name_entry.get().strip())
        flight_dir = self.flight_dir_var.get().lower()
        if flight_dir == "descending":
            xdir = "des"
        elif flight_dir == "ascending":
            xdir = "asc"
        maindir = os.path.join(outdir, xdir)
        def process_files_thread():        
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
                

        # Create BaselineGUI and pass the callback
        BaselineGUI(baseline_window, self.dem_path, self.paths, on_edges_exported=on_edges_exported)

    def _create_TS_steps_buttons(self):
        """Create buttons for TS steps after orbits download."""
        row = self._next_row("ts_steps_frame")

        # Create a frame to hold all 4 buttons in a single row, side by side
        ts_steps_frame = tk.Frame(self.root)
        ts_steps_frame.grid(row=row, column=0, columnspan=8, padx=10, pady=10, sticky="w")

        
        self.download_orbit_btn = tk.Button(
            ts_steps_frame, 
            text="00_Download Orbit Files", 
            width=16, 
            command=self.on_next_step
        )
        self.download_orbit_btn.pack(side="left", padx=8)       

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
        self.align_intf_gen_btn = tk.Button(
            ts_steps_frame,
            text="02_Align imgs & Gen. INTFs",
            state="disabled",
            command=self._process_02
        )
        self.unwrap_btn = tk.Button(
            ts_steps_frame,
            text="03_Unwrap INTFs",
            state="disabled",
            command=self._show_unwrap_app
        )
        self.inversion_btn = tk.Button(
            ts_steps_frame,
            text="04_SBAS",
            state="disabled",
            command=self._show_sbas_app
        )

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
                    if check_align_completion(subswath):
                        print(f"Alignment completed successfully for {subswath}")
                    else:
                        print(f"Alignment not completed successfully for {subswath}")
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

        UnwrapApp(self.unwrap_window, self.ifgsroot, self.IFGs, self.gacos_data_path)
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
        self.sbas_window = tk.Toplevel(self.root)
        SBASApp(self.sbas_window, self.paths, ifgsroot, IFGs, gacosdir)
        self.sbas_window.wait_window()
        # Set 04_SBAS button to green and disabled
        if hasattr(self, "inversion_btn") and self.inversion_btn.winfo_exists():
            self.inversion_btn.config(state="disabled", bg="green", activebackground="green")

    def _handle_zip_files_found(self, folder, zip_files, zip_pol_summary):
        self.zip_prompted = True
        self._set_data_browse_bg("yellow")
        prev_folder = folder

        # Setup controls for user to select subswaths and polarization
        self._setup_polarization_controls(dir_pol_summary=None, zip_pol_summary=zip_pol_summary)
        self._setup_subswath_controls(safe_dirs=None, zip_files=zip_files)        

        # Extraction button reference
        self._extract_btn = None

        # Flag to block all further actions until extraction completes
        self._extraction_in_progress = False

        def extract_zip_files_thread(selected_subswaths, selected_pol):
            try:
                tiff_pattern = re.compile(
                    r"s1[ab]-iw(?P<subswath>[123])-slc-(?P<polarization>vv|vh|hh|hv)-\d{8}t\d{6}-\d{8}t\d{6}-\d{6}-[0-9a-f]{6}-\d{3}\.tiff$",
                    re.IGNORECASE
                )
                for zip_path in zip_files:
                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        safe_dirs_in_zip = [name for name in zf.namelist() if name.endswith('.SAFE/') and '/' not in name.rstrip('/').split('/')[-2:]]
                        if not safe_dirs_in_zip:
                            continue
                        safe_dir = safe_dirs_in_zip[0].rstrip('/')                        
                        # Extract all except measurement/*.tiff first
                        for member in zf.namelist():
                            if member.startswith(safe_dir + '/measurement/') and member.lower().endswith('.tiff'):
                                continue
                            out_path = os.path.join(prev_folder, member)
                            if member.endswith('/'):
                                os.makedirs(out_path, exist_ok=True)
                            else:
                                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                                with zf.open(member) as src, open(out_path, 'wb') as dst:
                                    print(f"Extracting {member} to {out_path}")
                                    shutil.copyfileobj(src, dst)
                        # Now extract only selected tiffs
                        for member in zf.namelist():
                            if member.startswith(safe_dir + '/measurement/') and member.lower().endswith('.tiff'):
                                fname = os.path.basename(member)
                                m = tiff_pattern.match(fname)
                                if not m:
                                    continue
                                subswath_num = int(m.group("subswath"))
                                pol = m.group("polarization").lower()
                                if subswath_num in selected_subswaths and pol == selected_pol:
                                    out_path = os.path.join(prev_folder, member)
                                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                                    with zf.open(member) as src, open(out_path, 'wb') as dst:
                                        print(f"Extracting {member} to {out_path}")
                                        shutil.copyfileobj(src, dst)
                safe_dirs_after = [os.path.join(prev_folder, f) for f in os.listdir(prev_folder) if f.endswith('.SAFE')]
                def after_extraction():
                    self._extraction_in_progress = False
                    if safe_dirs_after:
                        self.data_folder_entry.delete(0, tk.END)
                        self.data_folder_entry.insert(0, prev_folder)
                        self.data_browse.config(state="normal", bg="green", activebackground="green")
                        setattr(self, "zip_prompted", False)
                        self.hide_extract_btn()
                        self._on_data_folder_change()
                    else:
                        handle_prompt(edit_mode=True)
                        self.fail_prompt()
                self.root.after(0, after_extraction)
            except Exception:
                def after_fail():
                    self._extraction_in_progress = False
                    self.fail_prompt()
                self.root.after(0, after_fail)

        def on_start_extraction():
            if self._extraction_in_progress:
                return
            self._extraction_in_progress = True
            if self._extract_btn:
                self._extract_btn.config(state="disabled")
            self.data_browse.config(state="disabled")
            self.data_folder_entry.config(state="disabled")
            # Block all events in the root window except extraction
            self.root.grab_set()
            selected_subswaths = self.get_selected_subswaths()
            selected_pol = self.pol_var.get().lower()
            thread = threading.Thread(target=extract_zip_files_thread, args=(selected_subswaths, selected_pol), daemon=True)
            thread.start()
            # thread.join()

        def show_extract_btn():
            # Place the Start Extraction button below the Load button
            row = self._get_row("data_folder")
            if hasattr(self, "_extract_btn") and self._extract_btn:
                self._extract_btn.destroy()
            self._extract_btn = tk.Button(self.root, text="Start Extraction", command=on_start_extraction)
            self._extract_btn.grid(row=row, column=3, padx=10, pady=5, sticky="w")
            self._extract_btn.lift()

        def hide_extract_btn():
            if hasattr(self, "_extract_btn") and self._extract_btn:
                self._extract_btn.grid_remove()
                self._extract_btn.destroy()
                self._extract_btn = None
            # Release grab if held
            try:
                self.root.grab_release()
            except Exception:
                pass

        # Attach to self for use in thread
        self.hide_extract_btn = hide_extract_btn

        def handle_prompt(edit_mode=False):
            def on_extract():
                prompt.destroy()
                self.data_browse.config(state="disabled")
                show_extract_btn()
                # Do not start extraction yet; wait for Start Extraction button
            def on_edit():
                prompt.destroy()
                self.data_folder_entry.delete(0, tk.END)
                self.data_folder_entry.config(state="normal")
                self.data_browse.config(state="normal", bg=self.DEFAULT_BROWSE_BG, activebackground=self.DEFAULT_BROWSE_BG)
                setattr(self, "zip_prompted", False)
                hide_extract_btn()
                self._on_data_folder_change()
                # Disable controls if entry is empty                
                self._set_controls_state("disabled")
            prompt = tk.Toplevel(self.root)
            prompt.title("Zip Files Detected")
            tk.Label(prompt, text="Zip files detected in the folder.\nSelect subswaths and polarization, then extract or edit the path.").pack(padx=20, pady=10)
            btn_frame = tk.Frame(prompt)
            btn_frame.pack(pady=10)
            extract_btn = tk.Button(btn_frame, text="Extract", width=10, command=lambda: [extract_btn.config(state="disabled"), on_extract()])
            extract_btn.pack(side="left", padx=5)
            tk.Button(btn_frame, text="Edit Path", command=on_edit, width=10).pack(side="left", padx=5)
            prompt.transient(self.root)
            prompt.grab_set()
            if edit_mode:
                self.root.after(0, on_edit)
            prompt.wait_window()

        handle_prompt()        

    def _load_and_update(self):
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
        self._validate_dates()  # Ensure dates are validated and UI updated
        self._enforce_date_limits()  # Ensure dates are clamped to limits
        self._on_data_folder_change()

def main():
    root = tk.Tk()
    InSARLiteApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
