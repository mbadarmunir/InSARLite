import tkinter as tk
from tkinter import ttk
from tkintermapview import TkinterMapView
import os
import subprocess
from ..utils.utils import create_ref_point_ra


class ReferencePointGUI(tk.Toplevel):
    def __init__(self, parent, dem, save_dir=None):
        super().__init__(parent)
        self.save_dir = save_dir
        if os.path.basename(self.save_dir) == "merge":
            self.topodir = self.save_dir
        else:
            self.topodir = os.path.join(os.path.dirname(self.save_dir), "topo")
        self.title("Reference Point Selector")
        self.geometry("600x500")
        self.dem = dem

        # Disable close (X) button and window manager close
        self.protocol("WM_DELETE_WINDOW", self.disable_close)
        self.bind("<Alt-F4>", lambda e: "break")
        self.bind("<Escape>", lambda e: "break")
        self.resizable(False, False)

        # Option selection
        self.option_var = tk.StringVar(value="highest_corr")
        options = [
            ("Highest mean correlation", "highest_corr"),
            ("Lowest standard deviation", "lowest_std"),
            ("Define", "define")
        ]
        self.radio_frame = ttk.LabelFrame(self, text="Select Reference Point Option")
        self.radio_frame.pack(fill="x", padx=10, pady=10)

        for text, value in options:
            ttk.Radiobutton(self.radio_frame, text=text, variable=self.option_var, value=value, command=self.on_option_change).pack(anchor="w", padx=5, pady=2)

        # Define option widgets
        self.define_frame = ttk.LabelFrame(self, text="Define Reference Point")
        self.lat_var = tk.StringVar()
        self.lon_var = tk.StringVar()

        # Layout: left side for entries, right side for map, button below entries
        left_frame = ttk.Frame(self.define_frame)
        left_frame.grid(row=0, column=0, sticky="n", padx=5, pady=5)
        right_frame = ttk.Frame(self.define_frame)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.define_frame.columnconfigure(1, weight=1)
        self.define_frame.rowconfigure(0, weight=1)

        ttk.Label(left_frame, text="Latitude:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.lat_entry = ttk.Entry(left_frame, textvariable=self.lat_var, width=15)
        self.lat_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(left_frame, text="Longitude:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.lon_entry = ttk.Entry(left_frame, textvariable=self.lon_var, width=15)
        self.lon_entry.grid(row=1, column=1, padx=5, pady=5)

        self.define_submit_button = ttk.Button(left_frame, text="Submit", command=self.on_define_submit)
        self.define_submit_button.grid(row=2, column=0, columnspan=2, pady=10)

        # Map widget
        self.map_widget = TkinterMapView(right_frame, width=400, height=300, corner_radius=0)
        self.map_widget.pack(fill="both", expand=True)
        self.map_widget.set_position(0, 0)  # Default position
        self.map_widget.set_zoom(2)

        self.map_pin = None

        # Bindings
        self.map_widget.add_left_click_map_command(self.on_map_click)
        self.lat_var.trace_add("write", self.on_latlon_entry)
        self.lon_var.trace_add("write", self.on_latlon_entry)

        self.define_frame.pack_forget()  # Hide initially

        # Submit button for non-define options
        self.option_submit_button = ttk.Button(self, text="Submit", command=self.on_option_submit)
        self.option_submit_button.pack(pady=10)

        self.on_option_change()  # Set initial state

    def disable_close(self):
        pass  # Do nothing to disable close

    def on_option_change(self):
        if self.option_var.get() == "define":
            self.option_submit_button.pack_forget()
            self.define_frame.pack(fill="both", expand=True, padx=10, pady=10)
            self.define_submit_button.config(state="normal")
        else:
            self.define_frame.pack_forget()
            self.option_submit_button.pack(pady=10)
            self.define_submit_button.config(state="disabled")

    def on_map_click(self, coords):
        lat, lon = coords
        self.lat_var.set(f"{lat:.6f}")
        self.lon_var.set(f"{lon:.6f}")
        self.set_map_pin(lat, lon)

    def set_map_pin(self, lat, lon):
        if self.map_pin:
            self.map_widget.delete(self.map_pin)
        self.map_pin = self.map_widget.set_marker(lat, lon, text="Selected Point")
        self.map_widget.set_position(lat, lon)
        self.map_widget.set_zoom(10)

    def on_latlon_entry(self, *args):
        try:
            lat = float(self.lat_var.get())
            lon = float(self.lon_var.get())
            self.set_map_pin(lat, lon)
        except ValueError:
            pass  # Ignore invalid input

    def on_define_submit(self):
        try:
            lat = float(self.lat_var.get())
            lon = float(self.lon_var.get())
        except ValueError:
            tk.messagebox.showerror("Invalid Input", "Please enter valid latitude and longitude.")
            return
        if self.save_dir:        
            topo_path = self.topodir
            filepath = os.path.join(topo_path, "ref_point.ll")
            dem_path = os.path.join(topo_path, os.path.basename(self.dem))
            with open(filepath, "w") as f:
                f.write(f"{lon}, {lat}\n")
            filepathe = os.path.join(topo_path, "ref_point.lle")
            filepathr = os.path.join(topo_path, "ref_point.ra")
            os.chdir(topo_path)
            subprocess.call(f"gmt grdtrack {filepath} -G{dem_path} > {filepathe}", shell=True)
            prm = os.path.join(topo_path, "master.PRM")
            prec = 0
            subprocess.call(f"SAT_llt2rat {prm} {prec} < {filepathe} > {filepathr}", shell=True)
            # Run grdtrack and capture its output
            result = subprocess.run(
                f"gmt grdtrack {filepathr} -G{os.path.join(topo_path, 'corr_stack.grd')}",
                shell=True,
                capture_output=True,
                text=True
            )
            # Parse the output to get mval
            if result.stdout:
                parts = result.stdout.strip().split()
                if len(parts) >= 3 and parts[2] != "NaN":
                    mval = float(parts[2])
                else:
                    mval = None
            else:
                mval = None
            with open(filepathr, "r") as f:
                line = f.readline().strip()
                if float(line[0]) < 0 or float(line[1]) < 0:
                    tk.messagebox.showerror(
                        "Invalid Input",
                        (
                            "Your selected lat/lon are outside valid bounds.\n"
                            "Please reselect a point within the footprint images being processed."
                        )
                    )
                    return
                elif mval is None:
                    tk.messagebox.showwarning(
                        "Warning",
                        (
                            "Your selected lat/lon are inside valid bounds.\n"
                            "However, the selected point has no correlation value for at least one of the IFGs.\n"
                            "The workflow will continue using only raw unwrapped IFGs without reference point normalization."
                        )
                    )
                    
        self.destroy()

    def on_option_submit(self):
        option = self.option_var.get()
        topodir = self.topodir
        
        corr_lyr = None
        if option == "highest_corr":
            corr_lyr = os.path.join(self.save_dir, "corr_stack.grd")            
            print("Selected option is highest mean correlation")
        elif option == "lowest_std":
            corr_lyr = os.path.join(self.save_dir, "std.grd")
            print("Selected option is lowest standard deviation")
        if corr_lyr:
            create_ref_point_ra(topodir, corr_lyr)
        self.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # hide the root window
    app = ReferencePointGUI("/home/badar/0_PhD/01_data/01_raw/02_InSAR/hout/chtr/des/F3/intf_all")
    app.mainloop()