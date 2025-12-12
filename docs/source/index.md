# InSARLite Documentation

Welcome to **InSARLite**, a comprehensive GUI application for Interferometric Synthetic Aperture Radar (InSAR) processing using the GMTSAR workflow. InSARLite provides an intuitive interface for processing Sentinel-1 SAR data to generate interferograms and perform time series analysis.

```{image} https://img.shields.io/badge/python-3.8+-blue.svg
:alt: Python Version
```

```{image} https://img.shields.io/badge/license-MIT-green.svg
:alt: License
```

```{image} https://img.shields.io/badge/version-1.3.0-blue.svg
:alt: Version
```

## What is InSAR?

Interferometric Synthetic Aperture Radar (InSAR) is a radar technique used to generate maps of surface deformation or digital elevation models (DEMs) using differences in the phase of the waves returning to the satellite or aircraft. InSARLite simplifies the complex InSAR processing workflow by providing:

- **Automated data download** from ASF and other sources
- **Interactive baseline planning** and network design
- **Streamlined interferogram generation** 
- **Advanced visualization tools** for results analysis
- **Time series processing** capabilities

## Quick Start

### Installation

Install InSARLite using pip:

```bash
pip install insarlite
```

For detailed installation instructions including GMTSAR setup, see the [Installation Guide](installation.md).

### Launch the Application

```bash
InSARLiteApp
```

On first launch, InSARLite will automatically detect and install GMTSAR if needed.

## Learn by Example

The best way to learn InSARLite is through our comprehensive tutorial using real research data:

**[Turkey Landslide Case Study →](tutorials/turkey-case-study.md)**

This tutorial demonstrates the complete InSARLite workflow using 60 Sentinel-1 acquisitions to detect precursory deformation signals before the December 8, 2024 Güngören landslide in Turkey. You'll learn:

- Complete project setup from installation to results
- Data querying, downloading, and extraction
- Interactive baseline network design
- Interferogram generation and unwrapping
- SBAS time series analysis
- Publication-quality visualization

**Processing time**: ~50 hours | **Storage required**: ~710 GB

## Documentation Structure

```{toctree}
:maxdepth: 2
:caption: Getting Started

user-guide/overview
installation
quickstart
tutorials/index
```

```{toctree}
:maxdepth: 2
:caption: User Guide

user-guide/index
```

```{toctree}
:maxdepth: 2
:caption: Developer Guide

developer-guide/index
```

```{toctree}
:maxdepth: 1
:caption: About

about
contributing
changelog
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
  version={1.3.0},
  url={https://github.com/mbadarmunir/InSARLite}
}
```

## Support

- **Documentation**: You're reading it!
- **Issues**: [GitHub Issues](https://github.com/mbadarmunir/InSARLite/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mbadarmunir/InSARLite/discussions)

## License

InSARLite is licensed under the MIT License. See the [license](license.md) page for details.