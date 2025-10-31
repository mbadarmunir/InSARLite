# InSARLite

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.2.1-blue.svg)](https://github.com/mbadarmunir/InSARLite/releases)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17481377.svg)](https://doi.org/10.5281/zenodo.17481377)
[![Documentation](https://img.shields.io/badge/docs-available-brightgreen.svg)](https://insarlite.readthedocs.io/)

**InSARLite** is a comprehensive GUI application for Interferometric Synthetic Aperture Radar (InSAR) processing using the GMTSAR workflow. It provides an intuitive interface for processing Sentinel-1 SAR data to generate interferograms and perform time series analysis.

## 🌟 Key Features

- **🛰️ Automated Data Management**: Seamless Sentinel-1 data search, download, and organization
- **🎯 Interactive Baseline Planning**: Visual baseline network design with matplotlib-based plotting
- **⚡ Complete GMTSAR Integration**: Full workflow from raw data to unwrapped interferograms
- **📊 Advanced Visualization**: Professional plotting tools and time series analysis
- **🔧 User-Friendly Interface**: Intuitive step-by-step workflow with progress tracking
- **🖥️ Platform Support**: Optimized for Ubuntu Linux with WSL2 support for Windows
- **🚀 Enhanced Performance**: Automatic GNU Parallel and SBAS Parallel installation
- **🔄 WSL Auto-Configuration**: Automatic display configuration for all WSL versions

## 🚀 Quick Start

### Platform Compatibility

- **✅ Ubuntu Linux** (Primary platform - fully tested)
- **⚠️ Windows** (Use WSL2 with Ubuntu for best results)  
- **⚠️ macOS** (Experimental support)
- **⚠️ Other Linux** (May require manual configuration)

### Installation

Install InSARLite using pip:

```bash
pip install insarlite
```

**For Windows users**: Install WSL2 first, then install InSARLite inside Ubuntu:
```powershell
# In PowerShell as Administrator
wsl --install -d Ubuntu-20.04
```

### Launch the Application

```bash
InSARLiteApp
```

That's it! The InSARLite GUI will open and guide you through your first InSAR project.

## 📖 Documentation

Comprehensive documentation is available at [insarlite.readthedocs.io](https://insarlite.readthedocs.io/) including:

- **[Installation Guide](https://insarlite.readthedocs.io/en/latest/installation.html)** - Detailed installation instructions
- **[Quick Start Tutorial](https://insarlite.readthedocs.io/en/latest/quickstart.html)** - Get up and running in minutes
- **[User Guide](https://insarlite.readthedocs.io/en/latest/user-guide/)** - Complete usage documentation
- **[API Reference](https://insarlite.readthedocs.io/en/latest/api/)** - Detailed API documentation
- **[Developer Guide](https://insarlite.readthedocs.io/en/latest/developer-guide/)** - For contributors and developers

## 🛠️ What is InSAR?

Interferometric Synthetic Aperture Radar (InSAR) is a radar technique used to generate maps of surface deformation or digital elevation models using differences in the phase of radar waves returning to the satellite. InSARLite makes this powerful technique accessible through:

- **Automated workflows** for complex processing chains
- **Interactive tools** for network design and parameter selection
- **Professional visualization** for scientific analysis and publication

## 🔧 Requirements

- **Python**: 3.8 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: 4 GB RAM minimum (8 GB recommended)
- **Storage**: 2 GB free space (more for data processing)
- **Network**: Internet connection for data downloads

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

InSARLite is perfect for:

- **Research**: Academic studies in geodesy, geophysics, and remote sensing
- **Education**: Teaching InSAR principles and processing techniques
- **Monitoring**: Operational monitoring of volcanoes, earthquakes, and subsidence
- **Analysis**: Scientific analysis of surface deformation processes

## 📈 Example Applications

### Earthquake Studies
Monitor co-seismic and post-seismic deformation with millimeter precision.

### Volcano Monitoring
Track volcanic inflation and deflation patterns over time.

### Urban Subsidence
Measure land subsidence in urban areas and correlate with infrastructure.

### Natural Hazards
Assess landslides, floods, and other geohazards using InSAR techniques.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- How to report bugs and request features
- Development setup and workflow
- Code style and testing requirements
- Community guidelines

## 📄 License

InSARLite is released under the [MIT License](LICENSE). This allows free use, modification, and distribution for both academic and commercial purposes.

## 🙏 Acknowledgments

- **GMTSAR Team** - For the powerful InSAR processing engine
- **NASA/ESA** - For providing open access to Sentinel-1 data
- **Python Community** - For the excellent scientific computing ecosystem
- **Contributors** - For bug reports, features, and improvements

## 📧 Support

- **Documentation**: [insarlite.readthedocs.io](https://insarlite.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/mbadarmunir/InSARLite/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mbadarmunir/InSARLite/discussions)
- **Email**: mbadarmunir@gmail.com

## 📊 Citation

If you use InSARLite in your research, please cite:

**Zenodo DOI:**
```
Munir, Muhammad Badar. (2025). InSARLite: A GUI Application for GMTSAR-based InSAR Processing (v1.2.1). 
Zenodo. https://doi.org/10.5281/zenodo.17481377
```

**BibTeX:**
```bibtex
@software{insarlite2025,
  title={InSARLite: A GUI Application for GMTSAR-based InSAR Processing},
  author={Muhammad Badar Munir},
  year={2025},
  version={1.2.1},
  url={https://github.com/mbadarmunir/InSARLite},
  doi={10.5281/zenodo.17481377},
  license={MIT}
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