import os
import subprocess
from utils.utils import update_console

def preprocess(paths, console_text, log_file_path):        
    for key in ["pF1", "pF2", "pF3"]:
        dir_path = paths.get(key)   
        if dir_path and os.path.exists(dir_path):
            praw = os.path.join(dir_path, "raw")
            btable = os.path.join(dir_path, "baseline_table.dat")         
            if praw and os.path.exists(praw):
                os.chdir(praw)                
                update_console(console_text, f"Generating baselines for {key}...", log_file_path)
                if not os.path.exists(btable):
                    subprocess.call('preproc_batch_tops.csh data.in dem.grd 1', shell=True)
                    subprocess.call('mv baseline_table.dat ../', shell=True)