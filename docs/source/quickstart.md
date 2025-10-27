# Quick Start Guide

Get up and running with InSARLite in minutes! This guide will walk you through your first InSAR processing workflow.

## Prerequisites

- InSARLite installed ([see installation guide](installation.md))
- EarthData account for Sentinel-1 data downloads

```{important}
**Platform Requirements**: InSARLite works best on **Ubuntu Linux**. Windows users should use **WSL2** with Ubuntu. See the [installation guide](installation.md) for platform-specific instructions.
```

```{note}
**GMTSAR Auto-Installation**: InSARLite will automatically detect and install GMTSAR on first startup. No manual installation required!
```

## Launch InSARLite

Start the application from your terminal:

```bash
InSARLiteApp
```

```{important}
**First-Time Setup**: On first launch, InSARLite will:
1. Check for GMTSAR installation
2. Prompt to install GMTSAR automatically (if needed)
3. Install required system dependencies
4. Configure environment variables

This process takes 15-30 minutes but only happens once.
```

The main InSARLite window will appear with several tabs for different processing stages.

## Your First InSAR Project

### Step 1: Set Up EarthData Authentication

Before downloading Sentinel-1 data, you need to configure your NASA EarthData credentials:

1. **Create an EarthData Account**: Visit [https://urs.earthdata.nasa.gov/](https://urs.earthdata.nasa.gov/)
2. **In InSARLite**: The first time you download data, you'll be prompted for credentials
3. **Enter your username and password** - these will be securely stored for future use

### Step 2: Define Your Study Area

1. **Navigate to the Data Download tab**
2. **Set your Area of Interest (AOI)**:
   - Enter coordinates manually, OR
   - Use the interactive map to draw your area
   - Upload a shapefile or KML file

3. **Set Time Period**:
   - Start date: Choose your beginning date
   - End date: Choose your end date
   - *Tip: Start with a short time period (2-3 months) for your first project*

### Step 3: Download Sentinel-1 Data

1. **Configure download parameters**:
   - **Track/Path**: Specific satellite track (or leave blank for auto-detection)
   - **Flight Direction**: Ascending or Descending
   - **Polarization**: VV (recommended) or VH

2. **Click "Query Data"** to search for available scenes
3. **Review the results** in the data table
4. **Click "Download Selected"** to start downloading
   - Data will be saved to your specified project directory
   - Download progress will be shown

```{tip}
Start with a small area and short time period for your first project to minimize download time and processing complexity.
```

### Step 4: Plan Your Interferometric Network

1. **Navigate to the Baseline Planning tab**
2. **Load your downloaded data** - InSARLite will automatically detect Sentinel-1 files
3. **View the baseline plot**:
   - X-axis: Temporal baseline (time difference)
   - Y-axis: Perpendicular baseline (spatial separation)
   - Each point represents a Sentinel-1 acquisition

4. **Design your interferometric pairs**:
   - Click and drag to select acquisition pairs
   - Red lines show selected interferometric pairs
   - Blue points show individual acquisitions

5. **Select master scene**:
   - Choose a scene near the center of the temporal-spatial baseline plot
   - Or use the automatic master selection tool

### Step 5: Generate Interferograms

1. **Navigate to the Processing tab**
2. **Configure processing parameters**:
   - **DEM**: Choose DEM source (SRTM 30m or SRTM 90m)
   - **Processing steps**: Select which steps to run
   - **Output format**: Choose output formats

3. **Start processing**:
   - Click "Start Processing"
   - Monitor progress in the log window
   - Processing includes:
     - Image alignment
     - Interferogram formation
     - Coherence calculation
     - Phase unwrapping (if selected)

### Step 6: Visualize Results

1. **Navigate to the Visualization tab**
2. **Load your results**:
   - Browse to your project output directory
   - Select interferograms to visualize

3. **Explore your data**:
   - View wrapped/unwrapped phase
   - Examine coherence maps
   - Create displacement time series
   - Export figures and animations

## Example Workflow: Los Angeles Area

Here's a complete example processing the Los Angeles area:

### Parameters
- **Area**: 34.0°N to 34.2°N, -118.5°W to -118.2°W
- **Time Period**: January 2023 - March 2023
- **Track**: 71 (Descending)
- **Polarization**: VV

### Expected Results
- ~10-15 Sentinel-1 acquisitions
- ~50-100 interferometric pairs
- Coherence maps showing urban areas vs. vegetated regions
- Phase maps showing potential deformation signals

## Tips for Success

### Data Selection
- **Start small**: Begin with a limited area and time period
- **Check data availability**: Some areas have more frequent coverage
- **Consider seasonality**: Vegetation changes affect coherence

### Baseline Planning
- **Temporal baselines**: Keep under 48 days for good coherence
- **Perpendicular baselines**: Keep under 150m for C-band
- **Network design**: Create a well-connected network of pairs

### Processing
- **DEM quality**: Use the highest quality DEM available for your area
- **Parameter tuning**: Default parameters work well for most cases
- **Monitor resources**: Processing can be memory and CPU intensive

### Troubleshooting
- **Download issues**: Check your internet connection and EarthData credentials
- **Processing errors**: Check the log files for detailed error messages
- **Memory errors**: Process smaller areas or use data decimation

## Common Workflows

### Earthquake Deformation Study
1. Focus on time period around earthquake event
2. Use short temporal baselines (6-12 days)
3. Create before/after interferograms
4. Look for fringes indicating surface deformation

### Volcano Monitoring
1. Regular time series over volcanic area
2. Mix of short and long temporal baselines
3. Monitor coherence changes indicating surface changes
4. Create displacement time series

### Urban Subsidence Monitoring
1. Long time series over urban areas
2. Focus on areas with good coherence (buildings, roads)
3. Use persistent scatterer techniques
4. Track cumulative displacement over time

## Next Steps

Now that you've completed your first InSAR project:

1. **Explore advanced features**: Read the [User Guide](user-guide/index.md)
2. **Try different areas**: Process different geographical regions
3. **Learn about parameters**: Understand the processing parameters in detail
4. **Join the community**: Participate in discussions and share your results

## Getting Help

If you encounter issues:

- **Check the logs**: InSARLite provides detailed processing logs
- **Read the documentation**: This documentation covers most common scenarios
- **Search existing issues**: [GitHub Issues](https://github.com/mbadarmunir/InSARLite/issues)
- **Ask for help**: Create a new issue with your specific problem

Happy processing! 🛰️📊