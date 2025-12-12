import tkinter as tk
from ..gmtsar_gui.alignment import align_sec_imgs
from ..gmtsar_gui.ifgs_generation import gen_ifgs
from ..gmtsar_gui.mergeIFGs import merge_thread
from ..gmtsar_gui.mean_corr import create_mean_grd
from ..utils.utils import check_alignment_completion_status, check_ifgs_completion, check_merge_completion, check_first_ifg_completion, process_logger
import threading
from tkinter import messagebox
import os
import glob
import time

class GenIfg:
    def __init__(self, root, paths, mst, dem, align_mode=None, esd_mode=None, on_done=None):
        self.root = root
        self.root.title("Parameter Settings for IFGs Generation")
        self.dem_path = dem
        self.paths = paths
        self.mst = mst
        self.log_file_path = paths.get("log_file_path")
        self.align_mode = align_mode
        self.esd_mode = esd_mode
        self.on_done = on_done

        # Decimation Frame
        self.decimation_frame = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        self.decimation_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nw")

        tk.Label(self.decimation_frame, text="IFGs Generation", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(5, 15))

        # Range Decimation
        tk.Label(self.decimation_frame, text="Range Decimation:").grid(row=1, column=0, sticky="w", padx=5)
        self.range_dec_var = tk.StringVar(value="8")
        tk.Entry(self.decimation_frame, textvariable=self.range_dec_var).grid(row=1, column=1, padx=5)

        # Azimuth Decimation
        tk.Label(self.decimation_frame, text="Azimuth Decimation:").grid(row=2, column=0, sticky="w", padx=5)
        self.az_dec_var = tk.StringVar(value="2")
        tk.Entry(self.decimation_frame, textvariable=self.az_dec_var).grid(row=2, column=1, padx=5)

        # Filter Wavelength
        tk.Label(self.decimation_frame, text="Filter Wavelength (m):").grid(row=3, column=0, sticky="w", padx=5)
        self.filter_wl_var = tk.StringVar(value="200")
        tk.Entry(self.decimation_frame, textvariable=self.filter_wl_var).grid(row=3, column=1, padx=5)

        # Number of cores (next column)
        try:
            available_cores = os.cpu_count() or 1
            default_cores = max(1, available_cores - 1)
        except Exception:
            default_cores = 1
        tk.Label(self.root, text="Number of cores:").grid(row=1, column=2, sticky="w", padx=(20,5))
        self.cores_var = tk.StringVar(value=str(default_cores))
        tk.Entry(self.root, textvariable=self.cores_var).grid(row=1, column=3, padx=5)

        # Run Button
        self.run_btn = tk.Button(self.root, text="Run", command=self.on_run)
        self.run_btn.grid(row=4, column=0, pady=20, sticky="w")

    def on_run(self):
        print("Run button clicked.")

        def run_alignment():
            print("Starting alignment of secondary images...")
            # alignmethod = self.align_mode if hasattr(self, 'align_mode') else None
            # esd_mode = self.esd_mode if hasattr(self, 'esd_mode') else None
            
            align_sec_imgs(self.paths, self.mst, self.dem_path, self.align_mode, self.esd_mode)

        def ifg_generation():
            print("Starting IFG generation...")
            filter_wavelength = int(self.filter_wl_var.get())
            rng = int(self.range_dec_var.get())
            az = int(self.az_dec_var.get())
            ncores = int(self.cores_var.get())
            gen_ifgs(self.paths, self.mst, filter_wavelength, rng, az, ncores)

        def merge_ifgs():
            print("Starting IFG merging...")            
            if "pmerge" in self.paths.keys():
                pmerge = self.paths.get("pmerge")
                if pmerge and os.path.exists(pmerge):
                    # Call the merge_thread function
                    merge_thread(pmerge, self.log_file_path, self.mst)

        def calc_mean_corr():            
            ifgsroot = None
            if "pmerge" in self.paths.keys():
                pmerge = self.paths.get("pmerge")
                if pmerge and os.path.exists(pmerge):
                    ifgsroot = pmerge
                else:
                    for key in ["pF1", "pF2", "pF3"]:
                        dir_path = self.paths.get(key)
                        if dir_path and os.path.exists(dir_path):
                            ifgsroot = os.path.join(dir_path, 'intf_all')
                            break
            if ifgsroot:
                print(f"Creating mean & sd correlation grid in {ifgsroot}...")
                if os.path.exists(ifgsroot):
                    create_mean_grd(ifgsroot, log_file_path=self.log_file_path)

            

        msg = (
            "Press the \"Continue\" button if you understand that clicking run button will perform the following in specified sequence:\n"
            "  1. Alignment of secondary images w.r.t. the specified master.\n"
            "  2. Generation of IFGs as per generated IFGs network.\n"
            "  3. Merging the IFGs of selected subswaths if more than one was selected.\n"
            "  4. Calculation and creation of mean & sd correlation grid to be used for later steps. \nThe start and end of each process will be displayed in the terminal."
        )

        def process_sequence():
            try:
                self.root.destroy()
                run_alignment()
                ifg_generation()
                merge_ifgs()
                calc_mean_corr()
                print("All processes completed.")
                if self.on_done:
                    self.on_done()
                # self.root.quit()
                
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {e}")

        if messagebox.askokcancel("Confirm Run", msg):
            # Close the parameter window first
            self.root.destroy()
            
            # Create and show progress window
            self.progress_window = tk.Toplevel()
            self.progress_window.title("Image Alignment & Interferogram Generation Progress")
            self.progress_window.geometry("700x600")  # Increased size to show buttons
            self.progress_window.protocol("WM_DELETE_WINDOW", lambda: None)  # Prevent manual closure
            
            # Initialize progress tracking
            self._setup_progress_window()
            
            # Start the processing sequence with progress monitoring
            threading.Thread(target=self._process_sequence_with_progress, daemon=True).start()
        else:
            return
        

    def _setup_progress_window(self):
        """Setup the progress monitoring UI."""
        main_frame = tk.Frame(self.progress_window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Overall progress header (without the persistent blue label)
        tk.Label(main_frame, text="Overall Progress", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        # Stage progress frame
        self.stage_frame = tk.Frame(main_frame)
        self.stage_frame.pack(fill="x", pady=(0, 10))
        
        # Create stage progress labels with enhanced formatting
        self.stage_labels = {}
        self.stage_vars = {}
        self.stage_completion = {}
        stages = [
            ("Stage 1/4: Alignment", "alignment"),
            ("Stage 2/4: Interferogram Generation", "interferograms"), 
            ("Stage 3/4: Subswath Merging", "merging"),
            ("Stage 4/4: Mean Correlation Calculation", "correlation")
        ]
        
        for i, (stage_name, stage_key) in enumerate(stages):
            stage_var = tk.StringVar(value=f"{stage_name} | Pending")
            stage_label = tk.Label(self.stage_frame, textvariable=stage_var, fg="gray", font=("Arial", 10, "bold"))
            stage_label.pack(anchor="w", padx=10, pady=2)
            
            self.stage_vars[stage_key] = stage_var
            self.stage_labels[stage_key] = stage_label
            self.stage_completion[stage_key] = False
        
        # Create progress frames for each subswath
        self.subswath_frames = {}
        self.subswath_progress_vars = {}
        self.subswath_detail_vars = {}
        self.subswath_status_labels = {}
        self.subswath_status = {}
        
        # Get active subswaths
        active_subswaths = []
        for i, key in enumerate(['pF1', 'pF2', 'pF3'], 1):
            path = self.paths.get(key)
            if path and os.path.exists(path):
                active_subswaths.append((f"F{i}", key, path))
        
        self.active_subswaths = active_subswaths
        
        # Create UI for each active subswath
        for subswath_name, key, path in active_subswaths:
            frame = tk.LabelFrame(main_frame, text=f"Subswath {subswath_name}", font=("Arial", 10, "bold"))
            frame.pack(fill="x", pady=5)
            
            # Status and progress
            status_var = tk.StringVar(value="Pending")
            detail_var = tk.StringVar(value="Waiting to start...")
            
            tk.Label(frame, text="Status:", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=2)
            status_label = tk.Label(frame, textvariable=status_var, fg="orange")
            status_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)
            
            tk.Label(frame, text="Details:", font=("Arial", 9, "bold")).grid(row=1, column=0, sticky="w", padx=5, pady=2)
            detail_label = tk.Label(frame, textvariable=detail_var, fg="gray")
            detail_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)
            
            self.subswath_frames[key] = frame
            self.subswath_progress_vars[key] = status_var
            self.subswath_detail_vars[key] = detail_var
            self.subswath_status_labels[key] = status_label
            
            # Initialize status tracking
            self.subswath_status[key] = {
                'alignment_complete': False,
                'ifg_complete': False,
                'first_ifg_complete': False,
                'merge_complete': False,
                'path': path,
                'name': subswath_name
            }
        
        # Initialize stage completion tracking
        self.stage_completion = {
            'alignment': False,
            'interferograms': False, 
            'merging': False,
            'correlation': False
        }
        
        # Action buttons frame
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        self.cancel_btn = tk.Button(button_frame, text="Cancel Process", command=self._cancel_processing, bg="red", fg="white")
        self.cancel_btn.pack(side="left")
        
        self.close_btn = tk.Button(button_frame, text="Close", command=self._close_progress_window, state="disabled")
        self.close_btn.pack(side="right")

    def _process_sequence_with_progress(self):
        """Execute the processing sequence with real-time progress monitoring."""
        try:
            # Log start of entire workflow (Process-2)
            ui_params = {
                'master_image': self.mst,
                'alignment_mode': self.align_mode,
                'esd_mode': self.esd_mode,
                'dem_file': self.dem_path,
                'filter_wavelength': self.filter_wl_var.get(),
                'range_decimation': self.range_dec_var.get(),
                'azimuth_decimation': self.az_dec_var.get(),
                'cores': self.cores_var.get()
            }
            process_logger(process_num=2, log_file=self.log_file_path, 
                         message="Starting image alignment and interferogram generation...", 
                         mode="start", ui_params=ui_params)
            
            # Check current status first
            self._check_initial_status()
            
            # Start comprehensive monitoring
            self._start_comprehensive_monitoring()
            
            # Stage 1: Alignment - Process sequentially, wait for each subswath to complete
            self._update_stage_progress("alignment", "In Progress")
            if not self._execute_stage_1_alignment():
                return
            self._update_stage_progress("alignment", "Completed")
            
            # Stage 2: Interferogram Generation - Only start if Stage 1 complete
            self._update_stage_progress("interferograms", "In Progress") 
            if not self._execute_stage_2_interferograms():
                return
            self._update_stage_progress("interferograms", "Completed")
            
            # Stage 3: Merging (if applicable) - Only start if Stage 2 complete
            if "pmerge" in self.paths.keys():
                pmerge = self.paths.get("pmerge")
                if pmerge and os.path.exists(pmerge):
                    self._update_stage_progress("merging", "In Progress")
                    if not self._execute_stage_3_merging():
                        return
                    self._update_stage_progress("merging", "Completed")
                else:
                    self._update_stage_progress("merging", "Skipped")
            else:
                self._update_stage_progress("merging", "Skipped")
            
            # Stage 4: Mean correlation calculation - Only start if all previous complete
            self._update_stage_progress("correlation", "In Progress")
            if not self._execute_stage_4_correlation():
                return
            self._update_stage_progress("correlation", "Completed")
            
            # Stop monitoring
            self._stop_comprehensive_monitoring()
            
            # Log end of entire workflow (Process-2)
            process_logger(process_num=2, log_file=self.log_file_path, 
                         message="Image alignment and interferogram generation completed.", 
                         mode="end")
            
            # Complete
            self._handle_completion()
            
        except Exception as e:
            # Log error and close Process-2
            process_logger(process_num=2, log_file=self.log_file_path, 
                         message=f"Image alignment and interferogram generation failed: {str(e)}", 
                         mode="end")
            self._handle_error(f"Processing failed: {str(e)}")

    def _execute_stage_1_alignment(self):
        """Execute Stage 1: Alignment with subprocess completion verification."""
        print("Stage 1/4: Starting alignment of secondary images...")
        
        # Update stage progress with subprocess info
        self._update_stage_progress("alignment", "In Progress", "2.1")
        
        # Check if all subswaths are already aligned using network-aware status
        all_aligned = True
        for subswath_name, key, path in self.active_subswaths:
            raw_folder = os.path.join(path, "raw")
            if os.path.exists(raw_folder):
                status_info = check_alignment_completion_status(raw_folder)
                if status_info['status'] != 'complete':
                    all_aligned = False
                    break
            else:
                all_aligned = False
                break
        
        if all_aligned:
            print("All subswaths already aligned, skipping alignment stage")
            return True
        
        # Run alignment for all subswaths with subprocess tracking
        try:
            for i, (subswath_name, key, path) in enumerate(self.active_subswaths, 1):
                subprocess_id = f"2.1.{i}"
                self._update_stage_progress("alignment", "In Progress", subprocess_id)
                
            align_sec_imgs(self.paths, self.mst, self.dem_path, self.align_mode, self.esd_mode)
        except Exception as e:
            self._handle_error(f"Alignment failed: {str(e)}")
            return False
        
        # Wait for all subswaths to complete alignment before proceeding
        max_wait = 3600  # 1 hour maximum wait
        wait_time = 0
        check_interval = 5  # Check every 5 seconds
        
        while wait_time < max_wait:
            all_complete = True
            for subswath_name, key, path in self.active_subswaths:
                # Use network-aware alignment checking
                raw_folder = os.path.join(path, "raw")
                if os.path.exists(raw_folder):
                    status_info = check_alignment_completion_status(raw_folder)
                    if status_info['status'] != 'complete':
                        all_complete = False
                        break
                else:
                    all_complete = False
                    break
            
            if all_complete:
                if wait_time > 0:
                    print(f"All subswaths alignment completed after {wait_time} seconds")
                else:
                    print("All subswaths alignment already completed")
                return True
                
            time.sleep(check_interval)
            wait_time += check_interval
            
            if getattr(self, '_cancel_requested', False):
                return False
        
        # Timeout
        self._handle_error("Alignment stage timeout - not all subswaths completed")
        return False

    def _execute_stage_2_interferograms(self):
        """Execute Stage 2: Interferogram Generation with retry logic and better error handling."""
        print("Stage 2/4: Starting IFG generation...")
        
        # Initial stage progress update
        self._update_stage_progress("interferograms", "In Progress", "2.2")
        
        # Check if all subswaths already have interferograms
        all_ifgs_done = True
        for subswath_name, key, path in self.active_subswaths:
            if not check_ifgs_completion(path, verbose=False):
                all_ifgs_done = False
                break
        
        if all_ifgs_done:
            print("All interferograms already generated, skipping IFG generation stage")
            return True
        
        # Sequential processing with retry logic
        max_retries = 2  # Allow up to 2 retries per subswath
        
        try:
            filter_wavelength = int(self.filter_wl_var.get())
            rng = int(self.range_dec_var.get())
            az = int(self.az_dec_var.get())
            ncores = int(self.cores_var.get())
            
            # Process each subswath sequentially with retry mechanism
            for i, (subswath_name, key, path) in enumerate(self.active_subswaths, 1):
                subprocess_id = f"2.2.{i}"
                self._update_stage_progress("interferograms", "In Progress", subprocess_id)
                
                # Only process this subswath if not complete
                if not check_ifgs_completion(path, verbose=False):
                    print(f"Processing interferograms for subswath {subswath_name}...")
                    
                    # Retry logic for interferogram generation
                    retry_count = 0
                    success = False
                    
                    while retry_count <= max_retries and not success:
                        try:
                            # Check first interferogram completion using topo_ra.grd
                            first_ifg_complete = check_first_ifg_completion(path, verbose=False)
                            print(f"Attempt {retry_count + 1}: First IFG status for {subswath_name}: {'Complete' if first_ifg_complete else 'Incomplete'}")
                            
                            # Get existing interferograms to skip (refresh each retry)
                            existing_pairs = self._get_existing_interferogram_pairs(path)
                            print(f"Attempt {retry_count + 1}: Found {len(existing_pairs)} existing interferogram pairs for {subswath_name}")
                            
                            # Create a single-subswath paths dict
                            single_paths = {k: (v if k == key else None) for k, v in self.paths.items()}
                            single_paths['existing_pairs'] = existing_pairs
                            
                            # Call gen_ifgs for single subswath
                            print(f"Generating interferograms for {subswath_name} (attempt {retry_count + 1}/{max_retries + 1})")
                            
                            # Store initial completed count to track what was generated
                            initial_completed = self._count_completed_interferograms(path)
                            initial_total = self._count_total_interferograms(path)
                            
                            # gen_ifgs is synchronous - it completes when returned
                            gen_ifgs(single_paths, self.mst, filter_wavelength, rng, az, ncores)
                            
                            # Check final status after gen_ifgs completes
                            final_completed = self._count_completed_interferograms(path)
                            final_total = self._count_total_interferograms(path)
                            first_ifg_complete = check_first_ifg_completion(path, verbose=False)
                            
                            # Determine success based on what was expected to be generated
                            newly_generated = final_completed - initial_completed
                            all_complete = check_ifgs_completion(path, verbose=False)
                            
                            if all_complete:
                                print(f"✅ All {final_completed}/{final_total} interferograms completed for {subswath_name}")
                                success = True
                            elif newly_generated > 0:
                                print(f"✅ Generated {newly_generated} new interferograms for {subswath_name} ({final_completed}/{final_total} total)")
                                print(f"✅ Subswath {subswath_name} interferogram generation completed successfully")
                                success = True
                            else:
                                print(f"❌ No new interferograms generated for {subswath_name} ({final_completed}/{final_total} total)")
                                success = False
                            
                            # Brief verification wait only if needed
                            if not success:
                                print(f"Waiting briefly for {subswath_name} file system updates...")
                                time.sleep(10)  # Brief wait for file system updates
                                
                                # Re-check after brief wait
                                final_completed = self._count_completed_interferograms(path)
                                newly_generated = final_completed - initial_completed
                                all_complete = check_ifgs_completion(path, verbose=False)
                                
                                if all_complete or newly_generated > 0:
                                    print(f"✅ Verification successful for {subswath_name} ({final_completed}/{final_total} total)")
                                    success = True
                                else:
                                    print(f"❌ Verification failed for {subswath_name} ({final_completed}/{final_total} total)")
                            
                            if getattr(self, '_cancel_requested', False):
                                return False
                            
                        except Exception as e:
                            print(f"❌ Error in interferogram generation attempt {retry_count + 1} for {subswath_name}: {str(e)}")
                            success = False
                        
                        if not success:
                            retry_count += 1
                            if retry_count <= max_retries:
                                print(f"⚠️  Retrying interferogram generation for {subswath_name} (attempt {retry_count + 1}/{max_retries + 1})")
                                time.sleep(5)  # Brief pause before retry
                    
                    if not success:
                        error_msg = f"Failed to complete interferogram generation for {subswath_name} after {max_retries + 1} attempts"
                        self._update_stage_progress("interferograms", "Error", subprocess_id)
                        self._handle_error(error_msg)
                        return False
                else:
                    print(f"✅ Subswath {subswath_name} interferograms already completed")
            
        except Exception as e:
            self._handle_error(f"Interferogram generation failed: {str(e)}")
            return False
        
        # Final verification that all subswaths completed
        print("Performing final verification of all interferogram completions...")
        for subswath_name, key, path in self.active_subswaths:
            if not check_ifgs_completion(path, verbose=False):
                # Get actual counts for detailed error message
                completed = self._count_completed_interferograms(path)
                total = self._count_total_interferograms(path)
                error_msg = f"Final verification failed: {subswath_name} interferograms incomplete ({completed}/{total})"
                self._handle_error(error_msg)
                return False
        
        print("✅ All subswaths interferogram generation completed successfully")
        return True

    def _execute_stage_3_merging(self):
        """Execute Stage 3: Merging with completion verification."""
        print("Stage 3/4: Starting IFG merging...")
        
        pmerge = self.paths.get("pmerge")
        if not pmerge or not os.path.exists(pmerge):
            return True
        
        # Update stage progress with subprocess info
        self._update_stage_progress("merging", "In Progress", "2.3")
        
        # Check if merging is already complete
        if check_merge_completion(os.path.dirname(pmerge)):
            print("Merging already completed, skipping merge stage")
            return True
        
        try:
            merge_thread(pmerge, self.log_file_path, self.mst)
        except Exception as e:
            self._handle_error(f"Merging failed: {str(e)}")
            return False
        
        # Wait for merging to complete
        max_wait = 1800  # 30 minutes maximum wait
        wait_time = 0
        check_interval = 10  # Check every 10 seconds
        
        while wait_time < max_wait:
            if check_merge_completion(os.path.dirname(pmerge)):
                print(f"Merging completed after {wait_time} seconds")
                return True
                
            time.sleep(check_interval)
            wait_time += check_interval
            
            if getattr(self, '_cancel_requested', False):
                return False
        
        # Timeout
        self._handle_error("Merging stage timeout")
        return False

    def _execute_stage_4_correlation(self):
        """Execute Stage 4: Mean correlation calculation."""
        print("Stage 4/4: Creating mean & sd correlation grid...")
        
        # Update stage progress with subprocess info
        self._update_stage_progress("correlation", "In Progress", "2.4")
        
        ifgsroot = None
        if "pmerge" in self.paths.keys():
            pmerge = self.paths.get("pmerge")
            if pmerge and os.path.exists(pmerge):
                ifgsroot = pmerge
            else:
                for key in ["pF1", "pF2", "pF3"]:
                    dir_path = self.paths.get(key)
                    if dir_path and os.path.exists(dir_path):
                        ifgsroot = os.path.join(dir_path, 'intf_all')
                        break
        
        if not ifgsroot or not os.path.exists(ifgsroot):
            self._handle_error("No interferogram directory found for correlation calculation")
            return False
        
        try:
            create_mean_grd(ifgsroot, log_file_path=self.log_file_path)
            print("Mean correlation calculation completed")
            return True
        except Exception as e:
            self._handle_error(f"Mean correlation calculation failed: {str(e)}")
            return False

    def _check_initial_status(self):
        """Check what's already completed before starting using network-aware status functions."""
        for subswath_name, key, path in self.active_subswaths:
            # Check alignment status using network-aware function
            raw_folder = os.path.join(path, "raw")
            if os.path.exists(raw_folder):
                status_info = check_alignment_completion_status(raw_folder)
                
                if status_info['status'] == 'complete':
                    aligned = status_info['aligned_images'] 
                    total = status_info['total_images']
                    self._update_subswath_status(key, "Completed", f"Alignment already done: {aligned}/{total} images")
                    self.subswath_status[key]['alignment_complete'] = True
                elif status_info['status'] in ['partial', 'none']:
                    aligned = status_info['aligned_images'] 
                    total = status_info['total_images']
                    self._update_subswath_status(key, "Pending", f"Alignment needed: {aligned}/{total} images complete")
                else:
                    self._update_subswath_status(key, "Pending", "Alignment needed")
            else:
                self._update_subswath_status(key, "Pending", "Raw folder missing")
            
            # Check interferogram status (first IFG check will happen during generation)
            if check_ifgs_completion(path):
                self._update_subswath_status(key, "Completed", "Interferograms already done")
                self.subswath_status[key]['ifg_complete'] = True

    def _start_comprehensive_monitoring(self):
        """Start monitoring all subswaths comprehensively."""
        self._monitoring_active = True
        
        # Initialize state tracking to prevent duplicate messages
        self._last_first_ifg_status = {}
        self._last_ifg_progress = {}
        self._last_alignment_progress = {}
        
        def monitor_all_progress():
            while self._monitoring_active and not getattr(self, '_cancel_requested', False):
                try:
                    for subswath_name, key, path in self.active_subswaths:
                        if hasattr(self, '_cancel_requested') and self._cancel_requested:
                            break
                        
                        # Monitor alignment progress with subprocess tracking using network-aware status checking
                        if not self.subswath_status[key]['alignment_complete']:
                            raw_folder = os.path.join(path, "raw")
                            if os.path.exists(raw_folder):
                                # Use the enhanced alignment status function that accounts for network connectivity
                                status_info = check_alignment_completion_status(raw_folder)
                                
                                if status_info['status'] != 'error':
                                    total_images = status_info['total_images']
                                    aligned_images = status_info['aligned_images']
                                    
                                    if total_images > 0:
                                        progress = (aligned_images / total_images) * 100
                                        
                                        # Only update if progress changed
                                        if key not in self._last_alignment_progress or self._last_alignment_progress[key] != progress:
                                            self._last_alignment_progress[key] = progress
                                            
                                            # Determine subprocess info for alignment
                                            subswath_num = key[-1]  # F1->1, F2->2, F3->3
                                            subprocess_stage = f"2.1.{subswath_num}"
                                            detail = f"Alignment: {aligned_images}/{total_images} images ({progress:.1f}%)"
                                            
                                            # Update stage progress with subprocess info
                                            if not hasattr(self, '_current_align_subprocess') or self._current_align_subprocess != subprocess_stage:
                                                self._current_align_subprocess = subprocess_stage
                                                self.progress_window.after(0, lambda ss=subprocess_stage: self._update_stage_progress("alignment", "In Progress", ss))
                                            
                                            if aligned_images > 0 and progress < 100:
                                                self.progress_window.after(0, lambda k=key, d=detail: self._update_subswath_status(k, "In Progress", d))
                                            
                                            # Use network-aware completion check
                                            if status_info['status'] == 'complete':
                                                self.subswath_status[key]['alignment_complete'] = True
                                                self.progress_window.after(0, lambda k=key, ai=aligned_images, ti=total_images: self._update_subswath_status(k, "Completed", f"Alignment completed: {ai}/{ti} images (100%)"))
                        
                        # Monitor interferogram progress with detailed subprocess info
                        if self.subswath_status[key]['alignment_complete'] and not self.subswath_status[key]['ifg_complete']:
                            # Check first interferogram completion using topo_ra.grd (without verbose printing)
                            first_ifg_complete = check_first_ifg_completion(path, verbose=False)
                            
                            # Check all interferograms completion using corr.grd
                            ifg_details = self._get_interferogram_progress_details(path)
                            total_ifgs = ifg_details['total']
                            completed_ifgs = ifg_details['completed']
                            
                            # Only update if status changed
                            current_status = (first_ifg_complete, completed_ifgs, total_ifgs)
                            if key not in self._last_ifg_progress or self._last_ifg_progress[key] != current_status:
                                self._last_ifg_progress[key] = current_status
                                
                                # Log first IFG status change only
                                if key not in self._last_first_ifg_status or self._last_first_ifg_status[key] != first_ifg_complete:
                                    self._last_first_ifg_status[key] = first_ifg_complete
                                    if first_ifg_complete:
                                        print(f"✅ First IFG completed for {path} (topo_ra.grd found)")
                                    else:
                                        print(f"❌ First IFG not completed for {path} (topo_ra.grd missing)")
                                
                                # Print overall IFG progress only when it changes
                                if total_ifgs > 0:
                                    if completed_ifgs < total_ifgs:
                                        print(f"❌ Only {completed_ifgs} out of {total_ifgs} IFGs completed for {path}")
                                    elif completed_ifgs >= total_ifgs:
                                        print(f"✅ All {completed_ifgs} IFGs completed for {path}")
                                
                                if total_ifgs > 0:
                                    progress = (completed_ifgs / total_ifgs) * 100
                                    
                                    # Determine subprocess stage based on first IFG and overall progress
                                    subswath_num = key[-1]  # F1->1, F2->2, F3->3
                                    
                                    if not first_ifg_complete:
                                        # First interferogram generation stage (process x.x.1)
                                        subprocess_stage = f"2.{subswath_num}.1"
                                        detail = f"First IFG: Generating topo_ra.grd..."
                                    elif completed_ifgs < total_ifgs:
                                        # All interferograms generation stage (process x.x.2)
                                        subprocess_stage = f"2.{subswath_num}.2"
                                        detail = f"All IFGs: {completed_ifgs}/{total_ifgs} ({progress:.1f}%)"
                                        # Only print progress message once when status first changes
                                        # (The print is already controlled by the status change check above)
                                    else:
                                        # Completed
                                        subprocess_stage = f"2.{subswath_num}"
                                        detail = f"All IFGs completed: {completed_ifgs}/{total_ifgs} (100%)"
                                        # Only print completion message once when status first changes
                                        # (The print is already controlled by the status change check above)
                                    
                                    # Update stage progress with subprocess info
                                    if not hasattr(self, '_current_ifg_subprocess') or self._current_ifg_subprocess != subprocess_stage:
                                        self._current_ifg_subprocess = subprocess_stage
                                        self.progress_window.after(0, lambda ss=subprocess_stage: self._update_stage_progress("interferograms", "In Progress", ss))
                                    
                                    if completed_ifgs > 0 and progress < 100:
                                        self.progress_window.after(0, lambda k=key, d=detail: self._update_subswath_status(k, "In Progress", d))
                                    
                                    if completed_ifgs >= total_ifgs and first_ifg_complete:
                                        self.subswath_status[key]['ifg_complete'] = True
                                        self.progress_window.after(0, lambda k=key: self._update_subswath_status(k, "Completed", "Interferograms completed"))
                    
                    # Check if all subswaths are complete and stop monitoring
                    all_complete = all(
                        self.subswath_status[key]['alignment_complete'] and self.subswath_status[key]['ifg_complete'] 
                        for _, key, _ in self.active_subswaths
                    )
                    if all_complete:
                        print("✅ All subswaths completed - stopping monitoring")
                        break
                    
                    time.sleep(3)  # Check every 3 seconds
                    
                except Exception as e:
                    print(f"Error in comprehensive monitoring: {e}")
                    break
        
        self.monitor_thread = threading.Thread(target=monitor_all_progress, daemon=True)
        self.monitor_thread.start()

    def _stop_comprehensive_monitoring(self):
        """Stop comprehensive monitoring."""
        self._monitoring_active = False

    def _update_overall_progress(self, message):
        """Update the overall progress message - no longer displayed since stage labels are used."""
        # This method is kept for compatibility but does nothing since we removed the overall progress label
        pass

    def _update_stage_progress(self, stage_name, status, subprocess_info=None):
        """Update the visual progress of a specific stage with enhanced formatting."""
        if hasattr(self, 'stage_vars') and stage_name in self.stage_vars:
            # Map stage names to proper display names and numbers
            stage_map = {
                'alignment': ('Alignment', 1),
                'interferograms': ('Interferogram Generation', 2), 
                'merging': ('Subswath Merging', 3),
                'correlation': ('Mean Correlation Calculation', 4)
            }
            
            display_name, stage_num = stage_map.get(stage_name, (stage_name.title(), 1))
            
            # Create subprocess info string if provided (format: 2.3 or 2.3.1)
            if subprocess_info:
                subprocess_str = f" (Process {subprocess_info})"
            else:
                subprocess_str = ""
            
            if status == "In Progress":
                self.stage_vars[stage_name].set(f"Stage {stage_num}/4: {display_name} | In Progress{subprocess_str}")
                self.stage_labels[stage_name].config(fg="#FF8C00", font=("Arial", 10, "bold"))  # Dark orange
            elif status == "Completed":
                self.stage_vars[stage_name].set(f"Stage {stage_num}/4: {display_name} | Completed")
                self.stage_labels[stage_name].config(fg="#008000", font=("Arial", 10, "bold"))  # Dark green
                self.stage_completion[stage_name] = True
            elif status == "Skipped":
                self.stage_vars[stage_name].set(f"Stage {stage_num}/4: {display_name} | Skipped")
                self.stage_labels[stage_name].config(fg="#808080", font=("Arial", 10, "bold"))  # Gray
                self.stage_completion[stage_name] = True
            elif status == "Error":
                self.stage_vars[stage_name].set(f"Stage {stage_num}/4: {display_name} | Error{subprocess_str}")
                self.stage_labels[stage_name].config(fg="#DC143C", font=("Arial", 10, "bold"))  # Crimson
            else:  # Pending or other
                self.stage_vars[stage_name].set(f"Stage {stage_num}/4: {display_name} | Pending")
                self.stage_labels[stage_name].config(fg="#808080", font=("Arial", 10, "italic"))  # Gray italic
                self.stage_vars[stage_name].set(f"Stage {stage_num}/4: {display_name} → Pending")
                self.stage_labels[stage_name].config(fg="#808080", font=("Arial", 10))  # Gray

    def _count_total_interferograms(self, path):
        """Count total expected interferograms from intf.in file."""
        intf_file = os.path.join(path, 'intf.in')
        if os.path.exists(intf_file):
            with open(intf_file, 'r') as f:
                return sum(1 for _ in f)
        return 0

    def _count_completed_interferograms(self, path):
        """Count completed interferograms from both intf and intf_all directories using only corr.grd as indicator."""
        completed_pairs = set()
        
        # Check intf directory (temporary working directory)
        intf_dir = os.path.join(path, 'intf')
        if os.path.exists(intf_dir):
            for item in os.listdir(intf_dir):
                item_path = os.path.join(intf_dir, item)
                if os.path.isdir(item_path) and '_' in item:
                    # Check for corr.grd as the only completion indicator
                    corr_file = os.path.join(item_path, 'corr.grd')
                    if os.path.exists(corr_file):
                        completed_pairs.add(item)
        
        # Check intf_all directory (final destination)
        intf_all_dir = os.path.join(path, 'intf_all')
        if os.path.exists(intf_all_dir):
            for item in os.listdir(intf_all_dir):
                item_path = os.path.join(intf_all_dir, item)
                if os.path.isdir(item_path) and '_' in item:
                    # Check for corr.grd as the only completion indicator
                    corr_file = os.path.join(item_path, 'corr.grd')
                    if os.path.exists(corr_file):
                        completed_pairs.add(item)
        
        return len(completed_pairs)

    def _get_existing_interferogram_pairs(self, path):
        """Get set of existing interferogram pairs to skip during generation using only corr.grd as indicator."""
        existing_pairs = set()
        
        # Check both intf and intf_all directories for existing completed interferograms
        for intf_subdir in ['intf', 'intf_all']:
            intf_dir = os.path.join(path, intf_subdir)
            if os.path.exists(intf_dir):
                for item in os.listdir(intf_dir):
                    item_path = os.path.join(intf_dir, item)
                    if os.path.isdir(item_path) and '_' in item:
                        # Check for corr.grd as the only completion indicator
                        corr_file = os.path.join(item_path, 'corr.grd')
                        if os.path.exists(corr_file):
                            existing_pairs.add(item)
        
        return existing_pairs

    def _get_interferogram_progress_details(self, path):
        """Get detailed interferogram progress for display using only corr.grd as indicator."""
        total_ifgs = self._count_total_interferograms(path)
        completed_ifgs = self._count_completed_interferograms(path)
        first_ifg_complete = check_first_ifg_completion(path, verbose=False)
        
        return {
            'total': total_ifgs,
            'completed': completed_ifgs,
            'first_ifg_complete': first_ifg_complete
        }

    def _update_subswath_status(self, key, status, detail):
        """Update subswath status and detail."""
        if key in self.subswath_progress_vars:
            color = {"Pending": "orange", "In Progress": "blue", "Completed": "green", "Failed": "red"}.get(status, "black")
            self.progress_window.after(0, lambda: [
                self.subswath_progress_vars[key].set(status),
                self.subswath_status_labels[key].config(fg=color),
                self.subswath_detail_vars[key].set(detail)
            ])

    def _handle_completion(self):
        """Handle successful completion."""
        self._update_overall_progress("✅ All processes completed successfully!")
        print("All processes completed.")
        
        # Enable close button
        self.progress_window.after(0, lambda: self.close_btn.config(state="normal"))
        
        # Call the original completion callback
        if self.on_done:
            self.on_done()

    def _handle_error(self, error_message):
        """Handle process errors."""
        self._update_overall_progress(f"❌ {error_message}")
        print(f"Error: {error_message}")
        
        # Enable close button and show error
        self.progress_window.after(0, lambda: [
            self.close_btn.config(state="normal"),
            messagebox.showerror("Process Failed", error_message)
        ])

    def _cancel_processing(self):
        """Cancel the ongoing processing."""
        result = messagebox.askyesno("Cancel Process", "Are you sure you want to cancel the processing?")
        if result:
            self._cancel_requested = True
            self._update_overall_progress("⚠️ Cancelling process...")
            self.progress_window.after(2000, self._close_progress_window)

    def _close_progress_window(self):
        """Close the progress window."""
        if hasattr(self, 'progress_window') and self.progress_window.winfo_exists():
            self.progress_window.destroy()


# Example usage:
if __name__ == "__main__":
    root = tk.Tk()
    gui = GenIfg(root)
    root.mainloop()
