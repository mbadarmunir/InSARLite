"""
GMTSAR Installer for InSARLite
================================

This module provides two installation modes for GMTSAR:

1. FULL INSTALLATION (Requires Sudo Access)
   - Installs all system dependencies via apt-get
   - Downloads and installs orbit files
   - Compiles and installs GMTSAR to ~/.local
   - Compiles SBAS parallel tool
   - Configures environment variables
   - Ready to use immediately after terminal restart

2. MINIMAL INSTALLATION (No Sudo Required)
   - Clones GMTSAR repository to user-specified directory
   - Attempts configuration and compilation with existing system packages
   - If dependencies are missing, provides:
     * Complete list of required packages
     * Exact commands for system administrator
     * Instructions for manual installation
   - User can request admin to install dependencies, then re-run installer

Recommended Approach:
--------------------
- If you have sudo access: Use FULL installation
- If you don't have sudo access: 
  1. Try MINIMAL installation first
  2. If it fails due to missing dependencies, it will provide exact commands
  3. Request your system administrator to run those commands
  4. Re-run MINIMAL installation after dependencies are installed

Installation Check Strategy:
---------------------------
To optimize startup performance, InSARLite uses a smart GMTSAR check:

1. **Projects File Check** (~/.projs.json):
   - On startup, first checks if projects file exists
   - This file is created when user confirms configuration for the first time
   - If file exists: Assumes GMTSAR is installed (skips 'which' check)
   - If file doesn't exist: Performs full GMTSAR installation check

2. **Full Installation Check** (only when projects file missing):
   - Runs 'which gmtsar.csh' to verify GMTSAR installation
   - If not found: Prompts user with installation options
   - If found: Continues to check SBAS parallel

3. **Projects File Creation**:
   - Created automatically when user clicks "Confirm Configuration" button
   - Located at: ~/.projs.json
   - Contains list of InSARLite projects with their paths
   - Serves dual purpose: project history + GMTSAR installation indicator

This approach ensures:
- Fast startup for existing users (no 'which' command execution)
- Automatic GMTSAR check for first-time users
- GMTSAR verification before any project work begins

Environment Variables:
---------------------
Both modes add to ~/.bashrc:
  export GMTSAR=<installation_directory>/GMTSAR
  export PATH=$GMTSAR/bin:$HOME/.local/bin:$PATH
"""

import os
import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog


def is_wsl():
    """Check if running in Windows Subsystem for Linux."""
    try:
        # Check for WSL-specific files or environment variables
        if os.path.exists('/proc/version'):
            with open('/proc/version', 'r') as f:
                content = f.read().lower()
                return 'microsoft' in content or 'wsl' in content
        return False
    except:
        return False


def configure_wsl_display():
    """Configure DISPLAY environment variable for WSL."""
    if not is_wsl():
        return
    
    bashrc = os.path.expanduser("~/.bashrc")
    display_config = "\n# WSL Display configuration\nexport DISPLAY=:0\n"
    
    # Check if DISPLAY configuration already exists
    try:
        with open(bashrc, 'r') as f:
            content = f.read()
            if 'export DISPLAY=' in content:
                print("DISPLAY variable already configured in .bashrc")
                return
    except FileNotFoundError:
        pass
    
    # Add DISPLAY configuration
    with open(bashrc, "a") as f:
        f.write(display_config)
    print("Added DISPLAY=:0 configuration for WSL")


def check_gmtsar_availability():
    """Check if GMTSAR is properly installed and accessible."""
    try:
        # Check if gmtsar.csh is accessible via which command
        result = subprocess.run("which gmtsar.csh", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            gmtsar_path = result.stdout.strip()
            return True, gmtsar_path
        
        return False, None
    except Exception as e:
        print(f"Warning: Error checking GMTSAR availability: {e}")
        return False, None


def check_and_install_sbas_parallel():
    """Check for SBAS parallel and install if GMTSAR is available but SBAS parallel is not."""
    print("Checking SBAS parallel availability...")
    
    # First check if sbas_parallel is already available
    try:
        result = subprocess.run("which sbas_parallel", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ SBAS parallel is already installed and available")
            return True
    except:
        pass
    
    # Check if GMTSAR is available
    gmtsar_available, gmtsar_path = check_gmtsar_availability()
    
    if not gmtsar_available:
        print("❌ GMTSAR not found - cannot install SBAS parallel")
        print("💡 Please ensure GMTSAR is installed and terminal has been restarted")
        return False
    
    print(f"✅ GMTSAR found at: {gmtsar_path}")
    print("🔄 Installing SBAS parallel...")
    
    # Get GMTSAR directory from the path
    gmtsar_bin_dir = os.path.dirname(gmtsar_path)
    gmtsar_root = os.path.dirname(gmtsar_bin_dir)
    
    try:
        install_sbas_parallel(gmtsar_root)
        return True
    except Exception as e:
        print(f"⚠️  SBAS parallel installation failed: {e}")
        return False


def install_sbas_parallel(gmtsar_dir):
    """Install SBAS parallel with proper compilation flags."""
    print("Installing SBAS parallel...")
    
    # Check if sbas_parallel is already available
    try:
        result = subprocess.run("which sbas_parallel", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("SBAS parallel is already installed and available in PATH")
            return
    except:
        pass
    
    original_dir = os.getcwd()
    
    # Check multiple possible locations for sbas_parallel.c
    # 1. Source tree (fresh git clone): GMTSAR_ROOT/gmtsar/sbas_parallel.c
    # 2. Installed version: GMTSAR_ROOT/sbas_parallel.c
    # 3. Alternative case: GMTSAR_ROOT/GMTSAR/gmtsar/sbas_parallel.c
    
    possible_paths = [
        os.path.join(gmtsar_dir, "gmtsar"),           # Fresh clone: test/gmtsar/gmtsar/
        gmtsar_dir,                                    # Installed: installed_soft/gmtsar/
        os.path.join(gmtsar_dir, "GMTSAR", "gmtsar")  # Alternative case
    ]
    
    sbas_dir = None
    print(f"Searching for SBAS directory in multiple locations...")
    for path in possible_paths:
        print(f"  Checking: {path}")
        if os.path.exists(path) and os.path.exists(os.path.join(path, "sbas_parallel.c")):
            sbas_dir = path
            print(f"✅ Found sbas_parallel.c at: {sbas_dir}")
            break
    
    if not sbas_dir:
        print(f"Warning: sbas_parallel.c not found in any expected location")
        # List available directories for debugging
        print(f"Available directories in {gmtsar_dir}:")
        try:
            for item in os.listdir(gmtsar_dir):
                item_path = os.path.join(gmtsar_dir, item)
                if os.path.isdir(item_path):
                    print(f"  - {item}/")
        except Exception as e:
            print(f"  Could not list directories: {e}")
        return
    
    os.chdir(sbas_dir)
    
    try:
        # Verify sbas_parallel.c exists in this directory
        if not os.path.exists("sbas_parallel.c"):
            print(f"Error: sbas_parallel.c not found in {sbas_dir}")
            return

        # Try to rebuild GMTSAR library first for linking
        print("Rebuilding GMTSAR components for SBAS parallel compilation...")
        
        # Save current directory
        current_dir = os.getcwd()
        
        # Go to main GMTSAR directory and rebuild
        gmtsar_root = os.path.dirname(current_dir)
        os.chdir(gmtsar_root)
        
        try:
            # Run make to ensure all object files and libraries are built
            run_command("make")
            print("✅ GMTSAR rebuild completed")
        except Exception as e:
            print(f"Warning: GMTSAR rebuild failed: {e}")
        
        # Return to gmtsar subdirectory
        os.chdir(current_dir)
        
        # Now check for library
        if os.path.exists("libgmtsar.a"):
            print("✅ Found GMTSAR library after rebuild")
            gmtsar_lib_found = True
            gmtsar_lib_path = "."
        else:
            print("⚠️  GMTSAR library not found after rebuild")
            gmtsar_lib_found = False
            gmtsar_lib_path = ""

        # Detect GMT include paths dynamically (handles all installation types)
        gmt_include_paths = [
            "-I/usr/local/include/gmt",  # Common on manual installations
            "-I/usr/include/gmt",         # Common on apt-get installations
            "-I/opt/local/include/gmt",   # MacPorts
            "-I/usr/local/opt/gmt/include" # Homebrew (macOS)
        ]
        
        # Check which GMT paths exist
        valid_gmt_paths = []
        for path in gmt_include_paths:
            dir_path = path.replace("-I", "")
            if os.path.exists(dir_path) and os.path.exists(os.path.join(dir_path, "gmt.h")):
                valid_gmt_paths.append(path)
                print(f"✅ Found GMT headers at: {dir_path}")
        
        if not valid_gmt_paths:
            print("⚠️  Warning: GMT headers not found in standard locations, trying all paths...")
            valid_gmt_paths = gmt_include_paths  # Try all anyway
        
        # Build include flags
        gmt_flags = " ".join(valid_gmt_paths)

        # Compile sbas_parallel.o with OpenMP support
        print(f"Compiling with GMT paths: {gmt_flags}")
        compile_cmd = (
            f"gcc -fopenmp -O2 -Wall -m64 -fPIC -fno-strict-aliasing -std=c99 "
            f"-z muldefs {gmt_flags} -I./ -I/usr/local/include -I/usr/include "
            f"-c -o sbas_parallel.o sbas_parallel.c"
        )
        run_command(compile_cmd)

        # Link sbas_parallel executable
        # Detect library paths dynamically
        lib_paths = [
            "/usr/lib/x86_64-linux-gnu",
            "/usr/local/lib",
            "/usr/lib",
            "/opt/local/lib"
        ]
        
        valid_lib_paths = [path for path in lib_paths if os.path.exists(path)]
        lib_flags = " ".join([f"-L{path}" for path in valid_lib_paths])
        rpath = valid_lib_paths[0] if valid_lib_paths else "/usr/lib"
        
        print(f"Using library paths: {lib_flags}")
        
        if gmtsar_lib_found:
            # Use standard linking with GMTSAR library
            link_cmd = (
                f"gcc -fopenmp -m64 -s -Wl,-rpath,{rpath} "
                f"-z muldefs sbas_parallel.o -L{gmtsar_lib_path} -lgmtsar "
                f"{lib_flags} -lgmt -llapack -lblas -lm -ltiff -o sbas_parallel"
            )
        else:
            # Fallback: try linking without GMTSAR library (standalone compilation)
            print("Warning: GMTSAR library not found, attempting standalone compilation...")
            link_cmd = (
                f"gcc -fopenmp -m64 -s -Wl,-rpath,{rpath} "
                f"-z muldefs sbas_parallel.o "
                f"{lib_flags} -lgmt -llapack -lblas -lm -ltiff -o sbas_parallel"
            )
        
        try:
            run_command(link_cmd)
        except Exception as link_error:
            if gmtsar_lib_found:
                # If linking with GMTSAR library failed, try without it
                print("Warning: Linking with GMTSAR library failed, trying standalone compilation...")
                fallback_cmd = (
                    f"gcc -fopenmp -m64 -s -Wl,-rpath,/usr/lib/x86_64-linux-gnu "
                    f"-z muldefs sbas_parallel.o "
                    "-L/usr/lib/x86_64-linux-gnu -lgmt -llapack -lblas -lm "
                    "-L/usr/local/lib -ltiff -lm -o sbas_parallel"
                )
                try:
                    run_command(fallback_cmd)
                except Exception as fallback_error:
                    print(f"Warning: SBAS parallel compilation failed - requires GMTSAR library functions")
                    print(f"SBAS parallel will not be available, but GMTSAR installation will continue")
                    return  # Exit gracefully instead of raising error
            else:
                print(f"Warning: SBAS parallel compilation failed - GMTSAR library not found")
                print(f"SBAS parallel will not be available, but GMTSAR installation will continue")
                return  # Exit gracefully instead of raising error
        
        # Install sbas_parallel to user-accessible location
        user_bin = os.path.expanduser("~/.local/bin")
        os.makedirs(user_bin, exist_ok=True)
        run_command(f"cp sbas_parallel {user_bin}/")
        run_command(f"chmod +x {user_bin}/sbas_parallel")
        
        print("SBAS parallel installed to user bin directory")
        
    except Exception as e:
        print(f"Warning: SBAS parallel installation failed: {e}")
    finally:
        os.chdir(original_dir)


def run_command(cmd, cwd=None, verbose=True):
    """Run shell command with error handling."""
    if verbose:
        print(f"▶ Running: {cmd}")
    
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=600)
    
    if result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        if result.stderr:
            print(f"Error output:\n{result.stderr}")
        if result.stdout:
            print(f"Standard output:\n{result.stdout}")
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {cmd}")
    else:
        if verbose and result.stdout:
            # Only print first and last few lines for long outputs
            lines = result.stdout.strip().split('\n')
            if len(lines) > 10:
                print('\n'.join(lines[:3]))
                print(f"... ({len(lines) - 6} lines omitted) ...")
                print('\n'.join(lines[-3:]))
            else:
                print(result.stdout)
    
    return result


def check_missing_dependencies():
    """Check which system packages are missing."""
    pkgs = [
        "csh", "subversion", "autoconf", "libtiff5-dev", "libhdf5-dev", "wget",
        "liblapack-dev", "gfortran", "g++", "gcc", "libgmt-dev",
        "gmt-dcw", "gmt-gshhg", "gmt", "parallel"
    ]
    
    missing = []
    installed = []
    
    for pkg in pkgs:
        result = subprocess.run(
            f"dpkg -l | grep -q '^ii.*{pkg}' && echo 'yes' || echo 'no'",
            shell=True, capture_output=True, text=True
        )
        if 'no' in result.stdout:
            missing.append(pkg)
        else:
            installed.append(pkg)
    
    return missing, installed


def print_missing_dependencies_guide(missing_packages):
    """Print comprehensive guide for installing missing dependencies."""
    print("\n" + "="*80)
    print("  MISSING DEPENDENCIES DETECTED")
    print("="*80)
    print(f"\nGMTSAR compilation requires {len(missing_packages)} missing packages:\n")
    
    for i, pkg in enumerate(missing_packages, 1):
        print(f"  {i:2d}. {pkg}")
    
    print("\n" + "="*80)
    print("  INSTALLATION OPTIONS")
    print("="*80)
    
    print("\n📋 Option 1: Request System Administrator")
    print("-" * 80)
    print("Copy and send these commands to your system administrator:\n")
    print("# Update package lists")
    print("sudo dpkg --configure -a")
    print("sudo apt-get update\n")
    print("# Install required packages")
    print(f"sudo apt-get install -y {' '.join(missing_packages)}")
    
    print("\n📋 Option 2: Conda/Mamba (If Available)")
    print("-" * 80)
    print("If you have conda or mamba installed, you can install dependencies without sudo:\n")
    print("conda install -c conda-forge gmt libgmt liblapack libtiff libhdf5 gcc gfortran")
    print("# or using mamba (faster):")
    print("mamba install -c conda-forge gmt libgmt liblapack libtiff libhdf5 gcc gfortran")
    
    print("\n📋 Option 3: Manual Installation")
    print("-" * 80)
    print("Download and compile each dependency from source (advanced users only)")
    print("See: https://github.com/gmtsar/gmtsar for detailed instructions")
    
    print("\n" + "="*80)
    print("  NEXT STEPS")
    print("="*80)
    print("\n1. Choose one of the options above to install missing dependencies")
    print("2. After dependencies are installed, restart your terminal")
    print("3. Re-run InSARLite installer and select MINIMAL installation again")
    print("4. The installation should complete successfully\n")
    print("="*80 + "\n")


def install_dependencies():
    """Install required system packages for GMTSAR + GMT."""
    print("\n📦 Checking system dependencies...")
    
    missing, installed = check_missing_dependencies()
    
    if installed:
        print(f"✅ Already installed ({len(installed)}): {', '.join(installed[:5])}{'...' if len(installed) > 5 else ''}")
    
    if not missing:
        print("✅ All dependencies are already installed!")
        return True
    
    print(f"❌ Missing packages ({len(missing)}): {', '.join(missing)}")
    print("\n🔐 Installing missing packages requires sudo access...")
    
    try:
        # Fix dpkg configuration first
        print("Configuring package manager...")
        run_command("sudo dpkg --configure -a", verbose=False)
        
        print("Updating package lists...")
        run_command("sudo apt-get update", verbose=False)
        
        print(f"Installing {len(missing)} packages...")
        run_command(f"sudo apt-get install -y {' '.join(missing)}")
        
        print("✅ All dependencies installed successfully!")
        return True
    except Exception as e:
        print(f"❌ Dependency installation failed: {e}")
        print("\n💡 Alternative: Install using conda/mamba:")
        print("   conda install -c conda-forge gmt gmtsar csh")
        return False


def install_orbits(orbits_dir):
    """Download and extract orbit files."""
    url = "http://topex.ucsd.edu/gmtsar/tar/ORBITS.tar"
    tar_path = os.path.join(orbits_dir, "ORBITS.tar")
    run_command(f"wget -O {tar_path} {url}")
    run_command(f"tar -xvf {tar_path}", cwd=orbits_dir)
    run_command(f"rm {tar_path}")


def update_config_mk_for_gfortran9(gmtsar_dir):
    """Update config.mk to use gcc-9 and gfortran-9 if available."""
    config_mk_path = os.path.join(gmtsar_dir, "config.mk")
    
    if not os.path.exists(config_mk_path):
        print("ℹ️  config.mk not found, skipping compiler version update")
        return
    
    # Check if gcc-9 and gfortran-9 are available
    gcc9_available = subprocess.run("which gcc-9", shell=True, capture_output=True).returncode == 0
    gfortran9_available = subprocess.run("which gfortran-9", shell=True, capture_output=True).returncode == 0
    
    if not (gcc9_available and gfortran9_available):
        print("ℹ️  gcc-9/gfortran-9 not available, using system default compilers")
        return
    
    # Read the file
    with open(config_mk_path, 'r') as f:
        lines = f.readlines()
    
    # Update line 31 (index 30) to use gcc-9 if it exists
    if len(lines) > 30 and 'gcc' in lines[30]:
        lines[30] = lines[30].replace('gcc', 'gcc-9')
    
    # Also update any gfortran references to gfortran-9
    for i, line in enumerate(lines):
        if 'gfortran' in line and 'gfortran-9' not in line:
            lines[i] = line.replace('gfortran', 'gfortran-9')
    
    # Write the file back
    with open(config_mk_path, 'w') as f:
        f.writelines(lines)
    
    print("✅ Updated config.mk to use gcc-9 and gfortran-9")


def get_latest_gmtsar_version():
    """Get the latest stable GMTSAR version from GitHub."""
    try:
        result = subprocess.run(
            "git ls-remote --tags https://github.com/gmtsar/gmtsar | grep -v '{}' | tail -1 | awk '{print $2}' | sed 's|refs/tags/||'",
            shell=True, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return "6.6"  # Default fallback
    except:
        return "6.6"


def install_gmtsar_minimal(install_dir, version=None, skip_deps_check=False, self_contained=False):
    """
    Minimal GMTSAR installation without sudo access.
    
    This function:
    1. Clones GMTSAR repository to user-specified directory
    2. Attempts configuration with existing system packages
    3. If configuration fails, provides detailed dependency installation guide
    4. Does NOT require sudo access
    
    Args:
        install_dir: Directory where GMTSAR will be installed
        version: GMTSAR version to install (default: latest)
        skip_deps_check: If True, skip dependency checking and proceed with compilation
        self_contained: If True, install to clone directory instead of ~/.local
    
    Returns:
        bool or str: True if successful, 'missing_deps' if dependencies needed, False on error
    """
    print("\n" + "="*80)
    print("  MINIMAL GMTSAR INSTALLATION (No Sudo Required)")
    if skip_deps_check:
        print("  Mode: Skip dependency checks, force compilation")
    if self_contained:
        print("  Mode: Self-contained installation (in clone directory)")
    print("="*80)
    
    gmtsar_dir = os.path.join(install_dir, "GMTSAR")
    
    # Determine version to install
    if version is None:
        print("\n🔍 Checking for latest GMTSAR version...")
        version = get_latest_gmtsar_version()
    
    print(f"📥 Installing GMTSAR version: {version}")
    print(f"📁 Installation directory: {install_dir}")

    # Clone repository
    if not os.path.exists(gmtsar_dir):
        print(f"\n📦 Cloning GMTSAR {version} from GitHub...")
        try:
            run_command(f"git clone --branch {version} --depth 1 https://github.com/gmtsar/gmtsar {gmtsar_dir}")
        except Exception as e:
            print(f"⚠️  Failed to clone specific version, trying default branch...")
            try:
                run_command(f"git clone --depth 1 https://github.com/gmtsar/gmtsar {gmtsar_dir}")
            except Exception as e2:
                print(f"❌ Failed to clone GMTSAR: {e2}")
                return False
    else:
        print(f"✅ GMTSAR directory already exists: {gmtsar_dir}")
    
    original_dir = os.getcwd()
    os.chdir(gmtsar_dir)
    
    try:
        # Attempt configuration
        print("\n🔧 Configuring GMTSAR build system...")
        
        try:
            run_command("autoconf", verbose=False)
        except Exception as e:
            print(f"❌ autoconf failed: {e}")
            print("\n💡 autoconf is required. Install with: sudo apt-get install autoconf")
            return 'missing_deps'
        
        # Configure with installation prefix
        if self_contained:
            # Self-contained: install everything in the clone directory
            install_prefix = gmtsar_dir
            print(f"📦 Self-contained installation: {install_prefix}")
        else:
            # Standard: install to ~/.local
            install_prefix = os.path.expanduser("~/.local")
            print(f"📦 Standard user installation: {install_prefix}")
        
        config_cmd = f"./configure --prefix={install_prefix} CFLAGS='-z muldefs' LDFLAGS='-z muldefs'"
        
        print(f"\n🏗️  Running configuration...")
        print(f"   Command: {config_cmd}")
        
        try:
            result = run_command(config_cmd)
        except Exception as e:
            if skip_deps_check:
                print(f"\n⚠️  Configuration warning: {e}")
                print("   Continuing anyway (skip_deps_check=True)...")
            else:
                print(f"\n❌ Configuration failed!\n")
                
                # Check for missing dependencies
                print("🔍 Checking for missing dependencies...")
                missing, installed = check_missing_dependencies()
                
                if missing:
                    print_missing_dependencies_guide(missing)
                    return 'missing_deps'
                else:
                    print(f"\n❌ Configuration failed but dependencies appear to be installed.")
                    print(f"Error details: {e}")
                    print("\nPlease check the error messages above for specific issues.")
                    return False
        
        # If we reach here, configuration succeeded
        print("\n✅ Configuration successful!")
        
        # Compile GMTSAR
        print("\n🔨 Compiling GMTSAR (this may take several minutes)...")
        import multiprocessing
        n_cores = max(1, multiprocessing.cpu_count() - 1)
        print(f"   Using {n_cores} CPU cores for compilation")
        
        try:
            run_command(f"make -j{n_cores}")
        except:
            print("⚠️  Parallel compilation failed, trying single-threaded...")
            try:
                run_command("make")
            except Exception as e:
                if skip_deps_check:
                    print(f"\n⚠️  Compilation warning: {e}")
                    print("   Continuing anyway (skip_deps_check=True)...")
                else:
                    print(f"\n❌ Compilation failed: {e}")
                    print("\nPlease check the error messages above.")
                    return False
        
        # Install to specified directory
        print(f"\n📦 Installing GMTSAR to {install_prefix}...")
        try:
            run_command("make install")
        except Exception as e:
            if skip_deps_check:
                print(f"\n⚠️  Installation warning: {e}")
                print("   Continuing anyway (skip_deps_check=True)...")
            else:
                print(f"\n❌ Installation failed: {e}")
                return False
        
        # Configure environment
        print("\n⚙️  Configuring environment variables...")
        configure_wsl_display()
        
        bashrc = os.path.expanduser("~/.bashrc")
        
        # Remove any existing GMTSAR configurations
        print("Cleaning existing GMTSAR configurations from ~/.bashrc...")
        try:
            with open(bashrc, 'r') as f:
                lines = f.readlines()
            
            # Filter out old GMTSAR lines
            new_lines = []
            skip_next = False
            for line in lines:
                if 'GMTSAR configuration' in line or 'GMTSAR Configuration' in line:
                    skip_next = True
                    continue
                if skip_next and ('export GMTSAR=' in line or (line.strip() == '' and 'export PATH=' not in line)):
                    if line.strip() == '':
                        skip_next = False
                    continue
                if skip_next and 'export PATH=' in line and ('GMTSAR' in line or '.local' in line):
                    continue
                skip_next = False
                new_lines.append(line)
            
            with open(bashrc, 'w') as f:
                f.writelines(new_lines)
            
            print("✅ Cleaned existing GMTSAR configurations")
        except Exception as e:
            print(f"⚠️  Could not clean existing configurations: {e}")
        
        # Add new configuration
        with open(bashrc, "a") as f:
            f.write(f"\n# GMTSAR configuration\n")
            f.write(f"export GMTSAR={gmtsar_dir}\n")
            if self_contained:
                # For self-contained, only add the clone directory to PATH
                f.write(f"export PATH={gmtsar_dir}/bin:$PATH\n")
            else:
                # For standard installation, include both
                f.write(f"export PATH={gmtsar_dir}/bin:$HOME/.local/bin:$PATH\n")
        print("✅ Added GMTSAR configuration to .bashrc")
        
        print("\n" + "="*80)
        print("  ✅ MINIMAL INSTALLATION COMPLETED SUCCESSFULLY!")
        print("="*80)
        print("\n📋 Installation Summary:")
        print(f"   • GMTSAR installed to: {gmtsar_dir}")
        print(f"   • Binaries location: {install_prefix}/bin")
        if self_contained:
            print(f"   • Self-contained installation in: {gmtsar_dir}")
        else:
            print(f"   • User binaries: {install_prefix}/bin")
        print("\n⚠️  IMPORTANT: Restart your terminal for environment variables to take effect.")
        print("\n📋 Next steps:")
        print("   1. Close InSARLite application")
        print("   2. Close and restart your terminal")
        print("   3. Verify installation: which gmtsar.csh")
        if self_contained:
            print(f"      Should show: {gmtsar_dir}/bin/gmtsar.csh")
        print("   4. Launch InSARLite again: insarlite")
        print("   5. SBAS parallel will be checked and installed if needed")
        print("="*80 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Unexpected error during installation: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        os.chdir(original_dir)


def install_gmtsar(install_dir, orbits_dir=None, use_newer_ubuntu=True, version=None):
    """Clone, configure, make, and install GMTSAR."""
    gmtsar_dir = os.path.join(install_dir, "GMTSAR")
    
    # Determine version to install
    if version is None:
        print("\n🔍 Checking for latest GMTSAR version...")
        version = get_latest_gmtsar_version()
    
    print(f"📥 Installing GMTSAR version: {version}")

    if not os.path.exists(gmtsar_dir):
        print(f"\n📦 Cloning GMTSAR {version} from GitHub...")
        try:
            run_command(f"git clone --branch {version} --depth 1 https://github.com/gmtsar/gmtsar {gmtsar_dir}")
        except Exception as e:
            print(f"⚠️  Failed to clone specific version, trying default branch...")
            run_command(f"git clone --depth 1 https://github.com/gmtsar/gmtsar {gmtsar_dir}")
    else:
        print(f"✅ GMTSAR directory already exists: {gmtsar_dir}")

    original_dir = os.getcwd()
    os.chdir(gmtsar_dir)
    
    try:
        run_command("autoconf")
        run_command("autoupdate")

        # Configure with or without orbits directory and local installation prefix
        user_local = os.path.expanduser("~/.local")
        if orbits_dir:
            if use_newer_ubuntu:
                run_command(f"./configure --prefix={user_local} --with-orbits-dir={orbits_dir} CFLAGS='-z muldefs' LDFLAGS='-z muldefs'")
            else:
                run_command(f"./configure --prefix={user_local} --with-orbits-dir={orbits_dir}")
        else:
            if use_newer_ubuntu:
                run_command(f"./configure --prefix={user_local} CFLAGS='-z muldefs' LDFLAGS='-z muldefs'")
            else:
                run_command(f"./configure --prefix={user_local}")

        # Update config.mk to use gfortran-9 and gcc-9
        update_config_mk_for_gfortran9(gmtsar_dir)

        run_command("make")
        # Install to user's local directory instead of system-wide
        run_command("make install")

        # Configure WSL display if running in WSL
        configure_wsl_display()

        # Add GMTSAR env vars to .bashrc
        bashrc = os.path.expanduser("~/.bashrc")
        
        # Check if GMTSAR configuration already exists
        gmtsar_config_exists = False
        try:
            with open(bashrc, 'r') as f:
                content = f.read()
                if 'GMTSAR configuration' in content or f'export GMTSAR={gmtsar_dir}' in content:
                    gmtsar_config_exists = True
                    print("GMTSAR configuration already exists in .bashrc")
        except FileNotFoundError:
            pass
        
        if not gmtsar_config_exists:
            with open(bashrc, "a") as f:
                f.write(f"\n# GMTSAR configuration\n")
                f.write(f"export GMTSAR={gmtsar_dir}\n")
                f.write(f"export PATH=$GMTSAR/bin:$HOME/.local/bin:$PATH\n")
            print("Added GMTSAR configuration to .bashrc")
        
        # Note: SBAS parallel installation is handled separately after terminal restart
        print("\n" + "="*60)
        print("🎉 GMTSAR INSTALLATION COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("✅ GMTSAR installed to user directory - no sudo access required")
        print("⚠️  IMPORTANT: You must restart your terminal for environment variables to take effect.")
        print("📋 Next steps:")
        print("   1. Close InSARLite application")
        print("   2. Close and restart your terminal")
        print("   3. Launch InSARLite again: insarlite")
        print("   4. SBAS parallel will be checked and installed if needed")
        print("🌍 Environment variables added to ~/.bashrc:")
        print(f"   export GMTSAR={gmtsar_dir}")
        print(f"   export PATH=$GMTSAR/bin:$HOME/.local/bin:$PATH")
        print("="*60)
    
    finally:
        os.chdir(original_dir)


def check_gmtsar_installation():
    """
    Check if GMTSAR is properly installed by running gmtsar.csh.
    
    Returns:
        bool: True if GMTSAR is available and working
    """
    try:
        # Check if gmtsar.csh is accessible
        result = subprocess.run(['which', 'gmtsar.csh'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        
        if result.returncode == 0:
            print(f"✅ GMTSAR found at: {result.stdout.strip()}")
            return True
        else:
            print("❌ gmtsar.csh not found in PATH")
            return False
            
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        print(f"❌ Error checking GMTSAR: {e}")
        return False


def install_gmtsar_gui():
    """GUI-based GMTSAR installation with mode selection."""
    root = tk.Tk()
    root.withdraw()  # Hide root window

    # Ask user to select installation mode
    mode_message = (
        "GMTSAR Installation - Select Mode:\n\n"
        "• FULL Installation (Requires Sudo)\n"
        "  - Installs all dependencies automatically\n"
        "  - Downloads orbit files (optional)\n"
        "  - Ready to use immediately\n\n"
        "• MINIMAL Installation (No Sudo)\n"
        "  - Uses existing system packages\n"
        "  - Compiles GMTSAR only\n"
        "  - Provides dependency commands if needed\n\n"
        "Click YES for FULL installation\n"
        "Click NO for MINIMAL installation\n"
        "Click CANCEL to abort"
    )
    
    mode_choice = messagebox.askyesnocancel("Installation Mode", mode_message)
    
    if mode_choice is None:  # Cancel
        messagebox.showinfo("Cancelled", "Installation cancelled.")
        return False
    
    use_full_mode = mode_choice  # True = FULL, False = MINIMAL
    
    # Ask for installation directory
    if use_full_mode:
        install_dir = filedialog.askdirectory(
            title="Select installation directory (FULL mode)", 
            initialdir=os.path.expanduser("~")
        )
    else:
        install_dir = filedialog.askdirectory(
            title="Select installation directory (MINIMAL mode - no sudo)", 
            initialdir=os.path.expanduser("~")
        )
    
    if not install_dir:
        messagebox.showinfo("Cancelled", "Installation cancelled.")
        return False

    if use_full_mode:
        # FULL INSTALLATION MODE
        # Ask user about orbit installation
        install_orbits_flag = messagebox.askyesno(
            "Orbits Installation", 
            "Do you want to download and install orbit files?\n\n"
            "(Recommended for complete installation)"
        )
        if install_orbits_flag:
            orbits_dir = os.path.join(install_dir, "orbits")
            os.makedirs(orbits_dir, exist_ok=True)
        else:
            orbits_dir = None

        # Confirm
        if orbits_dir:
            proceed = messagebox.askyesno(
                "Confirm FULL Installation", 
                f"FULL Installation (requires sudo):\n\n"
                f"GMTSAR: {install_dir}\n"
                f"Orbits: {orbits_dir}\n\n"
                f"This will:\n"
                f"• Install system dependencies (requires password)\n"
                f"• Download orbit files\n"
                f"• Compile and install GMTSAR\n\n"
                f"Proceed?"
            )
        else:
            proceed = messagebox.askyesno(
                "Confirm FULL Installation", 
                f"FULL Installation (requires sudo):\n\n"
                f"GMTSAR: {install_dir}\n"
                f"Skip orbit files\n\n"
                f"This will:\n"
                f"• Install system dependencies (requires password)\n"
                f"• Compile and install GMTSAR\n\n"
                f"Proceed?"
            )
        
        if not proceed:
            return False

        try:
            success = install_dependencies()
            if not success:
                messagebox.showerror(
                    "Dependency Installation Failed", 
                    "Failed to install dependencies.\n\n"
                    "Please check the console output for details."
                )
                return False
            
            if install_orbits_flag:
                install_orbits(orbits_dir)
            
            install_gmtsar(install_dir, orbits_dir, use_newer_ubuntu=True)
            
            messagebox.showinfo(
                "Installation Complete", 
                "GMTSAR FULL installation completed successfully!\n\n"
                "IMPORTANT: Please close InSARLite and restart your terminal\n"
                "for environment variables to take effect.\n\n"
                "Then restart InSARLite to check for SBAS parallel installation."
            )
            return "close_app"
        except Exception as e:
            messagebox.showerror("Installation Error", f"Installation failed:\n\n{str(e)}")
            return False
    
    else:
        # MINIMAL INSTALLATION MODE
        
        # Ask about skip dependency check
        skip_deps_msg = (
            "Would you like to SKIP dependency checking?\n\n"
            "• YES: Force compilation without checking dependencies\n"
            "  (Use if you know dependencies are installed)\n\n"
            "• NO: Check dependencies first (recommended)\n"
        )
        skip_deps_check = messagebox.askyesno("Skip Dependency Check?", skip_deps_msg)
        
        # Ask about self-contained installation
        self_contained_msg = (
            "Would you like a SELF-CONTAINED installation?\n\n"
            "• YES: Install everything in the clone directory\n"
            "  (Portable, matches manual installations)\n\n"
            "• NO: Install to ~/.local (standard Linux convention)\n"
        )
        self_contained = messagebox.askyesno("Self-Contained Installation?", self_contained_msg)
        
        proceed = messagebox.askyesno(
            "Confirm MINIMAL Installation", 
            f"MINIMAL Installation (no sudo required):\n\n"
            f"Directory: {install_dir}\n"
            f"Skip dependency check: {'YES' if skip_deps_check else 'NO'}\n"
            f"Self-contained: {'YES' if self_contained else 'NO'}\n\n"
            f"This will:\n"
            f"• Clone GMTSAR repository\n"
            f"• {'Force' if skip_deps_check else 'Attempt'} compilation\n"
            f"• Install to {'clone directory' if self_contained else '~/.local'}\n"
            f"{'• Continue on errors' if skip_deps_check else '• Provide dependency commands if needed'}\n\n"
            f"No sudo access required.\n\n"
            f"Proceed?"
        )
        
        if not proceed:
            return False
        
        try:
            result = install_gmtsar_minimal(install_dir, skip_deps_check=skip_deps_check, self_contained=self_contained)
            
            if result is True:
                messagebox.showinfo(
                    "Installation Complete", 
                    "GMTSAR MINIMAL installation completed successfully!\n\n"
                    "IMPORTANT: Please close InSARLite and restart your terminal\n"
                    "for environment variables to take effect.\n\n"
                    "Then restart InSARLite to check for SBAS parallel installation."
                )
                return "close_app"
            elif result == 'missing_deps':
                messagebox.showwarning(
                    "Missing Dependencies", 
                    "GMTSAR compilation requires additional system packages.\n\n"
                    "Please check the CONSOLE OUTPUT for:\n"
                    "• Complete list of missing packages\n"
                    "• Commands for system administrator\n"
                    "• Alternative installation options\n\n"
                    "After dependencies are installed, restart InSARLite\n"
                    "and run MINIMAL installation again."
                )
                return False
            else:
                messagebox.showerror(
                    "Installation Failed", 
                    "MINIMAL installation failed.\n\n"
                    "Please check the console output for error details."
                )
                return False
        except Exception as e:
            messagebox.showerror("Installation Error", f"Installation failed:\n\n{str(e)}")
            return False





def check_and_install_gmtsar(projects_file_path):
    """
    Check if GMTSAR is installed and install if needed.
    This function is called by InSARLite on startup.
    
    Strategy:
    1. First check if projects file exists (created when user confirms first configuration)
    2. If projects file exists: Assume GMTSAR installed, skip 'which' check (performance)
    3. If projects file missing: Run full GMTSAR check via 'which gmtsar.csh'
    4. If GMTSAR not found: Prompt for installation via GUI
    
    Args:
        projects_file_path: Path to the projects file (~/.projs.json)
        
    Returns:
        bool or str: True if GMTSAR available, "close_app" if installed, False on error
    """
    # Optimization: Check if projects file exists first
    if os.path.exists(projects_file_path):
        print("ℹ️  Projects file found - assuming GMTSAR is installed")
        print(f"   {projects_file_path}")
        # Still check SBAS parallel as it's a quick check
        check_and_install_sbas_parallel()
        return True
    
    # Projects file doesn't exist - this might be first run
    # Perform full GMTSAR installation check
    print("ℹ️  Projects file not found - performing GMTSAR installation check...")
    
    if check_gmtsar_installation():
        print("✅ GMTSAR is available")
        # Check and install SBAS parallel if needed
        check_and_install_sbas_parallel()
        return True
    
    # GMTSAR not found - need to install it
    print("❌ GMTSAR not found")
    
    try:
        import tkinter as tk
        from tkinter import messagebox
        
        root = tk.Tk()
        root.withdraw()  # Hide root window
        
        # Inform user that GMTSAR is required
        message = ("GMTSAR not found!\n\n"
                  "InSARLite requires GMTSAR to function properly.\n\n"
                  "Would you like to install GMTSAR now?")
        
        install_choice = messagebox.askyesno("GMTSAR Required", message)
        
        if not install_choice:
            messagebox.showerror("Cannot Proceed", 
                               "InSARLite cannot function without GMTSAR.\n"
                               "Please install GMTSAR manually or restart the application.")
            root.destroy()
            return False
        
        root.destroy()
        
        # Proceed with GUI installation
        return install_gmtsar_gui()
        
    except Exception as e:
        print(f"❌ Installation dialog failed: {e}")
        print("InSARLite requires GMTSAR to function.")
        print("Please install GMTSAR manually and restart the application.")
        return False


if __name__ == "__main__":
    """Test the GMTSAR installer."""
    print("=== GMTSAR Installation Test ===")
    
    # Use test projects file path
    test_projects_file = os.path.join(os.path.expanduser('~'), ".projs.json")
    
    # Check current status
    if check_gmtsar_installation():
        print("✅ GMTSAR is already installed and working")
    else:
        print("❌ GMTSAR not found")
        
        # Test the installation workflow
        success = check_and_install_gmtsar(test_projects_file)
        print(f"Installation result: {success}")

