# Project Overview

InSARLite is a comprehensive Graphical User Interface (GUI) application designed to simplify and streamline Interferometric Synthetic Aperture Radar (InSAR) processing using the GMTSAR workflow. This page provides an overview of InSAR fundamentals, InSARLite's architecture, and the complete processing workflow.

## What is InSAR?

### Interferometric Synthetic Aperture Radar Basics

Interferometric Synthetic Aperture Radar (InSAR) is a remote sensing technique that uses radar satellites to measure ground deformation and create digital elevation models. By comparing the phase information between two or more radar images of the same area taken at different times, InSAR can detect surface changes as small as a few millimeters.

#### Key InSAR Concepts

**Interferogram**: The phase difference between two SAR images, revealing surface deformation patterns.

**Baseline**: The spatial and temporal separation between satellite acquisitions:
- **Temporal Baseline**: Time difference between acquisitions
- **Perpendicular Baseline**: Spatial separation perpendicular to the satellite track

**Coherence**: A measure of phase stability between two SAR images, indicating the quality of interferometric information.

**Phase Unwrapping**: The process of converting wrapped phase values (-π to π) into continuous displacement measurements.

### Applications of InSAR

InSAR is widely used for:

- **Earthquake Monitoring**: Measuring co-seismic and post-seismic deformation
- **Volcano Studies**: Monitoring volcanic uplift and subsidence
- **Urban Subsidence**: Tracking land subsidence in cities
- **Landslide Detection**: Identifying and monitoring slope instability
- **Glacier Monitoring**: Measuring ice sheet dynamics
- **Infrastructure Monitoring**: Tracking deformation of buildings and bridges

## InSARLite Architecture

### Design Philosophy

InSARLite is built on the principle of **accessibility without compromising capability**. It provides:

- **Intuitive GUI**: User-friendly interface for complex InSAR workflows
- **GMTSAR Integration**: Full integration with the powerful GMTSAR processing engine
- **Automated Workflows**: Streamlined processing with minimal manual intervention
- **Interactive Tools**: Visual baseline planning and result analysis
- **Extensible Design**: Modular architecture allowing for customization
- **Automatic Dependency Management**: Self-installing system that handles GMTSAR setup automatically

```{note}
**Platform Compatibility**: InSARLite is primarily developed and tested on Ubuntu Linux. For Windows users, WSL2 with Ubuntu provides the best experience. macOS and other Linux distributions have experimental support.
```

```{note}
**Zero Configuration Setup**: InSARLite automatically detects and installs GMTSAR on first startup, requiring no manual dependency management from users.
```

### Core Components

```{mermaid}
graph TD
    A[Data Management] --> B[Baseline Planning]
    B --> C[Image Processing]
    C --> D[Interferogram Generation]
    D --> E[Phase Unwrapping]
    E --> F[Time Series Analysis]
    F --> G[Visualization]
    
    A1[EarthData Authentication] --> A
    A2[Sentinel-1 Download] --> A
    A3[DEM Management] --> A
    
    B1[Interactive Plotting] --> B
    B2[Master Selection] --> B
    B3[Network Design] --> B
    
    C1[Orbit Processing] --> C
    C2[Image Alignment] --> C
    C3[Coregistration] --> C
    
    D1[Interferometry] --> D
    D2[Coherence Calculation] --> D
    D3[Filtering] --> D
    
    E1[Reference Point] --> E
    E2[Mask Definition] --> E
    E3[Unwrapping Algorithms] --> E
    
    F1[SBAS Processing] --> F
    F2[Time Series Generation] --> F
    F3[Velocity Calculation] --> F
    
    G1[Interactive Viewing] --> G
    G2[Export Tools] --> G
    G3[Animation Creation] --> G
```

### Module Structure

#### 1. **Main Application (`main.py`)**
- Central GUI orchestrator
- User interface management
- Workflow coordination
- Configuration handling

#### 2. **Data Management Module**
- **EarthData Authentication**: Secure credential management
- **Data Downloads**: Automated Sentinel-1 acquisition
- **DEM Handling**: Digital Elevation Model processing
- **File Organization**: Structured project management

#### 3. **GMTSAR GUI Modules**
- **Baseline Planning**: Interactive network design
- **Image Processing**: Alignment and coregistration
- **Interferometry**: Interferogram generation
- **Unwrapping**: Phase unwrapping and masking
- **Time Series**: SBAS processing and analysis

#### 4. **Utilities**
- **Configuration Management**: Settings and preferences
- **Authentication**: Secure API access
- **Data Handlers**: File I/O operations
- **Plotting Tools**: Matplotlib integration

#### 5. **Visualization**
- **Interactive Viewers**: Real-time data exploration
- **Export Functions**: Publication-ready outputs
- **Animation Tools**: Time series animations

## Processing Workflow

### Complete InSAR Processing Pipeline

InSARLite implements a comprehensive 7-step processing workflow:

#### Step 0: Project Setup
1. **Authentication**: Configure EarthData credentials
2. **Area Definition**: Define study area and time period
3. **Data Search**: Query available Sentinel-1 acquisitions
4. **Data Download**: Automated data acquisition
5. **DEM Preparation**: Download and prepare elevation data

#### Step 1: Data Preparation
1. **File Organization**: Structure downloaded data
2. **Metadata Extraction**: Parse Sentinel-1 metadata
3. **Quality Assessment**: Verify data integrity
4. **Subswath Selection**: Choose processing subswaths

#### Step 2: Baseline Analysis and Network Design
1. **Baseline Calculation**: Compute temporal and spatial baselines
2. **Interactive Planning**: Visual network design
3. **Master Selection**: Optimal reference scene selection
4. **Pair Generation**: Create interferometric pairs

#### Step 3: Orbit Processing
1. **Orbit Download**: Acquire precise orbit files
2. **Orbit Integration**: Apply orbital corrections
3. **Geometric Correction**: Improve geolocation accuracy

#### Step 4: Image Alignment and Interferometry
1. **Coregistration**: Align slave images to master
2. **Interferogram Formation**: Generate phase difference images
3. **Coherence Calculation**: Assess interferometric quality
4. **Filtering**: Reduce noise and improve quality

#### Step 5: Phase Unwrapping
1. **Mask Definition**: Define processing areas
2. **Reference Point**: Set phase reference
3. **Unwrapping**: Convert wrapped to continuous phase
4. **Quality Control**: Validate unwrapping results

#### Step 6: Time Series Analysis
1. **SBAS Processing**: Small Baseline Subset analysis
2. **Atmospheric Correction**: Remove atmospheric effects
3. **Velocity Estimation**: Calculate deformation rates
4. **Time Series Generation**: Create displacement time series

#### Step 7: Visualization and Export
1. **Interactive Viewing**: Explore results
2. **Statistical Analysis**: Generate summary statistics
3. **Export Functions**: Save results in various formats
4. **Publication Tools**: Create figures and animations

### Data Flow

```{mermaid}
flowchart LR
    A[Sentinel-1 Data] --> B[Preprocessing]
    B --> C[Alignment]
    C --> D[Interferometry]
    D --> E[Unwrapping]
    E --> F[Time Series]
    F --> G[Results]
    
    H[DEM Data] --> B
    I[Orbit Files] --> C
    J[Reference Point] --> E
    K[Atmospheric Data] --> F
```

## Key Features

### 🎯 **Interactive Baseline Planning**
- Real-time baseline network visualization
- Click-and-drag pair selection
- Automatic master scene selection
- Network optimization tools

### 🛰️ **Automated Data Management**
- Seamless EarthData integration
- Bulk data downloads with progress tracking
- Automatic file organization
- DEM data acquisition and processing

### ⚙️ **Professional Processing**
- Complete GMTSAR workflow integration
- Parallel processing capabilities
- Quality control at each step
- Flexible parameter configuration

### 📊 **Advanced Visualization**
- Interactive result viewing
- Time series plotting and analysis
- Publication-ready figure generation
- Animation creation tools

### 🔧 **User-Friendly Interface**
- Intuitive step-by-step workflow
- Progress tracking and logging
- Error handling and recovery
- Comprehensive help system

## Technical Specifications

### Supported Data Types
- **SAR Data**: Sentinel-1 (C-band)
- **DEM Data**: SRTM (30m and 90m resolution)
- **Orbits**: Precise and restituted orbits
- **Atmospheric**: GACOS atmospheric corrections

```{note}
**Future DEM Support**: ASTER and NASADEM DEM options are planned for future releases.
```

### Output Formats
- **Raster**: NetCDF, GeoTIFF, GMT GRD
- **Vector**: Shapefiles, KML
- **Images**: PNG, PDF, SVG
- **Data**: CSV, HDF5

### Performance Characteristics
- **Processing Speed**: Optimized for multi-core systems
- **Memory Usage**: Efficient memory management
- **Scalability**: Handles large datasets and long time series
- **Reliability**: Robust error handling and recovery

## Best Practices

### Project Planning
1. **Start Small**: Begin with limited areas and time periods
2. **Check Data Availability**: Verify Sentinel-1 coverage
3. **Consider Baselines**: Plan for optimal temporal/spatial baselines
4. **Resource Planning**: Ensure adequate storage and computation

### Data Quality
1. **Coherence Assessment**: Monitor interferometric quality
2. **Baseline Optimization**: Use appropriate baseline thresholds
3. **Seasonal Considerations**: Account for vegetation and weather
4. **Validation**: Cross-check results with independent data

### Processing Efficiency
1. **Parallel Processing**: Utilize multiple CPU cores
2. **Storage Management**: Use fast storage for processing
3. **Memory Optimization**: Monitor memory usage
4. **Incremental Processing**: Process in manageable chunks

## Next Steps

Ready to start using InSARLite? Continue to:

- [User Interface Guide](interface.md) - Learn the InSARLite interface
- [Data Management](data-management.md) - Set up data downloads
- [Quick Start Guide](../quickstart.md) - Complete your first project

For technical details, see:
- [API Reference](../api/index.md) - Detailed function documentation
- [Developer Guide](../developer-guide/index.md) - Architecture and internals