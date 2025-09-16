import os
import shutil
import subprocess
from ..utils.utils import update_console
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
            # Remove IMGs from data.in file(s) who are not connected in final network                
            dind_old = dind + '.old'
            shutil.copy(dind, dind_old)
            
            with open(dind_old, 'r') as f_old, open(dind, 'w') as f_new:
                for line in f_old:
                    date_str = line[15:23]
                    if date_str in unique_integers:
                        f_new.write(line)                

            print(
                "Image epochs not connected to the network are removed from data.in file(s) "
                "so that they are not aligned in next step to save time"
            )
        else:
            print(
                "All image epochs are connected in the network and will be aligned in next step"            
            )
            
def gen_pairs(paths, parallel_baseline, perpendicular_baseline, console_text, log_file_path):
    for key in ["pF1", "pF2", "pF3"]:
        dir_path = paths.get(key)                  
        if dir_path and os.path.exists(dir_path):     
            ind = os.path.join(dir_path, "intf.in")
            dind = os.path.join(dir_path, "raw", "data.in")
            if not os.path.exists(ind):
                os.chdir(dir_path)
                update_console(console_text, f"Starting IFGs pairs selection {key}...", log_file_path)
                subprocess.call('select_pairs.csh baseline_table.dat {} {}'.format(parallel_baseline, perpendicular_baseline), shell=True)
                
                # Copy the generated intf.in file to other paths
                for other_key in ["pF1", "pF2", "pF3"]:
                    if other_key != key:
                        other_dir_path = paths.get(other_key)
                        
                        if other_dir_path and os.path.exists(other_dir_path):
                            other_ind = os.path.join(other_dir_path, "intf.in")
                            if not os.path.exists(other_ind):
                                shutil.copy(ind, other_ind)
                                with open(other_ind, 'r') as f:
                                    lines = f.readlines()
                                with open(other_ind, 'w') as f:
                                    for line in lines:
                                        f.write(line.replace(f'F{key[-1]}', f'F{other_key[-1]}'))

            remove_unconnected_images(ind, dind)