import tkinter as tk
from ..gmtsar_gui.alignment import align_sec_imgs
from ..gmtsar_gui.ifgs_generation import gen_ifgs
from ..gmtsar_gui.mergeIFGs import merge_thread
from ..gmtsar_gui.mean_corr import create_mean_grd
import threading
from tkinter import messagebox
import os

class GenIfg:
    def __init__(self, root, paths, mst, dem, align_mode=None, esd_mode=None, on_done=None):
        self.root = root
        self.root.title("Parameter Settings for IFGs Generation")
        self.dem_path = dem
        self.paths = paths
        self.mst = mst
        self.align_mode = align_mode
        self.esd_mode = esd_mode
        self.on_done = on_done

        # Decimation Frame
        self.decimation_frame = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        self.decimation_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nw")

        tk.Label(self.decimation_frame, text="IFGs Generation", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(5, 15))

        # Range Decimation
        tk.Label(self.decimation_frame, text="Range Decimation:").grid(row=1, column=0, sticky="w", padx=5)
        self.range_dec_var = tk.StringVar(value="8")
        tk.Entry(self.decimation_frame, textvariable=self.range_dec_var).grid(row=1, column=1, padx=5)

        # Azimuth Decimation
        tk.Label(self.decimation_frame, text="Azimuth Decimation:").grid(row=2, column=0, sticky="w", padx=5)
        self.az_dec_var = tk.StringVar(value="2")
        tk.Entry(self.decimation_frame, textvariable=self.az_dec_var).grid(row=2, column=1, padx=5)

        # Filter Wavelength
        tk.Label(self.decimation_frame, text="Filter Wavelength (m):").grid(row=3, column=0, sticky="w", padx=5)
        self.filter_wl_var = tk.StringVar(value="200")
        tk.Entry(self.decimation_frame, textvariable=self.filter_wl_var).grid(row=3, column=1, padx=5)

        # Number of cores (next column)
        try:
            available_cores = os.cpu_count() or 1
            default_cores = max(1, available_cores - 1)
        except Exception:
            default_cores = 1
        tk.Label(self.root, text="Number of cores:").grid(row=1, column=2, sticky="w", padx=(20,5))
        self.cores_var = tk.StringVar(value=str(default_cores))
        tk.Entry(self.root, textvariable=self.cores_var).grid(row=1, column=3, padx=5)

        # Run Button
        self.run_btn = tk.Button(self.root, text="Run", command=self.on_run)
        self.run_btn.grid(row=4, column=0, pady=20, sticky="w")

    def on_run(self):
        print("Run button clicked.")

        def run_alignment():
            print("Starting alignment of secondary images...")
            # alignmethod = self.align_mode if hasattr(self, 'align_mode') else None
            # esd_mode = self.esd_mode if hasattr(self, 'esd_mode') else None
            
            align_sec_imgs(self.paths, self.mst, self.dem_path, self.align_mode, self.esd_mode)

        def ifg_generation():
            print("Starting IFG generation...")
            filter_wavelength = int(self.filter_wl_var.get())
            rng = int(self.range_dec_var.get())
            az = int(self.az_dec_var.get())
            ncores = int(self.cores_var.get())
            gen_ifgs(self.paths, self.mst, filter_wavelength, rng, az, ncores)

        def merge_ifgs():
            print("Starting IFG merging...")
            if "pmerge" in self.paths.keys():
                pmerge = self.paths.get("pmerge")
                if pmerge and os.path.exists(pmerge):
                    # Call the merge_thread function
                    merge_thread(pmerge, int(self.cores_var.get()), self.mst)

        def calc_mean_corr():            
            ifgsroot = None
            if "pmerge" in self.paths.keys():
                pmerge = self.paths.get("pmerge")
                if pmerge and os.path.exists(pmerge):
                    ifgsroot = pmerge
                else:
                    for key in ["pF1", "pF2", "pF3"]:
                        dir_path = self.paths.get(key)
                        if dir_path and os.path.exists(dir_path):
                            ifgsroot = os.path.join(dir_path, 'intf_all')
                            break
            if ifgsroot:
                print(f"Creating mean & sd correlation grid in {ifgsroot}...")
                if os.path.exists(ifgsroot):
                    create_mean_grd(ifgsroot)

            

        msg = (
            "Press the \"Continue\" button if you understand that clicking run button will perform the following in specified sequence:\n"
            "  1. Alignment of secondary images w.r.t. the specified master.\n"
            "  2. Generation of IFGs as per generated IFGs network.\n"
            "  3. Merging the IFGs of selected subswaths if more than one was selected.\n"
            "  4. Calculation and creation of mean & sd correlation grid to be used for later steps. \nThe start and end of each process will be displayed in the terminal."
        )

        def process_sequence():
            try:
                self.root.destroy()
                run_alignment()
                ifg_generation()
                merge_ifgs()
                calc_mean_corr()
                print("All processes completed.")
                if self.on_done:
                    self.on_done()
                # self.root.quit()
                
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {e}")

        if messagebox.askokcancel("Confirm Run", msg):
            threading.Thread(target=process_sequence, daemon=True).start()
        else:
            return
        

# Example usage:
if __name__ == "__main__":
    root = tk.Tk()
    gui = GenIfg(root)
    root.mainloop()
