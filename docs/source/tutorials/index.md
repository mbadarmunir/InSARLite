# Turkey Landslide Tutorial

This section contains a comprehensive tutorial demonstrating InSARLite's complete workflow.

```{toctree}
:maxdepth: 2

turkey-case-study
```

## Tutorial Overview

The **[Turkey Landslide Case Study](turkey-case-study.md)** provides a complete end-to-end demonstration of InSAR time series analysis using InSARLite. This tutorial uses real research data from the December 8, 2024 Güngören landslide event in northeastern Turkey.

### What You'll Learn

- **Installation**: GMTSAR automatic setup and verification
- **Project Configuration**: Data folder, AOI definition, temporal range
- **Data Management**: Querying, downloading, and extracting Sentinel-1 data
- **Baseline Network**: Interactive design using Base2Net tool
- **Interferogram Generation**: Alignment and IFG creation
- **Phase Unwrapping**: Masking, reference point selection, and unwrapping
- **SBAS Analysis**: Time series inversion and velocity mapping
- **Visualization**: Interactive exploration of deformation results

### Dataset Details

- **Location**: Güngören, northeastern Turkey (41.34°N, 41.27°E)
- **Event**: Catastrophic landslide failure on December 8, 2024
- **Satellite**: Sentinel-1 ascending orbit
- **Acquisitions**: 60 scenes covering ~18 months
- **Master Scene**: August 29, 2023
- **Subswath**: IW2 (F2 only)
- **Results**: Mean VLOS velocities up to 25 mm/yr, precursory acceleration detected

### Time and Storage Requirements

- **Processing Time**: ~50+ hours (highly dependent on CPU cores and internet speed)
- **Storage Space**: ~710 GB total (328.8 GB downloads + ~320 GB processing + ~60 GB outputs)
- **Download Time**: 1-3 hours (depends on internet connection)
- **RAM**: 16 GB minimum, 32 GB strongly recommended

### Prerequisites

Before starting this tutorial:

1. **Install InSARLite**: Follow the [Installation Guide](../installation.md)
2. **NASA EarthData Account**: Register at [https://urs.earthdata.nasa.gov/](https://urs.earthdata.nasa.gov/)
3. **System Requirements**: Ubuntu 20.04 or 22.04 LTS
4. **Multi-core CPU**: Strongly recommended for parallel processing
5. **Basic InSAR Knowledge**: Understanding of interferometry principles helpful but not required

### Getting Help

If you encounter issues:

- Check troubleshooting sections within the tutorial
- Search [GitHub Issues](https://github.com/mbadarmunir/InSARLite/issues)
- Create a new issue with error details and screenshots