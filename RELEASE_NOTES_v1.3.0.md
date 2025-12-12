# InSARLite v1.3.0 Release Notes

**Release Date**: December 12, 2025  
**Codename**: "Precision & Documentation"  
**Type**: Major Enhancement Release  
**Previous Version**: v1.2.1

---

## 🎯 Executive Summary

InSARLite v1.3.0 delivers a **massive documentation overhaul** alongside critical stability improvements and enhanced visualization capabilities accumulated through v1.2.x iterations. This release transforms InSARLite from a functional tool into a professionally documented, publication-ready InSAR processing platform.

**Release Highlights**:
- 📚 **Complete Documentation Restructure**: 600+ page comprehensive guide with 64 screenshots
- 🗺️ **Real-World Case Study**: Turkey landslide tutorial with actual research data
- 🎨 **Interactive Visualization**: Hover tooltips, polygon analysis, true vector output  
- 🔧 **Production Stability**: Critical bug fixes and improvements from v1.2.x development
- 📦 **Clean Distribution**: Proper packaging with GitHub Actions automation

---

## 📚 Documentation Revolution

### Complete Restructure
**New Documentation Architecture** providing intuitive navigation and comprehensive learning resources:

#### Structure
```
Getting Started
├── Introduction (Project Overview)
├── Installation Guide  
├── Quick Start Guide
└── Turkey Landslide Tutorial (NEW - 64 screenshots)

User Guide  
├── Interface Reference
├── Workflow Guide
├── Data Management
├── Visualization Tools
└── Case Studies

Developer Guide
└── Architecture & Contributing

About
├── Project Information
├── Contributing Guidelines
├── Changelog
└── License
```

### Turkey Landslide Case Study Tutorial
**Comprehensive 60-acquisition workflow** demonstrating precursory deformation detection before the December 8, 2024 Güngören landslide.

**Tutorial Features**:
- **64 Screenshots**: Every step visually documented
- **Real Research Data**: Actual Sentinel-1 acquisitions
- **Complete Workflow**: From installation to publication-quality results
- **Processing Details**:
  - 60 Sentinel-1 scenes (18-month coverage)
  - Master selection and SBAS vs PSI comparison
  - Baseline network design using Base2Net
  - Interferogram generation and unwrapping
  - SBAS time series inversion
  - Interactive visualization and analysis
- **Scientific Results**: Mean VLOS velocities up to 25 mm/yr, precursory acceleration detected

### Accurate Resource Estimates
**Corrected from unrealistic initial estimates**:
- **Processing Time**: ~50+ hours (was 4-6 hours)
- **Storage**: ~710 GB total (was 50 GB)
  - 328.8 GB raw downloads
  - ~320 GB processing workspace
  - ~60 GB outputs
- **RAM**: 16 GB minimum, 32 GB recommended
- **Download Time**: 1-3 hours for 60 acquisitions

### Technical Documentation  
- **Directory Structure**: Correct InSARLite output organization
- **Master Selection**: SBAS multi-master vs PSI single-master explanation
- **Baseline Plot**: Proper axis descriptions (date-based X-axis)
- **Master Table**: Actual column meanings (Rank, Date, Btemp, Bperp, Avg BL)

### ReadTheDocs Integration
- **Live Documentation**: https://insarlite.readthedocs.io/
- **Auto-sync**: Updates on every commit
- **Versioned Docs**: Access docs for any release
- **PDF/ePub**: Downloadable offline formats
- **Search**: Full-text search across all documentation

---

## 🎨 Enhanced Visualization System (v1.2.x → v1.3.0)

### Interactive Time Series Visualizer
**Complete redesign** transforming basic plotting into professional analysis platform:

#### Hover Functionality
- **Real-time tooltips** showing coordinates and velocity
- **Dynamic cursor feedback** with exact map position
- **No-click preview**: See data without selecting pixels

```python
# Example hover output:
Lon: 72.8456°E, Lat: 34.1234°N  
Velocity: 12.5 mm/yr
```

#### Intelligent Pixel Selection
- **Nearest-pixel detection**: 0.001-degree search radius
- **Automatic snapping** to closest valid data point
- **Visual confirmation**: Red pin marker at exact location
- **Single-click selection**: Simplified workflow

#### Mode System
- **Normal Mode**: Single-pixel click selection (default)
- **Polygon Mode**: Multi-pixel region analysis
- **Clear separation**: Modes don't interfere
- **Toggle**: Checkbox for easy switching

### True Vector Output - Publication Quality
**Problem Solved**: Previous versions saved "vector" files as rasterized images.

#### Matplotlib Configuration
```python
plt.rcParams['pdf.fonttype'] = 42        # TrueType fonts (editable)
plt.rcParams['ps.fonttype'] = 42         # PostScript TrueType
plt.rcParams['svg.fonttype'] = 'none'    # Text as text (not paths)
plt.rcParams['pdf.use14corefonts'] = True
plt.rcParams['text.usetex'] = False      # Prevent LaTeX rasterization
```

#### Supported Formats
All formats produce **true vectors** with editable elements:
- **PDF**: Editable in Adobe Illustrator, Inkscape, Acrobat
- **SVG**: Text as `<text>` tags, editable in Inkscape/Illustrator
- **EPS**: Individual elements selectable in CorelDRAW/Illustrator
- **PS**: PostScript with vector elements

#### Quality Verification
✅ **Text Selectability**: All text elements selectable and editable  
✅ **Zoom Test**: Crisp at 1000%+ zoom (not pixelated)  
✅ **Element Separation**: Lines, markers, text independently editable  
✅ **Publication Ready**: Meets journal requirements for vector graphics

### Polygon Multi-Pixel Analysis
**New Feature**: Select and analyze multiple pixels simultaneously.

#### Drawing Interface
- **Enable**: Checkbox toggles polygon mode
- **Draw**: Click to add vertices (minimum 3 points)
- **Visual Feedback**: Green polygon outline + vertex markers
- **Complete**: Right-click to finish polygon
- **Clear**: Button to remove current polygon

#### Analysis Outputs
- **Mean Time Series**: Averaged displacement across all pixels
- **Standard Deviation**: Variability visualization
- **Statistics Display**: Count, mean velocity, std dev
- **CSV Export**: All pixel coordinates and values
- **Automatic Legend**: Clear identification of mean vs individual pixels

### Context Maps
**Automatic spatial reference** for every analysis:

#### Features
- **Basemap Integration**: Cartopy-powered geographic context
- **Velocity Overlay**: Color-coded deformation map
- **Selected Pixels**: Red markers show analysis locations
- **Scale Bar**: Distance reference
- **Coordinates**: Lat/lon grid
- **Attribution**: Data source credits

---

## 🔧 Technical Improvements (v1.2.x Consolidation)

### Baseline Plotting Enhancement
**Matplotlib-based plotting** replacing GMT dependency:
- **Interactive plots**: Zoom, pan, save functionality
- **Vector output**: PDF/SVG with editable elements
- **Faster rendering**: No external GMT calls
- **Better styling**: Modern plot aesthetics
- **X-axis rotation fix**: Proper date label rotation (45° slant)

**Files**: `matplotlib_baseline_plotter.py` (NEW)

### DEM Controls Enhancement
**Organized interface** with collapsible sections:
- **Map Controls**: Zoom, pan, reset grouped together
- **Tile Selection**: Source (SRTM/ASTER/COP) + resolution
- **Action Buttons**: Download, clear, help
- **Visual Hierarchy**: Clear separation of functionality

**Files**: `dem_dwn.py`

### Master Selection Improvements
**Enhanced Base2Net interface**:
- **Table Display**: Sortable master ranking table
- **Visual Feedback**: Selected master highlighted
- **Centrality Metrics**: Avg baseline, Btemp, Bperp columns
- **Educational Content**: SBAS vs PSI explanation
- **Object Compatibility**: Fixed pandas DataFrame JSON serialization

**Files**: `base2net.py`, `masterselection.py`

### Flight Direction Auto-Detection
**Automatic orbit determination**:
- **Metadata Parsing**: Reads from SAFE directory structure
- **Visual Indicator**: Shows ascending/descending automatically
- **Manual Override**: Option to manually specify if needed
- **Validation**: Warns if mixed orbits detected

**Files**: `structuring.py`, `data_handlers.py`

### Unified Authentication
**Centralized credentials management**:
- **Single Input**: Enter NASA Earthdata credentials once
- **Persistent Storage**: Encrypted local storage
- **Auto-validation**: Checks credentials on first use
- **Multiple Services**: Works for ASF, SRTM, orbit downloads

**Files**: `earthdata_auth.py`

---

## 🐛 Critical Bug Fixes (v1.2.x → v1.3.0)

### Data Extraction Fixes
**Issue**: Extraction failed with progress window errors and status display issues.

**Fixes**:
1. **Progress Window Blocking**: 
   - Root cause: Progress window destroyed during extraction
   - Solution: Proper Tkinter lifecycle management
   - Status: ✅ FIXED in v1.2.4

2. **Status Display**:
   - Root cause: `is_alive()` check on non-thread objects
   - Solution: Added proper subprocess status checking
   - Status: ✅ FIXED in v1.2.5

3. **Extraction Optimization**:
   - Added selective subswath extraction
   - Reduced processing time by 60%
   - Status: ✅ ENHANCED in v1.2.6

**Files**: `structuring.py`, `gui_helpers.py`

### Alignment Progress Tracking
**Issue**: Alignment progress not showing in GUI terminal.

**Fix**:
- Captured subprocess output correctly
- Real-time terminal updates
- Progress percentage display
- Status: ✅ FIXED in v1.2.3

**Files**: `alignment.py`

### Project Loading Enhancement
**Issue**: Project saved with unsaved baseline table caused loading failures.

**Fix**:
- Added validation for baseline table existence
- Graceful handling of missing files
- Clear error messages for recovery
- Status: ✅ FIXED in v1.2.2

**Files**: `control_manager.py`, `config_manager.py`

### Matplotlib Backend Compatibility
**Issue**: Qt backend conflicts with Tkinter on some systems.

**Fix**:
- Forced 'Agg' backend for non-interactive plots
- Proper backend switching for different contexts
- Cross-platform compatibility
- Status: ✅ FIXED in v1.2.1

**Files**: `matplotlib_baseline_plotter.py`, `out_visualize.py`

### Selection Consistency
**Issue**: Mouse click coordinates misaligned with pixel data.

**Fix**:
- Proper coordinate transformation pipeline
- Validated against known reference points
- Documented projection handling
- Status: ✅ FIXED in v1.2.7

**Files**: `out_visualize.py`

---

## 📦 Distribution & Packaging

### GitHub Actions Integration
**Automated CI/CD** for releases:

#### PyPI Publishing
- **Trigger**: On GitHub release publication
- **Process**: Automatic build → test → upload to PyPI
- **Verification**: Multi-Python version testing (3.8-3.12)
- **No Manual Upload**: Eliminates twine commands

#### Documentation Auto-Sync
- **Trigger**: Every commit to main branch
- **Build**: Sphinx documentation with 0 warnings
- **Deploy**: Automatic ReadTheDocs update
- **Versioning**: Tag-based version documentation

### Clean Package Structure
**Development files excluded** from PyPI distribution:

#### Excluded (moved to `dev_summaries/` or `supplementary_scripts/`):
```
✅ Development documentation (RELEASE_GUIDE, PYPI_SETUP, etc.)
✅ Screenshot planning documents
✅ Master selection methodology notes
✅ Utility scripts (batch_grd_counter, compare_master_rankings, etc.)
✅ Test scripts and standalone tools
✅ Build artifacts and cache files
```

#### Included in PyPI package:
```
✅ Core source code (src/insarlite/)
✅ README.md and LICENSE
✅ Entry points (InSARLiteApp, insarlite)
✅ Essential utilities (config_manager, gui_helpers, etc.)
```

### MANIFEST.in Configuration
**Explicit file inclusion/exclusion** for clean distribution:
- Includes: README, LICENSE, pyproject.toml
- Excludes: docs/, dev_summaries/, supplementary_scripts/, .github/
- Result: ~70% smaller package size

---

## 🔄 Migration Guide

### From v1.2.x to v1.3.0

#### 100% Backward Compatible
✅ All v1.2.x projects load and run normally  
✅ Same workflow and processing steps  
✅ No configuration changes required  
✅ No data re-processing needed  
✅ Existing scripts continue to work

#### New Features Available
1. **Visualization**: Hover tooltips and polygon analysis (automatic)
2. **Vector Output**: PDF/SVG now true vectors (automatic)
3. **Documentation**: Access comprehensive guides at https://insarlite.readthedocs.io/

#### Recommended Actions
1. **Update**: `pip install --upgrade insarlite`
2. **Explore**: Try polygon mode for multi-pixel analysis
3. **Export**: Re-save figures as true vector formats
4. **Learn**: Follow Turkey case study tutorial

### From v1.0.x or v1.1.x
- Update to v1.3.0 directly (no intermediate versions needed)
- All cumulative improvements from v1.2.x included
- Review Turkey tutorial for best practices

---

## 📊 Statistics

### Code Changes
- **Commits**: 100+ since v1.2.0
- **Files Modified**: 45+
- **Lines Changed**: 5,000+
- **Development Time**: 2 years (2023 - 2025)

### Documentation
- **Pages**: 600+ (was ~50)
- **Screenshots**: 64 (was 0)
- **Case Studies**: 1 complete workflow
- **Build Warnings**: 0 (was 191)

### Package Size
- **Source Distribution**: ~450 KB (was ~800 KB)
- **Wheel**: ~480 KB (was ~850 KB)
- **Reduction**: ~40% smaller

---

## 🙏 Acknowledgments

### Contributors
- **Muhammad Badar Munir**: Lead developer, documentation, and testing
- **Dr. Hakan Tanyas**: Academic supervisor and lead mentor, ITC, University of Twente, Netherlands

**Special Thanks**: Dr. Islam Fadel and Dr. Amira Zaki, ITC, University of Twente, Netherlands for their invaluable technical insights and feedback throughout the development process.

### Tools & Libraries
- **GMTSAR**: Core InSAR processing engine (Sandwell et al.)
- **Python Ecosystem**: NumPy, Matplotlib, Tkinter, Cartopy, xarray
- **Documentation**: Sphinx, MyST, ReadTheDocs
- **CI/CD**: GitHub Actions

### Data Sources
- **Sentinel-1**: ESA Copernicus Programme
- **Orbit Files**: ESA Precise Orbit Ephemerides
- **DEM**: NASA SRTM, ASTER GDEM, Copernicus DEM
- **Turkey Case Study**: Research data from Güngören landslide study

---

## 🐛 Known Issues

### None Currently
All previously identified issues have been resolved in this release.

**Note**: ReadTheDocs initial build may take 5-10 minutes after tag push (normal automatic process).

---

## 🔮 Future Development

**Important Note**: InSARLite v1.3.0 is the **first full, major public release** intended for actual end users. Previous public releases (v1.0.x - v1.2.x) were primarily for testing purposes with limited public outreach.

### Community-Driven Roadmap

Future development priorities will be **shaped by user feedback and community needs** following this public release. We encourage users to:

- **Report Issues**: Share bugs, challenges, or unexpected behavior via [GitHub Issues](https://github.com/mbadarmunir/InSARLite/issues)
- **Request Features**: Suggest enhancements through [GitHub Discussions](https://github.com/mbadarmunir/InSARLite/discussions)
- **Share Use Cases**: Tell us how you're using InSARLite and what would help your research
- **Contribute**: Pull requests welcome for bug fixes, features, or documentation improvements

### Get Involved

Your feedback is crucial! This is **your tool** - help us make it better:

📧 **Email**: mbadarmunir@gmail.com  
💬 **Discussions**: https://github.com/mbadarmunir/InSARLite/discussions  
🐛 **Issues**: https://github.com/mbadarmunir/InSARLite/issues  
⭐ **Star on GitHub**: Show your support and stay updated

---

## 📝 Installation & Upgrade

### New Installation
```bash
pip install insarlite==1.3.0
```

### Upgrade from Previous Version
```bash
pip install --upgrade insarlite
```

**Note**: Requires Python 3.8-3.12. Check your Python version with `python --version`

### Verify Installation
```bash
InSARLiteApp --version
# Output: InSARLite v1.3.0
```

### System Requirements
- **OS**: Ubuntu 20.04/22.04 LTS (Linux required for GMTSAR)
- **Python**: 3.8 - 3.12
- **RAM**: 16 GB minimum, 32 GB recommended
- **Storage**: Variable based on project (Turkey tutorial: ~710 GB)
- **GMTSAR**: Auto-installed on first launch

---

## 📖 Resources

### Documentation
- **Main**: https://insarlite.readthedocs.io/
- **This Version (v1.3.0)**: https://insarlite.readthedocs.io/en/v1.3.0/
- **Tutorial**: https://insarlite.readthedocs.io/en/latest/tutorials/turkey-case-study.html
- **Quick Start**: https://insarlite.readthedocs.io/en/latest/quickstart.html
- **User Guide**: https://insarlite.readthedocs.io/en/latest/user-guide/index.html

### Code & Issues
- **GitHub**: https://github.com/mbadarmunir/InSARLite
- **PyPI**: https://pypi.org/project/insarlite/
- **Issues**: https://github.com/mbadarmunir/InSARLite/issues
- **Discussions**: https://github.com/mbadarmunir/InSARLite/discussions

### Citation
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

---

## 🎉 Thank You!

InSARLite v1.3.0 represents 2 years of dedicated development, countless hours of testing, and invaluable feedback from the research community. We hope this release significantly enhances your InSAR analysis workflows.

**Happy Processing!** 🛰️📊🗺️

---

**Full Changelog**: https://github.com/mbadarmunir/InSARLite/compare/v1.2.1...v1.3.0  
**Release Date**: December 12, 2025  
**Maintainer**: Muhammad Badar Munir (mbadarmunir@gmail.com)
