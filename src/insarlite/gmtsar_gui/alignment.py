import os
import subprocess
import shutil
import datetime
import threading
import json
import tkinter as tk
import re
from tkinter import messagebox
from ..utils.utils import process_logger, parse_data_in_line, generate_expected_filenames, check_alignment_completion_status, create_temp_data_in
from ..gmtsar_gui.pair_generation import remove_unconnected_images
from concurrent.futures import ThreadPoolExecutor

# REMOVED: backup_slc_files_for_realignment function was deleted as it caused data loss by moving/deleting original SLC files

def check_alignment_method_change(praw, current_alignmode, current_esd_mode):
    """Check if the current alignment method differs from what was used for existing SLC files."""
    if not os.path.exists(praw):
        return False
    
    # Check if SLC files exist
    slc_files = [f for f in os.listdir(praw) if f.endswith('.SLC')]
    if len(slc_files) == 0:
        return False  # No existing SLC files, so no method change
    
    # Try to load previous alignment configuration from project directory
    # praw is like /project/asc/F1/raw, go up three levels to /project
    f_dir = os.path.dirname(praw)  # /project/asc/F1
    flight_dir = os.path.dirname(f_dir)  # /project/asc
    project_root = os.path.dirname(flight_dir)  # /project
    config_path = os.path.join(project_root, '.config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            prev_alignmode = config.get('align_mode')
            prev_esd_mode = config.get('esd_mode')
            
            # Check if method has changed
            if prev_alignmode and prev_esd_mode:
                if current_alignmode != prev_alignmode or current_esd_mode != prev_esd_mode:
                    print(f"🔍 Alignment method changed: {prev_alignmode}({prev_esd_mode}) → {current_alignmode}({current_esd_mode})")
                    return True
                else:
                    print(f"✅ Alignment method unchanged: {current_alignmode}({current_esd_mode})")
                    return False
        except Exception as e:
            print(f"Warning: Could not read config for method comparison: {e}")
    
    # If no previous config found, assume method change to be safe
    print(f"⚠️  No previous alignment config found, assuming method change")
    return True



def align_sec_imgs(paths, mst, dem, alignmode, esd_mode):
    """
    Enhanced alignment function with smart partial alignment support.
    
    Args:
        paths: Dictionary with subswath paths 
        mst: Master image identifier
        dem: DEM file path
        alignmode: Alignment mode (esd/no_esd)
        esd_mode: ESD threshold value
    """
    # Identify and validate existing subswaths (only pF1, pF2, pF3)
    valid_subswaths = []
    for subswath in ["pF1", "pF2", "pF3"]:
        if subswath in paths and paths[subswath] and os.path.exists(paths[subswath]):
            valid_subswaths.append(subswath)
    
    if not valid_subswaths:
        print("❌ No valid subswath directories found (pF1, pF2, pF3)")
        return
    
    print(f"🔍 Found {len(valid_subswaths)} valid subswath(s): {', '.join(valid_subswaths)}")
    
    lock = threading.Lock()

    def process_key(key):
        print(f"🔧 Starting process_key for {key} - CLEAN VERSION")
        
        dir_path = paths.get(key)
        
        # Skip if subswath directory doesn't exist
        if not dir_path or not os.path.exists(dir_path):
            print(f"⚠️  Skipping {key} - directory does not exist: {dir_path}")
            return
            
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
            
            # Check alignment status using network-aware function (network filtering enabled by default)
            alignment_status = check_alignment_completion_status(praw, apply_network_filtering=True)
            print(f"✅ Alignment status for {key}: {alignment_status.get('status')} - {alignment_status.get('aligned_images', 0)}/{alignment_status.get('total_images', 0)} connected images")
            
            if alignment_status['status'] == 'complete':
                # Check if alignment method has changed even though alignment is complete
                if check_alignment_method_change(praw, alignmode, esd_mode):
                    print(f"🔄 Alignment method changed for {key} - offering to backup and re-align")
                    _backup_alignment_files_with_permission(praw, key, reason="method_change")
                    print(f"🔄 Proceeding with full re-alignment due to method change")
                    _perform_full_alignment(praw, mst, dem, aligncommand, esd_mode, key, lock)
                else:
                    print(f"✅ Alignment already completed for {key} - all {alignment_status['aligned_images']}/{alignment_status['total_images']} connected images aligned")
                    process_logger(process_num=process_num, log_file=paths.get("log_file_path"), message=f"Alignment already complete for {key} (all connected images)", mode="end")
                    return
            elif alignment_status['status'] == 'partial':
                connected_missing_count = len(alignment_status['missing_images'])
                print(f"🔄 Partial alignment detected for {key} - {alignment_status['aligned_images']}/{alignment_status['total_images']} connected images aligned")
                if connected_missing_count > 0:
                    print(f"   Missing connected images: {alignment_status['missing_images'][:5]}{'...' if len(alignment_status['missing_images']) > 5 else ''}")
                    
                    # BYPASS PARTIAL ALIGNMENT: Always offer backup and do full alignment
                    print(f"🔄 Offering to backup existing aligned images before full re-alignment")
                    _backup_alignment_files_with_permission(praw, key, reason="partial_alignment")
                    print(f"🔄 Proceeding with full alignment (bypassing partial alignment)")
                    _perform_full_alignment(praw, mst, dem, aligncommand, esd_mode, key, lock)
                else:
                    print(f"✅ All missing images are unconnected in network - marking as complete")
                    process_logger(process_num=process_num, log_file=paths.get("log_file_path"), message=f"Alignment complete for {key} (all connected images aligned, unconnected skipped)", mode="end")
                    return
            elif alignment_status['status'] == 'none':
                print(f"🔄 No aligned images found for {key} - performing full alignment")
                
                # Check for method change and optionally backup if necessary
                if check_alignment_method_change(praw, alignmode, esd_mode):
                    print(f"🔄 Alignment method changed, offering to backup any existing files...")
                    _backup_alignment_files_with_permission(praw, key, reason="method_change")
                
                _perform_full_alignment(praw, mst, dem, aligncommand, esd_mode, key, lock)
            else:
                print(f"❌ Error checking alignment status for {key}: {alignment_status.get('message', 'Unknown error')}")
        
        # Log completion
        process_logger(process_num=process_num, log_file=paths.get("log_file_path"), 
                      message=f"Alignment processing completed for {key}", mode="end")

    def _backup_alignment_files_with_permission(praw, key, reason="partial_alignment"):
        """🔒 SAFE BACKUP: Backup alignment files with user permission.
        NEVER deletes original files - only creates backup copies.
        
        Args:
            praw: Path to raw directory
            key: Subswath key (pF1, pF2, pF3)
            reason: Reason for backup ("method_change" or "partial_alignment")
        """
        print(f"🔧 Checking for existing alignment files to backup for {key}")
        
        data_in_path = os.path.join(praw, "data.in")
        if not os.path.exists(data_in_path):
            return False
            
        # Read data.in to get expected files
        with open(data_in_path, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
            
        # Get all existing alignment files
        existing_files = os.listdir(praw)
        alignment_files = []
        
        for line in lines:
            entry = parse_data_in_line(line)
            if entry and entry['date']:
                # Collect all files that match this image's pattern
                base_pattern = f"S1_{entry['date']}"
                matching_files = [f for f in existing_files if f.startswith(base_pattern) and 
                                (f.endswith('.SLC') or f.endswith('.LED') or f.endswith('.PRM'))]
                alignment_files.extend(matching_files)
        
        # Remove duplicates
        alignment_files = list(set(alignment_files))
        
        if not alignment_files:
            print(f"ℹ️  No existing alignment files found for {key}")
            return False
            
        # Ask user for explicit permission to backup files
        try:
            # Create a temporary root window for the dialog
            temp_root = tk.Tk()
            temp_root.withdraw()  # Hide the main window
            
            if reason == "method_change":
                message = (f"Alignment method has changed for {key}.\n\n"
                          f"Found {len(alignment_files)} existing alignment files.\n\n"
                          f"Would you like to create a backup copy before re-alignment?\n\n"
                          f"📋 Files to backup: {', '.join(alignment_files[:5])}"
                          f"{'...' if len(alignment_files) > 5 else ''}\n\n"
                          f"⚠️  Note: Original files will be PRESERVED (not deleted).\n"
                          f"Re-alignment will overwrite them with new data.")
                title = "Alignment Method Changed - Backup Files?"
            else:  # partial_alignment
                message = (f"Partial alignment detected for {key}.\n\n"
                          f"Found {len(alignment_files)} existing alignment files.\n\n"
                          f"Would you like to create a backup copy before full re-alignment?\n\n"
                          f"📋 Files to backup: {', '.join(alignment_files[:5])}"
                          f"{'...' if len(alignment_files) > 5 else ''}\n\n"
                          f"⚠️  Note: Original files will be PRESERVED (not deleted).\n"
                          f"Full re-alignment will overwrite them with new data.")
                title = "Partial Alignment Detected - Backup Files?"
            
            user_response = messagebox.askyesno(
                title,
                message,
                parent=temp_root
            )
            
            temp_root.destroy()
            
            if not user_response:
                print(f"ℹ️  User chose not to backup existing alignment files for {key}")
                return False
                
        except Exception as e:
            print(f"⚠️  Could not show user dialog: {e}")
            print(f"ℹ️  Proceeding without backup for {key}")
            return False
            
        # Create timestamped backup directory
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(praw, f"alignment_backup_{timestamp}")
        
        try:
            os.makedirs(backup_dir)
            backed_up_count = 0
            
            # 🔒 CRITICAL: ONLY COPY files (never move or delete originals)
            for filename in alignment_files:
                src = os.path.join(praw, filename)
                dst = os.path.join(backup_dir, filename)
                try:
                    shutil.copy2(src, dst)  # COPY ONLY - preserves originals
                    backed_up_count += 1
                except Exception as e:
                    print(f"Warning: Could not backup {filename}: {e}")
            
            if backed_up_count > 0:
                print(f"✅ Successfully backed up {backed_up_count} alignment files to: {backup_dir}")
                print(f"🔒 Original files preserved - they will be overwritten during re-alignment")
                return True
            else:
                os.rmdir(backup_dir)  # Remove empty backup directory
                return False
                
        except Exception as e:
            print(f"❌ Error creating alignment backup: {e}")
            return False

    def _perform_full_alignment(praw, mst, dem, aligncommand, esd_mode, key, lock):
        """Perform full alignment of all images."""
        dind = os.path.join(praw, "data.in")
        ind = os.path.join(os.path.dirname(praw), "intf.in")
        
        if os.path.exists(dind):
            # Reorder data.in to put master first
            with open(dind, 'r') as f:
                lines = f.readlines()
                
            # Find and move master to first position
            master_line = None
            for i, line in enumerate(lines):
                if mst in line:
                    master_line = lines.pop(i)
                    break
                    
            if master_line:
                lines.insert(0, master_line)
                with open(dind, 'w') as f:
                    for line in lines:
                        f.write(line)
            
            # 🔒 CRITICAL: Check network connectivity BEFORE alignment
            print(f"🔍 Checking network connectivity before alignment for {key}...")
            if os.path.exists(ind):
                # Read intf.in to see which images are connected
                with open(ind, 'r') as f:
                    intf_lines = f.readlines()
                
                # Extract connected image dates from intf.in
                connected_images = set()
                for intf_line in intf_lines:
                    if ':' in intf_line:
                        # Parse interferogram pair (format: master:slave)
                        parts = intf_line.strip().split(':')
                        if len(parts) >= 2:
                            # Extract dates from image filenames
                            for part in parts:
                                # Look for 8-digit date pattern
                                date_match = re.search(r'\d{8}', part)
                                if date_match:
                                    connected_images.add(date_match.group())
                
                # Filter data.in to only include connected images
                if connected_images:
                    print(f"🌐 Found {len(connected_images)} connected images in network")
                    filtered_lines = []
                    skipped_count = 0
                    
                    for line in lines:
                        # Check if this line contains a connected image date
                        line_has_connected_image = False
                        for date in connected_images:
                            if date in line:
                                line_has_connected_image = True
                                break
                        
                        if line_has_connected_image or mst in line:  # Always include master
                            filtered_lines.append(line)
                        else:
                            skipped_count += 1
                            print(f"⚠️  Skipping unconnected image: {line.strip()}")
                    
                    if skipped_count > 0:
                        print(f"⚠️  Skipped {skipped_count} unconnected images from alignment")
                        # Write filtered data.in
                        with open(dind, 'w') as f:
                            for line in filtered_lines:
                                f.write(line)
                        lines = filtered_lines
                else:
                    print(f"⚠️  No network connectivity information found, processing all images")
            else:
                print(f"⚠️  No intf.in file found, processing all images")
            
            # Continue with alignment only if we have images to process
            if len(lines) > 1:  # Master + at least one slave
                with lock:
                    print(f"🔄 Starting full alignment for {key} with {len(lines)} connected images...")
                    print(f'{aligncommand} data.in {dem} 2 {esd_mode}'.strip())
                    subprocess.call(f'{aligncommand} data.in {dem} 2 {esd_mode}'.strip(), shell=True, cwd=praw)
            else:
                print(f"⚠️  No connected slave images found for {key}, skipping alignment")

    # COMMENTED OUT: Partial alignment function (no longer used)
    # def _perform_partial_alignment(praw, mst, missing_images, dem, aligncommand, esd_mode, key, lock):
    #     """🔒 CRITICAL FIX: Check network connectivity before partial alignment."""
    #     print(f"🔧 [TEST] Starting partial alignment for {key}")
    #     
    #     # First, check which images are actually connected in the network
    #     ind = os.path.join(os.path.dirname(praw), "intf.in")
    #     connected_missing_images = []
    #     
    #     if os.path.exists(ind):
    #         # Read intf.in to see which images are connected
    #         with open(ind, 'r') as f:
    #             intf_lines = f.readlines()
    #         
    #         # Extract connected image dates from intf.in
    #         connected_images = set()
    #         for intf_line in intf_lines:
    #             if ':' in intf_line:
    #                 parts = intf_line.strip().split(':')
    #                 if len(parts) >= 2:
    #                     for part in parts:
    #                         date_match = re.search(r'\d{8}', part)
    #                         if date_match:
    #                             connected_images.add(date_match.group())
    #         
    #         # Filter missing images to only include connected ones
    #         for missing_date in missing_images:
    #             if missing_date in connected_images:
    #                 connected_missing_images.append(missing_date)
    #             else:
    #                 print(f"⚠️  Skipping unconnected missing image: {missing_date}")
    #     else:
    #         print(f"⚠️  No intf.in file found, assuming all missing images are connected")
    #         connected_missing_images = missing_images
    #     
    #     if not connected_missing_images:
    #         print(f"✅ All missing images for {key} are unconnected in network - no partial alignment needed")
    #         return
    #     
    #     print(f"🔄 Performing partial alignment for {len(connected_missing_images)} connected missing images: {connected_missing_images}")
    #     
    #     # Extract master date from master string (assuming format contains date)
    #     master_date = None
    #     mst_f = mst.replace('-', '')
    #     if mst_f and len(mst_f) >= 8:
    #         # Try to extract date from master string
    #         for i in range(len(mst_f) - 7):
    #             potential_date = mst_f[i:i+8]
    #             if potential_date.isdigit():
    #                 master_date = potential_date
    #                 break
    #     
    #     if not master_date:
    #         print(f"❌ Could not determine master date for partial alignment of {key}")
    #         return
    #         
    #     # Create temporary data.in with master + connected unaligned images only
    #     temp_data_in = create_temp_data_in(praw, master_date, connected_missing_images)
    #     
    #     if temp_data_in:
    #         try:
    #             with lock:
    #                 print(f"🔄 Starting partial alignment for {key} - master + {len(connected_missing_images)} connected missing images...")
    #                 print(f'{aligncommand} {os.path.basename(temp_data_in)} {dem} 2 {esd_mode}'.strip())
    #                 
    #                 # Run alignment with temporary data.in file
    #                 subprocess.call(f'{aligncommand} {os.path.basename(temp_data_in)} {dem} 2 {esd_mode}'.strip(), shell=True, cwd=praw)
    #                 
    #                 print(f"✅ Partial alignment completed for {key}")
    #                 
    #         finally:
    #             # Clean up temporary file
    #             if os.path.exists(temp_data_in):
    #                 os.remove(temp_data_in)
    #     else:
    #         print(f"❌ Failed to create temporary data.in for partial alignment of {key}")

    # Only process valid existing subswaths
    with ThreadPoolExecutor() as executor:
        executor.map(process_key, valid_subswaths)