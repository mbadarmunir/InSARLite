import os
import re
import subprocess
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from ..utils.utils import add_tooltip, run_command, projgrd, velkml
from ..gmtsar_gui.out_visualize import run_visualize_app

class SBASApp(tk.Frame):
    def __init__(self, parent, paths, ifgsroot, ifgs, gacosdir):
        super().__init__(parent)
        parent.title("SBASApp")
        parent.geometry("1200x300")
        self.paths = paths
        self.ifgsroot = ifgsroot
        self.ifgs = ifgs
        self.gacosdir = gacosdir
        self.topodir = self.ifgsroot if os.path.basename(self.ifgsroot) == "merge" else os.path.join(os.path.dirname(self.ifgsroot), "topo")        
        self.sdir = self.paths.get("psbas")
        self._init_widgets()
        self.pack(fill="both", expand=True)

    def _init_widgets(self):
        # Incidence angle
        tk.Label(self, text="Incidence Angle (format: float):").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.incidence_angle_entry = tk.Entry(self, width=50)
        self.incidence_angle_entry.grid(row=0, column=1, padx=10, pady=5)
        self.incidence_angle_entry.insert(0, "37")

        # Number of cores
        try:
            available_cores = os.cpu_count() or 1
            default_cores = max(1, available_cores - 1)
        except Exception:
            default_cores = 1

        tk.Label(self, text="Number of cores:").grid(row=0, column=3, padx=10, pady=5)

        self.cores_var = tk.StringVar(value=str(default_cores))
        self.cores_entry = tk.Entry(self, width=10, textvariable=self.cores_var)
        self.cores_entry.grid(row=0, column=4, padx=10, pady=5)


        # SBAS Arguments
        tk.Label(self, text="SBAS Arguments:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.rms_var = tk.BooleanVar(value=True)
        self.dem_var = tk.BooleanVar(value=True)
        sbas_args_frame = tk.Frame(self)
        sbas_args_frame.grid(row=1, column=1, columnspan=3, padx=10, pady=5, sticky="w")
        rms_checkbox = tk.Checkbutton(sbas_args_frame, text="-rms", variable=self.rms_var)
        rms_checkbox.pack(side=tk.LEFT, padx=(0, 10))
        add_tooltip(rms_checkbox, "Check to calculate RMS of residuals (-rms).")
        dem_checkbox = tk.Checkbutton(sbas_args_frame, text="-dem", variable=self.dem_var)
        dem_checkbox.pack(side=tk.LEFT)
        add_tooltip(dem_checkbox, "Check to generate DEM residual error file in SB inversion (-dem).")

        # Smoothing factor
        tk.Label(self, text="Smoothing factor:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.smooth_var_entry = tk.Entry(self, width=10)
        self.smooth_var_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        self.smooth_var_entry.insert(0, "5.0")
        add_tooltip(self.smooth_var_entry, "Enter the smoothing factor for the SBAS inversion.\nDefault is 5.0, but you can adjust it based on your data.")

        # Atmospheric correction iterations
        tk.Label(self, text="Atmospheric correction iterations:").grid(row=2, column=2, padx=10, pady=5, sticky="w")
        self.atm_var_entry = tk.Entry(self, width=10)
        self.atm_var_entry.grid(row=2, column=3, padx=10, pady=5, sticky="w")
        self.atm_var_entry.insert(0, "0")
        add_tooltip(self.atm_var_entry, "Enter the No. of iterations for atm corrections.")

        # SBAS mode selection
        tk.Label(self, text="SBAS Mode:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.sbas_mode_var = tk.StringVar(value="SBAS")
        sbas_mode_dropdown = ttk.Combobox(
            self,
            textvariable=self.sbas_mode_var,
            values=["SBAS", "SBAS Parallel"],
            state="readonly",
            width=20
        )
        sbas_mode_dropdown.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        # Run Button
        run_button = tk.Button(self, text="Run", command=self.run_sbas)
        run_button.grid(row=4, column=0, columnspan=2, padx=10, pady=20, sticky="w")

    def run_sbas(self):        
        
        args = self.get_args()
        inc_angle = args.get("incidence_angle")
        cores = args.get("cores")
        atm = args.get("atm")
        rms = args.get("rms")
        dem = args.get("dem")
        sbas = args.get("sbas_mode")
        if sbas == "SBAS":
            sbas = "sbas"
        elif sbas == "SBAS Parallel":
            sbas = "sbas_parallel"
            os.environ["OMP_NUM_THREADS"] = cores if cores else "1"
        smooth = args.get("smooth")
        # print(self.paths)
        sdir = self.sdir
        disp_files = []
        nsce = 0
        ndisp = 0

        # Regex pattern: disp_<7digits>.grd
        pattern = re.compile(r"^disp_\d{7}\.grd$")
        for root, _, files in os.walk(sdir):
            for f in files:
                if f == "scene.tab":
                    sce = os.path.join(root, f)
                    with open(sce) as file:     
                        nsce = sum(1 for line in file)
                if pattern.match(f):
                    disp_files.append(os.path.join(root, f))

        # Total count of disp_*.grd files
        ndisp = len(disp_files)                
        if nsce > 0 and inc_angle and sbas:
            if nsce > 0 and ndisp > 0 and nsce == ndisp:
                confirm = messagebox.askyesno("SBAS Confirmation", "SBAS seems to have already been completed. Redo the process?")
                if confirm:
                    self.sb_inversion(sdir, self.paths, inc_angle, atm, rms, dem, sbas, smooth)
                else:
                    print("Rerunning SBAS skipped.")
            else:
                self.sb_inversion(sdir, self.paths, inc_angle, atm, rms, dem, sbas, smooth)
        disp_files_ll = []
        # Regex pattern: disp_<7digits>_ll.grd
        patternll = re.compile(r"^disp_\d{7}_ll\.grd$")
        for root, _, files in os.walk(sdir):
            for f in files:
                if patternll.match(f):
                    disp_files_ll.append(os.path.join(root, f))

        if len(disp_files_ll) == len(disp_files) and len(disp_files_ll) == nsce:
            self.create_visualize()
        # confirm2 = messagebox.askyesno("Confirm Projection", "Do you want to reproject SBAS results and generate Velocity KML file?")
        # if confirm2:
        #     projgrd(sdir)
        #     velkml(sdir, True, self.paths)
        #     messagebox.showinfo("Process Completed", "SBAS processing and KML generation completed.")
    def create_visualize(self):
        # Disable run button and set its background to green
        for child in self.winfo_children():
            if isinstance(child, tk.Button) and child.cget("text") == "Run":
                child.config(state="disabled", bg="green")
                break

        # Create and show visualize button next to run button
        self.visualize_button = tk.Button(self, text="Visualize", bg="lightblue", command=self.visualize_action)
        self.visualize_button.grid(row=4, column=2, padx=10, pady=20, sticky="w")

    def visualize_action(self):
        run_visualize_app(self.sdir)

    def sb_prep(self, intf, btable, intfdir, uwp):    
        if not os.path.exists('intf.tab') and not os.path.exists('scene.tab'):
            subprocess.call(
                f'prep_sbas.csh {intf} {btable} {intfdir} {uwp} corr.grd',
                shell=True)
                
    def sb_inversion(self, sdir, paths, inc_angle, atm="", rms=" -rms", dem=" -dem", sbas="sbas", smooth=" -smooth 5.0"):
        os.chdir(sdir)
        pmerge = paths.get("pmerge")
    
        for key in ["pF1", "pF2", "pF3"]:
            dir_path = paths.get(key)
            if dir_path and os.path.exists(dir_path):
                intf = os.path.join(dir_path, 'intf.in')
                btable = os.path.join(dir_path, 'baseline_table.dat')
                if pmerge and os.path.exists(pmerge):
                    intfdir = pmerge
                else:
                    intfdir = os.path.join(dir_path, 'intf_all')
                break
        uwp = 'unwrap.grd'
        for subfolder in os.listdir(intfdir):
            if os.path.exists(os.path.join(intfdir, subfolder, 'unwrap_GACOS_corrected_detrended.grd')):
                uwp = 'unwrap_GACOS_corrected_detrended.grd'
            else:
                uwps = [os.path.join(root, f) for root, _, files in os.walk(intfdir) for f in files if f == 'unwrap.grd']
                uwpn = [os.path.join(root, f) for root, _, files in os.walk(intfdir) for f in files if f == 'unwrap_pin.grd']
                if len(uwps) == len(uwpn):
                    uwp = "unwrap_pin.grd"
                else:
                    uwp = "unwrap.grd"
        print(f"Creating required files for sbas using uwp: {uwp}, intf.in: {intf}, btable: {btable}, intfdir: {intfdir}")
        self.sb_prep(intf, btable, intfdir, uwp)

        if os.path.exists('intf.tab') and os.path.exists('scene.tab'):
            with open('intf.tab') as file:     
                intf_count = sum(1 for line in file)
            with open('intf.tab') as file:
                for line in file:
                    grd = line.strip().split()[0]
                    break
            with open('scene.tab') as file:
                scene_count = sum(1 for line in file)

            grdinfo = subprocess.check_output(f"gmt grdinfo {grd}", shell=True).decode().strip().split()
            x = grdinfo.index('x')
            y = grdinfo.index('y')
            xval = grdinfo[x + 2]
            yval = grdinfo[y + 2]
            xmin = float(grdinfo[grdinfo.index('x_min:') + 1])
            xmax = float(grdinfo[grdinfo.index('x_max:') + 1])
            c = 3 * 10 ** 8
            grdir = os.path.dirname(grd)
            prm = next((os.path.join(rootx, f) for rootx, _, files in os.walk(grdir) for f in files if f.endswith('.PRM')), os.path.join(grdir, 'supermaster.PRM'))
            with open(prm) as file:
                for line in file:
                    if 'near_range' in line:
                        nr = float(line.split('=')[1].strip())
                    if 'rng_samp_rate' in line:
                        rs = float(line.split('=')[1].strip())
                    if 'radar_wavelength' in line:
                        rw = float(line.split('=')[1].strip())
            range = c / rs / 2 * (xmin + xmax) / 2 + nr
            print('Starting SBAS process')

            sb_command = f"{sbas.lower()} intf.tab scene.tab {intf_count} {scene_count} {xval} {yval} -range {range} -incidence {inc_angle} -wavelength {rw} {smooth} {atm} {rms} {dem}".rstrip()

            if sbas == 'sbas_parallel':
                sb_command = sb_command + ' -mmap'
            
            print(sb_command)
            run_command(sb_command)
            print('SBAS process completed')

            print('Projecting SBAS results to geographic coordinates')
            velkml(sdir)
            print('Velocity KML generation completed')
            projgrd(sdir)
            print('Projection completed')


    def get_args(self):
        rms = "-rms" if self.rms_var.get() else ""
        dem = "-dem" if self.dem_var.get() else ""
        smooth = f"-smooth {self.smooth_var_entry.get()}" if self.smooth_var_entry.get() else ""
        atm = f"-atm {self.atm_var_entry.get()}" if self.atm_var_entry.get() else "-atm 0"
        return {
            "incidence_angle": self.incidence_angle_entry.get(),
            "cores": self.cores_entry.get(),
            "rms": rms,
            "dem": dem,
            "smooth": smooth,
            "atm": atm,
            "sbas_mode": self.sbas_mode_var.get()
        }