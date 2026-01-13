import os
import shutil
import subprocess
import sys
import tkinter as tk

def remove_unconnected_images(ind, dind):
    # Open the ind file and read it line by line
    unique_integers = set()            
    with open(ind, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('_')
            parts = [parts[1], parts[4]]                    
            if len(parts) == 2:
                unique_integers.update(parts)

    # Check if the number of unique integers matches the number of rows in dind
    with open(dind, 'r') as f:
        nrows = sum(1 for _ in f)
    if len(unique_integers) == 0:
        print("No pairs found.")
        for widget in tk._default_root.children.values():
            try:
                widget.destroy()
            except Exception:
                pass
        sys.exit()
        return
    else:
        if len(unique_integers) != nrows:
            # Get list of disconnected dates before removing from data.in
            disconnected_dates = set()
            with open(dind, 'r') as f:
                for line in f:
                    # Extract date from data.in format: s1a-iw2-slc-vv-YYYYMMDDtHHMMSS...
                    # Date is at position 15-23 (YYYYMMDD)
                    if len(line) >= 23:
                        date_str = line[15:23]
                        if date_str not in unique_integers:
                            disconnected_dates.add(date_str)
            
            # Remove IMGs from data.in file(s) who are not connected in final network                
            dind_old = dind + '.old'
            shutil.copy(dind, dind_old)
            
            with open(dind_old, 'r') as f_old, open(dind, 'w') as f_new:
                for line in f_old:
                    # Extract date from data.in format: s1a-iw2-slc-vv-YYYYMMDDtHHMMSS...
                    if len(line) >= 23:
                        date_str = line[15:23]
                        if date_str in unique_integers:
                            f_new.write(line)
            
            # Remove symlinks/files for disconnected images from both pdata and pfraw
            # Get the data directory (parent of raw directory)
            raw_dir = os.path.dirname(dind)
            data_dir = os.path.join(os.path.dirname(raw_dir), "data")
            
            removed_pdata_count = 0
            removed_pfraw_count = 0
            
            # 1. Remove .SAFE symlinks from pdata (project/asc/data/)
            if os.path.exists(data_dir):
                for safe_dir in os.listdir(data_dir):
                    if safe_dir.endswith(".SAFE"):
                        # Extract date from SAFE directory name (position 17:25 is YYYYMMDD)
                        if len(safe_dir) >= 25:
                            safe_date = safe_dir[17:25]
                            if safe_date in disconnected_dates:
                                safe_path = os.path.join(data_dir, safe_dir)
                                # Check if it's a symlink and remove it (don't touch real directories)
                                if os.path.islink(safe_path):
                                    os.unlink(safe_path)
                                    removed_pdata_count += 1
                                    print(f"  Removed unconnected .SAFE symlink from pdata: {safe_dir}")
                                elif os.path.isdir(safe_path):
                                    # It's a real directory, not a symlink - leave it alone (user's source data)
                                    print(f"  ⚠️  Found unconnected directory (not removed - may be user source data): {safe_dir}")
            
            # 2. Remove XML/TIFF symlinks from pfraw (project/asc/F*/raw/)
            # The raw_dir we have is for one subswath, but we need to clean all F1/F2/F3
            project_asc_dir = os.path.dirname(raw_dir)  # project/asc/F*
            parent_dir = os.path.dirname(project_asc_dir)  # project/asc
            
            for subswath in ["F1", "F2", "F3"]:
                subswath_raw = os.path.join(parent_dir, subswath, "raw")
                if os.path.exists(subswath_raw):
                    # List all files in raw directory
                    for filename in os.listdir(subswath_raw):
                        # Check if file matches unconnected date pattern
                        # Files are like: s1a-iw1-slc-vv-20230829t...-001.xml or .tiff
                        file_lower = filename.lower()
                        if file_lower.endswith(('.xml', '.tiff', '.tif')):
                            # Try to extract date from filename
                            # Format: ...YYYYMMDDTHHMMSS...
                            for disconnected_date in disconnected_dates:
                                if disconnected_date in filename:
                                    file_path = os.path.join(subswath_raw, filename)
                                    # Only remove symlinks, not real files
                                    if os.path.islink(file_path):
                                        os.unlink(file_path)
                                        removed_pfraw_count += 1
                                    break
            
            if removed_pdata_count > 0 or removed_pfraw_count > 0:
                print(f"✅ Removed {removed_pdata_count} .SAFE symlink(s) from pdata and {removed_pfraw_count} XML/TIFF symlink(s) from pfraw")

            print(
                f"Image epochs not connected to the network are removed from data.in file(s) "
                f"so that they are not aligned in next step to save time. "
                f"Removed {len(disconnected_dates)} unconnected image(s)."
            )
            return disconnected_dates
        else:
            print(
                "All image epochs are connected in the network and will be aligned in next step"            
            )
            return set()
            
def gen_pairs(paths, parallel_baseline, perpendicular_baseline, console_text, log_file_path):
    # Generate intf.in for the first valid subswath, then copy to others
    primary_key = None
    primary_dir = None
    
    # Find the first valid subswath
    for key in ["pF1", "pF2", "pF3"]:
        dir_path = paths.get(key)
        if dir_path and os.path.exists(dir_path):
            primary_key = key
            primary_dir = dir_path
            break
    
    if not primary_key:
        print("No valid subswath directories found for pair generation")
        return
    
    # Generate intf.in for primary subswath (always regenerate, don't check if exists)
    ind = os.path.join(primary_dir, "intf.in")
    dind = os.path.join(primary_dir, "raw", "data.in")
    
    os.chdir(primary_dir)
    print(f"Generating IFGs pairs for {primary_key}...")
    subprocess.call('select_pairs.csh baseline_table.dat {} {}'.format(parallel_baseline, perpendicular_baseline), shell=True)
    print(f"✅ Generated intf.in for {primary_key}")
    
    # Copy the generated intf.in file to other subswaths
    for other_key in ["pF1", "pF2", "pF3"]:
        if other_key != primary_key:
            other_dir_path = paths.get(other_key)
            
            if other_dir_path and os.path.exists(other_dir_path):
                other_ind = os.path.join(other_dir_path, "intf.in")
                # Copy the file
                shutil.copy(ind, other_ind)
                # Always modify subswath references after copying
                with open(other_ind, 'r') as f:
                    lines = f.readlines()
                with open(other_ind, 'w') as f:
                    for line in lines:
                        # Replace _ALL_F1 with _ALL_F2, etc.
                        modified_line = line.replace(f'_ALL_F{primary_key[-1]}', f'_ALL_F{other_key[-1]}')
                        f.write(modified_line)
                print(f"  Copied and modified intf.in: F{primary_key[-1]} -> F{other_key[-1]}")
    
    # Remove unconnected images from data.in for all subswaths
    for key in ["pF1", "pF2", "pF3"]:
        dir_path = paths.get(key)
        if dir_path and os.path.exists(dir_path):
            ind = os.path.join(dir_path, "intf.in")
            dind = os.path.join(dir_path, "raw", "data.in")
            if os.path.exists(ind) and os.path.exists(dind):
                remove_unconnected_images(ind, dind)