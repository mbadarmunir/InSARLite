#!/usr/bin/env python3
import os
import re
import sys
from datetime import datetime, timedelta
import xarray as xr
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import matplotlib.dates as mdates
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from dask.diagnostics import ProgressBar
import tkinter as tk
from tkinter import messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# -----------------------------------------------------------------------------
# Helper: collect files and their datetime from filenames
# -----------------------------------------------------------------------------
def get_file_paths(folder_path):
    pattern = re.compile(r"disp_(\d{4})(\d{3})_ll\.grd$")
    files_to_load = []
    for filename in sorted(os.listdir(folder_path)):
        match = pattern.match(filename)
        if match:
            year = int(match.group(1))
            doy = int(match.group(2))
            date = datetime(year, 1, 1) + timedelta(days=doy - 1)
            file_path = os.path.join(folder_path, filename)
            files_to_load.append((file_path, date))
    files_to_load.sort(key=lambda x: x[1])
    return files_to_load

# -----------------------------------------------------------------------------
# Open all files lazily and concat along 'time' dimension
# -----------------------------------------------------------------------------
def load_all_data_lazy(files_to_load, chunk_dict=None):
    if not files_to_load:
        raise ValueError("No files to load")
    dataarrays = []
    for fp, dt in files_to_load:
        try:
            da = xr.open_dataarray(fp)
        except Exception:
            ds = xr.open_dataset(fp)
            if len(ds.data_vars) == 0:
                raise RuntimeError(f"No data variables found in {fp}")
            da = ds[list(ds.data_vars)[0]]
        da = da.expand_dims(time=[np.datetime64(dt)])
        dataarrays.append(da)
    stacked = xr.concat(dataarrays, dim="time")
    if chunk_dict:
        stacked = stacked.chunk(chunk_dict)
    return stacked

# -----------------------------------------------------------------------------
# TopLevel window for time series plot
# -----------------------------------------------------------------------------
class TimeSeriesWindow(tk.Toplevel):
    def __init__(self, master, lat, lon, stacked_data):
        super().__init__(master)
        self.title(f"Time Series at ({lat:.4f}, {lon:.4f})")
        self.geometry("900x600")
        self.lat = lat
        self.lon = lon
        self.stacked_data = stacked_data
        self.time_series_fig = None
        self.time_series_data = None

        self.ts_frame = tk.Frame(self)
        self.ts_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.download_frame = tk.Frame(self)
        self.download_frame.pack(side=tk.TOP, fill=tk.X, pady=10)
        self.btn_save_png = tk.Button(self.download_frame, text="Download Time Series PNG", command=self.save_png, state=tk.DISABLED)
        self.btn_save_png.pack(side=tk.LEFT, padx=10)
        self.btn_save_csv = tk.Button(self.download_frame, text="Download Time Series CSV", command=self.save_csv, state=tk.DISABLED)
        self.btn_save_csv.pack(side=tk.LEFT, padx=10)
        self.ts_canvas = None

        self.plot_time_series()

    def plot_time_series(self):
        lat_name = None; lon_name = None
        for n in self.stacked_data.coords:
            if n.lower().startswith("lat"): lat_name = n; break
        for n in self.stacked_data.coords:
            if n.lower().startswith("lon"): lon_name = n; break
        if lat_name is None or lon_name is None:
            if 'y' in self.stacked_data.coords and 'x' in self.stacked_data.coords:
                lat_name, lon_name = 'y','x'
            else:
                messagebox.showerror("Error", "Could not detect lat/lon coordinate names in DataArray")
                return

        point_series = self.stacked_data.sel({lat_name: self.lat, lon_name: self.lon}, method="nearest")
        times = pd.to_datetime(point_series['time'].values)
        deformation = point_series.values.astype(float)
        self.time_series_data = pd.DataFrame({"Time": times, "Deformation": deformation})

        num_years = (times[-1] - times[0]).days / 365.0 if len(times) > 1 else 0
        fig = plt.Figure(figsize=(8, 5))
        ax = fig.add_subplot(111)
        ax.plot(times, deformation, marker='o', linestyle='-')
        if num_years <= 1:
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
        elif num_years <= 4:
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
        else:
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.set_title(f"Surface Deformation Time Series at ({self.lat:.4f}, {self.lon:.4f})")
        ax.set_xlabel("Time")
        ax.set_ylabel("Deformation")
        ax.tick_params(axis='x', rotation=45)
        ax.grid()
        fig.tight_layout()

        # Avoid re-plotting while pan/zoom is active
        if self.ts_canvas and hasattr(self.ts_canvas, 'toolbar'):
            if self.ts_canvas.toolbar.mode != '':
                # Pan/zoom is active, skip re-plotting
                return

        if self.ts_canvas:
            self.ts_canvas.get_tk_widget().destroy()
        self.ts_canvas = FigureCanvasTkAgg(fig, master=self.ts_frame)
        self.ts_canvas.draw()
        self.ts_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Add toolbar for pan/zoom
        if hasattr(self, 'ts_toolbar') and self.ts_toolbar:
            self.ts_toolbar.destroy()
        self.ts_toolbar = NavigationToolbar2Tk(self.ts_canvas, self.ts_frame)
        self.ts_toolbar.update()
        self.ts_toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.btn_save_png.config(state=tk.NORMAL)
        self.btn_save_csv.config(state=tk.NORMAL)
        self.time_series_fig = fig

    def save_png(self):
        if self.time_series_fig is None:
            return
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                 filetypes=[("PNG files", "*.png")],
                                                 title="Save Time Series PNG")
        if file_path:
            try:
                self.time_series_fig.savefig(file_path)
                messagebox.showinfo("Saved", f"PNG saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save PNG:\n{e}")

    def save_csv(self):
        if self.time_series_data is None:
            return
        
        file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                 filetypes=[("CSV files", "*.csv")],
                                                 title="Save Time Series CSV")
        if file_path:
            try:
                self.time_series_data.to_csv(file_path, index=False)
                messagebox.showinfo("Saved", f"CSV saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save CSV:\n{e}")

# -----------------------------------------------------------------------------
# Tkinter App
# -----------------------------------------------------------------------------
class VisualizeApp(tk.Tk):
    def __init__(self, indir):
        super().__init__()
        self.title("GMTSAR Surface Deformation Visualizer")
        self.geometry("1200x800")
        self.folder_path = indir
        self.stacked_data = None
        self.vel_file_path = None

        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        frame_top = tk.Frame(self)
        frame_top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        tk.Label(frame_top, text="Data Folder:").pack(side=tk.LEFT)
        self.folder_label = tk.Label(frame_top, text=self.folder_path, anchor="w", width=80)
        self.folder_label.pack(side=tk.LEFT, padx=5)

        # Latitude and Longitude input
        tk.Label(frame_top, text="Latitude:").pack(side=tk.LEFT, padx=5)
        self.lat_entry = tk.Entry(frame_top, width=10)
        self.lat_entry.pack(side=tk.LEFT)
        tk.Label(frame_top, text="Longitude:").pack(side=tk.LEFT, padx=5)
        self.lon_entry = tk.Entry(frame_top, width=10)
        self.lon_entry.pack(side=tk.LEFT)
        self.plot_btn = tk.Button(frame_top, text="Plot Time Series", command=self.plot_time_series_from_entry)
        self.plot_btn.pack(side=tk.LEFT, padx=10)

        self.map_frame = tk.Frame(self)
        self.map_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.map_canvas = None

    def load_data(self):
        folder_path = self.folder_path
        if not folder_path or not os.path.isdir(folder_path):
            messagebox.showerror("Error", "Please select a valid folder.")
            self.destroy()
            return
        files_to_load = get_file_paths(folder_path)
        if not files_to_load:
            messagebox.showerror("Error", "No displacement files found in folder.")
            self.destroy()
            return

        first_fp, _ = files_to_load[0]
        samp = xr.open_dataarray(first_fp, chunks={})
        lat_name = None; lon_name = None
        for n in samp.coords:
            if n.lower().startswith("lat"): lat_name = n; break
        for n in samp.coords:
            if n.lower().startswith("lon"): lon_name = n; break
        if lat_name is None or lon_name is None:
            if 'y' in samp.coords and 'x' in samp.coords:
                lat_name, lon_name = 'y','x'
            else:
                samp.close()
                messagebox.showerror("Error", "Could not detect lat/lon coordinate names in files.")
                self.destroy()
                return
        samp.close()
        chunk_dict = {lat_name: 256, lon_name: 256}

        with ProgressBar():
            self.stacked_data = load_all_data_lazy(files_to_load, chunk_dict=chunk_dict)

        vel_file_path = os.path.join(folder_path, "vel_ll.grd")
        if not os.path.exists(vel_file_path):
            messagebox.showerror("Error", "Velocity file vel_ll.grd not found.")
            self.destroy()
            return
        self.vel_file_path = vel_file_path

        self.plot_interactive_map()

    def plot_interactive_map(self):
        ds = xr.open_dataarray(self.vel_file_path)

        # Detect coordinate names
        lat_name = None; lon_name = None
        for n in ds.coords:
            if n.lower().startswith("lat"): 
                lat_name = n; break
        for n in ds.coords:
            if n.lower().startswith("lon"): 
                lon_name = n; break
        if lat_name is None or lon_name is None:
            if 'y' in ds.coords and 'x' in ds.coords:
                lat_name, lon_name = 'y', 'x'
            else:
                messagebox.showerror("Error", "Could not detect lat/lon in velocity file.")
                return

        # Extract data
        lons = ds[lon_name].values
        lats = ds[lat_name].values
        lon2d, lat2d = np.meshgrid(lons, lats)
        vel = ds.values

        # Create figure
        fig = plt.Figure(figsize=(8, 6))
        ax = fig.add_subplot(111, projection=ccrs.PlateCarree())
        ax.set_extent([lons.min(), lons.max(), lats.min(), lats.max()], crs=ccrs.PlateCarree())
        # ax.add_feature(cfeature.COASTLINE)
        # ax.add_feature(cfeature.BORDERS, linestyle=':')
        # ax.add_feature(cfeature.LAND, facecolor='lightgray', edgecolor='none')
        # ax.add_feature(cfeature.LAKES, alpha=0.5)
        # ax.add_feature(cfeature.RIVERS, alpha=0.5)

        # Add gridlines for lat/lon
        gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', alpha=0.5, linestyle='--')
        gl.top_labels = False
        gl.right_labels = False
        gl.xlabel_style = {'size': 10}
        gl.ylabel_style = {'size': 10}

        # Plot velocity map
        c = ax.pcolormesh(lon2d, lat2d, vel, cmap='jet', transform=ccrs.PlateCarree())
        fig.colorbar(c, ax=ax, orientation='vertical')
        ax.set_title("Interactive Map of Surface Deformation Velocity")

        # Destroy old canvas if exists
        if self.map_canvas:
            self.map_canvas.get_tk_widget().destroy()
        self.map_canvas = FigureCanvasTkAgg(fig, master=self.map_frame)
        self.map_canvas.draw()
        self.map_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Destroy old toolbar if exists
        if hasattr(self, 'toolbar') and self.toolbar:
            self.toolbar.destroy()
        self.toolbar = NavigationToolbar2Tk(self.map_canvas, self.map_frame)
        self.toolbar.update()
        self.toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Click handler
        def onclick(event):
            if event.inaxes != ax:
                return

            # Check if pan/zoom is active
            if self.toolbar.mode != '':
                # Skip click when panning/zooming
                return

            lon_click, lat_click = event.xdata, event.ydata
            if lon_click is not None and lat_click is not None:
                TimeSeriesWindow(self, lat_click, lon_click, self.stacked_data)

        fig.canvas.mpl_connect('button_release_event', onclick)

    def plot_time_series_from_entry(self):
        try:
            lat = float(self.lat_entry.get())
            lon = float(self.lon_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric Latitude and Longitude.")
            return
        TimeSeriesWindow(self, lat, lon, self.stacked_data)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def run_visualize_app(indir):
    app = VisualizeApp(indir)
    app.mainloop()

# To use from another script:
# from out_visualize import run_visualize_app
# run_visualize_app("/path/to/data_folder")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python out_visualize.py <indir>")
        sys.exit(1)
    indir = sys.argv[1]
    run_visualize_app(indir)
