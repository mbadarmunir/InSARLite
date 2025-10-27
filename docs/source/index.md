# InSARLite Documentation

Welcome to **InSARLite**, a comprehensive GUI application for Interferometric Synthetic Aperture Radar (InSAR) processing using the GMTSAR workflow. InSARLite provides an intuitive interface for processing Sentinel-1 SAR data to generate interferograms and perform time series analysis.

```{image} https://img.shields.io/badge/python-3.8+-blue.svg
:alt: Python Version
```

```{image} https://img.shields.io/badge/license-MIT-green.svg
:alt: License
```

```{image} https://img.shields.io/badge/version-1.0.0-blue.svg
:alt: Version
```

## What is InSAR?

Interferometric Synthetic Aperture Radar (InSAR) is a radar technique used to generate maps of surface deformation or digital elevation models (DEMs) using differences in the phase of the waves returning to the satellite or aircraft. InSARLite simplifies the complex InSAR processing workflow by providing:

- **Automated data download** from ASF and other sources
- **Interactive baseline planning** and network design
- **Streamlined interferogram generation** 
- **Advanced visualization tools** for results analysis
- **Time series processing** capabilities

## Key Features

::::{grid} 1 2 2 3
:gutter: 3

:::{grid-item-card} 🛰️ Data Management
:class-card: sd-text-center

Automated download of Sentinel-1 data with EarthData authentication, orbit files, and DEM data
:::

:::{grid-item-card} 🎯 Interactive Planning
:class-card: sd-text-center

Visual baseline network design with matplotlib-based interactive plotting and selection tools
:::

:::{grid-item-card} ⚡ Automated Processing
:class-card: sd-text-center

Complete GMTSAR workflow integration from raw data to unwrapped interferograms
:::

:::{grid-item-card} 📊 Advanced Visualization
:class-card: sd-text-center

Professional plotting tools with customizable displays and analysis capabilities
:::

:::{grid-item-card} 🔧 Extensible Architecture
:class-card: sd-text-center

Modular design allowing for custom processing workflows and plugin development
:::

:::{grid-item-card} 🌐 Cross-Platform
:class-card: sd-text-center

Works on Linux, macOS, and Windows with consistent user experience
:::

::::

## Quick Start

### Installation

Install InSARLite using pip:

```bash
pip install insarlite
```

### Launch the Application

```bash
InSARLiteApp
```

## Documentation Sections

```{toctree}
:maxdepth: 2
:caption: User Guide

installation
quickstart
user-guide/index
tutorials/index
```

```{toctree}
:maxdepth: 2
:caption: API Reference

api/index
```

```{toctree}
:maxdepth: 2
:caption: Developer Guide

developer-guide/index
contributing
changelog
```

```{toctree}
:maxdepth: 1
:caption: About

about
license
```

## Indices and Tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`

## Citation

If you use InSARLite in your research, please cite:

```bibtex
@software{insarlite2025,
  title={InSARLite: A GUI Application for GMTSAR-based InSAR Processing},
  author={Muhammad Badar Munir},
  year={2025},
  version={1.0.0},
  url={https://github.com/mbadarmunir/InSARLite}
}
```

## Support

- **Documentation**: You're reading it!
- **Issues**: [GitHub Issues](https://github.com/mbadarmunir/InSARLite/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mbadarmunir/InSARLite/discussions)

## License

InSARLite is licensed under the MIT License. See the [license](license.md) page for details.