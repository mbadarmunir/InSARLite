#!/usr/bin/env python3
import os
import re
import sys
import time
from datetime import datetime, timedelta
import xarray as xr
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import matplotlib.dates as mdates
import tkinter as tk
from tkinter import messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# Configure matplotlib for TRUE VECTOR output (editable text, not rasterized)
# This MUST be set before creating any figures
plt.rcParams['pdf.fonttype'] = 42        # TrueType fonts (editable text)
plt.rcParams['ps.fonttype'] = 42         # TrueType fonts (editable text)
plt.rcParams['svg.fonttype'] = 'none'    # Preserve text as text (not paths)
plt.rcParams['pdf.use14corefonts'] = True  # Use standard PDF fonts
plt.rcParams['text.usetex'] = False      # Don't use LaTeX (prevents rasterization)

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
            # Fix GMTSAR native 1-day offset: add 1 day to the calculated date
            date = datetime(year, 1, 1) + timedelta(days=doy)  # Changed from doy-1 to doy
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
        self.master_app = master  # Store reference immediately

        self.ts_frame = tk.Frame(self)
        self.ts_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.download_frame = tk.Frame(self)
        self.download_frame.pack(side=tk.TOP, fill=tk.X, pady=10)
        self.btn_save_all = tk.Button(self.download_frame, text="Save All (PNG+Vector+CSV+Map)", command=self.save_all_files, state=tk.DISABLED)
        self.btn_save_all.pack(side=tk.LEFT, padx=10)
        self.ts_canvas = None

        # Set up window close handler to remove pin and clean up
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.plot_time_series()
        
    def on_closing(self):
        """Handle window closing - remove pin and clean up"""
        try:
            # Remove this window from master's open windows list
            if hasattr(self.master_app, 'open_windows'):
                if self in self.master_app.open_windows:
                    self.master_app.open_windows.remove(self)
            
            # Reset pin if this is the last/only window
            if hasattr(self.master_app, 'reset_pin'):
                # Check if this is the last window for this coordinate
                same_coord_windows = [w for w in getattr(self.master_app, 'open_windows', []) 
                                    if hasattr(w, 'lat') and hasattr(w, 'lon') and 
                                    abs(w.lat - self.lat) < 0.0001 and abs(w.lon - self.lon) < 0.0001]
                if len(same_coord_windows) <= 1:  # This window + possibly others
                    self.master_app.reset_pin()
        except Exception as e:
            print(f"Warning: Error during window cleanup: {e}")
        
        # Destroy the window
        self.destroy()

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

        try:
            point_series = self.stacked_data.sel({lat_name: self.lat, lon_name: self.lon}, method="nearest")
            times = pd.to_datetime(point_series['time'].values)
            deformation = point_series.values.astype(float)
            
            # Validate extracted data
            if len(times) == 0:
                messagebox.showerror("Error", "No time series data found at this location.")
                return
                
            # Check for meaningful time series data
            valid_data_count = np.sum(~np.isnan(deformation))
            valid_ratio = valid_data_count / len(deformation) if len(deformation) > 0 else 0
            
            if valid_data_count == 0:
                messagebox.showerror("No Valid Data", 
                                   f"All time series values are NaN at location ({self.lat:.4f}, {self.lon:.4f}).\n\n"
                                   "This pixel has no valid temporal data.")
                return
            elif valid_data_count == 1:
                messagebox.showwarning("Insufficient Data", 
                                     f"Only 1 valid time point found at location ({self.lat:.4f}, {self.lon:.4f}).\n\n"
                                     "Cannot create a meaningful time series plot with a single data point.\n"
                                     "Try clicking on a different location with more temporal coverage.")
                return
            elif valid_data_count < 3:
                response = messagebox.askyesno("Sparse Data", 
                                             f"Only {valid_data_count} valid time points found at location ({self.lat:.4f}, {self.lon:.4f}).\n\n"
                                             "This will create a very sparse time series plot.\n\n"
                                             "Do you want to continue?")
                if not response:
                    return
            elif valid_ratio < 0.1:  # Less than 10% valid data
                response = messagebox.askyesno("Sparse Data", 
                                             f"Only {valid_data_count}/{len(deformation)} time points have valid data ({valid_ratio:.1%}) at this location.\n\n"
                                             "The time series may have significant gaps.\n\n"
                                             "Do you want to continue?")
                if not response:
                    return
            
            # Get actual coordinates of selected pixel for accurate title
            actual_lat = float(point_series[lat_name].values)
            actual_lon = float(point_series[lon_name].values)
            
            self.lat = actual_lat  # Update to actual pixel location
            self.lon = actual_lon
            self.title(f"Time Series at ({actual_lat:.4f}, {actual_lon:.4f})")
            
            print(f"✅ Time series extracted: {valid_data_count}/{len(deformation)} valid points ({valid_ratio:.1%}) at ({actual_lat:.4f}, {actual_lon:.4f})")
            
            self.time_series_data = pd.DataFrame({"Time": times, "Deformation": deformation})
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to extract time series data:\n{str(e)}")
            return

        # Calculate quality metrics for plotting
        valid_data_count = np.sum(~np.isnan(deformation))
        valid_ratio = valid_data_count / len(deformation) if len(deformation) > 0 else 0

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

        # Add hover functionality for exact date display
        def on_hover(event):
            if event.inaxes == ax and len(times) > 0:
                # Find nearest point
                if event.xdata is not None:
                    hover_time = matplotlib.dates.num2date(event.xdata)
                    # Ensure timezone compatibility by making both timezone-naive
                    if hasattr(hover_time, 'tz') and hover_time.tz is not None:
                        hover_time = hover_time.replace(tzinfo=None)
                    
                    # Convert times to timezone-naive datetime objects if needed
                    times_naive = []
                    for t in times:
                        if hasattr(t, 'tz_localize'):  # pandas Timestamp
                            if t.tz is not None:
                                times_naive.append(t.tz_localize(None))
                            else:
                                times_naive.append(t.to_pydatetime())
                        elif hasattr(t, 'tz') and t.tz is not None:  # datetime with timezone
                            times_naive.append(t.replace(tzinfo=None))
                        elif hasattr(t, 'to_pydatetime'):  # pandas Timestamp without timezone
                            times_naive.append(t.to_pydatetime())
                        else:  # regular datetime
                            times_naive.append(t)
                    
                    # Calculate time differences safely
                    time_diffs = []
                    for t in times_naive:
                        try:
                            if hasattr(t, 'total_seconds'):
                                # t is already a timedelta
                                time_diffs.append(abs(t.total_seconds()))
                            else:
                                # t is a datetime, calculate difference
                                diff = abs((t - hover_time).total_seconds())
                                time_diffs.append(diff)
                        except (TypeError, AttributeError):
                            # Fallback: convert to timestamp and calculate difference
                            try:
                                t_timestamp = t.timestamp() if hasattr(t, 'timestamp') else time.mktime(t.timetuple())
                                hover_timestamp = hover_time.timestamp() if hasattr(hover_time, 'timestamp') else time.mktime(hover_time.timetuple())
                                time_diffs.append(abs(t_timestamp - hover_timestamp))
                            except:
                                time_diffs.append(float('inf'))  # Skip this point
                    nearest_idx = np.argmin(time_diffs)
                    
                    if nearest_idx < len(times) and nearest_idx < len(deformation):
                        exact_date = times[nearest_idx].strftime('%Y-%m-%d (%A)')
                        deform_value = deformation[nearest_idx]
                        
                        # Update status or create tooltip with intelligent positioning
                        # Remove existing annotation safely
                        if hasattr(self, 'hover_annotation') and self.hover_annotation:
                            try:
                                self.hover_annotation.remove()
                            except (ValueError, RuntimeError):
                                pass  # Already removed or invalid
                            self.hover_annotation = None
                            
                        if not np.isnan(deform_value):
                            # Get axes bounds for intelligent positioning
                            xlim = ax.get_xlim()
                            ylim = ax.get_ylim()
                            
                            # Convert data coordinates to relative position (0-1)
                            point_x_rel = (matplotlib.dates.date2num(times[nearest_idx]) - xlim[0]) / (xlim[1] - xlim[0])
                            point_y_rel = (deform_value - ylim[0]) / (ylim[1] - ylim[0]) if ylim[1] != ylim[0] else 0.5
                            
                            # Intelligent positioning based on point location to avoid edges
                            if point_x_rel > 0.75:  # Far right - position left
                                ha, offset_x = 'right', -15
                            elif point_x_rel < 0.25:  # Far left - position right  
                                ha, offset_x = 'left', 15
                            else:  # Center - position right
                                ha, offset_x = 'left', 10
                                
                            if point_y_rel > 0.75:  # Top area - position below
                                va, offset_y = 'top', -15
                            elif point_y_rel < 0.25:  # Bottom area - position above
                                va, offset_y = 'bottom', 15
                            else:  # Middle area - position above
                                va, offset_y = 'bottom', 10
                            
                            # Highlight the data point being hovered
                            hover_x_data = matplotlib.dates.date2num(times[nearest_idx])
                            hover_y_data = deform_value
                            
                            # Remove previous highlight
                            if hasattr(self, 'hover_point') and self.hover_point:
                                try:
                                    self.hover_point.remove()
                                except:
                                    pass
                            
                            # Create highlighted point
                            self.hover_point = ax.plot(hover_x_data, hover_y_data, 'ro', markersize=8, zorder=999)[0]
                            
                            self.hover_annotation = ax.annotate(f'{exact_date}\nDeformation: {deform_value:.2f} mm',
                                                               xy=(hover_x_data, hover_y_data),
                                                               xytext=(offset_x, offset_y), textcoords="offset points",
                                                               bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.9, edgecolor="gray"),
                                                               arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0", color="red", lw=1.5),
                                                               ha=ha, va=va, fontsize=9, zorder=1000)
                        else:
                            # Handle NaN values
                            if not hasattr(self, 'hover_annotation'):
                                self.hover_annotation = None
                        
                        self.ts_canvas.draw_idle()
                else:
                    # Remove annotation and highlight when mouse leaves data area
                    if hasattr(self, 'hover_annotation') and self.hover_annotation:
                        try:
                            self.hover_annotation.remove()
                        except (ValueError, RuntimeError):
                            pass  # Already removed or invalid
                        self.hover_annotation = None
                    
                    if hasattr(self, 'hover_point') and self.hover_point:
                        try:
                            self.hover_point.remove()
                        except (ValueError, RuntimeError):
                            pass  # Already removed or invalid
                        self.hover_point = None
                        
                    self.ts_canvas.draw_idle()

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
        
        # Connect hover event for exact date display
        self.ts_canvas.mpl_connect('motion_notify_event', on_hover)

        # Add toolbar for pan/zoom
        if hasattr(self, 'ts_toolbar') and self.ts_toolbar:
            self.ts_toolbar.destroy()
        self.ts_toolbar = NavigationToolbar2Tk(self.ts_canvas, self.ts_frame)
        self.ts_toolbar.update()
        self.ts_toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.btn_save_all.config(state=tk.NORMAL)
        self.time_series_fig = fig
        
        # Store reference to master for pin reset functionality
        self.master_app = self.master

    def save_all_files(self):
        """Save all files: PNG, vector formats, CSV, and map with unified naming"""
        if self.time_series_fig is None or self.time_series_data is None:
            return
            
        # Ask user for save location
        from tkinter import filedialog
        save_dir = filedialog.askdirectory(title="Select Directory to Save Files")
        if not save_dir:
            return
            
        # Generate intelligent filename based on coordinates
        lat_str = f"{'N' if self.lat >= 0 else 'S'}{abs(self.lat):.4f}".replace('.', 'p')
        lon_str = f"{'E' if self.lon >= 0 else 'W'}{abs(self.lon):.4f}".replace('.', 'p')
        base_filename = f"timeseries_{lat_str}_{lon_str}"
        base_path = os.path.join(save_dir, base_filename)
        
        try:
            saved_files = []
            
            # Create a clean figure without hover annotations for saving
            clean_fig = plt.Figure(figsize=(8, 5))
            clean_ax = clean_fig.add_subplot(111)
            
            # Get original data from the time series
            times = self.time_series_data['Time']
            deformation = self.time_series_data['Deformation']
            
            # Plot clean time series
            clean_ax.plot(times, deformation, marker='o', linestyle='-')
            
            # Set up time formatting
            num_years = (times.iloc[-1] - times.iloc[0]).days / 365.0 if len(times) > 1 else 0
            if num_years <= 1:
                clean_ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
                clean_ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
            elif num_years <= 4:
                clean_ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                clean_ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
            else:
                clean_ax.xaxis.set_major_locator(mdates.YearLocator())
                clean_ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
                
            clean_ax.set_title(f"Surface Deformation Time Series at ({self.lat:.4f}, {self.lon:.4f})")
            clean_ax.set_xlabel("Time")
            clean_ax.set_ylabel("Deformation (mm)")
            clean_ax.tick_params(axis='x', rotation=45)
            clean_ax.grid()
            clean_fig.tight_layout()
            
            # Save PNG and vector formats (rcParams already configured globally for true vector output)
            for fmt, ext in [('png', 'png'), ('pdf', 'pdf'), ('svg', 'svg'), ('eps', 'eps'), ('ps', 'ps')]:
                try:
                    file_path = f"{base_path}.{ext}"
                    clean_fig.savefig(file_path, format=fmt, bbox_inches='tight', 
                                    facecolor='white', dpi=300 if fmt == 'png' else None)
                    saved_files.append(f"{fmt.upper()}: {file_path}")
                except Exception as e:
                    print(f"Warning: Could not save {fmt.upper()} file: {e}")
            
            # Close the clean figure
            plt.close(clean_fig)
                    
            # Save CSV
            try:
                csv_path = f"{base_path}.csv"
                self.time_series_data.to_csv(csv_path, index=False)
                saved_files.append(f"CSV: {csv_path}")
            except Exception as e:
                print(f"Warning: Could not save CSV file: {e}")
                
            # Save map with pin location (3x zoom out)
            try:
                if hasattr(self.master_app, 'save_map_with_pin'):
                    map_path = f"{base_path}_map.png"
                    self.master_app.save_map_with_pin(map_path, self.lat, self.lon)
                    saved_files.append(f"MAP: {map_path}")
            except Exception as e:
                print(f"Warning: Could not save map file: {e}")
                
            # Reset pin on master application
            try:
                if hasattr(self.master_app, 'reset_pin'):
                    self.master_app.reset_pin()
            except Exception as e:
                print(f"Warning: Could not reset pin: {e}")
                
            # Close the window after saving
            self.destroy()
            
            if saved_files:
                files_list = "\n".join(saved_files)
                messagebox.showinfo("Files Saved", f"All files saved successfully:\n\n{files_list}")
            else:
                messagebox.showerror("Error", "No files could be saved.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save files:\n{e}")

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
        
        # Polygon and multi-plot management
        self.polygon_points = []
        self.polygon_line = None
        self.polygon_vertex_markers = []  # Track vertex markers for cleanup
        self.open_windows = []
        self.polygon_mode_active = False
        
        # Pin marker
        self.pin_marker = None

        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        frame_top = tk.Frame(self)
        frame_top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        # Latitude and Longitude input (moved to left)
        tk.Label(frame_top, text="Latitude:").pack(side=tk.LEFT, padx=5)
        self.lat_entry = tk.Entry(frame_top, width=10)
        self.lat_entry.pack(side=tk.LEFT)
        tk.Label(frame_top, text="Longitude:").pack(side=tk.LEFT, padx=5)
        self.lon_entry = tk.Entry(frame_top, width=10)
        self.lon_entry.pack(side=tk.LEFT)
        self.plot_btn = tk.Button(frame_top, text="Plot Time Series", command=self.plot_time_series_from_entry)
        self.plot_btn.pack(side=tk.LEFT, padx=10)
        
        # Add polygon drawing controls
        polygon_frame = tk.Frame(frame_top)
        polygon_frame.pack(side=tk.LEFT, padx=20)
        
        self.polygon_mode = tk.BooleanVar()
        self.polygon_checkbox = tk.Checkbutton(polygon_frame, text="Polygon Mode", 
                                             variable=self.polygon_mode, 
                                             command=self.toggle_polygon_mode)
        self.polygon_checkbox.pack(side=tk.LEFT)
        
        self.clear_polygon_btn = tk.Button(polygon_frame, text="Clear Polygon", 
                                          command=self.clear_polygon, state=tk.DISABLED)
        self.clear_polygon_btn.pack(side=tk.LEFT, padx=5)

        # Add status label for click feedback (wider without data path)
        self.status_label = tk.Label(frame_top, text="Click on map to view time series", 
                                   fg="blue", font=("Arial", 9), width=60)
        self.status_label.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # Add hover tooltip for data path (will be implemented in plot_interactive_map)
        self.data_path_tooltip = None

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

        # Load data without ProgressBar to avoid tkinter conflicts
        self.stacked_data = load_all_data_lazy(files_to_load, chunk_dict=chunk_dict)

        vel_file_path = os.path.join(folder_path, "vel_ll.grd")
        if not os.path.exists(vel_file_path):
            messagebox.showerror("Error", "Velocity file vel_ll.grd not found.")
            self.destroy()
            return
        self.vel_file_path = vel_file_path

        self.plot_interactive_map()

    def toggle_polygon_mode(self):
        """Toggle polygon drawing mode"""
        self.polygon_mode_active = self.polygon_mode.get()
        if self.polygon_mode_active:
            self.status_label.config(text="Polygon Mode: Click to draw polygon vertices", fg="orange")
            self.clear_polygon_btn.config(state=tk.NORMAL)
        else:
            # Clear polygon when exiting polygon mode
            self.clear_polygon()
            self.status_label.config(text="Click on map to view time series", fg="blue")
            self.clear_polygon_btn.config(state=tk.DISABLED)
            
    def clear_polygon(self):
        """Clear current polygon"""
        self.polygon_points = []
        if self.polygon_line:
            try:
                self.polygon_line.remove()
            except:
                pass
            self.polygon_line = None
        
        # Clear all vertex markers
        for marker in self.polygon_vertex_markers:
            try:
                marker.remove()
            except:
                pass
        self.polygon_vertex_markers = []
        
        if hasattr(self, 'map_canvas') and self.map_canvas:
            self.map_canvas.draw_idle()
            
    def reset_pin(self):
        """Reset pin marker (called from time series window after saving)"""
        if hasattr(self, 'pin_marker') and self.pin_marker:
            self.pin_marker.remove()
            self.pin_marker = None
        if hasattr(self, 'map_canvas') and self.map_canvas:
            self.map_canvas.draw_idle()
            
    def close_all_windows(self):
        """Close all open time series windows"""
        for window in self.open_windows[:]:
            try:
                window.destroy()
            except:
                pass
        self.open_windows = []
        
    def save_map_with_pin(self, file_path, lat, lon):
        """Save current map with pin at specified location (3x zoom out from current view)"""
        try:
            self._save_context_map(file_path, lat, lon, zoom_factor=3.0)
        except Exception as e:
            print(f"Warning: Could not save map: {e}")
    
    def _save_context_map(self, file_path, lat, lon, zoom_factor=3.0):
        """Save context map with pin, zoomed out by zoom_factor
        
        Args:
            file_path: Path to save the map
            lat, lon: Coordinates for the pin location
            zoom_factor: How much to zoom out (3.0 = 3x zoom out)
        """
        try:
            # Load velocity data
            ds = xr.open_dataarray(self.vel_file_path)
            
            # Detect coordinate names
            lat_name = lon_name = None
            for n in ds.coords:
                if n.lower().startswith("lat"): 
                    lat_name = n; break
            for n in ds.coords:
                if n.lower().startswith("lon"): 
                    lon_name = n; break
            if lat_name is None or lon_name is None:
                if 'y' in ds.coords and 'x' in ds.coords:
                    lat_name, lon_name = 'y', 'x'
                    
            if not (lat_name and lon_name):
                return
                
            lons = ds[lon_name].values
            lats = ds[lat_name].values
            lon2d, lat2d = np.meshgrid(lons, lats)
            vel = ds.values
            
            # Get current map extent if available
            if hasattr(self, 'map_canvas') and self.map_canvas:
                try:
                    ax_current = self.map_canvas.figure.axes[0]
                    current_xlim = ax_current.get_xlim()
                    current_ylim = ax_current.get_ylim()
                    
                    # Calculate center and size
                    center_lon = (current_xlim[0] + current_xlim[1]) / 2
                    center_lat = (current_ylim[0] + current_ylim[1]) / 2
                    width = (current_xlim[1] - current_xlim[0]) * zoom_factor
                    height = (current_ylim[1] - current_ylim[0]) * zoom_factor
                    
                    # Calculate new extent
                    lon_min = max(lons.min(), center_lon - width / 2)
                    lon_max = min(lons.max(), center_lon + width / 2)
                    lat_min = max(lats.min(), center_lat - height / 2)
                    lat_max = min(lats.max(), center_lat + height / 2)
                    
                except:
                    # Fallback: center on pin with reasonable zoom
                    lon_range = lons.max() - lons.min()
                    lat_range = lats.max() - lats.min()
                    margin = 0.1  # 10% margin around pin
                    
                    lon_min = max(lons.min(), lon - lon_range * margin)
                    lon_max = min(lons.max(), lon + lon_range * margin)
                    lat_min = max(lats.min(), lat - lat_range * margin)
                    lat_max = min(lats.max(), lat + lat_range * margin)
            else:
                # No current view, use full extent
                lon_min, lon_max = lons.min(), lons.max()
                lat_min, lat_max = lats.min(), lats.max()
            
            # Create clean map figure with basic matplotlib
            clean_fig = plt.Figure(figsize=(8, 6))
            clean_ax = clean_fig.add_subplot(111)
            clean_ax.set_xlim(lon_min, lon_max)
            clean_ax.set_ylim(lat_min, lat_max)
            
            # Plot velocity map
            c = clean_ax.pcolormesh(lon2d, lat2d, vel, cmap='jet')
            clean_fig.colorbar(c, ax=clean_ax, orientation='vertical')
            clean_ax.set_xlabel('Longitude')
            clean_ax.set_ylabel('Latitude')
            clean_ax.grid(True, alpha=0.3, linestyle='--')
            clean_ax.set_aspect('equal', adjustable='box')
            
            # Add pin at specified location
            clean_ax.plot(lon, lat, '+', markersize=15, 
                        markeredgecolor='red', markeredgewidth=3, 
                        label=f'Location: ({lat:.4f}, {lon:.4f})')
            clean_ax.legend(loc='upper right')
            
            clean_ax.set_title("Surface Deformation Velocity - Context Map")
            clean_fig.tight_layout()
            
            # Save the map
            clean_fig.savefig(file_path, bbox_inches='tight', facecolor='white', dpi=300)
            plt.close(clean_fig)
            
            ds.close()
                
        except Exception as e:
            print(f"Warning: Could not save context map: {e}")

    def process_polygon_selection(self):
        """Process polygon selection and ask user for action"""
        if len(self.polygon_points) < 3:
            messagebox.showwarning("Invalid Polygon", "Polygon must have at least 3 vertices.")
            return
            
        # Ask user what to do with polygon selection
        response = messagebox.askyesnocancel(
            "Polygon Selection", 
            "Multiple pixels selected within polygon.\n\n"
            "Choose action:\n"
            "• YES: Open interactive plots for all pixels\n"
            "• NO: Save all time series files without showing plots\n"
            "• CANCEL: Cancel polygon selection"
        )
        
        if response is None:  # Cancel - clear polygon
            self.clear_polygon()
            return
            
        try:
            # Find all pixels within polygon
            pixels_in_polygon = self._find_pixels_in_polygon()
            
            if not pixels_in_polygon:
                messagebox.showwarning("No Data", "No valid pixels found within the polygon.")
                self.clear_polygon()
                return
                
            if response:  # YES - Interactive plots
                self._show_interactive_polygon_plots(pixels_in_polygon)
            else:  # NO - Save files only
                self._save_polygon_files(pixels_in_polygon)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process polygon: {e}")
            
        # Clear polygon after processing
        self.clear_polygon()
        
    def _find_pixels_in_polygon(self):
        """Find all valid pixels within the drawn polygon"""
        from matplotlib.path import Path
        import numpy as np
        
        # Debug: Print polygon points
        print(f"🔍 Polygon points (lon, lat):")
        for i, (lon, lat) in enumerate(self.polygon_points):
            print(f"   Point {i+1}: ({lon:.4f}, {lat:.4f})")
        
        # Create polygon path
        polygon_path = Path(self.polygon_points)
        
        # Get data coordinates
        ds = xr.open_dataarray(self.vel_file_path)
        
        # Detect coordinate names
        lat_name = lon_name = None
        for n in ds.coords:
            if n.lower().startswith("lat"): 
                lat_name = n; break
        for n in ds.coords:
            if n.lower().startswith("lon"): 
                lon_name = n; break
        if lat_name is None or lon_name is None:
            if 'y' in ds.coords and 'x' in ds.coords:
                lat_name, lon_name = 'y', 'x'
                
        lons = ds[lon_name].values
        lats = ds[lat_name].values
        
        print(f"   Data bounds: Lon [{lons.min():.4f}, {lons.max():.4f}], Lat [{lats.min():.4f}, {lats.max():.4f}]")
        
        ds.close()
        
        pixels_in_polygon = []
        pixels_checked = 0
        pixels_in_bounds = 0
        
        # DON'T subsample for debugging - check all pixels to find the issue
        # After finding pixels, we can re-enable subsampling if needed
        step_size = 1  # Check every pixel
        
        print(f"   Grid size: {len(lats)}x{len(lons)}, step_size: {step_size}")
        
        # Check each pixel
        for i in range(0, len(lats), step_size):
            for j in range(0, len(lons), step_size):
                lat, lon = lats[i], lons[j]
                pixels_checked += 1
                
                # Test containment
                point = (lon, lat)
                if polygon_path.contains_point(point):
                    pixels_in_bounds += 1
                    if pixels_in_bounds <= 5:  # Print first few matches for debugging
                        print(f"   ✓ Pixel ({lat:.6f}, {lon:.6f}) is INSIDE polygon")
                    
                    # Use the same validation as single-click mode
                    quality_info = self._validate_time_series_quality(lat, lon)
                    if quality_info['is_valid']:
                        pixels_in_polygon.append({
                            'lat': lat,
                            'lon': lon,
                            'quality': quality_info
                        })
        
        print(f"✅ Polygon scan complete:")
        print(f"   Pixels checked: {pixels_checked}")
        print(f"   Pixels in polygon bounds: {pixels_in_bounds}")
        print(f"   Valid pixels found: {len(pixels_in_polygon)}")
        
        # If we found pixels, re-run with subsampling to avoid too many
        if pixels_in_bounds > 100:
            print(f"⚠️ Too many pixels ({pixels_in_bounds}), re-running with subsampling...")
            step_size = max(1, int(np.sqrt(pixels_in_bounds / 50)))  # Aim for ~50 pixels
            pixels_in_polygon = []
            
            for i in range(0, len(lats), step_size):
                for j in range(0, len(lons), step_size):
                    lat, lon = lats[i], lons[j]
                    point = (lon, lat)
                    if polygon_path.contains_point(point):
                        quality_info = self._validate_time_series_quality(lat, lon)
                        if quality_info['is_valid']:
                            pixels_in_polygon.append({
                                'lat': lat,
                                'lon': lon,
                                'quality': quality_info
                            })
            
            print(f"   Resampled to {len(pixels_in_polygon)} pixels")
        
        return pixels_in_polygon

    def _show_interactive_polygon_plots(self, pixels_in_polygon):
        """Show interactive time series plots for all pixels in polygon"""
        max_plots = 20  # Limit to prevent overwhelming UI
        
        if len(pixels_in_polygon) > max_plots:
            response = messagebox.askyesno(
                "Too Many Plots",
                f"Polygon contains {len(pixels_in_polygon)} valid pixels. "
                f"Opening more than {max_plots} interactive plots may be overwhelming.\n\n"
                f"Do you want to open the {max_plots} best quality pixels instead?"
            )
            if response:
                # Sort by quality score and take top pixels
                pixels_in_polygon.sort(key=lambda x: x['quality']['quality_score'], reverse=True)
                pixels_in_polygon = pixels_in_polygon[:max_plots]
            else:
                return
        
        # Close existing windows
        self.close_all_windows()
        
        # Open time series for each pixel
        for pixel in pixels_in_polygon:
            try:
                window = TimeSeriesWindow(self, pixel['lat'], pixel['lon'], self.stacked_data)
                self.open_windows.append(window)
            except Exception as e:
                print(f"Warning: Failed to open time series for pixel ({pixel['lat']:.4f}, {pixel['lon']:.4f}): {e}")
        
        self.status_label.config(text=f"Opened {len(self.open_windows)} time series windows", fg="green")
        
    def _save_polygon_files(self, pixels_in_polygon):
        """Save time series files for all pixels without opening plots"""
        from tkinter import filedialog
        import os
        
        save_dir = filedialog.askdirectory(title="Select Directory to Save Polygon Time Series")
        if not save_dir:
            return
        
        # Create subdirectory for this polygon
        polygon_dir = os.path.join(save_dir, f"polygon_{len(self.polygon_points)}vertices_{len(pixels_in_polygon)}pixels")
        os.makedirs(polygon_dir, exist_ok=True)
        
        progress_window = tk.Toplevel(self)
        progress_window.title("Saving Polygon Time Series")
        progress_window.geometry("400x150")
        progress_window.grab_set()  # Make modal
        
        tk.Label(progress_window, text="Processing polygon selection...", font=("Arial", 12)).pack(pady=10)
        
        progress_var = tk.StringVar()
        progress_label = tk.Label(progress_window, textvariable=progress_var)
        progress_label.pack(pady=5)
        
        progress_bar_frame = tk.Frame(progress_window)
        progress_bar_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Simple progress bar using Label (since tkinter.ttk may not be available)
        progress_bar = tk.Label(progress_bar_frame, text="", bg="lightblue", height=1)
        progress_bar.pack(fill=tk.X)
        
        saved_count = 0
        total_pixels = len(pixels_in_polygon)
        
        for i, pixel in enumerate(pixels_in_polygon):
            try:
                # Update progress
                progress_var.set(f"Processing pixel {i+1} of {total_pixels}")
                progress_width = int((i+1) / total_pixels * 40)  # 40 characters wide
                progress_text = "█" * progress_width + "░" * (40 - progress_width)
                progress_bar.config(text=progress_text)
                progress_window.update()
                
                lat, lon = pixel['lat'], pixel['lon']
                
                # Extract time series data
                lat_name = lon_name = None
                for n in self.stacked_data.coords:
                    if n.lower().startswith("lat"): lat_name = n; break
                for n in self.stacked_data.coords:
                    if n.lower().startswith("lon"): lon_name = n; break
                if lat_name is None or lon_name is None:
                    if 'y' in self.stacked_data.coords and 'x' in self.stacked_data.coords:
                        lat_name, lon_name = 'y', 'x'
                    else:
                        continue
                
                point_series = self.stacked_data.sel({lat_name: lat, lon_name: lon}, method="nearest")
                times = pd.to_datetime(point_series['time'].values)
                deformation = point_series.values.astype(float)
                
                # Get actual coordinates
                actual_lat = float(point_series[lat_name].values)
                actual_lon = float(point_series[lon_name].values)
                
                # Create filename
                lat_str = f"{'N' if actual_lat >= 0 else 'S'}{abs(actual_lat):.4f}".replace('.', 'p')
                lon_str = f"{'E' if actual_lon >= 0 else 'W'}{abs(actual_lon):.4f}".replace('.', 'p')
                base_filename = f"timeseries_{lat_str}_{lon_str}"
                
                # Save CSV
                csv_path = os.path.join(polygon_dir, f"{base_filename}.csv")
                time_series_data = pd.DataFrame({"Time": times, "Deformation": deformation})
                time_series_data.to_csv(csv_path, index=False)
                
                # Create and save plot
                fig = plt.Figure(figsize=(8, 5))
                ax = fig.add_subplot(111)
                ax.plot(times, deformation, marker='o', linestyle='-')
                
                # Format time axis
                num_years = (times[-1] - times[0]).days / 365.0 if len(times) > 1 else 0
                if num_years <= 1:
                    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
                elif num_years <= 4:
                    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
                else:
                    ax.xaxis.set_major_locator(mdates.YearLocator())
                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
                
                ax.set_title(f"Time Series at ({actual_lat:.4f}, {actual_lon:.4f})")
                ax.set_xlabel("Time")
                ax.set_ylabel("Deformation (mm)")
                ax.tick_params(axis='x', rotation=45)
                ax.grid()
                fig.tight_layout()
                
                # Save PNG (rcParams already configured globally for true vector output)
                png_path = os.path.join(polygon_dir, f"{base_filename}.png")
                fig.savefig(png_path, bbox_inches='tight', facecolor='white', dpi=300)
                
                # Save true vector formats
                for fmt in ['pdf', 'svg', 'eps']:
                    vector_path = os.path.join(polygon_dir, f"{base_filename}.{fmt}")
                    fig.savefig(vector_path, format=fmt, bbox_inches='tight', facecolor='white')
                
                plt.close(fig)
                
                # Save context map with pin (3x zoom out)
                try:
                    map_path = os.path.join(polygon_dir, f"{base_filename}_map.png")
                    self._save_context_map(map_path, actual_lat, actual_lon, zoom_factor=3.0)
                except Exception as e:
                    print(f"Warning: Could not save context map: {e}")
                
                saved_count += 1
                
            except Exception as e:
                print(f"Warning: Failed to save files for pixel ({lat:.4f}, {lon:.4f}): {e}")
        
        progress_window.destroy()
        
        # Show completion message
        messagebox.showinfo(
            "Polygon Processing Complete",
            f"Successfully saved {saved_count} out of {total_pixels} time series.\n\n"
            f"Files saved to: {polygon_dir}"
        )
        
        self.status_label.config(text=f"Saved {saved_count} polygon time series files", fg="green")
        
    def _validate_time_series_quality(self, lat, lon, min_valid_ratio=0.05):
        """Validate time series data quality at given coordinates.
        
        Args:
            lat, lon: Coordinates to check
            min_valid_ratio: Minimum ratio of valid (non-NaN) time points required
        
        Returns:
            dict: Quality metrics for the time series
        """
        try:
            # Detect coordinate names
            lat_name = lon_name = None
            for n in self.stacked_data.coords:
                if n.lower().startswith("lat"): 
                    lat_name = n
                    break
            for n in self.stacked_data.coords:
                if n.lower().startswith("lon"): 
                    lon_name = n
                    break
            if lat_name is None or lon_name is None:
                if 'y' in self.stacked_data.coords and 'x' in self.stacked_data.coords:
                    lat_name, lon_name = 'y', 'x'
                else:
                    return {'is_valid': False, 'valid_count': 0, 'total_count': 0, 
                           'valid_ratio': 0.0, 'first_valid_idx': None, 'last_valid_idx': None,
                           'data_span_days': 0, 'quality_score': 0.0}
            
            # Extract time series at the coordinates
            point_series = self.stacked_data.sel({lat_name: lat, lon_name: lon}, method="nearest")
            times = pd.to_datetime(point_series['time'].values)
            deformation = point_series.values.astype(float)
            
            # Simple validation - just check if we have any data at all
            total_count = len(deformation)
            valid_mask = ~np.isnan(deformation)
            valid_count = np.sum(valid_mask)
            valid_ratio = valid_count / total_count if total_count > 0 else 0.0
            
            # Find first and last valid indices
            valid_indices = np.where(valid_mask)[0]
            first_valid_idx = valid_indices[0] if len(valid_indices) > 0 else None
            last_valid_idx = valid_indices[-1] if len(valid_indices) > 0 else None
            
            # Calculate data span
            data_span_days = 0
            if first_valid_idx is not None and last_valid_idx is not None and len(times) > 1:
                first_time = times[first_valid_idx]
                last_time = times[last_valid_idx]
                data_span_days = (last_time - first_time).days
            
            # Calculate quality score (0-1)
            quality_score = 0.0
            if valid_count > 0:
                # Base score from valid ratio
                quality_score = valid_ratio
                
                # Bonus for temporal span (prefer data covering longer periods)
                if data_span_days > 365:  # More than 1 year
                    quality_score *= 1.2
                elif data_span_days > 180:  # More than 6 months
                    quality_score *= 1.1
                
                # Bonus for minimum absolute count
                if valid_count >= 10:
                    quality_score *= 1.1
                elif valid_count >= 5:
                    quality_score *= 1.05
                
                # Cap at 1.0
                quality_score = min(1.0, quality_score)
            
            # Very lenient validation - accept anything with at least 1 valid point
            # This matches what single-click does (it opens windows even with sparse data)
            is_valid = (total_count > 0 and valid_count >= 1)
            
            return {
                'is_valid': is_valid,
                'valid_count': valid_count,
                'total_count': total_count, 
                'valid_ratio': valid_ratio,
                'first_valid_idx': first_valid_idx,
                'last_valid_idx': last_valid_idx,
                'data_span_days': data_span_days,
                'quality_score': quality_score
            }
            
        except Exception as e:
            print(f"Warning: Time series validation failed: {e}")
            return {'is_valid': False, 'valid_count': 0, 'total_count': 0,
                   'valid_ratio': 0.0, 'first_valid_idx': None, 'last_valid_idx': None,
                   'data_span_days': 0, 'quality_score': 0.0}

    def _find_nearest_valid_pixel(self, lon_click, lat_click, tolerance_factor=3.0):
        """Find nearest pixel with valid time series data within tolerance zone.
        
        Args:
            lon_click, lat_click: Clicked coordinates
            tolerance_factor: Multiplier for pixel resolution to define search radius
        
        Returns:
            tuple: (lon_nearest, lat_nearest, quality_info) if valid pixel found, (None, None, None) otherwise
        """
        try:
            # Load small sample to get coordinate info
            ds = xr.open_dataarray(self.vel_file_path)
            
            # Detect coordinate names
            lat_name = lon_name = None
            for n in ds.coords:
                if n.lower().startswith("lat"): 
                    lat_name = n
                    break
            for n in ds.coords:
                if n.lower().startswith("lon"): 
                    lon_name = n
                    break
            if lat_name is None or lon_name is None:
                if 'y' in ds.coords and 'x' in ds.coords:
                    lat_name, lon_name = 'y', 'x'
                else:
                    return None, None, None
            
            lons = ds[lon_name].values
            lats = ds[lat_name].values
            
            # Calculate pixel resolution
            lon_res = abs(np.mean(np.diff(lons))) if len(lons) > 1 else 0.001
            lat_res = abs(np.mean(np.diff(lats))) if len(lats) > 1 else 0.001
            
            # Define search radius based on pixel resolution
            search_radius_lon = lon_res * tolerance_factor
            search_radius_lat = lat_res * tolerance_factor
            
            # Check if click is within data bounds with some buffer
            if (lon_click < lons.min() - search_radius_lon or 
                lon_click > lons.max() + search_radius_lon or
                lat_click < lats.min() - search_radius_lat or 
                lat_click > lats.max() + search_radius_lat):
                return None, None, None
            
            # Find nearest pixel and validate its time series quality
            try:
                nearest_point = ds.sel({lat_name: lat_click, lon_name: lon_click}, method="nearest")
                
                # Get coordinates of nearest pixel
                nearest_lat = float(nearest_point[lat_name].values)
                nearest_lon = float(nearest_point[lon_name].values)
                
                # Check if within tolerance
                lat_dist = abs(nearest_lat - lat_click)
                lon_dist = abs(nearest_lon - lon_click)
                
                if lat_dist <= search_radius_lat and lon_dist <= search_radius_lon:
                    # Validate time series quality at this location
                    quality_info = self._validate_time_series_quality(nearest_lat, nearest_lon)
                    
                    if quality_info['is_valid']:
                        ds.close()
                        return nearest_lon, nearest_lat, quality_info
                
                # If nearest pixel has poor time series, search nearby pixels
                lon_idx = np.argmin(np.abs(lons - lon_click))
                lat_idx = np.argmin(np.abs(lats - lat_click))
                
                # Create list of candidates with their quality scores
                candidates = []
                
                # Search in expanding square around nearest pixel
                for radius in range(1, min(6, len(lons)//10, len(lats)//10)):
                    for di in range(-radius, radius+1):
                        for dj in range(-radius, radius+1):
                            try:
                                test_lat_idx = lat_idx + di
                                test_lon_idx = lon_idx + dj
                                
                                if (0 <= test_lat_idx < len(lats) and 
                                    0 <= test_lon_idx < len(lons)):
                                    
                                    test_lat = lats[test_lat_idx]
                                    test_lon = lons[test_lon_idx]
                                    
                                    # Check if within tolerance
                                    if (abs(test_lat - lat_click) <= search_radius_lat and 
                                        abs(test_lon - lon_click) <= search_radius_lon):
                                        
                                        # Validate time series quality
                                        test_quality = self._validate_time_series_quality(test_lat, test_lon)
                                        
                                        if test_quality['is_valid']:
                                            # Calculate distance for ranking
                                            distance = np.sqrt((test_lat - lat_click)**2 + (test_lon - lon_click)**2)
                                            candidates.append({
                                                'lat': test_lat,
                                                'lon': test_lon, 
                                                'quality': test_quality,
                                                'distance': distance,
                                                'score': test_quality['quality_score'] / (1 + distance)  # Quality/distance ratio
                                            })
                            except:
                                continue
                    
                    # If we found valid candidates, pick the best one
                    if candidates:
                        best_candidate = max(candidates, key=lambda x: x['score'])
                        ds.close()
                        return best_candidate['lon'], best_candidate['lat'], best_candidate['quality']
                
            except Exception as e:
                print(f"Warning: Time series search failed: {e}")
            
            ds.close()
            return None, None, None
            
        except Exception as e:
            print(f"Error in pixel search: {e}")
            return None, None, None

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

        # Create figure with basic matplotlib (no cartopy)
        fig = plt.Figure(figsize=(8, 6))
        ax = fig.add_subplot(111)
        
        # Plot velocity map
        c = ax.pcolormesh(lon2d, lat2d, vel, cmap='jet')
        fig.colorbar(c, ax=ax, orientation='vertical')
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.set_title("Interactive Map of Surface Deformation Velocity")
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_aspect('equal', adjustable='box')

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

        # Simple click handler - no dragging
        
        # Click handler with polygon mode support
        def onclick(event):
            if event.inaxes != ax:
                return

            # Check if pan/zoom is active
            if self.toolbar.mode != '':
                # Skip click when panning/zooming
                return

            lon_click, lat_click = event.xdata, event.ydata
            if lon_click is None or lat_click is None:
                return

            # Handle polygon mode FIRST - complete isolation from other modes
            if self.polygon_mode_active:
                if event.button == 1:  # Left click only
                    # Add point to polygon
                    self.polygon_points.append((lon_click, lat_click))
                    self.status_label.config(text=f"Polygon: {len(self.polygon_points)} vertices (Right-click to finish)", fg="orange")
                    
                    # Update polygon visualization
                    if len(self.polygon_points) > 1:
                        if self.polygon_line:
                            self.polygon_line.remove()
                        
                        # Create closed polygon for visualization
                        poly_x = [p[0] for p in self.polygon_points] + [self.polygon_points[0][0]]
                        poly_y = [p[1] for p in self.polygon_points] + [self.polygon_points[0][1]]
                        self.polygon_line, = ax.plot(poly_x, poly_y, 'g-', linewidth=2, alpha=0.7)
                        
                    # Add vertex marker and store it for cleanup
                    vertex_marker, = ax.plot(lon_click, lat_click, 'go', markersize=8)
                    self.polygon_vertex_markers.append(vertex_marker)
                    self.map_canvas.draw_idle()
                    return  # COMPLETE EXIT from function
                
                elif event.button == 3:  # Right click to finalize
                    if len(self.polygon_points) >= 3:
                        self.process_polygon_selection()
                    return  # COMPLETE EXIT from function
                
                else:
                    # Any other button in polygon mode - ignore
                    return

            # Regular single-point mode
            # Close all existing windows and remove pin
            for window in self.open_windows[:]:
                try:
                    window.destroy()
                except:
                    pass
            self.open_windows = []
            
            if self.pin_marker:
                try:
                    self.pin_marker.remove()
                except:
                    pass
                self.pin_marker = None
            
            if ax.get_legend():
                try:
                    ax.get_legend().remove()
                except:
                    pass
            
            # Find nearest valid pixel with quality time series data
            result = self._find_nearest_valid_pixel(lon_click, lat_click)
            lon_nearest, lat_nearest, quality_info = result if result[0] is not None else (None, None, None)
            
            if lon_nearest is not None and lat_nearest is not None:
                print(f"📍 Click at ({lat_click:.4f}, {lon_click:.4f}) → Valid pixel: ({lat_nearest:.4f}, {lon_nearest:.4f})")
                print(f"📊 Time series quality: {quality_info['valid_count']}/{quality_info['total_count']} valid points ({quality_info['valid_ratio']:.1%})")
                
                # Create new pin marker at selected location
                self.pin_marker = ax.plot(lon_nearest, lat_nearest, '+', markersize=15, 
                                        markeredgecolor='red', markeredgewidth=3, 
                                        label=f'Selected: ({lat_nearest:.4f}, {lon_nearest:.4f})')[0]
                ax.legend(loc='upper right')
                self.map_canvas.draw_idle()
                
                self.status_label.config(text=f"✅ Opening time series ({quality_info['valid_count']} points) at ({lat_nearest:.4f}, {lon_nearest:.4f})", fg="green")
                self.update()
                try:
                    window = TimeSeriesWindow(self, lat_nearest, lon_nearest, self.stacked_data)
                    self.open_windows.append(window)
                    self.status_label.config(text="Click on map to view time series", fg="blue")
                except Exception as e:
                    self.status_label.config(text="❌ Failed to create time series", fg="red")
                    messagebox.showerror("Time Series Error", 
                                       f"Failed to create time series plot:\n{str(e)}\n\n"
                                       f"Clicked: ({lat_click:.4f}, {lon_click:.4f})\n"
                                       f"Selected pixel: ({lat_nearest:.4f}, {lon_nearest:.4f})")
            else:
                # Provide helpful feedback for failed clicks
                try:
                    # Check if click is within general data bounds
                    ds_temp = xr.open_dataarray(self.vel_file_path)
                    lat_name = lon_name = None
                    for n in ds_temp.coords:
                        if n.lower().startswith("lat"): lat_name = n; break
                    for n in ds_temp.coords:
                        if n.lower().startswith("lon"): lon_name = n; break
                    if lat_name is None or lon_name is None:
                        if 'y' in ds_temp.coords and 'x' in ds_temp.coords:
                            lat_name, lon_name = 'y', 'x'
                    
                    if lat_name and lon_name:
                        lons = ds_temp[lon_name].values
                        lats = ds_temp[lat_name].values
                        
                        if (lon_click < lons.min() or lon_click > lons.max() or
                            lat_click < lats.min() or lat_click > lats.max()):
                            feedback_msg = f"Click outside data bounds.\n\nClicked: ({lat_click:.4f}, {lon_click:.4f})\nData bounds: Lat [{lats.min():.4f}, {lats.max():.4f}], Lon [{lons.min():.4f}, {lons.max():.4f}]"
                        else:
                            feedback_msg = f"No valid time series data found near clicked location.\n\nClicked: ({lat_click:.4f}, {lon_click:.4f})\n\nThe clicked area may have insufficient temporal coverage or too many missing values.\nTry clicking on areas with consistent colored data across the map."
                    else:
                        feedback_msg = f"Unable to extract time series at clicked location.\n\nClicked: ({lat_click:.4f}, {lon_click:.4f})"
                    
                    ds_temp.close()
                    
                except Exception:
                    feedback_msg = f"No valid time series data at clicked location: ({lat_click:.4f}, {lon_click:.4f})"
                
                self.status_label.config(text="❌ No valid time series data at clicked location", fg="red")
                messagebox.showwarning("No Time Series Data", feedback_msg)

        # Connect only the click event
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
