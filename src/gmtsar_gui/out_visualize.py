import os
import re
from datetime import datetime, timedelta
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import matplotlib.dates as mdates
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from dask.diagnostics import ProgressBar

def load_netcdf_file(file_path):
    da = xr.open_dataarray(file_path, chunks={'time': 1})
    return da

def get_file_paths(folder_path):
    # Regex pattern to match the filename pattern "disp_2023002_ll.grd"
    pattern = re.compile(r"disp_(\d{4})(\d{3})_ll\.grd")

    files_to_load = []
    for filename in os.listdir(folder_path):
        match = pattern.match(filename)
        if match:
            year = int(match.group(1))
            doy = int(match.group(2))

            # Convert year and doy to dd_mm_yyyy format
            date = datetime(year, 1, 1) + timedelta(days=doy - 1)
            date_str = date.strftime("%d_%m_%Y")

            # Load .grd file as an xarray DataArray
            file_path = os.path.join(folder_path, filename)
            files_to_load.append((file_path, date_str, date))
    print(len(files_to_load))

    return files_to_load

def plot_time_series(files_to_load, lat, lon):
    """
    Plot the time series of surface deformation at a specified lat, lon location,
    with dynamically spaced x-axis ticks for better readability.
    Also save the plot and dump the actual time series values in a CSV file.
    """
    time_series = []
    time_stamps = []

    for file_path, date_str, date in files_to_load:
        da = load_netcdf_file(file_path)
        point_series = da.sel(lat=lat, lon=lon, method="nearest").compute()
        time_series.append(point_series.values)
        time_stamps.append(date)

    # Convert the time coordinates to datetime using the correct format
    time_range = pd.to_datetime(time_stamps)

    # Calculate the time span to decide tick frequency
    num_years = (time_range[-1] - time_range[0]).days / 365
    plt.figure(figsize=(10, 6))
    plt.plot(time_range, time_series, marker='o', linestyle='-')
    
    # Set tick frequency based on the time span
    if num_years <= 1:
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    elif num_years <= 4:
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=3))  # Quarterly
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    else:
        plt.gca().xaxis.set_major_locator(mdates.YearLocator())
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    plt.title(f"Surface Deformation Time Series at ({lat}, {lon})")
    plt.xlabel("Time")
    plt.ylabel("Deformation Rate")
    plt.xticks(rotation=45)
    plt.grid()
    
    # Save the plot with latlon in the filename
    plot_filename = f"time_series_{lat:.6f}_{lon:.6f}.png"
    plt.savefig(plot_filename)
    
    # Dump the actual time series values in a CSV file
    csv_filename = f"time_series_{lat:.6f}_{lon:.6f}.csv"
    df = pd.DataFrame({"Time": time_range, "Deformation Rate": time_series})
    df.to_csv(csv_filename, index=False)
    
    plt.show()

def plot_interactive_map(file_path, files_to_load):
    """
    Plot an interactive map of the specified grd/netcdf file.
    When a user clicks on a location and releases the mouse button,
    it plots the time series at that location.
    """
    
    # Load the vel_ll.grd file as an xarray DataArray
    vel_data = xr.open_dataarray(file_path)

    fig, ax = plt.subplots(figsize=(10, 6), subplot_kw={'projection': ccrs.Mercator()})
    
    # Create a Cartopy instance for plotting
    ax.set_extent([vel_data.lon.min(), vel_data.lon.max(), vel_data.lat.min(), vel_data.lat.max()], crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE)
    
    lon, lat = np.meshgrid(vel_data.lon.values, vel_data.lat.values)
    
    c_scheme = ax.pcolormesh(lon, lat, vel_data.values, cmap='jet', transform=ccrs.PlateCarree())
    
    fig.colorbar(c_scheme, ax=ax, orientation='vertical')
    
    def onrelease(event):
        if event.inaxes == ax:
            toolbar = plt.get_current_fig_manager().toolbar
            if toolbar.mode == '':
                lon_click, lat_click = event.xdata, event.ydata
                print(f"Clicked at longitude: {lon_click}, latitude: {lat_click}")
                
                plot_time_series(files_to_load, lat_click, lon_click)
    
    fig.canvas.mpl_connect('button_release_event', onrelease)
    
    plt.title("Interactive Map of Surface Deformation Velocity")
    
    plt.show()

def visualize(folder_path):
    files_to_load = get_file_paths(folder_path)

    # Plot interactive map for vel_ll.grd file
    vel_file_path = os.path.join(folder_path, "vel_ll.grd")  # Replace with your vel_ll.grd file path
    plot_interactive_map(vel_file_path, files_to_load)

if __name__ == "__main__":
    folder_path = "/home/badar/0_PhD/01_data/02_processed/02_InSAR/02_Chitral/SBAS"  # Replace with your folder path
    visualize(folder_path)