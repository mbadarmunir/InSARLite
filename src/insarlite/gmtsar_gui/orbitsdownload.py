import os
import re
import requests
import time
from requests.exceptions import ConnectionError, Timeout
from datetime import datetime, timedelta
from ..utils.utils import read_file_lines, create_symlink
from ..utils.earthdata_auth import get_earthdata_session, ensure_earthdata_auth

# Set local directory that stores S1A and S1B orbits
# orb_dir = "/geosat2/InSAR_Processing/Sentinel_Orbits"
url_root = "https://s1qc.asf.alaska.edu/aux_poeorb/"
data_in_file = "data.in"

def sort_file_lines(input_file, output_file=None):
    """Sort lines of a text file alphabetically."""
    with open(input_file, 'r') as f:
        lines = f.readlines()

    # Sort the lines alphabetically
    sorted_lines = sorted(lines)

    # If no output file is provided, overwrite the input file
    if output_file is None:
        output_file = input_file

    # Write the sorted lines to the output file
    with open(output_file, 'w') as f:
        f.writelines(sorted_lines)

    print(f"Lines sorted and saved to {output_file}")

def get_orbits_list(porbit_file):
    """
    Download the list of orbits if not present, and store in orbits.list.
    """
    url_root = "https://s1qc.asf.alaska.edu/aux_poeorb/"
    if not os.path.exists(porbit_file):
        response = requests.get(url_root)        
        orbit_files = re.findall(r'href="(S1[AB]_OPER_AUX_POEORB_OPOD_.*?\.EOF)"', response.text)        
        with open(porbit_file, 'w') as f:
            for orbit in orbit_files:
                f.write(orbit + '\n')


# Constants for the retry mechanism
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def download_or_copy_orbit(user_datadir, orb, proc_dir):
    """
    Download or copy the orbit file if not available locally using unified EarthData authentication.
    Creates symlinks in ALL F*/raw directories (F1/raw, F2/raw, F3/raw) where processing happens.
    
    Args:
        user_datadir: Directory where orbit files are stored (e.g., /project/data)
        orb: Orbit filename (e.g., S1A_OPER_AUX_POEORB_*.EOF)
        proc_dir: Processing directory (e.g., /project/asc or /project/des)
    """
    local_orbit_path = os.path.join(user_datadir, orb)
    
    # Download orbit file if it doesn't exist
    if not os.path.exists(local_orbit_path):    
        download_url = url_root + orb
        print(f"Attempting to download {download_url}")

        # Ensure EarthData authentication
        if not ensure_earthdata_auth():
            raise Exception("Could not authenticate with EarthData")
        
        # Get authenticated session
        session = get_earthdata_session()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                # Download using authenticated session
                print(f"Attempt {attempt}/{MAX_RETRIES}: Downloading {orb}")
                response = session.get(download_url, timeout=30, stream=True)
                
                if response.status_code == 404:
                    print(f"File not found at {download_url}. Skipping this file.")
                    return  # Exit the function since file doesn't exist
                
                if response.status_code == 200:
                    # Write the file
                    with open(local_orbit_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    print(f"✓ Successfully downloaded {orb}")
                    break  # Exit retry loop on success
                else:
                    print(f"⚠ Download failed with status code: {response.status_code}")
                    
            except (ConnectionError, Timeout) as e:
                print(f"❌ Attempt {attempt} failed: {e}")
                if attempt < MAX_RETRIES:
                    print(f"Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"❌ Failed to download {orb} after {MAX_RETRIES} attempts")
                    raise e
            except Exception as e:
                print(f"❌ Unexpected error downloading {orb}: {e}")
                raise e
    else:
        print(f"✓ Orbit file {orb} already exists locally")
    
    # 🛰️ CRITICAL: Create symlinks in ALL F*/raw directories where GMTSAR processing happens
    # This ensures orbit files are accessible regardless of which subswath is being processed
    f_dirs = [os.path.join(proc_dir, f"F{i}/raw") for i in [1, 2, 3]]
    symlinks_created = 0
    
    for f_dir in f_dirs:
        if os.path.exists(f_dir):
            target_path = os.path.join(f_dir, os.path.basename(local_orbit_path))
            if not os.path.exists(target_path):
                try:
                    create_symlink(local_orbit_path, target_path)
                    symlinks_created += 1
                except Exception as e:
                    print(f"⚠️  Failed to create symlink in {f_dir}: {e}")
    
    if symlinks_created > 0:
        print(f"✓ Created {symlinks_created} orbit symlink(s) in F*/raw directories")


def process_files(user_datadir, proc_dir):
    """
    Main function to process the XML files, prepare data.in, and download/copy orbit files as needed.
    """    
    
    porbits_list = os.path.join(user_datadir, "orbits.list") 

    d1, d2, d3 = os.path.join(proc_dir, "F1/raw"), os.path.join(proc_dir, "F2/raw"), os.path.join(proc_dir, "F3/raw")   

    for d in [d1, d2, d3]:
        if os.path.exists(d):
            os.chdir(d)
            if os.path.exists('data.in'):
                os.remove("data.in")

            # List all XML files and store in text.dat
            xml_files = [f for f in os.listdir() if f.endswith('.xml')]
            with open('text.dat', 'w') as f:
                for xml_file in xml_files:
                    f.write(xml_file + '\n')

            text_dat_lines = read_file_lines('text.dat')

            # Set mstem and mname based on the first line of text.dat
            mstem = text_dat_lines[0][15:23]  # Extract YYYYMMDD
            mname = text_dat_lines[0][:64]  # Extract name
            rec = None

            # Ensure orbit list is downloaded
            get_orbits_list(porbits_list)

            orbits_list = read_file_lines(porbits_list)

            for line in text_dat_lines:
                stem = line[15:23]  # Extract YYYYMMDD
                name = line[:64]  # Extract name

                if stem != mstem:
                    # Calculate n1 (previous day) and n2 (next day)
                    n1 = (datetime.strptime(mstem, "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")
                    n2 = (datetime.strptime(mstem, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
                    satellite = mname[:3].upper()  # Extract S1A or S1B

                    # Find orbit file matching satellite and dates
                    orb = None
                    for orbit_line in orbits_list:
                        if satellite in orbit_line and n1 in orbit_line and n2 in orbit_line:
                            orb = orbit_line.strip()
                            break

                    if orb:                
                        download_or_copy_orbit(user_datadir, orb, proc_dir)                
                        with open(data_in_file, 'a') as f:
                            f.write(f"{rec}:{orb}\n")
                    else:
                        print(f"No matching orbit file found for {mstem}")

                    rec = name
                    mstem = stem
                    mname = name
                else:
                    if rec is None:
                        rec = name
                    else:
                        rec = f"{rec}:{name}"

            # Process last record
            n1 = (datetime.strptime(mstem, "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")
            n2 = (datetime.strptime(mstem, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
            satellite = mname[:3].upper()  # Extract S1A or S1B

            orb = None
            for orbit_line in orbits_list:
                if satellite in orbit_line and n1 in orbit_line and n2 in orbit_line:
                    orb = orbit_line.strip()
                    break

            if orb:
                download_or_copy_orbit(user_datadir, orb, proc_dir)                
                with open(data_in_file, 'a') as f:
                    f.write(f"{rec}:{orb}\n")

            # Clean up
            os.remove('text.dat')
    os.remove(porbits_list)
    sort_file_lines('data.in')    
