import os
import re
import requests
import time
from requests.exceptions import ConnectionError, Timeout
from datetime import datetime, timedelta
from ..utils.utils import read_file_lines, load_config, save_config, create_symlink
import keyring
import getpass
import tkinter as tk
from tkinter import simpledialog

# Set local directory that stores S1A and S1B orbits
# orb_dir = "/geosat2/InSAR_Processing/Sentinel_Orbits"
url_root = "https://s1qc.asf.alaska.edu/aux_poeorb/"
data_in_file = "data.in"

# Earthdata credentials (replace with your own credentials)
# EARTHDATA_USERNAME = "MBadar"
# EARTHDATA_PASSWORD = "NSFSt3120"

SERVICE_NAME = "EarthdataCredentials"

def get_earthdata_credentials():
    username = keyring.get_password(SERVICE_NAME, "username")
    password = keyring.get_password(SERVICE_NAME, "password")
    if username is None or password is None:
        # Pop up a dialog box to get credentials
        root = tk.Tk()
        root.withdraw()
        username = simpledialog.askstring("Earthdata Login", "Enter your Earthdata username:", parent=root)
        password = simpledialog.askstring("Earthdata Login", "Enter your Earthdata password:", show='*', parent=root)
        root.destroy()
        if username and password:
            keyring.set_password(SERVICE_NAME, "username", username)
            keyring.set_password(SERVICE_NAME, "password", password)
        else:
            raise Exception("Earthdata credentials are required.")
    return username, password

EARTHDATA_USERNAME, EARTHDATA_PASSWORD = get_earthdata_credentials()

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


def download_or_copy_orbit(user_datadir, orb, d):
    """
    Download or copy the orbit file if not available locally using two-step authentication.
    """
    local_orbit_path = os.path.join(user_datadir, orb)    
    if not os.path.exists(local_orbit_path):    
        download_url = url_root + orb
        print(f"Attempting to download {download_url}")

        # Two-step authentication with requests.Session
        with requests.Session() as session:
            session.auth = (EARTHDATA_USERNAME, EARTHDATA_PASSWORD)

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    # Initial request to get redirection URL
                    r1 = session.get(download_url, timeout=10)
                    if r1.status_code == 404:
                        print(f"File not found at {download_url}. Skipping this file.")
                        return  # Exit the function since file doesn't exist

                    # Check for authentication
                    if r1.status_code == 401:
                        print("Authentication required. Redirecting to login...")

                    # Follow the redirection URL and authenticate
                    r2 = session.get(r1.url, auth=(EARTHDATA_USERNAME, EARTHDATA_PASSWORD), timeout=10)

                    # Verify if the download was successful
                    if r2.ok:
                        with open(local_orbit_path, 'wb') as f:
                            f.write(r2.content)
                        create_symlink(local_orbit_path, os.path.join(d, os.path.basename(local_orbit_path)))
                        print(f"Downloaded {orb} successfully.")

                        return  # Exit after a successful download
                    else:
                        print(f"Failed to download {download_url}, status code: {r2.status_code}")
                        break  # Exit loop if status code is not OK and retry won't help

                except (ConnectionError, Timeout) as e:
                    print(
                        f"Attempt {attempt} of {MAX_RETRIES}: Connection issue: {e}. Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)

            # If all retries failed, print an error message
            print(f"Failed to download {orb} after {MAX_RETRIES} attempts due to connection issues.")
    elif os.path.exists(local_orbit_path) and not os.path.exists(os.path.join(d, os.path.basename(local_orbit_path))):
            create_symlink(local_orbit_path, os.path.join(d, os.path.basename(local_orbit_path)))


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
                        download_or_copy_orbit(user_datadir, orb, d)                
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
                download_or_copy_orbit(user_datadir, orb, d)                
                with open(data_in_file, 'a') as f:
                    f.write(f"{rec}:{orb}\n")

            # Clean up
            os.remove('text.dat')
    os.remove(porbits_list)
    sort_file_lines('data.in')    