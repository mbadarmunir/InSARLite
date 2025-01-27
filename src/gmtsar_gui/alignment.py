import os
import subprocess
from utils.utils import update_console

def align_sec_imgs(paths, mst, console_text, log_file_path):
    for key in ["pF1", "pF2", "pF3"]:
        dir_path = paths.get(key)                  
        if dir_path and os.path.exists(dir_path):            
            praw = os.path.join(dir_path, "raw")
            os.chdir(praw)
            dind = os.path.join(praw, "data.in")
            if os.path.exists(dind):                 
                with open(dind, 'r') as f:
                    lines = f.readlines()
                lines.insert(0, lines.pop(lines.index(list(filter(lambda x: mst in x, lines))[0])))
                with open(dind, 'w') as f:
                    for line in lines:
                        f.write(line)                
                
                update_console(console_text, f"Starting alignment for {key}...", log_file_path)
                
                if not any(f.endswith('.SLC') for f in os.listdir('.')):                        
                    subprocess.call('preproc_batch_tops.csh data.in dem.grd 2', shell=True)  