# Release Notes - InSARLite v1.3.2

**Release Date:** January 19, 2026

## Bug Fixes

### Critical Fix: Ubuntu/Linux Compatibility
- **Fixed visualizer crash on Ubuntu/Linux systems** (`free(): invalid size` error)
  - Removed cartopy dependency which caused C library conflicts with tkinter on Linux
  - Replaced cartopy geographic projections with basic matplotlib for improved stability
  - Visualizer now works reliably across all platforms (Windows, macOS, Linux)

### Technical Changes
- **Dependency Update:**
  - Removed `cartopy>=0.20.0` from required dependencies
  - Maps now use basic matplotlib coordinate system instead of geographic projections
  
- **Impact:**
  - ✅ Eliminates memory corruption crashes on Ubuntu/Linux
  - ✅ Faster loading and rendering performance
  - ✅ All time series and polygon selection features fully functional
  - ⚠️ Geographic features (coastlines, borders) no longer available
  - ⚠️ Minor map distortion for very large areas (>5° coverage) - negligible for typical InSAR scenes

## Compatibility
- **Python:** 3.8 - 3.12
- **Platforms:** Windows, macOS, Linux (Ubuntu 20.04+)
- **Dependencies:** All core dependencies remain unchanged except cartopy removal

## Installation

```bash
pip install --upgrade insarlite==1.3.2
```

Or from source:
```bash
git clone https://github.com/mbadarmunir/InSARLite.git
cd InSARLite
pip install -e .
```

## Migration from v1.3.1
No user action required - this is a drop-in replacement that fixes Linux compatibility issues.

## Known Issues
None

## Contributors
- Muhammad Badar Munir

---

**Full Changelog:** https://github.com/mbadarmunir/InSARLite/compare/v1.3.1...v1.3.2
