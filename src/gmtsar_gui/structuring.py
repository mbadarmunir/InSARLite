import os
import shutil
import subprocess
from utils.utils import update_console, create_symlink

"""
This script is used to create a directory structure and copy files appropriately based on user inputs.

Functions:
    create_directory_structure(base_path, structure):
        Creates the directory structure as specified in the 'structure' dictionary starting from 'base_path'.

    copy_files(source_dir, dest_dir, file_list):
        Copies the specified files from 'source_dir' to 'dest_dir'.

    main():
        Main function to handle user inputs and orchestrate the creation of directory structure and file copying.

Usage:
    Run this script and follow the prompts to specify the directory structure and files to be copied.
"""

def create_directory_structure(base_path, structure):
    """
    Creates the directory structure as specified in the 'structure' dictionary starting from 'base_path'.
    
    Parameters:
        base_path (str): The base path where the directory structure will be created.
        structure (dict): A dictionary representing the directory structure.
    """
    for key, value in structure.items():
        dir_path = os.path.join(base_path, key)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        if isinstance(value, dict):
            create_directory_structure(dir_path, value)

def copy_files(source_dir, dest_dir, file_list):
    """
    Copies the specified files from 'source_dir' to 'dest_dir'.
    
    Parameters:
        source_dir (str): The directory to copy files from.
        dest_dir (str): The directory to copy files to.
        file_list (list): A list of filenames to be copied.
    """
    for file_name in file_list:
        src_file = os.path.join(source_dir, file_name)
        dest_file = os.path.join(dest_dir, file_name)
        if os.path.isfile(src_file):
            shutil.copy2(src_file, dest_file)

def generate_structure(project_name, node, subswath_option):
    node_prefix = node[:3].lower()
    structure = {
        project_name: {
            node_prefix: {
                "data": {},
                "F1": {
                    "raw": {},
                    "topo": {}
                },
                "F2": {
                    "raw": {},
                    "topo": {}
                },
                "F3": {
                    "raw": {},
                    "topo": {}
                },
                "merge": {},
                "reframed": {},
                "SBAS": {},
                "topo": {}
            }
        }            
    }

    if subswath_option == "First and second subswaths only":
        del structure[project_name][node_prefix]["F3"]
    elif subswath_option == "Second and third subswaths only":
        del structure[project_name][node_prefix]["F1"]
    elif subswath_option == "First subswath only":
        del structure[project_name][node_prefix]["F2"]
        del structure[project_name][node_prefix]["F3"]
        del structure[project_name][node_prefix]["merge"]
    elif subswath_option == "Second subswath only":
        del structure[project_name][node_prefix]["F1"]
        del structure[project_name][node_prefix]["F3"]
        del structure[project_name][node_prefix]["merge"]
    elif subswath_option == "Third subswath only":
        del structure[project_name][node_prefix]["F1"]
        del structure[project_name][node_prefix]["F2"]
        del structure[project_name][node_prefix]["merge"]

    return structure

def generate_paths(output_dir, project_name, node, subswath_option):
    node_prefix = node[:3].lower()
    base_path = os.path.join(output_dir, project_name, node_prefix)
    
    paths = {
        "pdata": os.path.join(base_path, "data"),
        "pF1": os.path.join(base_path, "F1"),
        "pF1raw": os.path.join(base_path, "F1", "raw"),
        "pF1topo": os.path.join(base_path, "F1", "topo"),
        "pF2": os.path.join(base_path, "F2"),
        "pF2raw": os.path.join(base_path, "F2", "raw"),
        "pF2topo": os.path.join(base_path, "F2", "topo"),
        "pF3": os.path.join(base_path, "F3"),
        "pF3raw": os.path.join(base_path, "F3", "raw"),
        "pF3topo": os.path.join(base_path, "F3", "topo"),
        "pmerge": os.path.join(base_path, "merge"),
        "pref": os.path.join(base_path, "reframed"),
        "psbas": os.path.join(base_path, "SBAS"),
        "ptopo": os.path.join(base_path, "topo")
    }

    # Remove paths that are not in the structure
    structure = generate_structure(project_name, node, subswath_option)
    valid_keys = set(structure[project_name][node_prefix].keys())
    for key in ["F1", "F2", "F3"]:
        if key not in valid_keys:
            paths = {k: v for k, v in paths.items() if key not in k}
    return paths

def orchestrate_structure_and_copy(output_dir, project_name, node, subswath_option, dem_file, pin_file, in_data_dir, btconfig, console_text, log_file_path):
        
    # Generate and create the directory structure for the project and get the paths to be used later
    structure = generate_structure(project_name, node, subswath_option)
    create_directory_structure(output_dir, structure)
    paths = generate_paths(output_dir, project_name, node, subswath_option)
    pref = paths.get("pref")
    ptopo = paths.get("ptopo")
    pmerge = paths.get("pmerge")
    
    if pmerge and os.path.exists(pmerge) and os.path.isdir(pmerge):
        create_symlink(dem_file, os.path.join(pmerge, os.path.basename(dem_file)))
        shutil.copy(btconfig, pmerge)       

    create_symlink(dem_file, os.path.join(ptopo, os.path.basename(dem_file)))
    create_symlink(pin_file, os.path.join(pref, os.path.basename(pin_file)))
    pdata = paths.get("pdata")
    if pdata:
        [create_symlink(os.path.join(in_data_dir, sd), pdata) for sd in os.listdir(in_data_dir) if sd.endswith('.SAFE')]
    
    for key in ["pF1", "pF2", "pF3"]:
        dir_path = paths.get(key)
        if dir_path and os.path.exists(dir_path):
            shutil.copy(btconfig, dir_path)            
            create_symlink(dem_file, os.path.join(dir_path, "topo", os.path.basename(dem_file)))
            create_symlink(dem_file, os.path.join(dir_path, "raw", os.path.basename(dem_file)))
            subprocess.call(f'ln -s {os.path.join(os.path.dirname(dir_path), "data")}/*.SAFE/*/*iw{key[-1]}*vv*xml {os.path.join(dir_path, "raw")}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)    
            subprocess.call(f'ln -s {os.path.join(os.path.dirname(dir_path), "data")}/*.SAFE/*/*iw{key[-1]}*vv*tiff {os.path.join(dir_path, "raw")}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if console_text and log_file_path:
        update_console(console_text, "Copied files and created symlinks as required", log_file_path)
    else:
        print("Copied files and created symlinks as required")
    return paths, structure  

def main(output_dir, project_name, node, subswath_option, dem_file, pin_file, in_data_dir, btconfig, console_text=None, log_file_path=None):
    """
    Main function to handle user inputs and orchestrate the creation of directory structure and file copying.
    """
    paths, structure = orchestrate_structure_and_copy(output_dir, project_name, node, subswath_option, dem_file, pin_file, in_data_dir, btconfig, console_text, log_file_path)
    return paths, structure  

if __name__ == "__main__":
    main()