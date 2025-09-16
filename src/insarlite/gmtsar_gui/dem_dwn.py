import os
import sys
import subprocess
from ..utils.utils import run_command

def make_dem(west, east, south, north, outdir, mode=1):
    """
    Script to create DEM for GMTSAR, relative to WGS84 ellipsoid.

    Parameters:
    west, east, south, north: float
        Geographic boundaries of the region.
    mode: int, optional
        DEM mode. 1 for SRTM-1s, 2 for SRTM-3s.
    sharedir: str
        Directory to store intermediate and final files.
    """
    print("\nSTART: DEM Downloading\n")
    # Get GMTSAR shared directory
    try:
        sharedir = subprocess.check_output(["gmtsar_sharedir.csh"], text=True).strip()
    except subprocess.CalledProcessError as e:
        print(f"[ERROR]: Failed to get GMTSAR shared directory. {e}")
        sys.exit(1)    

    # File paths
    dem_ortho = os.path.join(outdir, "dem_ortho.grd")
    geoid_resamp = os.path.join(outdir, "geoid_resamp.grd")
    dem_final = os.path.join(outdir, "dem.grd")
    geoid_file = os.path.join(sharedir, "geoid_egm96_icgem.grd")

    # Get region in GMT format
    region = f"-R{west}/{east}/{south}/{north}"

    # Get SRTM data based on mode
    try:
        if mode == 1:
            run_command(f"gmt grdcut @earth_relief_01s {region} -G{dem_ortho}")
        elif mode == 2:
            run_command(f"gmt grdcut @earth_relief_03s {region} -G{dem_ortho}")
    except Exception as e:
        print(f"[ERROR]: Failed to download SRTM data. {e}")
        sys.exit(1)

    # Resample and remove geoid
    try:
        run_command(f"gmt grdsample {geoid_file} -R{dem_ortho} -G{geoid_resamp} -Vq")
        run_command(f"gmt grdmath -Vq {dem_ortho} {geoid_resamp} ADD = {dem_final}")
    except Exception as e:
        print(f"[ERROR]: Failed to process geoid or DEM. {e}")
        sys.exit(1)

    # Clean up intermediate file
    try:
        os.remove(geoid_resamp)
    except OSError as e:
        print(f"[WARNING]: Failed to delete temporary file. {e}")

    print(f"\ncreated {dem_final}, heights relative to WGS84 ellipsoid")
    print("\nEND: DEM Downloading\n")
