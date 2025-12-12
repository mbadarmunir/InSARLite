import tkinter as tk
from tkinter import ttk, messagebox
from tkintermapview import TkinterMapView
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import numpy as np
import os
import subprocess
from ..utils.utils import create_ref_point_ra
try:
    import rioxarray
    RIOXARRAY_AVAILABLE = True
except ImportError:
    RIOXARRAY_AVAILABLE = False


class ReferencePointGUI(tk.Toplevel):
    def __init__(self, parent, dem, save_dir=None):
        super().__init__(parent)
        self.save_dir = save_dir
        if os.path.basename(self.save_dir) == "merge":
            self.topodir = self.save_dir
        else:
            self.topodir = os.path.join(os.path.dirname(self.save_dir), "topo")
        
        self.title("Enhanced Reference Point Selector")
        self.geometry("1000x700")
        self.dem = dem
        
        # File paths
        self.corr_stack_path = os.path.join(self.save_dir, "corr_stack.grd")
        self.validity_path = os.path.join(self.save_dir, "validity_pin.grd")
        self.std_path = os.path.join(self.save_dir, "std.grd")
        
        # Check if validity raster exists
        self.validity_available = os.path.exists(self.validity_path)
        
        # Current selection variables
        self.current_lat = None
        self.current_lon = None
        self.current_x = None
        self.current_y = None
        self.current_validity_count = None
        self.current_corr_value = None

        # Disable close (X) button
        self.protocol("WM_DELETE_WINDOW", self.disable_close)
        self.bind("<Alt-F4>", lambda e: "break")
        self.bind("<Escape>", lambda e: "break")
        self.resizable(False, False)

        # Try to initialize enhanced GUI, fallback to simple if it fails
        try:
            self._init_widgets()
            self._load_grid_data()
        except Exception as e:
            print(f"Enhanced GUI failed to initialize: {e}")
            print("Falling back to simple reference point GUI...")
            self._init_simple_gui()

    def _init_widgets(self):
        # Main layout: left panel for options and coordinates, right panel for visualization
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        left_panel = ttk.Frame(main_frame, width=300)
        left_panel.pack(side="left", fill="y", padx=(0, 10))
        left_panel.pack_propagate(False)
        
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side="right", fill="both", expand=True)
        
        # === Left Panel ===
        
        # Option selection
        self.option_var = tk.StringVar(value="highest_corr")
        options_frame = ttk.LabelFrame(left_panel, text="Automatic Selection Options")
        options_frame.pack(fill="x", pady=(0, 10))

        options = [
            ("Highest mean correlation", "highest_corr"),
            ("Lowest standard deviation", "lowest_std"),
            ("Manual definition", "define")
        ]

        for text, value in options:
            ttk.Radiobutton(options_frame, text=text, variable=self.option_var, 
                          value=value, command=self.on_option_change).pack(anchor="w", padx=5, pady=2)

        # Coordinate input frame
        self.coord_frame = ttk.LabelFrame(left_panel, text="Coordinate Input")
        # Don't pack initially - will be shown only when Manual definition is selected
        
        # Coordinate system selection
        self.coord_system_var = tk.StringVar(value="geographic")
        coord_sys_frame = ttk.Frame(self.coord_frame)
        coord_sys_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Radiobutton(coord_sys_frame, text="Geographic (Lat/Lon)", variable=self.coord_system_var,
                       value="geographic", command=self.on_coord_system_change).pack(anchor="w")
        ttk.Radiobutton(coord_sys_frame, text="Radar (Range/Azimuth)", variable=self.coord_system_var,
                       value="radar", command=self.on_coord_system_change).pack(anchor="w")
        
        # Geographic coordinates
        self.geo_frame = ttk.Frame(self.coord_frame)
        # Don't pack initially - will be shown when Manual definition is selected
        
        ttk.Label(self.geo_frame, text="Latitude:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.lat_var = tk.StringVar()
        self.lat_entry = ttk.Entry(self.geo_frame, textvariable=self.lat_var, width=12)
        self.lat_entry.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(self.geo_frame, text="Longitude:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.lon_var = tk.StringVar()
        self.lon_entry = ttk.Entry(self.geo_frame, textvariable=self.lon_var, width=12)
        self.lon_entry.grid(row=1, column=1, padx=5, pady=2)
        
        # Radar coordinates
        self.radar_frame = ttk.Frame(self.coord_frame)
        # Don't pack initially - will be shown when Manual definition is selected
        
        ttk.Label(self.radar_frame, text="Range:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.range_var = tk.StringVar()
        self.range_entry = ttk.Entry(self.radar_frame, textvariable=self.range_var, width=12)
        self.range_entry.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(self.radar_frame, text="Azimuth:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.azimuth_var = tk.StringVar()
        self.azimuth_entry = ttk.Entry(self.radar_frame, textvariable=self.azimuth_var, width=12)
        self.azimuth_entry.grid(row=1, column=1, padx=5, pady=2)
        
        # Coordinate conversion button
        self.convert_btn = ttk.Button(self.coord_frame, text="Convert & Update", command=self.convert_coordinates)
        # Don't pack initially - will be shown when Manual definition is selected
        
        # Current selection info
        info_frame = ttk.LabelFrame(left_panel, text="Current Selection Info")
        info_frame.pack(fill="x", pady=(0, 10))
        
        self.info_text = tk.Text(info_frame, height=8, width=35, wrap=tk.WORD, state=tk.DISABLED)
        self.info_text.pack(padx=5, pady=5, fill="x")
        
        # Buttons
        button_frame = ttk.Frame(left_panel)
        button_frame.pack(fill="x", pady=(0, 10))
        
        self.submit_btn = ttk.Button(button_frame, text="Submit Selection", command=self.submit_selection)
        self.submit_btn.pack(fill="x", pady=2)
        
        # === Right Panel ===
        
        # Visualization tabs
        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill="both", expand=True)
        
        # Tab 1: Correlation stack
        self.corr_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.corr_tab, text="Mean Correlation")
        
        # Tab 2: Validity raster (if available)
        if self.validity_available:
            self.validity_tab = ttk.Frame(self.notebook)
            self.notebook.add(self.validity_tab, text="Validity Count")
        
        # Setup matplotlib figures
        self.setup_correlation_plot()
        if self.validity_available:
            self.setup_validity_plot()
        
        # Bind coordinate entry changes
        self.lat_var.trace_add("write", self.on_coordinate_change)
        self.lon_var.trace_add("write", self.on_coordinate_change)
        self.range_var.trace_add("write", self.on_coordinate_change)
        self.azimuth_var.trace_add("write", self.on_coordinate_change)
        
        # Initial state - set coordinate input visibility first
        self._set_coordinate_input_visibility()

    def _set_coordinate_input_visibility(self):
        """Set coordinate input visibility without triggering automatic selection"""
        option = self.option_var.get()
        if option == "define":
            # Show entire coordinate input section for manual definition
            self.coord_frame.pack(fill="x", pady=(0, 10))
            self.on_coord_system_change()  # This will show the appropriate frame
            self.convert_btn.pack(pady=5)
            
            # Enable manual coordinate input
            self.lat_entry.config(state="normal")
            self.lon_entry.config(state="normal")
            self.range_entry.config(state="normal")
            self.azimuth_entry.config(state="normal")
            self.convert_btn.config(state="normal")
        else:
            # Hide entire coordinate input section for automatic selection (highest_corr, lowest_std)
            self.coord_frame.pack_forget()

    def setup_correlation_plot(self):
        """Setup matplotlib plot for correlation visualization"""
        self.corr_fig = Figure(figsize=(6, 5), dpi=80)
        self.corr_ax = self.corr_fig.add_subplot(111)
        
        self.corr_canvas = FigureCanvasTkAgg(self.corr_fig, self.corr_tab)
        self.corr_canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Add navigation toolbar for zoom and pan
        self.corr_toolbar = NavigationToolbar2Tk(self.corr_canvas, self.corr_tab)
        self.corr_toolbar.update()
        
        # Bind click events
        self.corr_canvas.mpl_connect('button_press_event', self.on_corr_plot_click)
        self.corr_canvas.mpl_connect('motion_notify_event', self.on_corr_plot_hover)

    def setup_validity_plot(self):
        """Setup matplotlib plot for validity visualization"""
        self.validity_fig = Figure(figsize=(6, 5), dpi=80)
        self.validity_ax = self.validity_fig.add_subplot(111)
        
        self.validity_canvas = FigureCanvasTkAgg(self.validity_fig, self.validity_tab)
        self.validity_canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Add navigation toolbar for zoom and pan
        self.validity_toolbar = NavigationToolbar2Tk(self.validity_canvas, self.validity_tab)
        self.validity_toolbar.update()
        
        # Bind click events
        self.validity_canvas.mpl_connect('button_press_event', self.on_validity_plot_click)
        self.validity_canvas.mpl_connect('motion_notify_event', self.on_validity_plot_hover)

    def _load_grid_data(self):
        """Load grid data using GMT"""
        try:
            # Load correlation data
            if os.path.exists(self.corr_stack_path):
                print(f"Loading correlation data from: {self.corr_stack_path}")
                self.corr_data, self.corr_extent = self._load_grd_data(self.corr_stack_path)
                if self.corr_data is not None:
                    self._plot_correlation()
                else:
                    print("Failed to load correlation data")
                    # Create empty plot with message
                    self.corr_ax.text(0.5, 0.5, 'Failed to load correlation data', 
                                    ha='center', va='center', transform=self.corr_ax.transAxes)
                    self.corr_canvas.draw()
            else:
                print(f"Correlation file not found: {self.corr_stack_path}")
                # Create empty plot with message
                self.corr_ax.text(0.5, 0.5, 'Correlation data not available', 
                                ha='center', va='center', transform=self.corr_ax.transAxes)
                self.corr_canvas.draw()
            
            # Load validity data if available
            if self.validity_available and os.path.exists(self.validity_path):
                print(f"Loading validity data from: {self.validity_path}")
                self.validity_data, self.validity_extent = self._load_grd_data(self.validity_path)
                if self.validity_data is not None:
                    self._plot_validity()
                else:
                    print("Failed to load validity data")
                    # Create empty plot with message
                    self.validity_ax.text(0.5, 0.5, 'Failed to load validity data', 
                                        ha='center', va='center', transform=self.validity_ax.transAxes)
                    self.validity_canvas.draw()
            elif self.validity_available:
                print(f"Validity file not found: {self.validity_path}")
                # Create empty plot with message
                self.validity_ax.text(0.5, 0.5, 'Validity data not available', 
                                    ha='center', va='center', transform=self.validity_ax.transAxes)
                self.validity_canvas.draw()
                
        except Exception as e:
            print(f"Error loading grid data: {e}")
            messagebox.showerror("Data Loading Error", f"Failed to load grid data: {str(e)}\n\nYou can still use manual coordinate input.")
            
            # Create error message plots
            error_msg = f'Error loading data:\n{str(e)}'
            self.corr_ax.text(0.5, 0.5, error_msg, ha='center', va='center', 
                            transform=self.corr_ax.transAxes, wrap=True)
            self.corr_canvas.draw()
            
            if self.validity_available:
                self.validity_ax.text(0.5, 0.5, error_msg, ha='center', va='center', 
                                    transform=self.validity_ax.transAxes, wrap=True)
                self.validity_canvas.draw()
        
        # After data is loaded, trigger initial automatic selection if appropriate
        self._trigger_initial_selection()
    
    def _trigger_initial_selection(self):
        """Trigger initial automatic selection after data is loaded"""
        option = self.option_var.get()
        if option == "highest_corr":
            self.select_highest_correlation()
        elif option == "lowest_std":
            self.select_lowest_std()

    def _load_grd_data(self, grd_path):
        """Load GMT grid data using rioxarray (same method as masking)"""
        try:
            print(f"Attempting to load grid data from: {grd_path}")
            
            # Check if file exists and is readable
            if not os.path.exists(grd_path):
                print(f"Grid file does not exist: {grd_path}")
                return None, None
                
            if not os.access(grd_path, os.R_OK):
                print(f"Grid file is not readable: {grd_path}")
                return None, None
            
            # Use rioxarray to load the grid (same as masking)
            print("Loading grid with rioxarray...")
            if not RIOXARRAY_AVAILABLE:
                print("rioxarray not available, falling back to GMT method...")
                return self._load_grd_data_gmt(grd_path)
                
            ds = rioxarray.open_rasterio(grd_path)
            data = ds.values.squeeze()
            
            x0, x1 = float(ds.x[0]), float(ds.x[-1])
            y0, y1 = float(ds.y[0]), float(ds.y[-1])
            
            print(f"Grid dimensions: {data.shape}")
            print(f"Coordinates: X: {x0} to {x1}, Y: {y0} to {y1}")
            
            extent = [x0, x1, y0, y1]
            print(f"Data extent: {extent}")
            
            # Close the dataset
            ds.close()
            
            return data, extent
            
        except ImportError:
            print("rioxarray not available, falling back to GMT method...")
            return self._load_grd_data_gmt(grd_path)
        except Exception as e:
            print(f"Error loading with rioxarray: {e}, falling back to GMT method...")
            return self._load_grd_data_gmt(grd_path)

    def _load_grd_data_gmt(self, grd_path):
        """Fallback GMT grid data loading using gmt grd2xyz"""
        try:
            print(f"GMT fallback: Attempting to load grid data from: {grd_path}")
            
            # Check if file exists and is readable
            if not os.path.exists(grd_path):
                print(f"Grid file does not exist: {grd_path}")
                return None, None
                
            if not os.access(grd_path, os.R_OK):
                print(f"Grid file is not readable: {grd_path}")
                return None, None
            
            # Use GMT to convert grid to xyz with data reduction for large files
            print("Running GMT grd2xyz command...")
            
            # For very large files, try with decimation to avoid timeout
            try:
                # First try with decimation for faster loading
                result = subprocess.run(
                    ["gmt", "grd2xyz", grd_path, "-I5"], # Every 5th point 
                    capture_output=True, text=True, check=True, timeout=30
                )
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                print("Decimated version failed, trying full resolution with longer timeout...")
                result = subprocess.run(
                    ["gmt", "grd2xyz", grd_path],
                    capture_output=True, text=True, check=True, timeout=120  # Even longer timeout
                )
            
            # Parse the xyz data
            lines = result.stdout.strip().split('\n')
            if not lines or lines[0] == '':
                print("GMT command returned empty output")
                return None, None
                
            x_coords = []
            y_coords = []
            values = []
            
            print(f"Parsing {len(lines)} lines of data...")
            for i, line in enumerate(lines[:5000]):  # Increased limit but still reasonable
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3 and parts[2] != 'NaN':
                        try:
                            x_coords.append(float(parts[0]))
                            y_coords.append(float(parts[1]))
                            values.append(float(parts[2]))
                        except ValueError:
                            continue
            
            if not x_coords or not y_coords or not values:
                print("No valid data points found")
                return None, None
            
            print(f"Found {len(values)} valid data points")
            
            # Create regular grid
            x_unique = sorted(set(x_coords))
            y_unique = sorted(set(y_coords))
            
            print(f"Grid dimensions: {len(x_unique)} x {len(y_unique)}")
            
            # Create meshgrid
            X, Y = np.meshgrid(x_unique, y_unique)
            Z = np.full(X.shape, np.nan)
            
            # Fill in the values
            for i, (x, y, z) in enumerate(zip(x_coords, y_coords, values)):
                try:
                    xi = x_unique.index(x)
                    yi = y_unique.index(y)
                    Z[yi, xi] = z
                except (ValueError, IndexError):
                    continue
            
            extent = [min(x_unique), max(x_unique), min(y_unique), max(y_unique)]
            print(f"Data extent: {extent}")
            
            return Z, extent
            
        except subprocess.TimeoutExpired:
            print(f"GMT command timed out for {grd_path}")
            print("This can happen with very large grid files. Consider using a smaller subset or checking if the file is corrupted.")
            return None, None
        except subprocess.CalledProcessError as e:
            print(f"GMT command failed for {grd_path}: {e}")
            print(f"GMT stderr: {e.stderr if e.stderr else 'No error details'}")
            return None, None
        except Exception as e:
            print(f"Error loading {grd_path}: {e}")
            return None, None

    def _plot_correlation(self):
        """Plot correlation data"""
        if self.corr_data is not None:
            self.corr_ax.clear()
            im = self.corr_ax.imshow(self.corr_data, extent=self.corr_extent, 
                                   aspect='auto', origin='lower', cmap='viridis')
            self.corr_ax.set_title('Mean Correlation')
            self.corr_ax.set_xlabel('Range')
            self.corr_ax.set_ylabel('Azimuth')
            
            # Add colorbar
            if hasattr(self, 'corr_cbar'):
                self.corr_cbar.remove()
            self.corr_cbar = self.corr_fig.colorbar(im, ax=self.corr_ax)
            
            self.corr_fig.tight_layout()
            self.corr_canvas.draw()

    def _plot_validity(self):
        """Plot validity data"""
        if self.validity_data is not None:
            self.validity_ax.clear()
            im = self.validity_ax.imshow(self.validity_data, extent=self.validity_extent,
                                       aspect='auto', origin='lower', cmap='plasma')
            self.validity_ax.set_title('Validity Count (# of valid observations)')
            self.validity_ax.set_xlabel('Range')
            self.validity_ax.set_ylabel('Azimuth')
            
            # Add colorbar
            if hasattr(self, 'validity_cbar'):
                self.validity_cbar.remove()
            self.validity_cbar = self.validity_fig.colorbar(im, ax=self.validity_ax)
            
            self.validity_fig.tight_layout()
            self.validity_canvas.draw()

    def _init_simple_gui(self):
        """Simple fallback GUI if enhanced version fails"""
        # Clear any existing widgets
        for widget in self.winfo_children():
            widget.destroy()
        
        self.geometry("400x300")
        self.title("Reference Point Selector")
        
        # Option selection
        self.option_var = tk.StringVar(value="highest_corr")
        options = [
            ("Highest mean correlation", "highest_corr"),
            ("Lowest standard deviation", "lowest_std"),
            ("Manual definition", "define")
        ]
        
        options_frame = ttk.LabelFrame(self, text="Reference Point Selection")
        options_frame.pack(fill="x", padx=10, pady=10)

        for text, value in options:
            ttk.Radiobutton(options_frame, text=text, variable=self.option_var, 
                          value=value, command=self.on_simple_option_change).pack(anchor="w", padx=5, pady=2)

        # Manual input frame
        self.manual_frame = ttk.LabelFrame(self, text="Manual Coordinates")
        
        ttk.Label(self.manual_frame, text="Latitude:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.lat_var = tk.StringVar()
        self.lat_entry = ttk.Entry(self.manual_frame, textvariable=self.lat_var, width=15)
        self.lat_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(self.manual_frame, text="Longitude:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.lon_var = tk.StringVar()
        self.lon_entry = ttk.Entry(self.manual_frame, textvariable=self.lon_var, width=15)
        self.lon_entry.grid(row=1, column=1, padx=5, pady=5)

        # Submit button
        self.submit_btn = ttk.Button(self, text="Submit", command=self.submit_simple_selection)
        self.submit_btn.pack(pady=10)
        
        # Initially hide manual frame
        self.on_simple_option_change()

    def on_simple_option_change(self):
        """Handle simple option change"""
        if self.option_var.get() == "define":
            self.manual_frame.pack(fill="x", padx=10, pady=5)
        else:
            self.manual_frame.pack_forget()

    def submit_simple_selection(self):
        """Submit selection from simple GUI"""
        option = self.option_var.get()
        
        if option == "highest_corr":
            self.select_highest_correlation()
        elif option == "lowest_std":
            self.select_lowest_std()
        else:
            # Manual definition
            try:
                lat = float(self.lat_var.get())
                lon = float(self.lon_var.get())
                self.save_geographic_reference_point(lat, lon)
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid latitude and longitude.")
                return
        
        self.destroy()

    def save_geographic_reference_point(self, lat, lon):
        """Save geographic coordinates as reference point"""
        try:
            topo_path = self.topodir
            filepath = os.path.join(topo_path, "ref_point.ll")
            with open(filepath, "w") as f:
                f.write(f"{lon} {lat}\n")
            
            # Convert to radar coordinates
            filepathr = os.path.join(topo_path, "ref_point.ra")
            prm = os.path.join(topo_path, "master.PRM")
            
            result = subprocess.run(
                f"SAT_llt2rat {prm} 0 < {filepath} > {filepathr}",
                shell=True, capture_output=True, text=True
            )
            
            if result.returncode == 0:
                # Validate coordinates
                with open(filepathr, "r") as f:
                    line = f.readline().strip().split()
                    if len(line) >= 2 and float(line[0]) >= 0 and float(line[1]) >= 0:
                        messagebox.showinfo("Success", "Reference point saved successfully!")
                    else:
                        messagebox.showerror("Invalid Location", 
                                           "Selected coordinates are outside valid bounds.")
            else:
                messagebox.showerror("Conversion Error", "Failed to convert coordinates.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save reference point: {str(e)}")

    def disable_close(self):
        pass  # Do nothing to disable close

    def on_option_change(self):
        """Handle option selection change"""
        option = self.option_var.get()
        if option == "define":
            # Show entire coordinate input section for manual definition
            self.coord_frame.pack(fill="x", pady=(0, 10))
            self.on_coord_system_change()  # This will show the appropriate frame
            self.convert_btn.pack(pady=5)
            
            # Enable manual coordinate input
            self.lat_entry.config(state="normal")
            self.lon_entry.config(state="normal")
            self.range_entry.config(state="normal")
            self.azimuth_entry.config(state="normal")
            self.convert_btn.config(state="normal")
        else:
            # Hide entire coordinate input section for automatic selection
            self.coord_frame.pack_forget()
            
            # Trigger automatic selection
            if option == "highest_corr":
                self.select_highest_correlation()
            elif option == "lowest_std":
                self.select_lowest_std()

    def on_coord_system_change(self):
        """Handle coordinate system change"""
        # Only show coordinate frames if Manual definition is selected
        if self.option_var.get() == "define":
            if self.coord_system_var.get() == "geographic":
                self.geo_frame.pack(fill="x", padx=5, pady=5)
                self.radar_frame.pack_forget()
                self.convert_btn.config(text="Convert & Update")
            else:
                self.geo_frame.pack_forget()
                self.radar_frame.pack(fill="x", padx=5, pady=5)
                self.convert_btn.config(text="Update")

    def on_corr_plot_click(self, event):
        """Handle click on correlation plot"""
        if event.inaxes == self.corr_ax and self.option_var.get() == "define":
            x, y = event.xdata, event.ydata
            if x is not None and y is not None:
                self.set_radar_coordinates(x, y)
                self.update_selection_info()

    def on_corr_plot_hover(self, event):
        """Handle hover on correlation plot"""
        if event.inaxes == self.corr_ax:
            x, y = event.xdata, event.ydata
            if x is not None and y is not None:
                # Get values at this location
                corr_val = self.get_value_at_location(self.corr_data, self.corr_extent, x, y)
                validity_val = None
                if self.validity_available:
                    validity_val = self.get_value_at_location(self.validity_data, self.validity_extent, x, y)
                
                # Update hover info in status bar or tooltip
                corr_text = f"{corr_val:.3f}" if corr_val is not None else 'N/A'
                hover_text = f"Range: {x:.2f}, Azimuth: {y:.2f}, Corr: {corr_text}"
                if validity_val is not None:
                    hover_text += f", Valid count: {int(validity_val) if validity_val else 0}"
                
                # Update plot title with hover info
                self.corr_ax.set_title(f'Mean Correlation - {hover_text}')
                self.corr_canvas.draw_idle()

    def on_validity_plot_click(self, event):
        """Handle click on validity plot"""
        if event.inaxes == self.validity_ax and self.option_var.get() == "define":
            x, y = event.xdata, event.ydata
            if x is not None and y is not None:
                self.set_radar_coordinates(x, y)
                self.update_selection_info()

    def on_validity_plot_hover(self, event):
        """Handle hover on validity plot"""
        if event.inaxes == self.validity_ax:
            x, y = event.xdata, event.ydata
            if x is not None and y is not None:
                # Get values at this location
                validity_val = self.get_value_at_location(self.validity_data, self.validity_extent, x, y)
                corr_val = self.get_value_at_location(self.corr_data, self.corr_extent, x, y)
                
                hover_text = f"Range: {x:.2f}, Azimuth: {y:.2f}, Valid count: {int(validity_val) if validity_val else 0}"
                if corr_val is not None:
                    hover_text += f", Corr: {corr_val:.3f}"
                
                self.validity_ax.set_title(f'Validity Count - {hover_text}')
                self.validity_canvas.draw_idle()

    def get_value_at_location(self, data, extent, x, y):
        """Get data value at specific coordinates"""
        if data is None:
            return None
        
        try:
            # Convert coordinates to array indices
            x_min, x_max, y_min, y_max = extent
            rows, cols = data.shape
            
            # Calculate normalized coordinates (0 to 1)
            x_norm = (x - x_min) / (x_max - x_min)
            y_norm = (y - y_min) / (y_max - y_min)
            
            # Convert to array indices
            col_idx = int(x_norm * (cols - 1))
            row_idx = int(y_norm * (rows - 1))
            
            # Clamp indices to valid range
            col_idx = max(0, min(cols - 1, col_idx))
            row_idx = max(0, min(rows - 1, row_idx))
            
            # For GMT grids, typically Y is stored from top to bottom, so we need to flip row index
            flipped_row_idx = rows - 1 - row_idx
            
            value = data[flipped_row_idx, col_idx]
            
            # Debug output for highest correlation case
            if hasattr(self, '_debug_highest_corr') and self._debug_highest_corr:
                print(f"Debug - Coords: ({x:.2f}, {y:.2f}) -> Normalized: ({x_norm:.4f}, {y_norm:.4f})")
                print(f"Debug - Array indices: row={flipped_row_idx}, col={col_idx}, value={value:.6f}")
                print(f"Debug - Data shape: {data.shape}, extent: {extent}")
                
                # Check surrounding values
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        r_check = max(0, min(rows-1, flipped_row_idx + dr))
                        c_check = max(0, min(cols-1, col_idx + dc))
                        val_check = data[r_check, c_check]
                        print(f"Debug - Surrounding [{dr},{dc}]: {val_check:.6f}")
                
                self._debug_highest_corr = False  # Reset debug flag
            
            return float(value) if not np.isnan(value) else None
            
        except Exception as e:
            print(f"Error in get_value_at_location: {e}")
            return None

    def set_radar_coordinates(self, x, y):
        """Set coordinates in radar system and update displays"""
        self.current_x = x
        self.current_y = y
        
        # Update radar coordinate entries
        self.range_var.set(f"{x:.6f}")
        self.azimuth_var.set(f"{y:.6f}")
        
        # Convert to geographic if needed
        if self.coord_system_var.get() == "geographic":
            lat, lon = self.radar_to_geographic(x, y)
            if lat is not None and lon is not None:
                self.current_lat = lat
                self.current_lon = lon
                self.lat_var.set(f"{lat:.6f}")
                self.lon_var.set(f"{lon:.6f}")

    def set_geographic_coordinates(self, lat, lon):
        """Set coordinates in geographic system and update displays"""
        self.current_lat = lat
        self.current_lon = lon
        
        # Update geographic coordinate entries
        self.lat_var.set(f"{lat:.6f}")
        self.lon_var.set(f"{lon:.6f}")
        
        # Convert to radar if needed
        if self.coord_system_var.get() == "radar":
            x, y = self.geographic_to_radar(lat, lon)
            if x is not None and y is not None:
                self.current_x = x
                self.current_y = y
                self.range_var.set(f"{x:.6f}")
                self.azimuth_var.set(f"{y:.6f}")

    def radar_to_geographic(self, x, y):
        """Convert radar coordinates to geographic"""
        try:
            # Create temporary file with radar coordinates
            temp_ra = os.path.join(self.topodir, "temp_point.ra")
            with open(temp_ra, "w") as f:
                f.write(f"{x} {y}\n")
            
            # Convert using SAT_rat2ll
            prm = os.path.join(self.topodir, "master.PRM")
            temp_ll = os.path.join(self.topodir, "temp_point.ll")
            
            result = subprocess.run(
                f"SAT_rat2ll {prm} 0 < {temp_ra} > {temp_ll}",
                shell=True, capture_output=True, text=True
            )
            
            if result.returncode == 0 and os.path.exists(temp_ll):
                with open(temp_ll, "r") as f:
                    line = f.readline().strip()
                    parts = line.split()
                    if len(parts) >= 2:
                        lon, lat = float(parts[0]), float(parts[1])
                        
                        # Cleanup temp files
                        os.remove(temp_ra)
                        os.remove(temp_ll)
                        
                        return lat, lon
            
            # Cleanup on error
            for temp_file in [temp_ra, temp_ll]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
        except Exception as e:
            print(f"Error converting radar to geographic: {e}")
        
        return None, None

    def geographic_to_radar(self, lat, lon):
        """Convert geographic coordinates to radar"""
        try:
            # Create temporary file with geographic coordinates
            temp_ll = os.path.join(self.topodir, "temp_point.ll")
            with open(temp_ll, "w") as f:
                f.write(f"{lon} {lat}\n")
            
            # Convert using SAT_llt2rat
            prm = os.path.join(self.topodir, "master.PRM")
            temp_ra = os.path.join(self.topodir, "temp_point.ra")
            
            result = subprocess.run(
                f"SAT_llt2rat {prm} 0 < {temp_ll} > {temp_ra}",
                shell=True, capture_output=True, text=True
            )
            
            if result.returncode == 0 and os.path.exists(temp_ra):
                with open(temp_ra, "r") as f:
                    line = f.readline().strip()
                    parts = line.split()
                    if len(parts) >= 2:
                        x, y = float(parts[0]), float(parts[1])
                        
                        # Cleanup temp files
                        os.remove(temp_ll)
                        os.remove(temp_ra)
                        
                        return x, y
            
            # Cleanup on error
            for temp_file in [temp_ll, temp_ra]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
        except Exception as e:
            print(f"Error converting geographic to radar: {e}")
        
        return None, None

    def on_coordinate_change(self, *args):
        """Handle coordinate entry changes"""
        if self.option_var.get() != "define":
            return
        
        try:
            if self.coord_system_var.get() == "geographic":
                lat_str = self.lat_var.get()
                lon_str = self.lon_var.get()
                if lat_str and lon_str:
                    lat, lon = float(lat_str), float(lon_str)
                    self.set_geographic_coordinates(lat, lon)
            else:
                x_str = self.range_var.get()
                y_str = self.azimuth_var.get()
                if x_str and y_str:
                    x, y = float(x_str), float(y_str)
                    self.set_radar_coordinates(x, y)
                    
            self.update_selection_info()
        except ValueError:
            pass  # Ignore invalid input during typing

    def convert_coordinates(self):
        """Convert between coordinate systems"""
        try:
            if self.coord_system_var.get() == "geographic":
                lat, lon = float(self.lat_var.get()), float(self.lon_var.get())
                x, y = self.geographic_to_radar(lat, lon)
                if x is not None and y is not None:
                    self.current_x, self.current_y = x, y
                    self.update_selection_info()
                else:
                    messagebox.showerror("Conversion Error", "Failed to convert geographic to radar coordinates")
            else:
                x, y = float(self.range_var.get()), float(self.azimuth_var.get())
                lat, lon = self.radar_to_geographic(x, y)
                if lat is not None and lon is not None:
                    self.current_lat, self.current_lon = lat, lon
                    self.update_selection_info()
                else:
                    messagebox.showerror("Conversion Error", "Failed to convert radar to geographic coordinates")
        except ValueError:
            messagebox.showerror("Input Error", "Please enter valid coordinates")

    def update_selection_info(self):
        """Update the selection information display"""
        if not (self.current_x and self.current_y):
            return
        
        info_lines = []
        
        # Basic coordinates
        if self.current_lat and self.current_lon:
            info_lines.append(f"Geographic:")
            info_lines.append(f"  Lat: {self.current_lat:.6f}")
            info_lines.append(f"  Lon: {self.current_lon:.6f}")
            info_lines.append("")
        
        info_lines.append(f"Radar coordinates:")
        info_lines.append(f"  Range: {self.current_x:.6f}")
        info_lines.append(f"  Azimuth: {self.current_y:.6f}")
        info_lines.append("")
        
        # Get correlation value
        if hasattr(self, 'corr_data') and self.corr_data is not None:
            corr_val = self.get_value_at_location(self.corr_data, self.corr_extent, self.current_x, self.current_y)
            info_lines.append(f"Mean correlation: {corr_val:.4f}" if corr_val else "Mean correlation: N/A")
        
        # Get validity count
        if self.validity_available and hasattr(self, 'validity_data') and self.validity_data is not None:
            validity_val = self.get_value_at_location(self.validity_data, self.validity_extent, self.current_x, self.current_y)
            count = int(validity_val) if validity_val else 0
            info_lines.append(f"Valid observations: {count}")
            
            # Calculate percentage if we know total
            if hasattr(self, '_total_ifgs'):
                percentage = (count / self._total_ifgs) * 100
                info_lines.append(f"Coverage: {percentage:.1f}%")
        
        # Update info display
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, "\n".join(info_lines))
        self.info_text.config(state=tk.DISABLED)
        
        # Update plot markers
        self.update_plot_markers()

    def update_plot_markers(self):
        """Update selection markers on plots"""
        if not (self.current_x and self.current_y):
            return
        
        # Clear existing markers
        if hasattr(self, '_corr_marker'):
            self._corr_marker.remove()
        if hasattr(self, '_validity_marker') and self.validity_available:
            self._validity_marker.remove()
        
        # Add new markers
        self._corr_marker = self.corr_ax.plot(self.current_x, self.current_y, 'r+', markersize=15, markeredgewidth=3)[0]
        self.corr_canvas.draw_idle()
        
        if self.validity_available:
            self._validity_marker = self.validity_ax.plot(self.current_x, self.current_y, 'r+', markersize=15, markeredgewidth=3)[0]
            self.validity_canvas.draw_idle()

    def select_highest_correlation(self):
        """Select point with highest correlation"""
        if not os.path.exists(self.corr_stack_path):
            messagebox.showerror("File Error", "Correlation stack file not found")
            return
        
        # Enable debug output for correlation value checking
        self._debug_highest_corr = True
        
        try:
            # Use GMT to find maximum
            result = subprocess.run(
                ["gmt", "grdinfo", "-M", self.corr_stack_path],
                capture_output=True, text=True, check=True
            )
            
            print(f"GMT grdinfo output: {result.stdout}")
            
            # Parse the output for maximum coordinates using GMT coordinate system
            lines = result.stdout.strip().split('\n')
            gmt_x, gmt_y = None, None
            
            for line in lines:
                if 'v_max:' in line and 'at x =' in line:
                    # Format: "v_min: value at x = coord y = coord v_max: value at x = coord y = coord"
                    parts = line.split()
                    try:
                        # Find v_max section
                        v_max_idx = parts.index('v_max:')
                        # Look for 'x' and 'y' after v_max
                        for i in range(v_max_idx, len(parts)-2):
                            if parts[i] == 'x' and parts[i+1] == '=':
                                gmt_x = float(parts[i+2])
                            elif parts[i] == 'y' and parts[i+1] == '=':
                                gmt_y = float(parts[i+2])
                                break  # We have both x and y
                        
                        if gmt_x is not None and gmt_y is not None:
                            break
                    except (ValueError, IndexError) as e:
                        print(f"GMT parsing error: {e}")
                        continue
            
            if gmt_x is None or gmt_y is None:
                print("GMT parsing failed, using fallback method")
                # Fallback: find max value in loaded data if GMT parsing fails
                if hasattr(self, 'corr_data') and self.corr_data is not None:
                    max_idx = np.unravel_index(np.nanargmax(self.corr_data), self.corr_data.shape)
                    
                    # Convert array indices back to coordinates using our extent
                    x_min, x_max, y_min, y_max = self.corr_extent
                    rows, cols = self.corr_data.shape
                    
                    col_idx, row_idx = max_idx[1], max_idx[0]
                    x = x_min + (col_idx / (cols - 1)) * (x_max - x_min)
                    y = y_min + ((rows - 1 - row_idx) / (rows - 1)) * (y_max - y_min)  # Flip Y back
                    
                    max_value = self.corr_data[max_idx]
                    print(f"Fallback method - Max value: {max_value:.6f} at ({x:.2f}, {y:.2f})")
                else:
                    raise Exception("No correlation data available")
            else:
                print(f"GMT method found max at GMT coords ({gmt_x:.2f}, {gmt_y:.2f})")
                
                # Convert GMT coordinates to our extent coordinate system
                # Get GMT bounds from grdinfo output
                gmt_x_min, gmt_x_max, gmt_y_min, gmt_y_max = None, None, None, None
                for line in lines:
                    if 'x_min:' in line and 'x_max:' in line:
                        parts = line.split()
                        gmt_x_min = float(parts[parts.index('x_min:') + 1])
                        gmt_x_max = float(parts[parts.index('x_max:') + 1])
                    elif 'y_min:' in line and 'y_max:' in line:
                        parts = line.split()
                        gmt_y_min = float(parts[parts.index('y_min:') + 1])
                        gmt_y_max = float(parts[parts.index('y_max:') + 1])
                
                if all(val is not None for val in [gmt_x_min, gmt_x_max, gmt_y_min, gmt_y_max]):
                    # Convert GMT coordinates to our extent coordinates
                    x_min, x_max, y_min, y_max = self.corr_extent
                    
                    # Normalize GMT coordinates (0 to 1)
                    x_norm = (gmt_x - gmt_x_min) / (gmt_x_max - gmt_x_min)
                    y_norm = (gmt_y - gmt_y_min) / (gmt_y_max - gmt_y_min)
                    
                    # Convert to our extent coordinates
                    x = x_min + x_norm * (x_max - x_min)
                    y = y_min + y_norm * (y_max - y_min)
                    
                    print(f"Converted to extent coords: ({x:.2f}, {y:.2f})")
                else:
                    print("Could not extract GMT bounds, using fallback")
                    # Use direct GMT coordinates as fallback
                    x, y = gmt_x, gmt_y
            
            # Set coordinates and update
            self.set_radar_coordinates(x, y)
            self.update_selection_info()
                
        except Exception as e:
            messagebox.showerror("Selection Error", f"Failed to find highest correlation point: {str(e)}")
            print(f"Error details: {e}")

    def select_lowest_std(self):
        """Select point with lowest standard deviation"""
        if not os.path.exists(self.std_path):
            messagebox.showerror("File Error", "Standard deviation file not found")
            return
        
        try:
            # Use GMT to find minimum with coordinate information
            result = subprocess.run(
                ["gmt", "grdinfo", "-M", self.std_path],
                capture_output=True, text=True, check=True
            )
            
            print(f"GMT grdinfo output for std: {result.stdout}")
            
            # Parse the output for minimum coordinates using GMT coordinate system
            lines = result.stdout.strip().split('\n')
            gmt_x, gmt_y = None, None
            
            for line in lines:
                if 'v_min:' in line and 'at x =' in line:
                    # Format: "v_min: value at x = coord y = coord"
                    parts = line.split()
                    try:
                        x_idx = parts.index('x') + 2  # Skip 'x' and '='
                        y_idx = parts.index('y') + 2  # Skip 'y' and '='
                        gmt_x = float(parts[x_idx])
                        gmt_y = float(parts[y_idx])
                        break
                    except (ValueError, IndexError):
                        continue
            
            if gmt_x is None or gmt_y is None:
                # Fallback: Load std data and find minimum using numpy
                print("GMT parsing failed, using fallback method for std minimum")
                if not hasattr(self, 'std_data'):
                    # Load std data if not already loaded
                    self.std_data, self.std_extent = self._load_grd_data(self.std_path)
                
                if hasattr(self, 'std_data') and self.std_data is not None:
                    min_idx = np.unravel_index(np.nanargmin(self.std_data), self.std_data.shape)
                    
                    # Convert array indices back to coordinates
                    x_min, x_max, y_min, y_max = self.std_extent
                    rows, cols = self.std_data.shape
                    
                    col_idx, row_idx = min_idx[1], min_idx[0]
                    x = x_min + (col_idx / (cols - 1)) * (x_max - x_min)
                    y = y_min + ((rows - 1 - row_idx) / (rows - 1)) * (y_max - y_min)  # Flip Y back
                    
                    min_value = self.std_data[min_idx]
                    print(f"Fallback method - Min std value: {min_value:.6f} at ({x:.2f}, {y:.2f})")
                else:
                    raise Exception("Could not load standard deviation data")
            else:
                print(f"GMT method found min std at GMT coords ({gmt_x:.2f}, {gmt_y:.2f})")
                
                # Convert GMT coordinates to our extent coordinate system
                # Get GMT bounds from grdinfo output
                gmt_x_min, gmt_x_max, gmt_y_min, gmt_y_max = None, None, None, None
                for line in lines:
                    if 'x_min:' in line and 'x_max:' in line:
                        parts = line.split()
                        gmt_x_min = float(parts[parts.index('x_min:') + 1])
                        gmt_x_max = float(parts[parts.index('x_max:') + 1])
                    elif 'y_min:' in line and 'y_max:' in line:
                        parts = line.split()
                        gmt_y_min = float(parts[parts.index('y_min:') + 1])
                        gmt_y_max = float(parts[parts.index('y_max:') + 1])
                
                if all(val is not None for val in [gmt_x_min, gmt_x_max, gmt_y_min, gmt_y_max]):
                    # Load std extent if not already loaded
                    if not hasattr(self, 'std_extent'):
                        self.std_data, self.std_extent = self._load_grd_data(self.std_path)
                    
                    # Convert GMT coordinates to our extent coordinates
                    x_min, x_max, y_min, y_max = self.std_extent
                    
                    # Normalize GMT coordinates (0 to 1)
                    x_norm = (gmt_x - gmt_x_min) / (gmt_x_max - gmt_x_min)
                    y_norm = (gmt_y - gmt_y_min) / (gmt_y_max - gmt_y_min)
                    
                    # Convert to our extent coordinates
                    x = x_min + x_norm * (x_max - x_min)
                    y = y_min + y_norm * (y_max - y_min)
                    
                    print(f"Converted to extent coords: ({x:.2f}, {y:.2f})")
                else:
                    print("Could not extract GMT bounds, using direct GMT coordinates")
                    # Use direct GMT coordinates as fallback
                    x, y = gmt_x, gmt_y
            
            # Set coordinates and update info
            self.set_radar_coordinates(x, y)
            self.update_selection_info()
            
            # Get the correlation value at this point for display
            if hasattr(self, 'corr_data') and self.corr_data is not None:
                corr_at_min_std = self.get_value_at_location(self.corr_data, self.corr_extent, x, y)
                print(f"Selected lowest std point at ({x:.2f}, {y:.2f}), Correlation: {corr_at_min_std}")
            
        except Exception as e:
            messagebox.showerror("Selection Error", f"Failed to find lowest std deviation point: {str(e)}")
            print(f"Error details: {e}")

    def submit_selection(self):
        """Submit the current selection"""
        if not (self.current_x and self.current_y):
            messagebox.showerror("No Selection", "Please select a reference point first")
            return
        
        try:
            # Save reference point in radar coordinates
            ref_point_path = os.path.join(self.topodir, "ref_point.ra")
            with open(ref_point_path, "w") as f:
                f.write(f"{self.current_x} {self.current_y}\n")
            
            # Also save geographic coordinates if available
            if self.current_lat and self.current_lon:
                ref_point_ll_path = os.path.join(self.topodir, "ref_point.ll")
                with open(ref_point_ll_path, "w") as f:
                    f.write(f"{self.current_lon} {self.current_lat}\n")
            
            # Validate the selection
            if self.current_x < 0 or self.current_y < 0:
                messagebox.showerror("Invalid Selection", 
                                   "Selected coordinates are outside valid bounds.\n"
                                   "Please select a point within the image footprint.")
                return
            
            # Check correlation value
            if hasattr(self, 'corr_data'):
                corr_val = self.get_value_at_location(self.corr_data, self.corr_extent, self.current_x, self.current_y)
                if corr_val is None or np.isnan(corr_val):
                    result = messagebox.askyesno("Low Quality Warning",
                                               "The selected point has no correlation value or low quality.\n"
                                               "This may affect normalization quality.\n\n"
                                               "Do you want to continue anyway?")
                    if not result:
                        return
            
            # Show success message with details
            success_msg = f"Reference point saved successfully!\n\n"
            success_msg += f"Radar coordinates: {self.current_x:.6f}, {self.current_y:.6f}\n"
            if self.current_lat and self.current_lon:
                success_msg += f"Geographic coordinates: {self.current_lat:.6f}, {self.current_lon:.6f}\n"
            
            if self.validity_available:
                validity_val = self.get_value_at_location(self.validity_data, self.validity_extent, self.current_x, self.current_y)
                if validity_val:
                    success_msg += f"Valid observations: {int(validity_val)}"
            
            messagebox.showinfo("Success", success_msg)
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save reference point: {str(e)}")

    # Legacy methods for backward compatibility
    def on_option_submit(self):
        """Legacy method - redirect to auto_select"""
        self.auto_select()
        if self.current_x and self.current_y:
            self.submit_selection()

    def on_define_submit(self):
        """Legacy method - redirect to submit_selection"""
        self.submit_selection()


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # hide the root window
    app = ReferencePointGUI("/home/badar/0_PhD/01_data/01_raw/02_InSAR/hout/chtr/des/F3/intf_all")
    app.mainloop()