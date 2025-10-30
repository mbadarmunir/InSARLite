## 🌟 InSARLite v1.2.0: Enhanced WSL Support & Performance Boost

This release brings major improvements for WSL users and significant performance enhancements for all platforms.

### 🔄 **Revolutionary WSL Support**
- **🎯 Automatic WSL Detection** - Smart detection for all WSL versions (WSL1, WSL2, all distributions)
- **🖥️ One-Click Display Setup** - Automatic `DISPLAY=:0` configuration for seamless GUI operation
- **🔧 Universal Compatibility** - Works with WSLg, X11 servers, and legacy setups

### 🚀 **Major Performance Improvements**
- **⚡ GNU Parallel Integration** - Up to 50% faster batch processing on multi-core systems
- **🔥 SBAS Parallel with OpenMP** - Multi-threaded time series analysis for faster results
- **⚙️ Optimized Compilation** - Custom gcc flags: `-fopenmp -O2 -Wall -m64 -fPIC -std=c99`

### 📦 **Enhanced Package Management**
- **📊 netCDF4 Support** - Added `netCDF4>=1.5.0` for better NetCDF file handling
- **🎮 Dual Entry Points** - Both `insarlite` and `InSARLiteApp` commands available
- **🛡️ Robust Installation** - Improved error handling and automatic recovery

### 🐛 **Bug Fixes**
- Fixed exception variable scoping in lambda functions (`unwrap.py`, `data_handlers.py`, `utils.py`)
- Resolved closure-related memory issues in multi-threaded operations
- Improved error handling in core processing modules

### 📋 **Installation**

**Standard Installation:**
```bash
pip install insarlite==1.2.0
```

**WSL Installation (Now Even Easier!):**
```bash
# In PowerShell as Administrator
wsl --install -d Ubuntu-20.04

# Inside WSL Ubuntu
sudo apt update && sudo apt install python3-pip python3-tk
pip install insarlite
InSARLiteApp  # GUI works automatically - no manual setup!
```

### 🎯 **What This Means for You**

| Improvement | Impact |
|-------------|--------|
| **Automatic WSL Setup** | No more manual DISPLAY configuration |
| **GNU Parallel** | Faster processing of large datasets |
| **SBAS Parallel** | Quicker time series analysis |
| **Better Dependencies** | More reliable installation process |
| **Enhanced Entry Points** | Better compatibility with different environments |

### 🔄 **Migration from v1.1.0**
✅ **Zero breaking changes** - Direct upgrade  
✅ **Automatic benefits** - New features work immediately  
✅ **Full compatibility** - All existing workflows supported

### 📊 **Performance Benchmarks**
- **50% faster** batch processing with GNU Parallel
- **Automatic** WSL display configuration (zero manual setup)
- **Enhanced** SBAS processing with OpenMP threading
- **Near-native** performance in WSL2 environments

### 🔧 **For Developers**
- Enhanced GMTSAR installer with WSL detection
- Improved exception handling patterns
- Better dependency management
- More robust build process

### 📞 **Support & Documentation**
- 📖 **Full Documentation**: [insarlite.readthedocs.io](https://insarlite.readthedocs.io/)
- 🐛 **Report Issues**: [GitHub Issues](https://github.com/mbadarmunir/InSARLite/issues)
- 💬 **Community**: [GitHub Discussions](https://github.com/mbadarmunir/InSARLite/discussions)

### 📁 **Assets**
- **Wheel Package**: `insarlite-1.2.0-py3-none-any.whl` (163,797 bytes)
- **Source Code**: Available via git tags and GitHub archive

---

**🎉 Ready to upgrade?** Run `pip install --upgrade insarlite` and enjoy the enhanced WSL support and performance improvements!

**📋 Supported Platforms**: Ubuntu Linux (primary), WSL1/WSL2 (enhanced), Other Debian-based Linux, RHEL/CentOS/Fedora (experimental), macOS (experimental)

**⚠️ Note**: Windows users should use WSL2 for the best experience. Native Windows is not supported.