# User Interface Guide

This guide provides a comprehensive overview of the InSARLite user interface, helping you navigate and efficiently use all the application features.

## Main Application Window

When you launch InSARLite with `InSARLiteApp`, the main window appears with a clean, organized interface designed for intuitive InSAR processing workflow.

```{note}
**First Launch**: On your first launch, InSARLite will check for GMTSAR and may show an installation dialog. This automatic setup ensures all processing capabilities are available without manual configuration.
```

### Window Layout

The main window is organized into logical sections that follow the typical InSAR processing workflow:

```
┌─────────────────────────────────────────────────────────────┐
│                    InSARLite Workflow Studio                │
├─────────────────────────────────────────────────────────────┤
│  Project Configuration                                      │
│  ┌─ Area of Interest ────┬─ Time Period ─────┬─ Settings ──┐ │
│  │                       │                   │             │ │
│  └───────────────────────┴───────────────────┴─────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Interactive Map                                            │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                                                         │ │
│  │                  Map Widget                             │ │
│  │                                                         │ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Data Management                                            │
│  ┌─ Data Folder ─────┬─ DEM ─────┬─ Output ─────────────────┐ │
│  │                   │           │                         │ │
│  └───────────────────┴───────────┴─────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Processing Controls                                        │
│  ┌─ Query ──┬─ Download ──┬─ Process Steps ─────────────────┐ │
│  │          │             │                                │ │
│  └──────────┴─────────────┴────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Status and Progress                                        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                Progress Indicators                      │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Interface Sections

### 1. Project Configuration Section

#### Area of Interest (AOI) Controls

**Coordinate Input Fields**:
- **North**: Northern boundary (latitude)
- **South**: Southern boundary (latitude) 
- **East**: Eastern boundary (longitude)
- **West**: Western boundary (longitude)

```{tip}
Coordinates are entered in decimal degrees. Use negative values for western longitudes and southern latitudes.
```

**Map Integration**:
- Click and drag on the map to define your AOI
- Coordinates auto-update when you interact with the map
- Rectangle overlay shows your selected area

#### Time Period Controls

**Date Selection**:
- **Start Date**: Beginning of your time series
- **End Date**: End of your time series
- Calendar widgets for easy date selection

**Date Validation**:
- Automatic validation prevents invalid date ranges
- Smart date limiting based on Sentinel-1 availability
- Visual feedback for date conflicts

```{warning}
Date limits are automatically applied when query button is inactive to prevent invalid searches.
```

#### Flight Direction and Polarization

**Flight Direction**:
- **Ascending**: Satellite moving from south to north
- **Descending**: Satellite moving from north to south
- Radio button selection
- Auto-detection from downloaded data

**Polarization Options**:
- **VV**: Vertical transmit, vertical receive (recommended)
- **VH**: Vertical transmit, horizontal receive
- **HH**: Horizontal transmit, horizontal receive (rare)
- **HV**: Horizontal transmit, vertical receive (rare)

### 2. Interactive Map Widget

The map widget provides visual feedback and interactive AOI selection:

#### Map Features
- **Base Maps**: Multiple map styles available
- **Zoom Controls**: Mouse wheel and buttons
- **Pan**: Click and drag to move
- **AOI Rectangle**: Visual representation of your study area

#### Interaction Modes
- **Rectangle Drawing**: Click and drag to define AOI
- **Coordinate Display**: Shows lat/lon on hover
- **Zoom to Fit**: Automatically centers on your AOI

```{tip}
Use the map for initial area selection, then fine-tune coordinates using the input fields for precision.
```

### 3. Data Management Section

#### Data Folder Configuration

**Data Folder Selection**:
- **Browse Button**: Select existing data folder
- **Path Display**: Shows current data folder path
- **Validation**: Automatic check for existing Sentinel-1 data

**Folder Status Indicators**:
- 🟢 **Green**: Valid folder with compatible data (ready to move on to next step)
- 🟡 **Yellow**: Valid data found but requires user intervention to make it ready for the next step (indicates presence of ZIP files ready for extraction as per user-defined subswaths, dates, and polarization)
- 🔴 **Red**: No data found (ready to prepare/download data through user intervention and AOI preferences)

#### DEM Management

**DEM Selection**:
- **Browse**: Select existing DEM file
- **Download**: Automated DEM download
- **Format Support**: GRD format (named exactly as `dem.grd` file)

**DEM Download Options**:
- **SRTM 30m**: 30-meter resolution global coverage
- **SRTM 90m**: 90-meter resolution global coverage

```{note}
**Future Plans**: Additional DEM options including ASTER (30-meter resolution, better at high latitudes) and NASADEM (enhanced SRTM data) are planned for future releases but not currently available.
```

#### Output Configuration

**Project Settings**:
- **Output Folder**: Where results will be saved
- **Project Name**: Unique identifier for your project
- **Folder Structure**: Automatic organization by flight direction

### 4. Processing Controls

#### Data Query and Download

**Query Button**:
- Searches for available Sentinel-1 data
- Shows results with acquisition details
- Displays data coverage on map

**Download Button**:
- Initiates bulk data download
- Progress tracking with statistics
- Pause/resume functionality

**Selection Tools**:
- **Legend**: Color-coded data tracks
- **Interactive Selection**: Click to select specific tracks
- **Metadata Display**: Detailed acquisition information

#### Processing Step Buttons

The interface dynamically shows processing steps as they become available:

**Step 00**: Download Orbit Files
- Downloads precise orbit data
- Essential for accurate geolocation

**Step 01**: Base2Net (Baseline Planning)
- Interactive baseline network design
- Master scene selection
- Interferometric pair planning

**Step 02**: Align and Generate IFGs
- Image alignment and coregistration
- Interferogram generation
- Coherence calculation

**Step 03**: Unwrapping
- Phase unwrapping configuration
- Reference point selection
- Quality mask definition

**Step 04**: SBAS Processing
- Time series analysis
- Atmospheric correction
- Velocity calculation

### 5. Progress and Status Indicators

#### Download Progress

When downloading data, the interface shows:
- **Elapsed Time**: Total download time
- **Downloaded**: Amount of data downloaded
- **Speed**: Current download speed
- **Mean Speed**: Average download speed
- **Completion**: Percentage complete
- **ETA**: Estimated time to completion

#### Processing Status

During processing operations:
- **Step Indicators**: Show current processing step
- **Button States**: Reflect available actions
- **Progress Logs**: Detailed processing information

## Navigation Patterns

### Typical Workflow Navigation

1. **Setup Phase**:
   - Define AOI using map or coordinates
   - Set time period with date controls
   - Configure data and output folders

2. **Data Phase**:
   - Query available data
   - Review and select data tracks
   - Download selected acquisitions
   - Download DEM data

3. **Processing Phase**:
   - Progress through processing steps sequentially
   - Each step enables the next upon completion
   - Monitor progress and logs

4. **Analysis Phase**:
   - Access visualization tools
   - Export results
   - Create time series animations

### State Management

The interface intelligently manages component states:

**Enabled/Disabled Controls**:
- Controls are disabled during active operations
- Sequential enablement ensures proper workflow
- Visual feedback shows available actions

**Dynamic Content**:
- Processing buttons appear as they become available
- Map overlays update with new data
- Progress indicators adapt to current operation

## Keyboard Shortcuts and Accessibility

### Keyboard Navigation

- **Tab**: Navigate between controls
- **Enter**: Activate buttons and confirm entries
- **Escape**: Cancel operations where applicable
- **Ctrl+S**: Save configuration (when available)

### Accessibility Features

- **High Contrast**: Clear visual separation
- **Consistent Layout**: Predictable element placement
- **Tooltips**: Helpful information on hover
- **Error Messages**: Clear feedback on issues

## Customization and Preferences

### Configuration Persistence

InSARLite automatically saves:
- **Last Used Paths**: Data and output folders
- **AOI Settings**: Previous study areas
- **Processing Parameters**: Parameter configurations
- **Window Layout**: Size and position preferences

### Theme and Appearance

The interface uses:
- **System Theme**: Adapts to your OS theme
- **Professional Colors**: Suitable for scientific work
- **Clear Typography**: Easy-to-read fonts
- **Consistent Icons**: Intuitive visual elements

## Troubleshooting Interface Issues

### Common Interface Problems

#### Window Not Responding
**Cause**: Long-running operations blocking the interface
**Solution**: Wait for operation completion or restart application

#### Missing Buttons or Controls
**Cause**: Window too small or resolution issues
**Solution**: Resize window or adjust display scaling

#### Map Not Loading
**Cause**: Internet connectivity issues
**Solution**: Check internet connection and restart application

#### Controls Disabled
**Cause**: Prerequisite steps not completed
**Solution**: Complete previous workflow steps first

#### GMTSAR Not Available Message
**Cause**: GMTSAR installation failed or not completed
**Solution**: 
- Restart InSARLite to retry automatic installation
- Check installation logs for specific errors
- Manually install GMTSAR if automatic installation fails
- For restricted systems, contact system administrator for required packages

#### Automatic Installation Errors
**Cause**: Permission issues, missing dependencies, or network problems
**Solution**: 
- Ensure sudo access for system package installation
- Check internet connectivity for GMTSAR download
- Verify adequate disk space (2GB+ required)
- See [Installation Guide](../installation.md) for manual installation steps

### Performance Optimization

#### For Better Responsiveness:
- **Close Unused Windows**: Reduce memory usage
- **Avoid Simultaneous Operations**: Complete one task before starting another
- **Monitor System Resources**: Ensure adequate RAM and storage
- **Regular Restarts**: Restart application for long sessions

## Tips for Efficient Use

### Workflow Efficiency
1. **Plan Your Project**: Define clear objectives before starting
2. **Start Small**: Test with limited areas first
3. **Sequential Processing**: Complete steps in order
4. **Monitor Progress**: Watch logs for early error detection

### Data Management
1. **Organize Folders**: Use descriptive project names
2. **Check Storage**: Ensure adequate space before downloads
3. **Backup Important Data**: Save critical results separately
4. **Clean Old Projects**: Remove unnecessary intermediate files

### Interface Best Practices
1. **Learn Shortcuts**: Use keyboard navigation for speed
2. **Read Tooltips**: Hover for additional information
3. **Watch State Changes**: Notice when controls become available
4. **Save Configurations**: Use consistent project settings

## Next Steps

Now that you understand the interface, continue to:

- [Data Management](data-management.md) - Learn data download and organization
- [Baseline Planning](baseline-planning.md) - Master the baseline network design
- [Processing Workflows](processing.md) - Execute complete InSAR processing

For specific issues, see:
- [Troubleshooting](troubleshooting.md) - Solve common problems
- [Quick Start](../quickstart.md) - Complete example workflow