# Installation Guide

This guide provides detailed instructions for installing InSARLite on different operating systems and environments.

```{important}
**Testing Status**: InSARLite has been primarily developed and tested on **Ubuntu Linux**. Installation instructions for other operating systems are provided as indicative approaches, but full compatibility is not guaranteed. For the most reliable experience, we recommend using Ubuntu 20.04 LTS or newer.
```

## Platform Compatibility

### ✅ Fully Supported
- **Ubuntu Linux 20.04+** (Primary development and testing platform)
- **Other Debian-based Linux** (Expected to work with minimal issues)

### ⚠️ Partially Supported  
- **RHEL/CentOS/Fedora** (Manual package management may be required)
- **macOS** (Additional dependencies may be needed)
- **Windows Subsystem for Linux (WSL2)** (Requires display configuration)

### ❌ Not Supported
- **Native Windows** (GMTSAR cannot be compiled on Windows)

## System Requirements

### Minimum Requirements

- **Python**: 3.8 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: 4 GB RAM (8 GB recommended)
- **Storage**: 2 GB free space (more needed for data processing)
- **Display**: GUI support (X11 forwarding for remote systems)

### Recommended Requirements

- **Python**: 3.9 or 3.10
- **Memory**: 16 GB RAM or more
- **Storage**: 50 GB+ SSD for optimal performance
- **Network**: Stable internet connection for data downloads

## Dependencies

InSARLite has two types of dependencies: **Python packages** (installed automatically) and **system dependencies** (managed automatically when possible).

### Python Dependencies (Automatic Installation)

These are installed automatically via pip:

#### Core Dependencies
- `numpy` - Numerical computing
- `matplotlib` - Plotting and visualization
- `tkinter` - GUI framework (usually included with Python)
- `rioxarray` - Geospatial raster data
- `xarray` - Multi-dimensional arrays

#### InSAR-Specific Dependencies
- `asf_search` - Alaska Satellite Facility data search
- `requests` - HTTP library for data downloads
- `beautifulsoup4` - HTML/XML parsing

#### Geospatial Dependencies
- `shapely` - Geometric operations
- `cartopy` - Cartographic projections
- `basemap` - Map plotting (Linux/macOS only)

#### Optional Dependencies
- `h5netcdf` - NetCDF4 via h5py
- `dask` - Parallel computing
- `scipy` - Scientific computing
- `pandas` - Data analysis

### System Dependencies (Automatic Management)

InSARLite automatically manages its primary dependency:

#### GMTSAR (Automatic Installation)
**GMTSAR** is the core processing engine for InSAR analysis. InSARLite includes an **automatic installation system** that:

- ✅ **Detects existing installations** on first startup
- ✅ **Prompts for automatic installation** if not found  
- ✅ **Handles system package dependencies** (when sudo access available)
- ✅ **Downloads and compiles GMTSAR** from source
- ✅ **Configures environment variables** automatically
- ⚠️  **Provides manual instructions** for restricted environments

```{note}
**Automatic Installation**: On first startup, InSARLite will check for GMTSAR and offer to install it automatically. This requires approximately 15-30 minutes and 2GB of disk space.
```

```{warning}
**Sudo Access**: Some system packages require administrator privileges. If you don't have sudo access, InSARLite will list the required packages for your system administrator to install.
```

## Installation Methods

### Method 1: Using pip (Recommended)

The easiest way to install InSARLite is using pip:

```bash
pip install insarlite
```

For Python 3 specifically:
```bash
pip3 install insarlite
```

### Method 2: Using conda

If you prefer conda, you can install the dependencies first:

```bash
# Create a new environment
conda create -n insarlite python=3.9

# Activate the environment
conda activate insarlite

# Install dependencies via conda
conda install -c conda-forge numpy matplotlib rioxarray xarray cartopy shapely

# Install InSARLite via pip
pip install insarlite
```

### Method 3: Development Installation

For development or to get the latest features:

```bash
# Clone the repository
git clone https://github.com/mbadarmunir/InSARLite.git
cd InSARLite

# Install in development mode
pip install -e .
```

## Platform-Specific Instructions

### Linux (Ubuntu/Debian) - Recommended Platform

```bash
# Update system packages
sudo apt update

# Install basic Python dependencies
sudo apt install python3-pip python3-tk

# Install InSARLite
pip3 install insarlite

# Launch InSARLite (GMTSAR will be installed automatically)
python3 -c "import insarlite; insarlite.main()"
```

```{note}
**Fully Tested Platform**: Ubuntu is our primary development and testing platform. All features are expected to work correctly.
```

```{note}
**Automatic GMTSAR Setup**: On first launch, InSARLite will automatically install GMTSAR and its dependencies. This includes packages like `csh`, `autoconf`, `gfortran`, `libgmt-dev`, etc.
```

### Linux (CentOS/RHEL/Fedora) - Experimental Support

```bash
# Install basic dependencies
sudo dnf install python3-pip python3-tkinter  # Fedora
# OR
sudo yum install python3-pip tkinter          # CentOS/RHEL

# Install InSARLite  
pip3 install insarlite

# Launch InSARLite (GMTSAR will be installed automatically)
python3 -c "import insarlite; insarlite.main()"
```

```{warning}
**Experimental Support**: The automatic GMTSAR installer is optimized for apt (Debian/Ubuntu). On RHEL-based systems, you may need to manually install some dependencies or work with your system administrator.
```

```{note}
**Package Manager Differences**: Some package names may differ on RHEL-based systems. If automatic installation fails, refer to the manual installation section.
```

### macOS - Experimental Support

```bash
# Install Python via Homebrew (if not already installed)
brew install python

# Install basic geospatial dependencies
brew install gdal geos proj

# Install InSARLite
pip3 install insarlite

# Launch InSARLite (GMTSAR installation may require additional steps)
python3 -c "import insarlite; insarlite.main()"
```

```{warning}
**Experimental Support**: InSARLite has limited testing on macOS. Some features may not work as expected.
```

```{warning}
**macOS GMTSAR Installation**: Automatic GMTSAR installation on macOS may require additional configuration. You might need to install Xcode command line tools first: `xcode-select --install`
```

### Windows Subsystem for Linux (WSL2) - Recommended for Windows Users

Since GMTSAR cannot be installed on native Windows, WSL2 provides the best solution for Windows users:

#### Prerequisites
1. **Windows 10 (Build 19041+) or Windows 11**
2. **WSL2 with Ubuntu 20.04+**
3. **WSLg or X11 server for GUI support**

#### Step-by-Step WSL Setup

**1. Install WSL2 and Ubuntu**
```powershell
# Run in PowerShell as Administrator
wsl --install -d Ubuntu-20.04

# Or update existing WSL
wsl --update
wsl --set-default-version 2
```

**2. Configure GUI Support**

**Option A: WSLg (Windows 11 or recent Windows 10)**
```bash
# WSLg should work automatically
# Test with: echo $DISPLAY
```

**Option B: X11 Server (older Windows 10)**
```bash
# Install VcXsrv on Windows
# In WSL, add to ~/.bashrc:
echo 'export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk "{print \$2}"):0' >> ~/.bashrc
source ~/.bashrc
```

**3. Install InSARLite in WSL**
```bash
# Inside WSL Ubuntu terminal
sudo apt update
sudo apt install python3-pip python3-tk x11-utils

# Install InSARLite
pip3 install insarlite

# Launch (GUI will work if display is configured)
python3 -c "import insarlite; insarlite.main()"
```

```{note}
**WSL Performance**: InSARLite in WSL2 provides near-native Linux performance. Store your data on the Linux filesystem (e.g., `/home/username/`) for optimal performance rather than on Windows drives (`/mnt/c/`).
```

```{warning}
**Display Configuration**: If the GUI doesn't appear, check your DISPLAY variable with `echo $DISPLAY`. You may need to install and configure an X11 server on Windows.
```

## Virtual Environment Setup (Recommended)

Using a virtual environment helps avoid dependency conflicts:

### Using venv (Python 3.3+)

```bash
# Create virtual environment
python3 -m venv insarlite_env

# Activate (Linux/macOS)
source insarlite_env/bin/activate

# Activate (Windows)
insarlite_env\\Scripts\\activate

# Install InSARLite
pip install insarlite
```

### Using conda

```bash
# Create environment
conda create -n insarlite python=3.9

# Activate environment
conda activate insarlite

# Install InSARLite
pip install insarlite
```

## Verification

After installation, verify that InSARLite is working correctly:

```bash
# Test the installation
python -c "import insarlite; print('InSARLite imported successfully')"

# Launch the GUI
InSARLiteApp
```

If the GUI opens without errors, the installation was successful!

## GMTSAR Installation Details

### Automatic Installation Process

When you first launch InSARLite, it will:

1. **Check for existing GMTSAR installation**
   - Searches common installation paths
   - Tests GMTSAR functionality
   - Displays version information if found

2. **Prompt for installation** (if not found)
   - Shows installation confirmation dialog
   - Explains requirements and time needed
   - Allows user to decline and continue with limited functionality

3. **Install system dependencies**
   - Updates package lists
   - Installs required system packages:
     - `csh` - C Shell (required by GMTSAR scripts)
     - `autoconf` - Automatic configure script builder  
     - `gfortran` - GNU Fortran compiler
     - `g++` - GNU C++ compiler
     - `libtiff5-dev` - TIFF library development files
     - `libhdf5-dev` - HDF5 library development files
     - `liblapack-dev` - Linear algebra library
     - `libgmt-dev` - Generic Mapping Tools library
     - `gmt`, `gmt-dcw`, `gmt-gshhg` - GMT and geographic datasets

4. **Download and compile GMTSAR**
   - Clones GMTSAR 6.6 from GitHub
   - Configures build system
   - Compiles with parallel make
   - Installs to system location

5. **Configure environment**
   - Sets GMTSAR environment variable
   - Updates PATH in ~/.bashrc
   - Downloads orbit files (optional)

### Manual Installation (Advanced Users)

If automatic installation fails, you can install manually:

```bash
# Install system dependencies
sudo apt update && sudo apt install -y \
    csh autoconf gfortran g++ \
    libtiff5-dev libhdf5-dev liblapack-dev \
    libgmt-dev gmt gmt-dcw gmt-gshhg

# Clone and build GMTSAR
cd /usr/local
sudo git clone --branch 6.6 https://github.com/gmtsar/gmtsar GMTSAR
cd GMTSAR
sudo autoconf
sudo ./configure --with-orbits-dir=/usr/local/orbits
sudo make -j$(nproc)
sudo make install

# Set environment variables
echo 'export GMTSAR=/usr/local/GMTSAR' >> ~/.bashrc
echo 'export PATH=$GMTSAR/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

### Restricted Environment Setup

For systems without sudo access, ask your administrator to install:

```bash
# Required system packages
sudo apt install csh autoconf gfortran g++ libtiff5-dev \
                 libhdf5-dev liblapack-dev libgmt-dev gmt
```

Then GMTSAR can be installed to your home directory:

```bash
# Install to user directory
cd ~/
git clone --branch 6.6 https://github.com/gmtsar/gmtsar GMTSAR
cd GMTSAR
autoconf
./configure --prefix=$HOME/gmtsar --with-orbits-dir=$HOME/orbits
make -j$(nproc)
make install

# Add to environment
echo 'export GMTSAR=$HOME/GMTSAR' >> ~/.bashrc
echo 'export PATH=$GMTSAR/bin:$PATH' >> ~/.bashrc
```

## Troubleshooting

### Windows and WSL Issues

#### "Platform Not Supported" Error on Windows
**Cause**: InSARLite attempted to install GMTSAR on native Windows

**Solution**: 
1. Install WSL2 with Ubuntu: `wsl --install -d Ubuntu-20.04`
2. Launch Ubuntu from Start Menu
3. Install InSARLite inside WSL, not on Windows

#### GUI Not Appearing in WSL
**Cause**: Display server not configured

**Solutions**:
- **Windows 11**: Update to latest version (WSLg should work automatically)
- **Windows 10**: Install VcXsrv and configure DISPLAY variable:
  ```bash
  export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
  ```
- **Test display**: Run `xeyes` or `xcalc` to verify X11 forwarding

#### WSL Performance Issues
**Cause**: Files stored on Windows filesystem

**Solution**: 
- Store data in WSL filesystem: `/home/username/data/`
- Avoid Windows drives: `/mnt/c/` (much slower)

#### "Cannot connect to X server" Error
**Cause**: X11 server not running or DISPLAY not set

**Solutions**:
1. **Install X11 tools in WSL**:
   ```bash
   sudo apt install x11-utils x11-apps
   ```
2. **Configure DISPLAY variable**:
   ```bash
   echo 'export DISPLAY=:0' >> ~/.bashrc
   source ~/.bashrc
   ```
3. **Install X11 server on Windows** (VcXsrv or Xming)

### InSARLite Issues

#### ImportError: No module named 'tkinter'

**Solution**: Install tkinter
```bash
# Ubuntu/Debian
sudo apt install python3-tk

# CentOS/RHEL/Fedora
sudo dnf install python3-tkinter
```

#### ModuleNotFoundError: No module named 'cartopy'

**Solution**: Install cartopy dependencies
```bash
# Linux
sudo apt install libproj-dev proj-data proj-bin libgeos-dev

# macOS
brew install proj geos

# Then reinstall
pip install cartopy
```

### GMTSAR Installation Issues

#### Permission denied during installation

**Cause**: Insufficient permissions for system directories

**Solution**: 
- Use sudo for system installation, OR
- Install to user directory (see Restricted Environment Setup above)

#### Compilation errors

**Cause**: Missing development tools or libraries

**Solution**: Install build essentials
```bash
sudo apt install build-essential cmake pkg-config
```

#### "Command not found" after installation  

**Cause**: Environment variables not set

**Solution**: Update environment
```bash
source ~/.bashrc
# OR restart terminal
```

#### Missing orbit files

**Cause**: Orbit download failed during installation

**Solution**: Download manually
```bash
cd $GMTSAR
wget http://topex.ucsd.edu/gmtsar/tar/ORBITS.tar
tar -xf ORBITS.tar
```

### General Issues

#### Memory errors during processing

**Solution**: 
- Increase system memory
- Process smaller data subsets
- Use data decimation options

#### Display issues on remote systems

**Solution**: Enable X11 forwarding
```bash
ssh -X username@hostname
# OR
ssh -Y username@hostname
```

### Getting Help

If you encounter issues:

1. **Check the error message** carefully
2. **Update your installation**: `pip install --upgrade insarlite`
3. **Check dependencies**: Ensure all required packages are installed
4. **Search existing issues**: [GitHub Issues](https://github.com/mbadarmunir/InSARLite/issues)
5. **Create a new issue**: Include your OS, Python version, and full error message

## Next Steps

After successful installation:

1. Read the [Quick Start Guide](quickstart.md)
2. Follow the [User Guide](user-guide/index.md)
3. Try the [Tutorials](tutorials/index.md)

## Updating InSARLite

To update to the latest version:

```bash
pip install --upgrade insarlite
```

To check your current version:

```python
import insarlite
print(insarlite.__version__)
```