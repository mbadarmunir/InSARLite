import os
import subprocess
from utils.utils import update_console
import threading

import concurrent.futures

lock = threading.Lock()

def process_key(key, paths, console_text, log_file_path):
    dir_path = paths.get(key)
    if dir_path and os.path.exists(dir_path):
        praw = os.path.join(dir_path, "raw")
        btable = os.path.join(dir_path, "baseline_table.dat")
        if praw and os.path.exists(praw):
            with lock:                
                update_console(console_text, f"Generating baselines for {key}...", log_file_path)
            if not os.path.exists(btable):
                subprocess.call('preproc_batch_tops.csh data.in dem.grd 1', shell=True, cwd=praw)
                subprocess.call('mv baseline_table.dat ../', shell=True, cwd=praw)

def preprocess(paths, console_text, log_file_path):
    keys = ["pF1", "pF2", "pF3"]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_key, key, paths, console_text, log_file_path) for key in keys]
        concurrent.futures.wait(futures)