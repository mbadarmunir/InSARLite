import os
import subprocess

import threading

import concurrent.futures

lock = threading.Lock()

def process_key(key, paths, dem,  method, mode=None):
    dir_path = paths.get(key)
    
    if dir_path and os.path.exists(dir_path):
        praw = os.path.join(dir_path, "raw")
        # btable = os.path.join(dir_path, "baseline_table.dat")
        prm_files = [f for f in os.listdir(praw) if f.endswith(".PRM")]
        led_files = [f for f in os.listdir(praw) if f.endswith(".LED")]
        tif_files = [f for f in os.listdir(praw) if f.endswith(".tiff")]
        if praw and os.path.exists(praw) and not (prm_files and led_files and tif_files and len(prm_files) == len(led_files) == len(tif_files)):
            with lock:                
                print(f"Generating baselines for {key}...")
            # DELETED btable not existance check from here.
            print(f'{method} data.in {dem} 1 {mode}'.strip())
            if method == "esd":
                comm = "preproc_batch_tops_esd.csh"
            else:
                comm = "preproc_batch_tops.csh"

            subprocess.call(f'{comm} data.in {dem} 1 {mode}'.strip(), shell=True, cwd=praw)
            subprocess.call('mv baseline_table.dat ../', shell=True, cwd=praw)

def preprocess(paths, dem, method, mode=None):
    keys = ["pF1", "pF2", "pF3"]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_key, key, paths, dem, method, mode) for key in keys]
        concurrent.futures.wait(futures)