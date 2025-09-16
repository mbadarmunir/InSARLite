import os
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox
from multiprocessing.pool import ThreadPool

from ..gmtsar_gui.mask import GrdViewer
from ..gmtsar_gui.ref_point import ReferencePointGUI
from ..gmtsar_gui.gacos_atm_corr import gacos
from ..utils.utils import execute_command


class UnwrapApp(tk.Frame):
    def __init__(self, parent, ifgsroot, ifgs, gacosdir):
        super().__init__(parent)
        parent.title("UnwrapApp")
        parent.geometry("400x400")
        self.ifgsroot = ifgsroot
        self.ifgs = ifgs
        self.gacosdir = gacosdir
        self.topodir = self.ifgsroot if os.path.basename(self.ifgsroot) == "merge" else os.path.join(os.path.dirname(self.ifgsroot), "topo")

        self._init_widgets()
        self.pack(fill="both", expand=True)

    def _init_widgets(self):
        self.btn_mask = tk.Button(self, text="Define Mask", command=self.define_mask)
        self.btn_mask.pack(pady=10)

        self.btn_ref = tk.Button(self, text="Define Reference Point", command=self.define_reference_point, state=tk.DISABLED)
        self.btn_ref.pack(pady=10)

        self.controls_frame = tk.Frame(self)
        self.controls_frame.pack(pady=10, fill="x")

        self.controls_inner_frame = None
        self.corr_label = None
        self.corr_entry = None
        self.cores_label = None
        self.cores_entry = None
        self.cores_var = None
        self.inc_label = None
        self.inc_entry = None
        self.inc_var = None
        self.unwrap_btn = None
        self._controls_packed = False

    def _set_button_state(self, mask_exists):
        self.btn_mask.config(bg="green" if mask_exists else "red", state=tk.DISABLED)
        self.btn_ref.config(state=tk.NORMAL)

    def define_mask(self):
        mask_path = os.path.join(self.ifgsroot, "mask_def.grd")
        grd_file = os.path.join(self.ifgsroot, "corr_stack.grd")

        if os.path.exists(mask_path):
            use_existing = messagebox.askyesno(
                "Mask Exists",
                "A mask already exists. Do you want to use the existing mask?\n\nYes: Use existing\nNo: Recreate",
                parent=self.winfo_toplevel()
            )
            self._focus_window()
            if use_existing:
                self._set_button_state(True)
                return
            recreate = messagebox.askyesno(
                "Recreate Mask",
                "Are you sure you want to delete the existing mask and create a new one?",
                parent=self.winfo_toplevel()
            )
            self._focus_window()
            if recreate:
                try:
                    os.remove(mask_path)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not delete mask: {e}", parent=self.winfo_toplevel())
                    self._focus_window()
                    return
                viewer = GrdViewer(self.winfo_toplevel(), grd_file)  # pass parent
                self.wait_window(viewer)            # pause execution until viewer is destroyed
                self._set_button_state(os.path.exists(mask_path))
                # self._set_button_state(os.path.exists(mask_path))
        else:
            answer = messagebox.askyesno("Define Mask", "Do you want to create/define a mask?", parent=self.winfo_toplevel())
            self._focus_window()
            if answer:
                viewer = GrdViewer(self.winfo_toplevel(), grd_file)  # pass parent
                self.wait_window(viewer)            # pause execution until viewer is destroyed
                self._set_button_state(os.path.exists(mask_path))
            else:
                self._set_button_state(False)
                # self._set_button_state(os.path.exists(mask_path))
        # self._set_button_state(os.path.exists(mask_path))

    def define_reference_point(self):
        topodir = self.topodir
        dem = os.path.join(topodir, "dem.grd")
        ra_file = os.path.join(topodir, "ref_point.ra")
        self.btn_ref.config(state=tk.DISABLED)

        if os.path.exists(ra_file):
            redefine = messagebox.askyesno(
                "Reference Point Exists",
                "A reference point is already defined. Do you want to redefine it?",
                parent=self.winfo_toplevel()
            )
            self._focus_window()
            if redefine:
                ref_window = ReferencePointGUI(self.winfo_toplevel(), dem,self.ifgsroot)
                ref_window.grab_set()
                self.wait_window(ref_window)
        else:
            ref_window = ReferencePointGUI(self.winfo_toplevel(), dem, self.ifgsroot)
            ref_window.grab_set()
            self.wait_window(ref_window)

        self.show_unwrap_controls()

    def _validate_float(self, value):
            if value == "":
                return True
            try:
                float(value)
                return True
            except ValueError:
                return False
            
    def show_unwrap_controls(self):
        self.btn_ref.config(bg="green", state=tk.DISABLED)
        if not self.controls_inner_frame:
            self.controls_inner_frame = tk.Frame(self.controls_frame)
            self.controls_inner_frame.pack(anchor="w", padx=20, pady=5, fill="x")

        # Correlation threshold
        if not self.corr_label:
            self.corr_label = tk.Label(self.controls_inner_frame, text="Correlation Threshold:")
        if not hasattr(self, 'corr_var'):
            self.corr_var = tk.StringVar(value="0.01")
        if not self.corr_entry:
            self.corr_entry = tk.Entry(self.controls_inner_frame, textvariable=self.corr_var, width=8, validate="key")
            self.corr_entry.config(validatecommand=(self.corr_entry.register(self._validate_float), '%P'))       

        # Cores
        if not self.cores_label:
            self.cores_label = tk.Label(self.controls_inner_frame, text="Cores:")
        if not self.cores_var:
            available_cores = os.cpu_count() or 1
            default_cores = max(1, available_cores - 1)
            self.cores_var = tk.StringVar(value=str(default_cores))
        if not self.cores_entry:
            self.cores_entry = tk.Entry(self.controls_inner_frame, textvariable=self.cores_var, width=5)

        # Incidence angle (only if gacosdir is not None)        
        if self.gacosdir is not None and not self.inc_label:
            self.inc_label = tk.Label(self.controls_inner_frame, text="Incidence Angle:")
            self.inc_var = tk.StringVar(value="37")
            self.inc_entry = tk.Entry(
            self.controls_inner_frame,
            textvariable=self.inc_var,
            width=8,
            validate="key"
            )
            self.inc_entry.config(validatecommand=(self.inc_entry.register(self._validate_float), '%P'))

        # Place controls
        if not self._controls_packed:
            col = 0
            self.corr_label.grid(row=0, column=col, sticky="w", padx=(0, 5), pady=2)
            col += 1
            self.corr_entry.grid(row=0, column=col, sticky="w", padx=(0, 15), pady=2)
            col += 1
            self.cores_label.grid(row=0, column=col, sticky="w", padx=(0, 5), pady=2)
            col += 1
            self.cores_entry.grid(row=0, column=col, sticky="w", pady=2)
            if self.gacosdir is not None:
                # Place incidence label and entry in next row, first and second columns
                self.inc_label.grid(row=1, column=0, sticky="w", padx=(0, 5), pady=2)
                self.inc_entry.grid(row=1, column=1, sticky="w", padx=(0, 15), pady=2)
                self._controls_packed = True

        if not self.unwrap_btn:
            self.unwrap_btn = tk.Button(self.controls_frame, text="Unwrap", command=self.run_unwrap)
            self.unwrap_btn.pack(pady=15, padx=20, anchor="w")

    def run_unwrap(self):
        threshold = self.corr_entry.get() if self.corr_entry else ""
        ncores = self.cores_var.get() if self.cores_var else 1
        incidence = None

        if not threshold:
            self._show_error("Please enter a correlation threshold.")
            return
        try:
            threshold = float(threshold)
        except ValueError:
            self._show_error("Correlation threshold must be a number.")
            return
        try:
            ncores = int(ncores)
            if ncores < 1:
                raise ValueError
        except ValueError:
            self._show_error("Number of cores must be a positive integer.")
            return

        if self.gacosdir is not None:
            incidence = self.inc_var.get()
            if not incidence:
                self._show_error("Please enter an incidence angle.")
                return
            try:
                incidence = float(incidence)
                self.incidence = incidence
            except ValueError:
                self._show_error("Incidence angle must be a float.")
                return

        self.ncores = ncores
        self.unwrap_btn.config(state=tk.DISABLED, bg="yellow")
        self.master.withdraw()

        def unwrap_worker():
            try:
                print("Starting unwrapping in parallel...")
                self.parall_unwrap(threshold, ncores)
                print("Normalizing unwrapped files...")
                self.post_unwrap(self.ifgsroot)            
                print("Starting GACOS correction...")
                self.run_gacos()
                self.master.after(0, lambda: [
                    self.unwrap_btn.config(bg="green", state=tk.NORMAL),
                    messagebox.showinfo("Unwrapping Complete", "Unwrapping process is complete.", parent=self.master),
                    self.master.destroy()
                ])
            except Exception as e:
                self.master.after(0, lambda: [
                    self.unwrap_btn.config(bg="red", state=tk.NORMAL),
                    messagebox.showerror("Unwrapping Error", f"An error occurred: {e}", parent=self.master),
                    self.master.deiconify(),
                    self.master.lift(),
                    self.master.focus_force()
                ])

        threading.Thread(target=unwrap_worker, daemon=True).start()

    def run_gacos(self):

        if None in [self.gacosdir, self.topodir, self.incidence, self.ifgsroot, self.ncores]:
            missing = [name for name, val in zip(
            ["gacosdir", "topodir", "incidence", "ifgsroot", "ncores"],
            [self.gacosdir, self.topodir, self.incidence, self.ifgsroot, self.ncores]
            ) if val is None]
            print(f"The following variables are None: {', '.join(missing)}\nUnable to perform GACOS correction")

        else:
            gacos(self.gacosdir, self.topodir, self.incidence, self.ifgsroot, self.ncores)
        

    def post_unwrap(self, ifgsroot=None):
        base_unwrap = []
        ifgsroot = self.ifgsroot if self.ifgsroot else ifgsroot
        topo_dir = self.topodir
        ref_point_ra = os.path.join(topo_dir, "ref_point.ra")
        line = None
        print(f"Reading reference point from {ref_point_ra}...")
        if os.path.exists(ref_point_ra):
            with open(ref_point_ra, 'r') as f:
                line = f.readline().strip()
        if not line:
            print("Reference point not found.")
            return

        for root, dirs, _ in os.walk(ifgsroot):
            for dirname in dirs:
                d = os.path.join(root, dirname)
                if os.path.isdir(d):
                    uwp = os.path.join(d, "unwrap.grd")
                    base_unwrap.append(uwp)

        parts = line.split()
        if len(parts) >= 2:
            x, y = parts[0], parts[1]
        else:
            x, y = None, None

        def process_unwrap(unwrap):
            out = os.path.join(os.path.dirname(unwrap), "unwrap_pin.grd")
            if not os.path.exists(out):
                try:
                    # gmt g2xyz 2023010_2023034/unwrap.grd -s >valid.txt
                    # Above is a command to see the coords of valid values i.e., not NaN
                    valid = subprocess.run(
                        ["gmt", "g2xyz", unwrap, "-s"],
                        text=True,
                        capture_output=True
                    )
                    if f"{x} {y}" not in valid.stdout:
                        print(f"Reference point ({x}, {y}) is not valid in {os.path.basename(os.path.dirname(unwrap))}. Skipping normalization.")
                        return
                    result = subprocess.run(
                        ["gmt", "grdtrack", "-G" + unwrap],
                        input=f"{x} {y}\n",
                        text=True,
                        capture_output=True,
                        check=True
                    )
                    a = float(result.stdout.strip().split()[2])                    
                    if a:
                        subprocess.run([
                            "gmt", "grdmath", str(unwrap), str(a), "SUB", "=", str(out)
                        ], check=True)
                        print(f"{os.path.basename(os.path.dirname(unwrap))} normalized through Reference Point")
                except Exception as e:
                    print(f"Error processing {unwrap}: {e}")
            else:
                print(f"{os.path.basename(os.path.dirname(unwrap))} already normalized.")

        with ThreadPool(processes=self.ncores) as pool:
            pool.map(process_unwrap, base_unwrap)

    def parall_unwrap(self, threshold, ncores):
        intfdir = self.ifgsroot
        IFGs = self.ifgs if self.ifgs else [
            os.path.join(intfdir, d)
            for d in next(os.walk(intfdir))[1]
            if os.path.exists(os.path.join(intfdir, d, 'phasefilt.grd')) and not os.path.exists(os.path.join(intfdir, d, 'unwrap.grd'))
        ]
        os.chdir(intfdir)
        mask_path = os.path.join(intfdir, "mask_def.grd")
        if os.path.exists(mask_path):
            for subdir in IFGs:
                link_path = os.path.join(subdir, "mask_def.grd")
                if not os.path.exists(link_path):
                    try:
                        os.symlink(mask_path, link_path)
                    except FileExistsError:
                        pass
        print(f"Number of IFGs to be unwrapped: {len(IFGs)}/{len(next(os.walk(intfdir))[1])}")
        if not IFGs:
            messagebox.showinfo("Unwrapping Skipped", "No IFGs to unwrap. All are already unwrapped or missing required files.", parent=self.winfo_toplevel())
            self._focus_window()
            return

        # Build unwrap commands
        unwrap_commands = []
        for i in IFGs:
            cmd = f"cd {i} && snaphu_interp.csh {threshold} 0"            
            cmd += " && cd .."
            unwrap_commands.append(cmd)

        with ThreadPool(processes=ncores) as pool:
            pool.map(execute_command, unwrap_commands)

    def _show_error(self, msg):
        messagebox.showerror("Input Error", msg, parent=self.winfo_toplevel())
        self._focus_window()

    def _focus_window(self):
        self.winfo_toplevel().lift()
        self.winfo_toplevel().focus_force()
