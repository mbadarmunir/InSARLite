# InSARLite

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.3.1-blue.svg)](https://github.com/mbadarmunir/InSARLite/releases)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17210560.svg)](https://doi.org/10.5281/zenodo.17210560)
[![Documentation](https://img.shields.io/badge/docs-available-brightgreen.svg)](https://insarlite.readthedocs.io/)

**InSARLite** is a comprehensive GUI application for Interferometric Synthetic Aperture Radar (InSAR) processing using the GMTSAR workflow. It provides an intuitive interface for processing Sentinel-1 SAR data to generate interferograms and perform time series analysis.

> **📣 v1.3.1 Released!** Patch release with important bug fixes: output folder validation to prevent data corruption, baseline constraints configuration persistence, subswath-specific interferogram generation fixes, and alignment workflow improvements. [See Release Notes](RELEASE_NOTES_v1.3.1.md)

## 🌟 Key Features

- **🛰️ Automated Data Management**: Seamless Sentinel-1 data search, download, and organization
- **🎯 Interactive Baseline Planning**: Visual baseline network design with matplotlib-based plotting
- **⚡ Complete GMTSAR Integration**: Full workflow from raw data to unwrapped interferograms
- **📊 Interactive Visualization**: Hover tooltips, polygon analysis, and true vector output (PDF/SVG/EPS)
- **🗺️ Complete Tutorial**: Turkey landslide case study with 60 acquisitions and 64 screenshots
- **📚 Professional Documentation**: 600+ pages covering installation to advanced analysis
- **🔧 User-Friendly Interface**: Intuitive step-by-step workflow with progress tracking
- **🖥️ Platform Support**: Optimized for Ubuntu Linux with WSL2 support for Windows

## 🚀 Quick Start

### Platform Compatibility

**Supported Platform**: InSARLite has been developed and tested **exclusively on Ubuntu Linux**.

- **✅ Ubuntu 20.04 LTS** (Fully tested and supported)
- **✅ Ubuntu 22.04 LTS** (Fully tested and supported)
- **⚠️ Other Linux** (Not tested - use at your own risk)
- **⚠️ WSL2** (May work but not officially supported)
- **❌ Native Windows** (Not supported - GMTSAR cannot compile on Windows)
- **❌ macOS** (Not tested or supported)

### Installation

Install InSARLite on Ubuntu using pip:

```bash
pip install insarlite
```

**Requirements**:
- Ubuntu 20.04 LTS or 22.04 LTS
- Python 3.8 or higher
- NASA Earthdata account ([Register here](https://urs.earthdata.nasa.gov/users/new))

### Launch the Application

```bash
InSARLiteApp
```

That's it! The InSARLite GUI will open and guide you through your first InSAR project.

## 📖 Documentation

Comprehensive documentation is available at [insarlite.readthedocs.io](https://insarlite.readthedocs.io/) including:

- **[Installation Guide](https://insarlite.readthedocs.io/en/latest/installation.html)** - Detailed installation instructions
- **[Quick Start Tutorial](https://insarlite.readthedocs.io/en/latest/quickstart.html)** - Get up and running in minutes
- **[Turkey Case Study](https://insarlite.readthedocs.io/en/latest/tutorials/turkey-case-study.html)** - Complete 60-acquisition workflow with screenshots
- **[User Guide](https://insarlite.readthedocs.io/en/latest/user-guide/)** - Interface, workflow, and visualization tools
- **[Developer Guide](https://insarlite.readthedocs.io/en/latest/developer-guide/)** - For contributors and developers

## 🛠️ What is InSAR?

Interferometric Synthetic Aperture Radar (InSAR) is a radar technique used to generate maps of surface deformation or digital elevation models using differences in the phase of radar waves returning to the satellite. InSARLite makes this powerful technique accessible through:

- **Automated workflows** for complex processing chains
- **Interactive tools** for network design and parameter selection
- **Professional visualization** for scientific analysis and publication

## 🔧 System Requirements

### Minimum
- **OS**: Ubuntu 20.04/22.04 LTS
- **Python**: 3.8+
- **RAM**: 8 GB
- **Storage**: 50 GB free space
- **Network**: Internet connection for data downloads
- **NASA Earthdata Account**: Required ([Register here](https://urs.earthdata.nasa.gov/users/new))

### Recommended
- **OS**: Ubuntu 22.04 LTS
- **Python**: 3.9 or 3.10
- **RAM**: 16 GB+
- **Storage**: 100 GB+ SSD
- **CPU**: Multi-core (4+ cores for parallel processing)

## 📊 Processing Workflow

InSARLite implements a complete 7-step InSAR processing pipeline:

1. **Project Setup** - Define study area, time period, and download data
2. **Data Preparation** - Organize and validate Sentinel-1 acquisitions
3. **Baseline Planning** - Design interferometric network and select master scene
4. **Orbit Processing** - Download and apply precise orbit corrections
5. **Interferometry** - Generate interferograms and coherence maps
6. **Phase Unwrapping** - Convert wrapped phase to displacement measurements
7. **Time Series Analysis** - SBAS processing for deformation time series

## 🎯 Use Cases

InSARLite is designed for:

- **🔬 Research**: Academic studies in geodesy, geophysics, and remote sensing
- **🎓 Education**: Teaching InSAR principles and processing workflows
- **📊 Analysis**: Scientific analysis of surface deformation (landslides, subsidence, earthquakes, volcanoes)
- **📖 Learning**: Comprehensive tutorial with real-world Turkey landslide case study

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- How to report bugs and request features
- Development setup and workflow
- Code style and testing requirements
- Community guidelines

## 📄 License

InSARLite is released under the [MIT License](LICENSE). This allows free use, modification, and distribution for both academic and commercial purposes.

##  Support

- **Documentation**: [insarlite.readthedocs.io](https://insarlite.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/mbadarmunir/InSARLite/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mbadarmunir/InSARLite/discussions)
- **Email**: mbadarmunir@gmail.com

## 📊 Citation

If you use InSARLite in your research, please cite:

**Zenodo DOI:**
```
Munir, Muhammad Badar. (2025). InSARLite: A GUI Application for GMTSAR-based InSAR Processing (v1.3.0). 
Zenodo. https://doi.org/10.5281/zenodo.17210560
```

**BibTeX:**
```bibtex
@software{insarlite2025,
  title={InSARLite: A GUI Application for GMTSAR-based InSAR Processing},
  author={Muhammad Badar Munir},
  year={2025},
  version={1.3.0},
  url={https://github.com/mbadarmunir/InSARLite},
  doi={10.5281/zenodo.17210560}
}
```

## 🙏 Acknowledgments

**InSARLite is built on the foundation of [GMTSAR](https://github.com/gmtsar/gmtsar)** - an excellent open-source InSAR processing system developed by the GMTSAR team at Scripps Institution of Oceanography, UC San Diego.

**Special appreciation to:**
- **GMTSAR Development Team** - For creating and maintaining the robust SAR processing toolkit that powers InSARLite
- **Dr. David Sandwell** and **Dr. Xiaopeng Tong** - For their leadership in GMTSAR development
- **The entire GMTSAR community** - For continuous improvements, bug fixes, and scientific contributions

InSARLite serves as a user-friendly interface to GMTSAR's powerful capabilities, making advanced InSAR processing more accessible to researchers and practitioners worldwide. Without GMTSAR's solid foundation, InSARLite would not exist.

**GMTSAR Citation:**
```bibtex
@article{sandwell2011open,
  title={Open radar interferometry software for mapping surface deformation},
  author={Sandwell, David and Mellors, Robert and Tong, Xiaopeng and Wei, Meng and Wessel, Paul},
  journal={Eos, Transactions American Geophysical Union},
  volume={92},
  number={28},
  pages={234--234},
  year={2011},
  publisher={Wiley Online Library}
}
```

---

**InSARLite - Making InSAR accessible to everyone** 🛰️📊