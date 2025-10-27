import os
import subprocess
import threading
from ..utils.utils import check_align_completion, process_logger
from ..gmtsar_gui.pair_generation import remove_unconnected_images
from concurrent.futures import ThreadPoolExecutor



def align_sec_imgs(paths, mst, dem, alignmode, esd_mode):
    lock = threading.Lock()

    def process_key(key):
        dir_path = paths.get(key)
        # Map subswath key to process number
        subswath_map = {"pF1": "2.1.1", "pF2": "2.1.2", "pF3": "2.1.3"}
        process_num = subswath_map.get(key, "2.1.x")
        process_logger(process_num=process_num, log_file=paths.get("log_file_path"), message=f"Starting alignment for subswath {key} (process {process_num})...", mode="start")
        aligncommand = None
        if alignmode == "esd":
            aligncommand = "preproc_batch_tops_esd.csh"
        elif alignmode == "no_esd":
            aligncommand = "preproc_batch_tops.csh"
            
        if dir_path and os.path.exists(dir_path):
            praw = os.path.join(dir_path, "raw")
            # os.chdir(praw)
            if not check_align_completion(dir_path):

                dind = os.path.join(praw, "data.in")
                ind = os.path.join(dir_path, "intf.in")
                if os.path.exists(dind):
                    with open(dind, 'r') as f:
                        lines = f.readlines()
                    lines.insert(0, lines.pop(lines.index(list(filter(lambda x: mst in x, lines))[0])))
                    with open(dind, 'w') as f:
                        for line in lines:
                            f.write(line)
                    remove_unconnected_images(ind, dind)
                    
                    with lock:                        
                        print(f"Starting alignment for {key}...")
                        print(f'{aligncommand} data.in {dem} 2 {esd_mode}'.strip())

                        if not any(f.endswith('.SLC') for f in os.listdir(praw)):      

                            subprocess.call(f'{aligncommand} data.in {dem} 2 {esd_mode}'.strip(), shell=True, cwd=praw)
                        else:
                            print(f"Skipping alignment for {key} as imgs seem to be already aligned.")
                        process_logger(process_num=process_num, log_file=paths.get("log_file_path"), message=f"Starting alignment for subswath {key} (process {process_num})...", mode="end")

    keys = ["pF1", "pF2", "pF3"]
    with ThreadPoolExecutor() as executor:
        executor.map(process_key, keys)