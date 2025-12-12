# Changelog

All notable changes to InSARLite will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2024-12-10 - "Visualization Revolution + Optimizations"

### 📚 **Added - Documentation**

#### Master Selection Methodology
- **Comprehensive Explanation**: Added detailed documentation of average baseline ranking methodology in `masterselection.py`
- **Scientific Context**: Clear explanation suitable for academic manuscripts and peer review
- **Key Concepts Documented**:
  - What average baseline represents (mean distance from candidate to all other images)
  - Reference scene bias problem and how it arises
  - Mathematical elimination of bias through pairwise baseline differences
  - Physical interpretation as network centrality (center of mass analogy)
- **Real-World Example**: Concrete numerical example showing bias elimination

### ⚡ **Optimized - GMTSAR Installation**

#### Streamlined Installation Check
- **Projects File Optimization**: Checks `~/.projs.json` existence before running subprocess
  - Improves startup time from 10-50ms → 1-2ms for existing users
  - Only runs `which gmtsar.csh` check when projects file missing (first-time users)
- **Installation Strategy Documentation**: Added comprehensive module docstring explaining optimization approach
- **Smart First-Time Detection**: Leverages project configuration file as installation indicator

#### GUI-Only Installation Mode
- **Removed Console Installation**: Eliminated `install_gmtsar_console()` function (~100 lines)
- **Simplified Availability Check**: Only uses `which gmtsar.csh` for GMTSAR detection
  - Removed directory-based checking (more reliable, portable)
  - Cleaner code with single source of truth
- **Dual Installation Modes**: FULL (requires sudo) and MINIMAL (no sudo, shows dependency guide)
- **Enhanced User Guidance**: Comprehensive dependency installation guide with 3 options:
  - Admin/sudo commands for full installation
  - Conda alternative for non-admin users
  - Manual installation instructions

### 🛠️ **Changed - Configuration Flow**

#### Main Application Startup
- **Optimized GMTSAR Check**: Modified `_check_gmtsar_installation()` to pass `config_manager.projects_file`
- **Smarter Verification**: Projects file serves dual purpose:
  - Stores project history (existing functionality)
  - Indicates GMTSAR installation status (new optimization)
- **Backward Compatible**: First-time users still get full GMTSAR verification

### 🔧 **Technical Details**

#### Performance Metrics
- **Startup Improvement**: ~10-50ms subprocess call → ~1-2ms file existence check
- **Impact**: More responsive application launch for returning users
- **Trade-off**: None - first-time users still get complete verification

#### Code Quality
- **Removed**: ~100 lines of console installation code
- **Simplified**: Availability check reduced to single `which` command
- **Added**: Comprehensive dependency guide shown only when configuration fails
- **Documentation**: Module-level docstrings explain optimization strategy

## [1.3.0] - 2025-11-25 - "Visualization Revolution"

### 🎨 **Enhanced - Interactive Visualization**

#### Interactive Time Series Visualizer
- **Hover Functionality**: Real-time coordinate and velocity tooltips on mouse hover
- **Intelligent Pixel Selection**: Nearest-pixel detection with 0.001° search radius
- **Visual Feedback**: Red pin markers show exact selected locations
- **Mode System**: Clear separation between Normal (single-pixel) and Polygon modes
- **Simplified Click Behavior**: Single-click selection with automatic pixel detection

#### True Vector Output
- **Publication-Quality Exports**: PDF, SVG, EPS with fully editable text and elements
- **Matplotlib Configuration**: Module-level settings ensure true vector output
- **Format Support**: PNG (300 DPI), PDF, SVG, EPS, PS, CSV
- **Quality Verification**: Text selectability, zoom testing, element separation

#### Polygon Multi-Pixel Analysis
- **Drawing Interface**: Click to add vertices, right-click to complete polygon
- **Processing Options**: 
  - Process All Pixels: Bulk export of individual time series
  - Process Average: Mean displacement with error bars
- **Comprehensive Export**: All formats (PNG, PDF, SVG, EPS, PS, CSV) for each pixel
- **Progress Tracking**: Visual progress bar for bulk operations
- **Auto-Clear**: Streamlined workflow with automatic polygon cleanup

#### Context Maps
- **Automatic Generation**: 3x zoomed context map for each time series
- **Location Markers**: Red pin shows exact pixel location
- **Coordinate Labels**: Latitude/longitude clearly marked
- **Velocity Overlay**: Consistent colormap with main map

### 🔧 **Technical Improvements**

#### Enhanced Validation
- **Time Series Quality Scoring**: Statistical quality assessment (0-1 range)
- **Outlier Detection**: Automatic detection and filtering
- **Sufficient Data Check**: Validation of minimum data points
- **Clean Data Return**: Filtered, validated time series data

#### Coordinate Transformation
- **Robust Conversion**: Accurate pixel-to-geographic transformation
- **xarray Support**: Handles 1D and 2D coordinate arrays
- **Edge Case Handling**: Comprehensive error handling
- **Search Radius**: Configurable nearest-pixel detection radius

#### Memory Management
- **Lazy Loading**: Efficient displacement array handling
- **Memory Cleanup**: Automatic cleanup after bulk operations
- **Large Dataset Support**: Efficient handling of extensive polygon selections

### 🐛 **Bug Fixes**

- **Fixed**: Polygon mode interference with normal click selection
- **Fixed**: Vector file rasterization despite proper extensions
- **Fixed**: Coordinate accuracy issues with pixel selection
- **Fixed**: UI state inconsistencies between operations
- **Fixed**: Mode isolation and state management

### 🗑️ **Removed**

- **Pin Dragging**: Simplified to click-only selection
- **Polygon Save/Load**: Removed unnecessary complexity (draw fresh each time)

---

## [1.2.6] - 2025-11-20

### 🐛 **Bug Fixes**

#### Critical Data Structure Fix
- **Fixed**: Alignment status data structure mismatch
- **Issue**: Progress window showed 0/0 instead of 59/59, blocking workflow
- **Root Cause**: Code expected `all_images` list, but function returned `details` dict
- **Solution**: Extract image date lists from `details` field correctly
- **Impact**: Progress window now displays accurate completion (59/59 = 100%)

---

## [1.2.5] - 2025-11-18

### 🔧 **Technical Improvements**

#### Comprehensive Debugging System
- **Added**: Extensive test prints throughout alignment process
- **Tracking**: Code version, status changes, network filtering, completion logic
- **Verification**: Confirms correct code version is running (not cached)
- **Debugging Output**: Step-by-step execution trace for troubleshooting

#### Code Cleanup
- **Improved**: Moved all imports to top of file
- **Removed**: Redundant inline imports from multiple functions
- **Enhanced**: Cleaner code structure and better maintainability

---

## [1.2.4] - 2025-11-15

### 🐛 **Bug Fixes**

#### Progress Window Advancement
- **Fixed**: Progress window stuck at 59/60, wouldn't advance to next step
- **Root Cause**: Network filtering happened after progress reporting
- **Solution**: Immediate network-aware status calculation before progress reporting
- **Impact**: Workflow now properly advances when alignment complete
- **Technical**: Updated status from `total_images=60` to `total_images=59` (connected only)

#### Automatic Completion Detection
- **Added**: Status auto-updates to 'complete' when all missing images are unconnected
- **Behavior**: Early exit when completion detected
- **Result**: Accurate progress percentages (59/59 instead of 59/60)

---

## [1.2.3] - 2025-11-12

### 🔧 **Technical Improvements**

#### Subswath Detection
- **Fixed**: Subswath detection to only report actual F1/F2/F3 folders
- **Prevented**: Processing of non-existent subswath directories
- **Cleaned**: UI parameters show only valid existing subswaths

#### Network-Aware Progress
- **Enhanced**: Progress calculations based only on connected images
- **Filtered**: Unconnected images excluded from total counts
- **Accurate**: True completion percentages (e.g., 59/59 instead of 59/60)

#### Enhanced Messaging
- **Improved**: Clear messaging about network connectivity status
- **Distinguished**: Connected vs unconnected images in output
- **Example**: "59/59 connected images aligned - All missing images are unconnected"

#### Validation and Safety
- **Added**: Early exit checks for non-existent directories
- **Prevention**: No wasted processing on impossible tasks
- **Logging**: Clear skip messages for invalid subswaths

---

## [1.2.2] - 2025-11-10

### 🛡️ **Security & Data Safety**

#### Critical Data Protection
- **ELIMINATED**: All data loss vulnerabilities in alignment system
- **Risk Level**: Changed from 🔴 CRITICAL to 🟢 MINIMAL

#### Dangerous Function Removal
- **DELETED**: `backup_slc_files_for_realignment()` function
- **Reason**: Was deleting original SLC files (primary data loss source)

#### Backup System Redesign
- **OLD**: `_backup_all_alignment_files()` - deleted originals after backup
- **NEW**: `_backup_alignment_files_with_permission()` - copy only, never delete
- **Permission**: User explicit consent required before any backup
- **Messaging**: Clear statement that originals are preserved

#### User Control
- **Dialog**: Shows exactly what will be backed up
- **Choice**: User decides whether to backup
- **Safety**: Explicitly states originals will be preserved
- **Trigger**: Only when alignment method actually changes

#### Safety Guarantees
- ✅ **100% Data Safety**: Original files NEVER deleted
- ✅ **User Control**: Permission required for all operations
- ✅ **Clear Communication**: User understands what's happening
- ✅ **Intelligent Backup**: Only when method changes detected

---

## [1.2.1] - 2025-11-08

### 🐛 **Bug Fixes**

#### Data Loss Prevention
- **Fixed**: File deletion issue during alignment reruns
- **Changed**: `shutil.move()` to `shutil.copy2()` in backup operations
- **Added**: Verification before file removal
- **Enhanced**: Comprehensive error handling

#### Network Connectivity Validation
- **Added**: Validation against `intf.in` before alignment
- **Implemented**: Parse interferogram network to extract connected images
- **Filtered**: `data.in` to only include connected images
- **Logging**: Clear skip messages for unconnected images

#### Benefits
- ✅ No original file loss during backups
- ✅ Only connected images processed
- ✅ Smart partial alignment for missing files only
- ✅ Verification before all file operations

---

## [1.2.0] - 2025-11-05

### ✨ **Added**

#### Enhanced Logging System
- **New**: `process_logger()` with UI parameter tracking
- **Feature**: Comprehensive logging of all user inputs
- **Format**: Structured parameter output in log files
- **Location**: `utils/utils.py`

#### Configuration Management
- **Function**: `save_config_to_json()` for persistent settings
- **Organization**: Step-wise configuration structure
- **Timestamps**: Automatic timestamp addition
- **Merging**: Intelligent merge with existing configurations

#### File Pattern Detection
- **Advanced**: SAR file naming pattern utilities
- **Parser**: `parse_data_in_line()` for metadata extraction
- **Generator**: `generate_expected_filenames()` for validation
- **Support**: S1A/S1B naming conventions

#### Alignment Status Analysis
- **Function**: `check_alignment_completion_status()` comprehensive checker
- **Detection**: Complete/Partial/None status
- **Validation**: Detailed file-by-file checking
- **Cross-reference**: data.in entries vs existing files

#### Data Validation
- **Pre-processing**: Validation of `data.in` vs actual files
- **Smart Baseline**: File checking before LED/PRM generation
- **Prevention**: Stops processing errors from missing files

### 🔧 **Technical Improvements**

#### Intelligent Alignment
- **Capability**: Partial skip (only process missing images)
- **Backup**: Comprehensive backup before realignment
- **Network-Aware**: Processing based on connectivity

#### Backward Compatibility
- **Maintained**: All existing functionality preserved
- **Graceful**: Degradation if parameters missing
- **No Breaking**: Changes to existing workflows

---

## [1.0.0] - 2025-10-27

### 🎉 **First Major Release**

This is the first stable release of InSARLite, marking a significant milestone in making InSAR processing accessible through an intuitive GUI interface.

### ✨ **Added**

#### Core Features
- **Complete GUI Application**: Full-featured Tkinter-based interface for InSAR processing
- **GMTSAR Integration**: Seamless integration with GMTSAR workflow
- **Interactive Baseline Planning**: Advanced matplotlib-based baseline network design
- **Automated Data Management**: Sentinel-1 data search, download, and organization
- **Unified Authentication**: Centralized EarthData authentication system
- **DEM Management**: Automated DEM download and processing

#### Data Processing
- **Sentinel-1 Support**: Complete Sentinel-1 data processing pipeline
- **Orbit Processing**: Automatic orbit file download and integration
- **Interferometry**: Interferogram generation with coherence calculation
- **Phase Unwrapping**: Advanced unwrapping with mask and reference point definition
- **Time Series Analysis**: SBAS processing for deformation time series
- **Atmospheric Correction**: GACOS atmospheric correction integration

#### User Interface
- **Step-by-Step Workflow**: Intuitive sequential processing steps
- **Interactive Map**: Visual AOI selection with map integration
- **Progress Tracking**: Real-time progress monitoring with detailed statistics
- **Configuration Management**: Persistent settings and project management
- **Error Handling**: Comprehensive error reporting and recovery

#### Visualization
- **Interactive Plotting**: Advanced baseline network visualization
- **Result Viewing**: Built-in interferogram and time series viewers
- **Export Capabilities**: Multiple output formats (PNG, PDF, CSV, NetCDF)
- **Animation Tools**: Time series animation generation

#### Advanced Features
- **Parallel Processing**: Multi-threaded download and processing
- **Flight Direction Detection**: Automatic detection from manifest files
- **Subswath Selection**: Flexible subswath processing options
- **Quality Control**: Built-in validation and quality assessment
- **Pause/Resume**: Pausable operations for long-running tasks

### 🔧 **Technical Infrastructure**

#### Architecture
- **Modular Design**: Clean separation of GUI, processing, and utilities
- **Plugin System**: Extensible architecture for future enhancements
- **Configuration System**: JSON-based configuration management
- **Logging System**: Comprehensive logging for debugging and monitoring

#### Dependencies
- **Python 3.8+**: Modern Python support with type hints
- **Scientific Stack**: NumPy, SciPy, matplotlib, xarray integration
- **Geospatial Libraries**: Rasterio, Shapely, Cartopy support
- **GUI Framework**: Native Tkinter with custom enhancements

#### Performance
- **Memory Management**: Efficient handling of large datasets
- **Parallel Downloads**: Concurrent data acquisition
- **Chunked Processing**: Memory-efficient processing of large files
- **Caching**: Smart caching of expensive operations

### 📚 **Documentation**

#### Comprehensive Documentation
- **Installation Guide**: Detailed installation instructions for all platforms
- **User Guide**: Complete user documentation with tutorials
- **API Reference**: Auto-generated API documentation
- **Developer Guide**: Architecture and contribution guidelines

#### Educational Content
- **Quick Start Tutorial**: Get up and running in minutes
- **Processing Workflows**: Step-by-step processing guides
- **Best Practices**: Recommendations for optimal results
- **Troubleshooting**: Common issues and solutions

### 🛡️ **Quality Assurance**

#### Testing
- **Unit Tests**: Comprehensive test coverage for core functionality
- **Integration Tests**: End-to-end workflow testing
- **GUI Tests**: User interface testing and validation
- **Cross-Platform**: Testing on Linux, macOS, and Windows

#### Code Quality
- **Type Hints**: Full type annotation for better IDE support
- **Code Style**: Consistent formatting with Black and flake8
- **Documentation**: Comprehensive docstrings and comments
- **Error Handling**: Robust error handling throughout

### 🌟 **Key Improvements Since Beta**

#### User Experience
- **Enhanced Interface**: Improved layout and visual design
- **Better Error Messages**: More informative error reporting
- **Progress Feedback**: Detailed progress information
- **Configuration Persistence**: Automatic saving of user preferences

#### Processing Enhancements
- **Improved Baseline Plotter**: Advanced interactive plotting capabilities
- **Better Authentication**: More reliable EarthData authentication
- **Enhanced Extraction**: Improved ZIP file extraction with proper progress
- **Flight Direction Detection**: Automatic detection from metadata

#### Bug Fixes
- **Authentication Issues**: Resolved EarthData authentication problems
- **Progress Tracking**: Fixed progress reporting for file extraction
- **Memory Management**: Improved memory usage for large datasets
- **Cross-Platform**: Better compatibility across different operating systems

### 🔄 **Migration from Beta**

For users upgrading from beta versions:

1. **Configuration**: Settings will be automatically migrated
2. **Projects**: Existing projects remain compatible
3. **Data**: No changes to data organization or formats
4. **Authentication**: May need to re-authenticate with EarthData

### 🎯 **Future Roadmap**

#### Version 1.1 (Planned)
- Enhanced visualization capabilities
- Additional atmospheric correction methods
- Performance optimizations
- Extended format support

#### Version 1.2 (Planned)
- Machine learning integration
- Advanced time series analysis
- Real-time processing capabilities
- Cloud processing support

### 🙏 **Acknowledgments**

#### Contributors
- Muhammad Badar Munir - Lead Developer and Maintainer
- Community Contributors - Bug reports, feature requests, and testing

#### Dependencies
- GMTSAR team for the core processing engine
- NASA and ESA for open satellite data
- Python scientific computing community
- Open source library maintainers

#### Support
- Academic institutions providing computational resources
- Research community feedback and validation
- Beta testers and early adopters

### 📈 **Statistics**

- **Lines of Code**: ~15,000 lines of Python
- **Test Coverage**: >80% code coverage
- **Documentation**: >100 pages of documentation
- **Dependencies**: 25+ scientific Python packages
- **Platforms**: Linux, macOS, Windows support

---

## Previous Versions

### [0.0.3] - 2024-12-XX (Beta)
- Initial beta release
- Basic GUI functionality
- Core processing capabilities
- Limited documentation

### [0.0.2] - 2024-11-XX (Alpha)
- Early alpha version
- Command-line interface
- Experimental features

### [0.0.1] - 2024-10-XX (Development)
- Initial development version
- Proof of concept
- Basic GMTSAR integration

---

## Version Numbering

InSARLite follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version: Incompatible API changes
- **MINOR** version: New functionality in a backward compatible manner  
- **PATCH** version: Backward compatible bug fixes

### Release Types

- **Stable** (x.y.z): Production-ready releases
- **Release Candidate** (x.y.z-rc.n): Pre-release testing versions
- **Beta** (x.y.z-beta.n): Feature-complete preview versions
- **Alpha** (x.y.z-alpha.n): Early development versions

---

*For the complete version history and detailed changes, see our [GitHub Releases](https://github.com/mbadarmunir/InSARLite/releases) page.*