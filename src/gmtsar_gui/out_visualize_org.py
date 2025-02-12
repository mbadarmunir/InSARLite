import os
import re
from datetime import datetime, timedelta
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import matplotlib.dates as mdates
from mpl_toolkits.basemap import Basemap

def load_netcdf_files(folder_path):
    data_list = []
    time_stamps = []

    # Regex pattern to match the filename pattern "disp_2023002_ll.grd"
    pattern = re.compile(r"disp_(\d{4})(\d{3})_ll\.grd")

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
            da = xr.open_dataarray(file_path)

            # Add date information to the DataArray
            da = da.expand_dims(time=[date_str])
            data_list.append(da)
            time_stamps.append(date)

    # Combine all DataArrays along the time dimension to create a data cube
    data_cube = xr.concat(data_list, dim="time")

    # Sort data_cube by time to ensure chronological order
    sorted_indices = np.argsort(time_stamps)
    data_cube = data_cube.isel(time=sorted_indices)
    
    return data_cube

def plot_time_series(data_cube, lat, lon):
    """
    Plot the time series of surface deformation at a specified lat, lon location,
    with dynamically spaced x-axis ticks for better readability.
    Also save the plot and dump the actual time series values in a CSV file.
    """
    point_series = data_cube.sel(lat=lat, lon=lon, method="nearest")
    
    # Convert the time coordinates to datetime using the correct format
    time_range = pd.to_datetime(point_series.time.values, format="%d_%m_%Y")

    # Calculate the time span to decide tick frequency
    num_years = (time_range[-1] - time_range[0]).days / 365
    plt.figure(figsize=(10, 6))
    plt.plot(time_range, point_series, marker='o', linestyle='-')
    
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
    df = pd.DataFrame({"Time": time_range, "Deformation Rate": point_series.values})
    df.to_csv(csv_filename, index=False)
    
    plt.show()

def plot_average_map(data_cube):
    """
    Plot the average surface deformation over the entire time span.
    """
    avg_map = data_cube.mean(dim="time")
    avg_map.plot(cmap="viridis")
    plt.title("Average Surface Deformation Rate")
    plt.show()

def plot_trend_map(data_cube):
    """
    Plot the linear trend of surface deformation across the time series.
    """
    time_nums = np.arange(len(data_cube.time))
    time_nums = time_nums[:, np.newaxis, np.newaxis]  # Reshape to (time, 1, 1) for broadcasting

    trend = (data_cube * time_nums).sum(dim="time") / time_nums.sum()
    trend.plot(cmap="coolwarm")
    plt.title("Surface Deformation Trend")
    plt.show()

def plot_interactive_map(file_path, data_cube):
    """
    Plot an interactive map of the specified grd/netcdf file.
    When a user clicks on a location and releases the mouse button,
    it plots the time series at that location.
    """
    
    # Load the vel_ll.grd file as an xarray DataArray
    vel_data = xr.open_dataarray(file_path)

    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Create a Basemap instance for plotting
    m = Basemap(projection='merc', llcrnrlat=vel_data.lat.min(), urcrnrlat=vel_data.lat.max(),
                llcrnrlon=vel_data.lon.min(), urcrnrlon=vel_data.lon.max(), resolution='i', ax=ax)
    
    m.drawcoastlines()
    
    lon, lat = np.meshgrid(vel_data.lon.values, vel_data.lat.values)
    
    x, y = m(lon, lat)
    
    c_scheme = m.pcolormesh(x, y, vel_data.values, cmap='jet')
    
    fig.colorbar(c_scheme, ax=ax, orientation='vertical')
    
    def onrelease(event):
        if event.inaxes == ax:
            toolbar = plt.get_current_fig_manager().toolbar
            if toolbar.mode == '':
                lon_click, lat_click = m(event.xdata, event.ydata, inverse=True)
                print(f"Clicked at longitude: {lon_click}, latitude: {lat_click}")
                
                plot_time_series(data_cube, lat_click, lon_click)
    
    fig.canvas.mpl_connect('button_release_event', onrelease)
    
    plt.title("Interactive Map of Surface Deformation Velocity")
    
    plt.show()

def visualize(folder_path):
    data_cube = load_netcdf_files(folder_path)

    # Plot interactive map for vel_ll.grd file
    vel_file_path = os.path.join(folder_path, "vel_ll.grd")  # Replace with your vel_ll.grd file path
    plot_interactive_map(vel_file_path, data_cube)

if __name__ == "__main__":
    folder_path = "/home/badar/0_PhD/01_data/02_processed/02_InSAR/02_Chitral/SBAS"  # Replace with your folder path
    visualize(folder_path)
