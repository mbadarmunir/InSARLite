# InSARLite v1.2.1 Release Notes

**Release Date**: October 30, 2025  
**Version**: 1.2.1  
**Previous Version**: 1.2.0  
**Type**: Patch Release

## 🐛 **Bug Fixes & Improvements**

### **SBAS Parallel Installation Fixes**
- **Fixed SBAS Parallel Detection**: Resolved issue where SBAS parallel installation was not being triggered when GMTSAR was already installed
- **Improved Library Linking**: Enhanced GMTSAR library detection and linking for SBAS parallel compilation
- **Smart Rebuild Strategy**: Added automatic GMTSAR rebuild to ensure proper library availability for SBAS parallel
- **Better Error Handling**: Improved graceful handling of SBAS parallel compilation failures

### **Enhanced Installation Flow**
- **Automatic SBAS Check**: Now automatically checks and installs SBAS parallel when GMTSAR is detected
- **Robust Library Creation**: Improved library detection and creation from GMTSAR object files
- **Comprehensive Logging**: Added detailed output for SBAS parallel installation process

## 🔧 **Technical Improvements**

### **Installation Logic Enhancements**
```python
# New: Automatic SBAS parallel check in main application flow
def _check_gmtsar_installation(self):
    if gmtsar_detected:
        # Now automatically triggers SBAS parallel installation
        check_and_install_sbas_parallel()
```

### **SBAS Parallel Compilation Strategy**
1. **GMTSAR Rebuild**: Ensures all necessary object files and libraries are available
2. **Library Detection**: Smart detection of `libgmtsar.a` after rebuild
3. **Proper Linking**: Uses GMTSAR library for successful SBAS parallel compilation
4. **Fallback Handling**: Graceful degradation when compilation fails

## 🎯 **Resolved Issues**

### **Issue: SBAS Parallel Not Installing**
**Problem**: When GMTSAR was already installed, SBAS parallel installation was skipped
**Solution**: Added automatic SBAS parallel check in the main application startup flow

### **Issue: Library Linking Failures** 
**Problem**: SBAS parallel compilation failed due to missing GMTSAR library functions
**Solution**: Implemented GMTSAR rebuild strategy to ensure library availability

### **Issue: Silent Installation Failures**
**Problem**: SBAS parallel installation failures were not properly diagnosed
**Solution**: Enhanced logging and error reporting for better troubleshooting

## 📋 **Migration Guide**

### **From v1.2.0 to v1.2.1**

**Automatic Upgrade** - No manual steps required:

```bash
# Standard upgrade
pip install --upgrade insarlite

# Or specific version
pip install insarlite==1.2.1

# Verify installation
insarlite --version
```

**For Existing Installations**:
- SBAS parallel will be automatically checked and installed on next application launch
- No configuration changes required
- Existing projects continue to work without modification

## 🔄 **What's New for Users**

### **Improved First-Time Experience**
- SBAS parallel now installs automatically when conditions are met
- Better feedback during installation process
- More reliable parallel processing capabilities

### **Enhanced Performance Tools**
- SBAS parallel compilation now succeeds in more environments
- Improved time series analysis performance when available
- Better fallback behavior when parallel tools unavailable

## 🚀 **Expected Behavior Changes**

### **Application Startup**
```bash
# New output when launching InSARLite:
✅ GMTSAR found at: /path/to/gmtsar.csh
Checking SBAS parallel availability...
🔄 Installing SBAS parallel...
Rebuilding GMTSAR components for SBAS parallel compilation...
✅ GMTSAR rebuild completed
✅ Found GMTSAR library after rebuild
SBAS parallel installed successfully
```

### **SBAS Processing**
- Enhanced time series analysis with parallel processing (when available)
- Automatic fallback to standard SBAS tools if parallel version unavailable
- No user action required - transparent performance improvements

## 🛠️ **Development Notes**

### **Code Changes Summary**
- Modified `src/insarlite/main.py` to include automatic SBAS parallel checking
- Enhanced `src/insarlite/utils/gmtsar_installer.py` with improved library handling
- Added smart rebuild strategy for GMTSAR library creation
- Improved error handling and user feedback

### **Testing Recommendations**
```bash
# Test SBAS parallel installation
python3 -m insarlite.main

# Verify SBAS parallel availability
which sbas_parallel

# Test SBAS processing workflows in InSARLite GUI
```

## 📞 **Support Information**

### **Getting Help**
- **Documentation**: [insarlite.readthedocs.io](https://insarlite.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/mbadarmunir/InSARLite/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mbadarmunir/InSARLite/discussions)

### **Known Limitations**
- SBAS parallel requires successful GMTSAR compilation and library creation
- Some systems may still experience compilation issues due to missing development tools
- Performance improvements vary based on system configuration and dataset size

## 🎉 **Acknowledgments**

**Thanks to**: Community users who reported the SBAS parallel installation issues and provided testing feedback

---

**Full Changelog**: [v1.2.0...v1.2.1](https://github.com/mbadarmunir/InSARLite/compare/v1.2.0...v1.2.1)

**Download**: 
- **PyPI**: `pip install insarlite==1.2.1`
- **GitHub Releases**: [v1.2.1 Release](https://github.com/mbadarmunir/InSARLite/releases/tag/v1.2.1)
- **Wheel File**: `insarlite-1.2.1-py3-none-any.whl`