import os
import shutil
import subprocess
from utils.utils import update_console

def gen_pairs(paths, parallel_baseline, perpendicular_baseline, console_text, log_file_path):
    for key in ["pF1", "pF2", "pF3"]:
        dir_path = paths.get(key)                  
        if dir_path and os.path.exists(dir_path):     
            ind = os.path.join(dir_path, "intf.in")
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