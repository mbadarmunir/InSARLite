# Quick Start Guide

Get up and running with InSARLite quickly! This guide provides essential information to start your first InSAR processing workflow.

## Prerequisites

- InSARLite installed ([see installation guide](installation.md))
- NASA EarthData account for Sentinel-1 data downloads

```{important}
**Platform Requirements**: InSARLite has been developed and tested exclusively on **Ubuntu 20.04 and 22.04 LTS**. Other operating systems (including WSL, macOS, or other Linux distributions) have not been tested and are not officially supported.
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

This process takes 15-30 minutes but only happens once. See the [Installation Guide](installation.md) for details.
```

## Learn InSARLite: Turkey Landslide Tutorial

**The best way to learn InSARLite is through our comprehensive tutorial:**

### [🏔️ Turkey Landslide Case Study →](tutorials/turkey-case-study.md)

This complete end-to-end tutorial demonstrates InSARLite's full workflow using real research data from the December 8, 2024 Güngören landslide in northeastern Turkey. The tutorial includes **63 screenshots** covering every step from installation to scientific results.

**What's Covered:**
- ✅ GMTSAR automatic installation (8 screenshots)
- ✅ Project configuration with AOI and temporal range (14 screenshots)
- ✅ Data querying, downloading, and extraction
- ✅ Baseline network design and master selection (9 screenshots)
- ✅ Interferogram generation (3 screenshots)
- ✅ Phase unwrapping with mask and reference point (20 screenshots)
- ✅ SBAS inversion and time series analysis (6 screenshots)
- ✅ Interactive visualization and results (2 screenshots)

**Dataset Details:**
- **Acquisitions**: 60 Sentinel-1 scenes
- **Processing Time**: ~50 hours
- **Storage Required**: ~710 GB
- **Results**: Mean VLOS velocities up to 25 mm/yr, precursory deformation detected

```{tip}
The Turkey tutorial uses actual research data demonstrating how InSAR can detect precursory deformation signals before catastrophic landslide failures—perfect for understanding InSARLite's scientific capabilities!
```

## Quick Workflow Overview

For reference, here are the main processing steps covered in the Turkey tutorial:

1. **Installation**: GMTSAR automatic setup
2. **Project Configuration**: Define AOI, temporal range, download data
3. **Baseline Network**: Design interferometric pairs using Base2Net
4. **Interferogram Generation**: Align and generate IFGs
5. **Phase Unwrapping**: Create mask, select reference point, unwrap
6. **SBAS Inversion**: Time series analysis and velocity mapping
7. **Visualization**: Interactive exploration of results

## Adapting the Tutorial to Your Study Area

Once you've completed the Turkey case study, you can adapt the workflow to your own study area by adjusting key parameters:

### Spatial Parameters
- **AOI coordinates**: Draw your own bounding box on the interactive map
- **Location**: Any area covered by Sentinel-1 (global coverage)
- **Frame selection**: Automatic based on your AOI

### Temporal Parameters  
- **Start date**: Beginning of your analysis period
- **End date**: End of your analysis period
- **Temporal baseline threshold**: 24-96 days typical (adjust based on application)

### Network Parameters
- **Perpendicular baseline threshold**: 150-300m (depends on coherence requirements)
- **Master image**: Select based on network centrality or specific date
- **Network density**: More pairs increase computation but improve temporal coverage

### Processing Parameters
- **Subswath**: IW1, IW2, IW3, or combinations thereof
- **Correlation threshold**: 0.05-0.15 (lower for challenging areas)
- **Reference point**: Select stable area in your region (critical for accurate results)
- **SBAS smoothing**: Adjust based on noise characteristics

```{tip}
Start with parameters similar to the Turkey case study, then refine based on your specific application, study area characteristics, and coherence conditions.
```

## Getting Help

If you encounter issues:

- **Check processing logs**: InSARLite provides detailed logs for each processing step
- **Review the tutorial**: The [Turkey Case Study](tutorials/turkey-case-study.md) includes troubleshooting tips
- **Search GitHub Issues**: [https://github.com/mbadarmunir/InSARLite/issues](https://github.com/mbadarmunir/InSARLite/issues)
- **Create new issue**: Provide error messages, screenshots, and system details

## Next Steps

- **Complete the tutorial**: Work through the [Turkey Landslide Case Study](tutorials/turkey-case-study.md)
- **Explore your data**: Apply InSARLite to your own research area
- **Understand the architecture**: Read the [Overview](user-guide/overview.md) for technical details

Happy processing! 🛰️📊