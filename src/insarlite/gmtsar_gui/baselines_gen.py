import os
import subprocess
import shutil
import datetime
import threading
import concurrent.futures

lock = threading.Lock()

def backup_slc_files_if_needed(praw, force_realign=False):
    """Backup existing SLC files to 'previous_aligned' folder before any processing that might overwrite them.
    
    Args:
        praw: Path to raw directory
        force_realign: Whether to force backup even if SLC files match expected count
    
    Returns:
        bool: True if backup was created, False otherwise
    """
    if not os.path.exists(praw):
        return False
    
    slc_files = [f for f in os.listdir(praw) if f.endswith('.SLC')]
    
    if len(slc_files) == 0:
        return False  # No SLC files to backup
    
    # Check if backup is needed
    data_in_path = os.path.join(praw, "data.in")
    if not force_realign and os.path.exists(data_in_path):
        with open(data_in_path, 'r') as f:
            data_in_count = sum(1 for line in f if line.strip())
        
        # If SLC files match data.in count and we're not forcing realignment, no backup needed
        if len(slc_files) == data_in_count:
            return False
    
    # Create backup directory with timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(praw, f"previous_aligned_{timestamp}")
    
    try:
        os.makedirs(backup_dir)
        
        # Move SLC files to backup
        backed_up_count = 0
        for slc_file in slc_files:
            src = os.path.join(praw, slc_file)
            dst = os.path.join(backup_dir, slc_file)
            try:
                shutil.move(src, dst)
                backed_up_count += 1
            except Exception as e:
                print(f"Warning: Could not backup {slc_file}: {e}")
        
        if backed_up_count > 0:
            print(f"🔒 Protected {backed_up_count} SLC files by moving to: {backup_dir}")
            return True
        else:
            # Remove empty backup directory
            os.rmdir(backup_dir)
            return False
            
    except Exception as e:
        print(f"Warning: Could not create backup directory: {e}")
        return False

def process_key(key, paths, dem, method, mode=None, force_regenerate=False):
    from ..utils.utils import parse_data_in_line, generate_expected_filenames, validate_data_in_vs_files
    import json
    
    dir_path = paths.get(key)
    
    if dir_path and os.path.exists(dir_path):
        praw = os.path.join(dir_path, "raw")
        
        # Extract subswath number from key (pF1->1, pF2->2, pF3->3)
        subswath_num = key.replace('pF', '') if key.startswith('pF') else '1'
        
        # Load removed unconnected images from config
        removed_images = set()
        ignore_removed = False
        try:
            # Calculate project root (go up 2 levels from F1/F2/F3)
            flight_dir = os.path.dirname(dir_path)  # /project/asc
            project_root = os.path.dirname(flight_dir)  # /project
            config_path = os.path.join(project_root, '.config.json')
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    removed_list = config.get('removed_unconnected_images', [])
                    ignore_removed = config.get('ignore_removed_in_validation', True)
                    removed_images = set(removed_list)
                    if removed_images and ignore_removed:
                        print(f"ℹ️  Ignoring {len(removed_images)} previously removed unconnected image(s) in validation")
                    elif removed_images and not ignore_removed:
                        print(f"⚠️  {len(removed_images)} removed image(s) will be treated as missing")
        except Exception as e:
            print(f"Warning: Could not load removed images from config: {e}")
        
        # Check data.in file and expected files based on its content
        data_in_path = os.path.join(praw, "data.in")
        baseline_files_complete = False
        
        if os.path.exists(data_in_path):
            # Read and parse data.in entries
            with open(data_in_path, 'r') as f:
                lines = [line.strip() for line in f if line.strip()]
                
            data_in_count = len(lines)
            
            # Check if all expected LED and PRM files exist
            missing_led = []
            missing_prm = []
            
            for line in lines:
                entry = parse_data_in_line(line)
                if entry and entry['date']:
                    # Skip if this image was removed as unconnected (and user chose to ignore)
                    if ignore_removed and entry['date'] in removed_images:
                        continue
                    
                    # Generate expected LED and PRM filenames
                    expected_files = generate_expected_filenames(entry, ['LED', 'PRM'])
                    
                    led_file = expected_files.get('LED_required')  # S1_20230407_ALL_F2.LED
                    prm_file = expected_files.get('PRM_required')  # S1_20230407_ALL_F2.PRM
                    
                    if led_file and not os.path.exists(os.path.join(praw, led_file)):
                        missing_led.append(led_file)
                    if prm_file and not os.path.exists(os.path.join(praw, prm_file)):
                        missing_prm.append(prm_file)
            
            # Baseline files are complete if no files are missing
            baseline_files_complete = (len(missing_led) == 0 and len(missing_prm) == 0 and data_in_count > 0)
            
            if baseline_files_complete:
                print(f"✅ Baseline files complete for {key} - all {data_in_count} LED/PRM files exist")
            else:
                print(f"🔄 Missing baseline files for {key} - LED: {len(missing_led)}, PRM: {len(missing_prm)}")
        
        # Check existing files for backward compatibility
        existing_files = os.listdir(praw) if os.path.exists(praw) else []
        prm_files = [f for f in existing_files if f.endswith(".PRM")]
        led_files = [f for f in existing_files if f.endswith(".LED")]
        tif_files = [f for f in existing_files if f.endswith(".tiff")]
        slc_files = [f for f in existing_files if f.endswith(".SLC")]
        
        # Check if alignment is already complete (SLC files exist and match data.in count)
        data_in_count = len(lines) if 'lines' in locals() else 0
        alignment_complete = (len(slc_files) > 0 and data_in_count > 0 and len(slc_files) == data_in_count)
        
        # Determine if processing is needed
        if baseline_files_complete and not force_regenerate:
            print(f"✅ Using existing baseline files for {key} - all expected LED/PRM files found")
            # Ensure baseline_table.dat exists in parent directory
            baseline_table = os.path.join(dir_path, "baseline_table.dat")
            if not os.path.exists(baseline_table):
                print(f"⚠️  baseline_table.dat missing for {key}, regenerating from existing files...")
                # Generate baseline table from existing LED/PRM files
                subprocess.call('baseline_table.csh *.PRM > ../baseline_table.dat', shell=True, cwd=praw)
        elif praw and os.path.exists(praw):
            with lock:
                if force_regenerate:
                    print(f"🔄 Regenerating baselines for {key} (master config invalid/changed)...")
                else:
                    print(f"🔄 Generating baselines for {key} (missing files detected)...")
                
                # 🔒 CRITICAL: Backup existing SLC files before any processing that might overwrite them
                if len(slc_files) > 0:
                    print(f"🔒 Found {len(slc_files)} existing SLC files - creating backup before processing")
                    backup_slc_files_if_needed(praw, force_realign=True)
                
            print(f'{method} data.in {dem} 1 {mode}'.strip())
            if method == "esd":
                comm = "preproc_batch_tops_esd.csh"
            else:
                comm = "preproc_batch_tops.csh"

            # Run baseline calculation (stage 1 only)
            subprocess.call(f'{comm} data.in {dem} 1 {mode}'.strip(), shell=True, cwd=praw)
            subprocess.call('mv baseline_table.dat ../', shell=True, cwd=praw)
        else:
            print(f"❌ Cannot process {key} - directory {praw} not accessible")

def preprocess(paths, dem, method, mode=None, force_regenerate=False):
    keys = ["pF1", "pF2", "pF3"]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_key, key, paths, dem, method, mode, force_regenerate) for key in keys]
        concurrent.futures.wait(futures)