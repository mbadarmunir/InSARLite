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
    sbas_dir = os.path.join(gmtsar_dir, "gmtsar")
    
    if not os.path.exists(sbas_dir):
        print(f"Warning: SBAS directory not found at {sbas_dir}")
        return
    
    os.chdir(sbas_dir)
    
    try:
        # Check if sbas_parallel.c exists
        if not os.path.exists("sbas_parallel.c"):
            print("Warning: sbas_parallel.c not found, skipping SBAS parallel installation")
            return
        
        # Clean previous builds
        run_command("make clean")
        
        # Compile sbas_parallel.o with OpenMP support
        compile_cmd = (
            "gcc -fopenmp -O2 -Wall -m64 -fPIC -fno-strict-aliasing -std=c99 "
            "-z muldefs -I/usr/include/gmt -I./ -I/usr/local/include "
            "-c -o sbas_parallel.o sbas_parallel.c"
        )
        run_command(compile_cmd)
        
        # Link sbas_parallel executable
        # First try to find GMTSAR library
        gmtsar_lib_paths = [
            f"{gmtsar_dir}/gmtsar",
            f"{gmtsar_dir}/lib", 
            "/usr/local/lib",
            "/usr/lib/x86_64-linux-gnu"
        ]
        
        gmtsar_lib_found = False
        gmtsar_lib_path = ""
        
        for lib_path in gmtsar_lib_paths:
            if os.path.exists(f"{lib_path}/libgmtsar.so") or os.path.exists(f"{lib_path}/libgmtsar.a"):
                gmtsar_lib_found = True
                gmtsar_lib_path = lib_path
                break
        
        if gmtsar_lib_found:
            # Use standard linking with GMTSAR library
            link_cmd = (
                f"gcc -fopenmp -m64 -s -Wl,-rpath,/usr/lib/x86_64-linux-gnu "
                f"-z muldefs sbas_parallel.o -L{gmtsar_lib_path} -lgmtsar "
                "-L/usr/lib/x86_64-linux-gnu -lgmt -llapack -lblas -lm "
                "-L/usr/local/lib -ltiff -lm -o sbas_parallel"
            )
        else:
            # Fallback: try linking without GMTSAR library (standalone compilation)
            print("Warning: GMTSAR library not found, attempting standalone compilation...")
            link_cmd = (
                f"gcc -fopenmp -m64 -s -Wl,-rpath,/usr/lib/x86_64-linux-gnu "
                f"-z muldefs sbas_parallel.o "
                "-L/usr/lib/x86_64-linux-gnu -lgmt -llapack -lblas -lm "
                "-L/usr/local/lib -ltiff -lm -o sbas_parallel"
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
                    raise RuntimeError(f"Both linking attempts failed. Original: {link_error}, Fallback: {fallback_error}")
            else:
                raise link_error
        
        # Install sbas_parallel to system
        run_command("sudo cp sbas_parallel /usr/local/bin/")
        run_command("sudo chmod +x /usr/local/bin/sbas_parallel")
        
        print("SBAS parallel installed successfully")
        
    except Exception as e:
        print(f"Warning: SBAS parallel installation failed: {e}")
    finally:
        os.chdir(original_dir)


def run_command(cmd, cwd=None):
    """Run shell command with error handling."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        raise RuntimeError(f"Command failed: {cmd}")
    else:
        print(result.stdout)


def install_dependencies():
    """Install required system packages for GMTSAR + GMT."""
    # Fix dpkg configuration first
    run_command("sudo dpkg --configure -a")
    
    pkgs = [
        "csh", "subversion", "autoconf", "libtiff5-dev", "libhdf5-dev", "wget",
        "liblapack-dev", "gfortran", "gfortran-9", "g++", "gcc-9", "libgmt-dev",
        "gmt-dcw", "gmt-gshhg", "gmt", "parallel"
    ]
    run_command(f"sudo apt-get update && sudo apt-get install -y {' '.join(pkgs)}")


def install_orbits(orbits_dir):
    """Download and extract orbit files."""
    url = "http://topex.ucsd.edu/gmtsar/tar/ORBITS.tar"
    tar_path = os.path.join(orbits_dir, "ORBITS.tar")
    run_command(f"wget -O {tar_path} {url}")
    run_command(f"tar -xvf {tar_path}", cwd=orbits_dir)
    run_command(f"rm {tar_path}")


def update_config_mk_for_gfortran9(gmtsar_dir):
    """Update config.mk to use gcc-9 and gfortran-9."""
    config_mk_path = os.path.join(gmtsar_dir, "config.mk")
    
    if os.path.exists(config_mk_path):
        # Read the file
        with open(config_mk_path, 'r') as f:
            lines = f.readlines()
        
        # Update line 31 (index 30) to use gcc-9
        if len(lines) > 30:
            lines[30] = lines[30].replace('gcc', 'gcc-9')
        
        # Also update any gfortran references to gfortran-9
        for i, line in enumerate(lines):
            if 'gfortran' in line and 'gfortran-9' not in line:
                lines[i] = line.replace('gfortran', 'gfortran-9')
        
        # Write the file back
        with open(config_mk_path, 'w') as f:
            f.writelines(lines)
        
        print("Updated config.mk to use gcc-9 and gfortran-9")


def install_gmtsar(install_dir, orbits_dir=None, use_newer_ubuntu=True):
    """Clone, configure, make, and install GMTSAR."""
    gmtsar_dir = os.path.join(install_dir, "GMTSAR")

    if not os.path.exists(gmtsar_dir):
        run_command(f"git clone --branch 6.6 https://github.com/gmtsar/gmtsar {gmtsar_dir}")
        run_command(f"sudo chown -R $USER {gmtsar_dir}")

    original_dir = os.getcwd()
    os.chdir(gmtsar_dir)
    
    try:
        run_command("autoconf")
        run_command("autoupdate")

        # Configure with or without orbits directory
        if orbits_dir:
            if use_newer_ubuntu:
                run_command(f"./configure --with-orbits-dir={orbits_dir} CFLAGS='-z muldefs' LDFLAGS='-z muldefs'")
            else:
                run_command(f"./configure --with-orbits-dir={orbits_dir}")
        else:
            if use_newer_ubuntu:
                run_command(f"./configure CFLAGS='-z muldefs' LDFLAGS='-z muldefs'")
            else:
                run_command(f"./configure")

        # Update config.mk to use gfortran-9 and gcc-9
        update_config_mk_for_gfortran9(gmtsar_dir)

        run_command("make")
        run_command("sudo make install")

        # Install SBAS parallel
        install_sbas_parallel(gmtsar_dir)

        # Configure WSL display if running in WSL
        configure_wsl_display()

        # Add GMTSAR env vars to .bashrc
        bashrc = os.path.expanduser("~/.bashrc")
        with open(bashrc, "a") as f:
            f.write(f"\n# GMTSAR configuration\n")
            f.write(f"export GMTSAR={gmtsar_dir}\n")
            f.write(f"export PATH=$GMTSAR/bin:$PATH\n")
    
    finally:
        os.chdir(original_dir)


def check_gmtsar_installation():
    """
    Check if GMTSAR is properly installed by running gmtsar.csh.
    
    Returns:
        bool: True if GMTSAR is available and working
    """
    try:
        result = subprocess.run(['gmtsar.csh'], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        
        # Check if command succeeded and contains version info
        if result.returncode == 0 and 'GMTSAR version' in result.stdout:
            return True
        else:
            return False
            
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return False


def install_gmtsar_gui():
    """GUI-based GMTSAR installation."""
    # Tkinter GUI
    root = tk.Tk()
    root.withdraw()  # Hide root window

    # Ask for installation directory
    install_dir = filedialog.askdirectory(title="Select installation directory", initialdir="/usr/local")
    if not install_dir:
        messagebox.showinfo("Cancelled", "Installation cancelled.")
        return False

    # Ask user about orbit installation
    install_orbits_flag = messagebox.askyesno("Orbits Installation", "Do you want to download and install orbit files?")
    if install_orbits_flag:
        orbits_dir = os.path.join(install_dir, "orbits")
        os.makedirs(orbits_dir, exist_ok=True)
    else:
        orbits_dir = None  # Skip orbits configuration

    # Confirm
    if orbits_dir:
        proceed = messagebox.askyesno("Confirm", f"Install GMTSAR in:\n{install_dir}\n\nOrbits in:\n{orbits_dir}\n\nProceed?")
    else:
        proceed = messagebox.askyesno("Confirm", f"Install GMTSAR in:\n{install_dir}\n\nSkip orbit files installation\n\nProceed?")
    if not proceed:
        return False

    try:
        install_dependencies()
        if install_orbits_flag:
            install_orbits(orbits_dir)
        install_gmtsar(install_dir, orbits_dir, use_newer_ubuntu=True)
        messagebox.showinfo("Success", "GMTSAR installation completed.\nPlease restart your terminal.")
        return True
    except Exception as e:
        messagebox.showerror("Error", str(e))
        return False


def install_gmtsar_console():
    """Console-based GMTSAR installation."""
    print("\n=== GMTSAR Installation ===")
    
    # Ask for installation directory
    install_dir = input("Enter installation directory (default: /usr/local): ").strip()
    if not install_dir:
        install_dir = "/usr/local"
    
    # Ask user about orbit installation
    install_orbits_choice = input("Download and install orbit files? (y/n): ").lower().strip()
    install_orbits_flag = install_orbits_choice in ['y', 'yes']
    
    if install_orbits_flag:
        orbits_dir = os.path.join(install_dir, "orbits")
        os.makedirs(orbits_dir, exist_ok=True)
    else:
        orbits_dir = None  # Skip orbits configuration
    
    # Confirm
    print(f"\nInstall GMTSAR in: {install_dir}")
    if orbits_dir:
        print(f"Orbits in: {orbits_dir}")
    else:
        print("Skip orbit files installation")
    proceed = input("Proceed? (y/n): ").lower().strip()
    
    if proceed not in ['y', 'yes']:
        print("Installation cancelled.")
        return False
    
    try:
        install_dependencies()
        if install_orbits_flag:
            install_orbits(orbits_dir)
        install_gmtsar(install_dir, orbits_dir, use_newer_ubuntu=True)
        print("GMTSAR installation completed. Please restart your terminal.")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def check_and_install_gmtsar(gui_mode=True):
    """
    Check if GMTSAR is installed and install if needed.
    This function is called by InSARLite on startup.
    
    Args:
        gui_mode: Whether to use GUI dialogs (True) or console (False)
        
    Returns:
        bool: True if GMTSAR is available after check/installation
    """
    # First check if GMTSAR is already installed
    if check_gmtsar_installation():
        print("✅ GMTSAR is available")
        return True
    
    # GMTSAR not found - need to install it
    print("❌ GMTSAR not found")
    
    if gui_mode:
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()  # Hide root window
            
            # Inform user that GMTSAR is required and sudo access is mandatory
            message = ("GMTSAR not found!\n\n"
                      "InSARLite requires GMTSAR to function properly.\n"
                      "GMTSAR installation requires sudo (administrator) access.\n\n"
                      "Would you like to install GMTSAR now?")
            
            install_choice = messagebox.askyesno("GMTSAR Required - Sudo Access Needed", message)
            
            if not install_choice:
                messagebox.showerror("Cannot Proceed", 
                                   "InSARLite cannot function without GMTSAR.\n"
                                   "Please install GMTSAR manually or restart the application.")
                root.destroy()
                return False
            
            # Confirm sudo requirement
            sudo_confirm = messagebox.askyesno(
                "Sudo Access Required",
                "GMTSAR installation requires sudo (administrator) access.\n"
                "You will be prompted for your password during installation.\n\n"
                "Do you have sudo access and wish to proceed?"
            )
            
            if not sudo_confirm:
                messagebox.showinfo("Installation Cancelled", 
                                  "GMTSAR installation cancelled.\n"
                                  "Please contact your system administrator to install GMTSAR.")
                root.destroy()
                return False
            
            root.destroy()
            
            # Proceed with GUI installation
            return install_gmtsar_gui()
            
        except Exception as e:
            print(f"GUI installation failed: {e}")
            # Fall back to console mode
    
    # Console mode installation
    print("\nGMTSAR Installation Required")
    print("=" * 40)
    print("InSARLite requires GMTSAR to function properly.")
    print("GMTSAR installation requires sudo (administrator) access.")
    
    choice = input("Install GMTSAR now? (y/n): ").lower().strip()
    if choice not in ['y', 'yes']:
        print("InSARLite cannot function without GMTSAR.")
        print("Please install GMTSAR manually and restart the application.")
        return False
    
    # Confirm sudo access
    sudo_confirm = input("Do you have sudo access? (y/n): ").lower().strip()
    if sudo_confirm not in ['y', 'yes']:
        print("GMTSAR installation requires sudo access.")
        print("Please contact your system administrator to install GMTSAR.")
        return False
    
    return install_gmtsar_console()


if __name__ == "__main__":
    """Test the GMTSAR installer."""
    print("=== GMTSAR Installation Test ===")
    
    # Check current status
    if check_gmtsar_installation():
        print("✅ GMTSAR is already installed and working")
    else:
        print("❌ GMTSAR not found")
        
        # Test the installation workflow
        success = check_and_install_gmtsar(gui_mode=False)
        print(f"Installation result: {success}")
