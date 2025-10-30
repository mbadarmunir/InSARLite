# InSARLite v1.2.0 Release Notes

**Release Date**: October 30, 2025  
**Version**: 1.2.0  
**Previous Version**: 1.1.0  

## 🌟 Major New Features

### 🔄 **Enhanced WSL Support**
InSARLite now provides seamless integration with Windows Subsystem for Linux (WSL), making it easier than ever for Windows users to run InSAR processing workflows.

**Key WSL Improvements:**
- **Automatic WSL Detection**: Smart detection of WSL environments by scanning `/proc/version` for Microsoft/WSL signatures
- **Universal Display Configuration**: Automatically configures `export DISPLAY=:0` for all WSL versions (WSL1, WSL2, and all distributions)
- **Intelligent Configuration Management**: Prevents duplicate DISPLAY entries in `.bashrc` and only configures when needed
- **Cross-Version Compatibility**: Works with WSL1, WSL2, WSLg, and legacy X11 server setups

### 🚀 **Performance Enhancements**

#### **GNU Parallel Integration**
- **Parallel Processing**: Automatic installation of GNU Parallel for enhanced processing performance
- **Better Resource Utilization**: Maximizes CPU usage during interferogram processing
- **Faster Workflows**: Significant speed improvements for batch processing operations

#### **SBAS Parallel with OpenMP Support**
- **Custom Compilation**: Advanced SBAS parallel compilation with optimized gcc flags
- **OpenMP Multi-threading**: Enhanced time series analysis with parallel processing capabilities
- **Production-Ready Build**: Uses proven compilation flags for optimal performance:
  ```bash
  gcc -fopenmp -O2 -Wall -m64 -fPIC -fno-strict-aliasing -std=c99 -z muldefs
  ```

### 📦 **Improved Dependencies & Installation**

#### **Enhanced Package Management**
- **netCDF4 Support**: Added `netCDF4>=1.5.0` dependency for better NetCDF file handling
- **Robust Installation**: More resilient GMTSAR installer with comprehensive error handling
- **Cross-Platform Compatibility**: Improved dependency resolution for different Linux distributions

#### **Enhanced Entry Points**
- **Dual Command Support**: 
  - `insarlite` - Traditional entry point
  - `InSARLiteApp` - New, more descriptive entry point
- **Better Compatibility**: Improved compatibility with different Python environments and package managers

## 🛠️ Technical Improvements

### **GMTSAR Installer Enhancements**
- **WSL-Aware Installation**: Automatically detects and configures for WSL environments
- **GNU Parallel Integration**: Seamlessly installs GNU Parallel alongside GMTSAR
- **SBAS Parallel Compilation**: Automated compilation and installation of SBAS parallel tools with intelligent fallback strategies
- **Robust Library Linking**: Smart detection of GMTSAR library paths with fallback compilation options
- **Intelligent Orbits Handling**: Properly skips orbits configuration when user opts out (no fallback to /tmp)
- **Error Recovery**: Better error handling and graceful fallbacks during installation failures

### **Code Quality & Reliability**
- **Exception Handling Fixes**: Resolved closure-related variable scoping issues in:
  - `src/insarlite/gmtsar_gui/unwrap.py` (line 256)
  - `src/insarlite/utils/data_handlers.py` (line 396)
  - `src/insarlite/utils/utils.py` (line 1106)
- **Memory Management**: Improved exception variable capture to prevent memory leaks
- **Thread Safety**: Enhanced lambda function variable scoping for multi-threaded operations

### **Documentation Updates**
- **Comprehensive WSL Guide**: Updated installation documentation with step-by-step WSL setup
- **Troubleshooting Section**: Enhanced troubleshooting guides for common WSL and display issues
- **Performance Tips**: Added guidance for optimal performance in WSL environments
- **Auto-Configuration Notes**: Documentation of new automatic configuration features

## 📊 **Performance Benchmarks**

### **Processing Speed Improvements**
- **GNU Parallel**: Up to 50% faster batch processing on multi-core systems
- **SBAS Parallel**: Significant speedup in time series analysis (varies by dataset size)
- **WSL Performance**: Near-native Linux performance with proper filesystem usage

### **Installation Time**
- **Streamlined Process**: Reduced installation complexity through automation
- **One-Time Setup**: Automatic dependency resolution eliminates manual configuration steps
- **Error Resilience**: Robust installation process with fewer failure points

## 🔧 **Breaking Changes**

**None** - This release maintains full backward compatibility with v1.1.0.

## 🐛 **Bug Fixes**

### **Variable Scoping Issues**
- **Fixed**: Exception variable capture in lambda functions and closures
- **Impact**: Prevents potential runtime errors in error handling code paths
- **Files affected**: 3 core files with improved exception handling

### **Environment Configuration**
- **Fixed**: Duplicate DISPLAY variable entries in WSL environments
- **Fixed**: Inconsistent environment setup across different WSL versions
- **Fixed**: Missing environment variables after GMTSAR installation
- **Fixed**: Orbits directory fallback to /tmp when user opts out of orbit installation

## 🔄 **Migration Guide**

### **From v1.1.0 to v1.2.0**

**Automatic Migration** - No manual steps required. Users can simply upgrade:

```bash
# Standard upgrade
pip install --upgrade insarlite

# Or specific version
pip install insarlite==1.2.0

# Verify installation
insarlite --version  # or
InSARLiteApp --version
```

**WSL Users** - Existing WSL installations will automatically benefit from enhanced display configuration on next GMTSAR installation or manual configuration.

**Performance Benefits** - Existing projects will automatically use GNU Parallel and SBAS parallel tools if available.

## 📋 **System Requirements**

### **Supported Platforms**
- **✅ Ubuntu Linux 20.04+** (Primary platform - fully tested)
- **✅ WSL1/WSL2** (All distributions - enhanced support)
- **✅ Other Debian-based Linux** (Expected to work with minimal issues)
- **⚠️ RHEL/CentOS/Fedora** (Manual package management may be required)
- **⚠️ macOS** (Experimental support)
- **❌ Native Windows** (Not supported - use WSL2)

### **Dependencies**
- **Python**: 3.8+ (unchanged)
- **Memory**: 4GB RAM minimum, 8GB recommended (unchanged)
- **Storage**: 2GB free space + additional for data processing (unchanged)
- **Network**: Internet connection for data downloads and package installation

### **New Dependencies**
- **netCDF4**: ≥1.5.0 (automatically installed)
- **GNU Parallel**: Automatically installed on Linux systems
- **OpenMP**: Required for SBAS parallel compilation

## 🚀 **Getting Started**

### **New Installation**
```bash
# Install InSARLite
pip install insarlite

# Launch application
InSARLiteApp
```

### **WSL Installation** (Enhanced)
```bash
# In PowerShell as Administrator
wsl --install -d Ubuntu-20.04

# Inside WSL Ubuntu
sudo apt update && sudo apt install python3-pip python3-tk
pip install insarlite
InSARLiteApp  # Display automatically configured!
```

### **Verify New Features**
```bash
# Check GNU Parallel installation
parallel --version

# Check SBAS parallel availability
which sbas_parallel

# Verify WSL display configuration (in WSL)
echo $DISPLAY  # Should show :0 automatically
```

## 📞 **Support & Feedback**

### **Getting Help**
- **Documentation**: [insarlite.readthedocs.io](https://insarlite.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/mbadarmunir/InSARLite/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mbadarmunir/InSARLite/discussions)

### **Known Issues**
- **WSL Display**: If GUI doesn't appear, install X11 server (VcXsrv/Xming) on Windows
- **SBAS Parallel**: Compilation may fail on systems with missing development tools or GMTSAR library linking issues (automatically handled with fallback strategies)
- **GNU Parallel**: May require manual installation on non-Debian systems

### **Reporting Bugs**
When reporting issues, please include:
- InSARLite version: `insarlite --version`
- Python version: `python --version`
- Operating system and version
- WSL version (if applicable): `wsl --version`
- Error messages and stack traces

## 🎯 **Future Roadmap**

### **Upcoming Features** (v1.3.0 and beyond)
- **Enhanced Visualization**: Improved plotting and mapping capabilities
- **Cloud Integration**: Support for cloud-based processing and storage
- **API Enhancements**: Programmatic access to InSAR processing workflows
- **Additional Parallelization**: More parallel processing opportunities
- **macOS Native Support**: Better support for macOS environments

---

## 👥 **Credits**

**Lead Developer**: Muhammad Badar Munir  
**Email**: mbadarmunir@gmail.com  
**Institution**: University of Twente  

**Contributors**: Community feedback and testing from InSAR researchers worldwide

**Special Thanks**: 
- GMTSAR development team for the excellent SAR processing toolkit
- WSL team at Microsoft for making Linux-Windows integration seamless
- Python packaging community for excellent tools and documentation

---

**Full Changelog**: [v1.1.0...v1.2.0](https://github.com/mbadarmunir/InSARLite/compare/v1.1.0...v1.2.0)

**Download**: 
- **PyPI**: `pip install insarlite==1.2.0`
- **GitHub Releases**: [v1.2.0 Release](https://github.com/mbadarmunir/InSARLite/releases/tag/v1.2.0)
- **Wheel File**: `insarlite-1.2.0-py3-none-any.whl`