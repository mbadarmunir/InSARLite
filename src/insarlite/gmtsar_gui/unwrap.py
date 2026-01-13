import os
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox
from multiprocessing.pool import ThreadPool
from datetime import datetime

from ..gmtsar_gui.mask import GrdViewer
from ..gmtsar_gui.ref_point import ReferencePointGUI
from ..gmtsar_gui.gacos_atm_corr import gacos
from ..utils.utils import execute_command, add_tooltip, process_logger, process_logger_consolidated


class UnwrapApp(tk.Frame):
    def __init__(self, parent, ifgsroot, ifgs, gacosdir, log_file=None):
        super().__init__(parent)
        parent.title("UnwrapApp")
        parent.geometry("400x400")
        self.ifgsroot = ifgsroot
        self.ifgs = ifgs
        self.gacosdir = gacosdir
        self.log_file = log_file
        self.topodir = self.ifgsroot if os.path.basename(self.ifgsroot) == "merge" else os.path.join(os.path.dirname(self.ifgsroot), "topo")
        
        # If ifgs list is empty (all unwrapped), scan for all interferogram directories
        if not self.ifgs and self.ifgsroot and os.path.exists(self.ifgsroot):
            print("IFGs list is empty, scanning for all interferogram directories...")
            try:
                all_dirs = next(os.walk(self.ifgsroot))[1]
                # Filter for valid interferogram directories (contain phasefilt.grd or unwrap.grd)
                self.ifgs = []
                for d in all_dirs:
                    ifg_dir = os.path.join(self.ifgsroot, d)
                    if (os.path.exists(os.path.join(ifg_dir, "phasefilt.grd")) or 
                        os.path.exists(os.path.join(ifg_dir, "unwrap.grd"))):
                        self.ifgs.append(d)
                print(f"Found {len(self.ifgs)} interferogram directories by scanning")
            except StopIteration:
                print("Could not scan interferogram directory")
                self.ifgs = []
        
        # Check initial states
        self._check_initial_states()

        self._init_widgets()
        self.pack(fill="both", expand=True)

    def _check_initial_states(self):
        """Check for existing unwrapped interferograms and validity file - store state only"""
        # Debug output
        print(f"Checking initial states - ifgsroot: {self.ifgsroot}")
        print(f"Number of interferograms to check: {len(self.ifgs)}")
        
        # Check if interferograms are already unwrapped
        unwrapped_count = 0
        for i, ifg in enumerate(self.ifgs):
            ifg_dir = os.path.join(self.ifgsroot, ifg)
            unwrap_file = os.path.join(ifg_dir, "unwrap.grd")
            if os.path.exists(unwrap_file):
                unwrapped_count += 1
            if i < 3:  # Show first few for debugging
                print(f"Checking: {unwrap_file} - {'EXISTS' if os.path.exists(unwrap_file) else 'MISSING'}")
        
        print(f"Found {unwrapped_count} unwrapped interferograms out of {len(self.ifgs)}")
        
        # Store state for later checking
        self._unwrapped_count = unwrapped_count
        self._total_ifgs = len(self.ifgs)
        
        # If all ifgs are unwrapped, check for validity file
        if unwrapped_count == len(self.ifgs) and len(self.ifgs) > 0:
            validity_file = os.path.join(self.ifgsroot, "validity_pin.grd")
            if os.path.exists(validity_file):
                # Mark phase 1 as completed if both unwrapped files and validity exist
                self._phase1_completed = True
                self._unwrapping_done = True
                print("Phase 1 already completed - unwrapping and validity both exist")
            else:
                # Store flag that validity is needed but don't prompt yet
                self._needs_validity = True
                self._unwrapping_done = True
                print("Unwrapping complete but validity file missing - will be created in Phase 1")

    def _init_widgets(self):
        # Create frame for mask buttons row
        mask_frame = tk.Frame(self)
        mask_frame.pack(pady=10)
        
        self.btn_mask = tk.Button(mask_frame, text="Define Mask", command=self.define_mask)
        self.btn_mask.pack(side="left", padx=5)
        add_tooltip(self.btn_mask, "Create or load a coherence mask\nMasks out low coherence areas before unwrapping\nButton color indicates status:\n• Red: No mask defined\n• Green: Mask defined")
        
        # Delete Mask button (initially disabled)
        self.btn_delete_mask = tk.Button(mask_frame, text="Delete Mask", command=self.delete_mask, state=tk.DISABLED)
        self.btn_delete_mask.pack(side="left", padx=5)
        add_tooltip(self.btn_delete_mask, "Delete existing mask\nOnly enabled when mask is defined")

        self.btn_ref = tk.Button(self, text="Define Reference Point", command=self.define_reference_point, state=tk.DISABLED)
        self.btn_ref.pack(pady=10)
        add_tooltip(self.btn_ref, "Select reference point for phase unwrapping\nUsually placed in stable, high coherence area\nButton color indicates status:\n• Disabled: Define mask first\n• Green: Reference point set")

        self.controls_frame = tk.Frame(self)
        self.controls_frame.pack(pady=10, fill="x")

        self.controls_inner_frame = None
        self.corr_label = None
        self.corr_entry = None
        self.cores_label = None
        self.cores_entry = None
        self.cores_var = None
        self.inc_label = None
        self.inc_entry = None
        self.inc_var = None
        self.unwrap_btn = None
        self._controls_packed = False
        
        # Check for existing mask and prompt user
        mask_path = os.path.join(self.ifgsroot, "mask_def.grd")
        if os.path.exists(mask_path):
            self.after(100, lambda: self._prompt_existing_mask(mask_path))
        else:
            # No mask exists - set button to red
            self.btn_mask.config(bg="red")
        
        # Show Phase 1 controls by default unless phase 1 is already completed
        if not (hasattr(self, '_phase1_completed') and self._phase1_completed):
            self.show_phase1_controls()
        
        # Check if unwrapping is already done and adjust button states accordingly
        if hasattr(self, '_unwrapping_done') and self._unwrapping_done:
            # Unwrapping is complete - enable reference point button
            self.btn_ref.config(state=tk.NORMAL)
            # If phase1 is complete, show controls for phase 2
            if hasattr(self, '_phase1_completed') and self._phase1_completed:
                self.btn_ref.config(text="Phase 2: Define Reference Point", bg="orange")

    def _prompt_existing_mask(self, mask_path):
        """Automatically prompt user about existing mask on startup"""
        use_existing = messagebox.askyesno(
            "Mask Exists",
            "A mask already exists. Do you want to use the existing mask?\n\nYes: Use existing mask\nNo: Mask not confirmed",
            parent=self.winfo_toplevel()
        )
        self._focus_window()
        if use_existing:
            self.btn_mask.config(bg="green")
            self.btn_delete_mask.config(state=tk.NORMAL)
        else:
            self.btn_mask.config(bg="red")
            self.btn_delete_mask.config(state=tk.DISABLED)
    
    def _set_button_state(self, mask_exists):
        self.btn_mask.config(bg="green" if mask_exists else "red")
        self.btn_delete_mask.config(state=tk.NORMAL if mask_exists else tk.DISABLED)
        if not mask_exists:
            self.btn_ref.config(state=tk.DISABLED)

    def delete_mask(self):
        """Delete existing mask after user confirmation"""
        mask_path = os.path.join(self.ifgsroot, "mask_def.grd")
        
        if not os.path.exists(mask_path):
            messagebox.showinfo("No Mask", "No mask file exists to delete.", parent=self.winfo_toplevel())
            self._focus_window()
            return
        
        confirm = messagebox.askyesno(
            "Delete Mask",
            "Are you sure you want to delete the existing mask?\n\nThis action cannot be undone.",
            parent=self.winfo_toplevel()
        )
        self._focus_window()
        
        if confirm:
            try:
                os.remove(mask_path)
                self.btn_mask.config(bg="red")
                self.btn_delete_mask.config(state=tk.DISABLED)
                messagebox.showinfo("Mask Deleted", "Mask has been deleted successfully.", parent=self.winfo_toplevel())
                self._focus_window()
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete mask: {e}", parent=self.winfo_toplevel())
                self._focus_window()
    
    def define_mask(self):
        """Open mask viewer to create/redefine mask"""
        mask_path = os.path.join(self.ifgsroot, "mask_def.grd")
        grd_file = os.path.join(self.ifgsroot, "corr_stack.grd")
        
        # If mask exists, ask if user wants to recreate
        if os.path.exists(mask_path):
            recreate = messagebox.askyesno(
                "Recreate Mask",
                "A mask already exists. Do you want to delete it and create a new one?\n\nYes: Delete and recreate\nNo: Cancel",
                parent=self.winfo_toplevel()
            )
            self._focus_window()
            if not recreate:
                return
            try:
                os.remove(mask_path)
            except Exception as e:
                messagebox.showerror("Error", f"Could not delete mask: {e}", parent=self.winfo_toplevel())
                self._focus_window()
                return
        
        # Open viewer to create mask
        viewer = GrdViewer(self.winfo_toplevel(), grd_file)
        self.wait_window(viewer)
        
        # Update button states based on whether mask was created
        self._set_button_state(os.path.exists(mask_path))

    def define_reference_point(self):
        topodir = self.topodir
        dem = os.path.join(topodir, "dem.grd")
        ra_file = os.path.join(topodir, "ref_point.ra")
        
        # Check if this is being called during Phase 2 workflow
        if hasattr(self, '_phase1_completed') and self._phase1_completed:
            # This is Phase 2 - proceed with reference point definition and normalization
            self.btn_ref.config(state=tk.DISABLED)

            if os.path.exists(ra_file):
                redefine = messagebox.askyesno(
                    "Reference Point Exists",
                    "A reference point is already defined. Do you want to redefine it?",
                    parent=self.winfo_toplevel()
                )
                self._focus_window()
                if redefine:
                    ref_window = ReferencePointGUI(self.winfo_toplevel(), dem, self.ifgsroot)
                    # Wait for window to be visible before setting grab
                    self.wait_visibility(ref_window)
                    ref_window.grab_set()
                    self.wait_window(ref_window)
            else:
                ref_window = ReferencePointGUI(self.winfo_toplevel(), dem, self.ifgsroot)
                # Wait for window to be visible before setting grab
                self.wait_visibility(ref_window)
                ref_window.grab_set()
                self.wait_window(ref_window)

            # After reference point is defined, proceed to Phase 2 normalization
            if os.path.exists(ra_file):
                self.show_unwrap_controls()
                # Start Phase 2 normalization
                self.run_phase2_normalization()
            else:
                self.btn_ref.config(state=tk.NORMAL, text="Phase 2: Define Reference Point")
                messagebox.showinfo("Reference Point Required", "Please define a reference point to continue with Phase 2.", parent=self.winfo_toplevel())
                self._focus_window()
        else:
            # This is legacy mode - show original behavior  
            self.btn_ref.config(state=tk.DISABLED)

            if os.path.exists(ra_file):
                redefine = messagebox.askyesno(
                    "Reference Point Exists",
                    "A reference point is already defined. Do you want to redefine it?",
                    parent=self.winfo_toplevel()
                )
                self._focus_window()
                if redefine:
                    ref_window = ReferencePointGUI(self.winfo_toplevel(), dem, self.ifgsroot)
                    # Wait for window to be visible before setting grab
                    self.wait_visibility(ref_window)
                    ref_window.grab_set()
                    self.wait_window(ref_window)
            else:
                ref_window = ReferencePointGUI(self.winfo_toplevel(), dem, self.ifgsroot)
                # Wait for window to be visible before setting grab
                self.wait_visibility(ref_window)
                ref_window.grab_set()
                self.wait_window(ref_window)

            # Legacy mode - just enable controls
            self.show_unwrap_controls()

    def _validate_float(self, value):
            if value == "":
                return True
            try:
                float(value)
                return True
            except ValueError:
                return False
    
    def show_phase1_controls(self):
        """Show Phase 1 unwrapping controls (correlation threshold, cores, run button)"""
        if self._controls_packed:
            return  # Already shown
            
        if not self.controls_inner_frame:
            self.controls_inner_frame = tk.Frame(self.controls_frame)
            self.controls_inner_frame.pack(anchor="w", padx=20, pady=5, fill="x")

        # Phase 1 Header
        phase1_label = tk.Label(self.controls_inner_frame, text="Phase 1: Unwrapping", font=("Arial", 10, "bold"))
        phase1_label.pack(anchor="w", pady=(5, 0))

        # Create row frame for controls
        row_frame = tk.Frame(self.controls_inner_frame)
        row_frame.pack(anchor="w", pady=5, fill="x")

        # Correlation threshold
        tk.Label(row_frame, text="Correlation Threshold:").pack(side="left")
        if not hasattr(self, 'corr_var'):
            self.corr_var = tk.StringVar(value="0.01")
        corr_entry = tk.Entry(row_frame, textvariable=self.corr_var, width=8, validate="key")
        corr_entry.config(validatecommand=(corr_entry.register(self._validate_float), '%P'))
        corr_entry.pack(side="left", padx=(5, 15))
        add_tooltip(corr_entry, "Enter correlation threshold (0.0-1.0)\nTypical values: 0.01-0.1\nLower values = more pixels unwrapped")

        # Cores
        tk.Label(row_frame, text="Cores:").pack(side="left")
        if not hasattr(self, 'cores_var') or self.cores_var is None:
            available_cores = os.cpu_count() or 1
            default_cores = max(1, available_cores - 1)
            self.cores_var = tk.StringVar(value=str(default_cores))
        cores_entry = tk.Entry(row_frame, textvariable=self.cores_var, width=8)
        cores_entry.pack(side="left", padx=5)
        add_tooltip(cores_entry, f"Number of CPU cores for parallel processing\nAvailable cores: {os.cpu_count()}\nRecommended: Leave 1 core for system")

        # Run Phase 1 button
        self.phase1_btn = tk.Button(self.controls_inner_frame, text="Run Phase 1: Unwrap + Create Validity", 
                                  command=self.run_phase1_unwrapping_ui, bg="orange")
        self.phase1_btn.pack(anchor="w", pady=5)
        add_tooltip(self.phase1_btn, "Start Phase 1: Unwrap interferograms and create validity raster\nThis enables Phase 2 reference point selection")
        
        self._controls_packed = True
            
    def show_unwrap_controls(self):
        self.btn_ref.config(bg="green", state=tk.DISABLED)
        if not self.controls_inner_frame:
            self.controls_inner_frame = tk.Frame(self.controls_frame)
            self.controls_inner_frame.pack(anchor="w", padx=20, pady=5, fill="x")

        # Correlation threshold
        if not self.corr_label:
            self.corr_label = tk.Label(self.controls_inner_frame, text="Correlation Threshold:")
            add_tooltip(self.corr_label, "Minimum coherence threshold for unwrapping\nPixels below this value will be masked")
        if not hasattr(self, 'corr_var'):
            self.corr_var = tk.StringVar(value="0.01")
        if not self.corr_entry:
            self.corr_entry = tk.Entry(self.controls_inner_frame, textvariable=self.corr_var, width=8, validate="key")
            self.corr_entry.config(validatecommand=(self.corr_entry.register(self._validate_float), '%P'))
            add_tooltip(self.corr_entry, "Enter correlation threshold (0.0-1.0)\nTypical values: 0.01-0.1\nLower values = more pixels unwrapped")

        # Cores
        if not self.cores_label:
            self.cores_label = tk.Label(self.controls_inner_frame, text="Cores:")
            add_tooltip(self.cores_label, "Number of CPU cores for parallel processing")
        if not self.cores_var:
            available_cores = os.cpu_count() or 1
            default_cores = max(1, available_cores - 1)
            self.cores_var = tk.StringVar(value=str(default_cores))
        if not self.cores_entry:
            self.cores_entry = tk.Entry(self.controls_inner_frame, textvariable=self.cores_var, width=5)
            add_tooltip(self.cores_entry, f"Number of CPU cores to use\nAvailable cores: {os.cpu_count()}\nRecommended: Leave 1 core for system")

        # Incidence angle (only if gacosdir is not None)        
        if self.gacosdir is not None and not self.inc_label:
            self.inc_label = tk.Label(self.controls_inner_frame, text="Incidence Angle:")
            add_tooltip(self.inc_label, "Radar incidence angle for GACOS atmospheric correction\nUsed to convert LOS displacement to vertical")
            self.inc_var = tk.StringVar(value="37")
            self.inc_entry = tk.Entry(
            self.controls_inner_frame,
            textvariable=self.inc_var,
            width=8,
            validate="key"
            )
            self.inc_entry.config(validatecommand=(self.inc_entry.register(self._validate_float), '%P'))
            add_tooltip(self.inc_entry, "Enter incidence angle in degrees\nTypical range for Sentinel-1: 29-46°\nCheck product metadata for exact value")

        # Place controls
        if not self._controls_packed:
            col = 0
            self.corr_label.grid(row=0, column=col, sticky="w", padx=(0, 5), pady=2)
            col += 1
            self.corr_entry.grid(row=0, column=col, sticky="w", padx=(0, 15), pady=2)
            col += 1
            self.cores_label.grid(row=0, column=col, sticky="w", padx=(0, 5), pady=2)
            col += 1
            self.cores_entry.grid(row=0, column=col, sticky="w", pady=2)
            if self.gacosdir is not None:
                # Place incidence label and entry in next row, first and second columns
                self.inc_label.grid(row=1, column=0, sticky="w", padx=(0, 5), pady=2)
                self.inc_entry.grid(row=1, column=1, sticky="w", padx=(0, 15), pady=2)
                self._controls_packed = True

        if not self.unwrap_btn:
            self.unwrap_btn = tk.Button(self.controls_frame, text="Unwrap", command=self.run_unwrap)
            self.unwrap_btn.pack(pady=15, padx=20, anchor="w")
            add_tooltip(self.unwrap_btn, "Start phase unwrapping process\nButton color indicates status:\n• Default: Ready to start\n• Yellow: Processing\n• Green: Completed successfully\n• Red: Error occurred")

    def run_unwrap(self):
        threshold = self.corr_entry.get() if self.corr_entry else ""
        ncores = self.cores_var.get() if self.cores_var else 1

        if not threshold:
            self._show_error("Please enter a correlation threshold.")
            return
        try:
            threshold = float(threshold)
        except ValueError:
            self._show_error("Correlation threshold must be a number.")
            return
        try:
            ncores = int(ncores)
            if ncores < 1:
                raise ValueError
        except ValueError:
            self._show_error("Number of cores must be a positive integer.")
            return

        self.ncores = ncores
        self.unwrap_btn.config(state=tk.DISABLED, bg="yellow")
        self.master.withdraw()

        # Run Phase 1: Unwrapping only
        self.run_phase1_unwrapping(threshold, ncores)

    def run_phase1_unwrapping_ui(self):
        """UI wrapper for Phase 1 unwrapping"""
        try:
            threshold = float(self.corr_var.get())
            if threshold <= 0 or threshold > 1:
                raise ValueError
        except ValueError:
            self._show_error("Correlation threshold must be a number between 0 and 1.")
            return
        
        try:
            # Safety check for cores_var
            if self.cores_var is None:
                available_cores = os.cpu_count() or 1
                default_cores = max(1, available_cores - 1)
                self.cores_var = tk.StringVar(value=str(default_cores))
            
            ncores = int(self.cores_var.get())
            if ncores < 1:
                raise ValueError
        except (ValueError, AttributeError):
            self._show_error("Number of cores must be a positive integer.")
            return

        # Check if unwrapping is needed or just validity creation
        if hasattr(self, '_needs_validity') and self._needs_validity:
            # All interferograms are unwrapped, just need validity file
            result = messagebox.askyesno(
                "Validity File Missing",
                f"Found {self._unwrapped_count} unwrapped interferograms but validity_pin.grd is missing.\n\n"
                "The validity raster tracks which pixels have valid unwrapped values across interferograms.\n"
                "This is needed for proper reference point selection and GACOS processing.\n\n"
                "Do you want to create the validity raster now?",
                parent=self.winfo_toplevel()
            )
            if not result:
                return
            
            # Just create validity raster
            self.phase1_btn.config(state=tk.DISABLED, text="Creating Validity Raster...", bg="yellow")
            self._create_validity_raster_threaded()
        else:
            # Normal unwrapping flow
            self.ncores = ncores
            self.phase1_btn.config(state=tk.DISABLED, text="Running Phase 1...", bg="yellow")
            self.run_phase1_unwrapping(threshold, ncores)

    def run_phase1_unwrapping(self, threshold, ncores):
        """Phase 1: Unwrapping and validity raster creation"""
        
        # Log the start of unwrapping
        if self.log_file:
            process_logger(process_num=5, log_file=self.log_file, message="Starting phase unwrapping sequence (Phase 1: Unwrapping)...", mode="start")

        def unwrap_worker():
            try:
                # Process 5.1: Parallel Phase Unwrapping + Validity Raster
                if self.log_file:
                    process_logger(process_num=5.1, log_file=self.log_file, message="Starting parallel phase unwrapping process...", mode="start")
                print("Starting unwrapping in parallel...")
                self.parall_unwrap(threshold, ncores)
                if self.log_file:
                    process_logger(process_num=5.1, log_file=self.log_file, message="Parallel phase unwrapping process completed.", mode="end")
                
                # Complete Phase 1
                if self.log_file:
                    process_logger(process_num=5, log_file=self.log_file, message="Phase 1 (unwrapping and validity raster) completed.", mode="end")
                    
                self.master.after(0, lambda: [
                    self.phase1_btn.config(bg="green", state=tk.DISABLED, text="Phase 1 Complete ✓") if hasattr(self, 'phase1_btn') and self.phase1_btn else None,
                    self.show_phase1_completion(),
                    self.master.deiconify(),
                    self.master.lift(),
                    self.master.focus_force()
                ])
            except Exception as e:
                error_msg = str(e)  # Capture exception message
                self.master.after(0, lambda: [
                    self.phase1_btn.config(bg="red", state=tk.NORMAL, text="Run Phase 1: Unwrap + Create Validity") if hasattr(self, 'phase1_btn') and self.phase1_btn else None,
                    messagebox.showerror("Unwrapping Error", f"An error occurred in Phase 1: {error_msg}", parent=self.master),
                    self.master.deiconify(),
                    self.master.lift(),
                    self.master.focus_force()
                ])

        threading.Thread(target=unwrap_worker, daemon=True).start()

    def show_phase1_completion(self):
        """Show completion message and enable Phase 2"""
        # Mark that Phase 1 is completed
        self._phase1_completed = True
        
        completion_msg = ("Phase 1 Complete!\n\n"
                         "✓ Phase unwrapping completed\n"
                         "✓ Validity raster created\n\n"
                         "Ready to proceed to Phase 2:\n"
                         "Define reference point and normalize interferograms")
        
        messagebox.showinfo("Phase 1 Complete", completion_msg, parent=self.master)
        
        # Update Phase 1 button to show completion
        if hasattr(self, 'phase1_btn'):
            self.phase1_btn.config(state=tk.DISABLED, text="Phase 1 Complete ✓", bg="green")
        
        # Enable the "Define Reference Point" button for Phase 2
        self.btn_ref.config(state=tk.NORMAL, text="Phase 2: Define Reference Point", bg="orange")
        
    def run_phase2_normalization(self):
        """Phase 2: Reference point definition and normalization"""
        
        if not self.gacosdir:
            # No GACOS, just run normalization
            self.start_phase2_normalization()
        else:
            # With GACOS, get incidence angle first
            incidence = self.inc_var.get() if self.inc_var else None
            if not incidence:
                self._show_error("Please enter an incidence angle for GACOS correction.")
                return
            try:
                incidence = float(incidence)
                self.incidence = incidence
                self.start_phase2_normalization()
            except ValueError:
                self._show_error("Incidence angle must be a float.")
                return

    def start_phase2_normalization(self):
        """Start the normalization and GACOS processes"""
        self.btn_ref.config(state=tk.DISABLED, bg="yellow")
        self.master.withdraw()

        # Log the start of Phase 2
        if self.log_file:
            process_logger(process_num="5.Phase2", log_file=self.log_file, message="Starting Phase 2 (normalization and GACOS)...", mode="start")

        def phase2_worker():
            try:
                # Process 5.2: Post-processing/Normalization
                if self.log_file:
                    process_logger(process_num=5.2, log_file=self.log_file, message="Starting unwrapped files normalization process...", mode="start")
                print("Normalizing unwrapped files...")
                self.post_unwrap(self.ifgsroot)
                if self.log_file:
                    process_logger(process_num=5.2, log_file=self.log_file, message="Unwrapped files normalization process completed.", mode="end")
                
                # Process 5.3: GACOS Atmospheric Correction (only if gacosdir is available)
                if self.gacosdir and self.gacosdir.strip():
                    if self.log_file:
                        process_logger(process_num=5.3, log_file=self.log_file, message="Starting GACOS atmospheric correction process...", mode="start")
                    print("Starting GACOS correction...")
                    self.run_gacos()
                    if self.log_file:
                        process_logger(process_num=5.3, log_file=self.log_file, message="GACOS atmospheric correction process completed.", mode="end")
                else:
                    if self.log_file:
                        process_logger(process_num=5.3, log_file=self.log_file, message="GACOS atmospheric correction skipped - no GACOS directory specified.", mode="end")
                    print("GACOS directory not specified. Skipping GACOS atmospheric correction.")
                
                # Complete entire unwrapping sequence
                if self.log_file:
                    process_logger(process_num="5.Phase2", log_file=self.log_file, message="Phase 2 (normalization and GACOS) completed.", mode="end")
                    process_logger(process_num=5, log_file=self.log_file, message="Complete phase unwrapping sequence finished.", mode="end")
                    
                self.master.after(0, lambda: [
                    self.btn_ref.config(bg="green", state=tk.NORMAL, text="Phase 2 Complete"),
                    messagebox.showinfo("Unwrapping Complete", "Phase 2 Complete!\n\n✓ Reference point normalization completed\n✓ GACOS correction applied (if enabled)\n\nFull unwrapping sequence finished.", parent=self.master),
                    self.master.destroy()
                ])
            except Exception as e:
                error_msg = str(e)  # Capture exception message
                self.master.after(0, lambda: [
                    self.btn_ref.config(bg="red", state=tk.NORMAL, text="Phase 2: Define Reference Point"),
                    messagebox.showerror("Phase 2 Error", f"An error occurred in Phase 2: {error_msg}", parent=self.master),
                    self.master.deiconify(),
                    self.master.lift(),
                    self.master.focus_force()
                ])

        threading.Thread(target=phase2_worker, daemon=True).start()

    def run_gacos(self):
        # Check if GACOS path is available and valid
        if self.gacosdir is None or not self.gacosdir.strip():
            if self.log_file:
                process_logger(process_num=5.3, log_file=self.log_file, 
                             message="GACOS atmospheric correction skipped - no GACOS directory specified.", mode="end")
            print("GACOS directory not specified. Skipping GACOS atmospheric correction.")
            return
        
        if not os.path.exists(self.gacosdir):
            if self.log_file:
                process_logger(process_num=5.3, log_file=self.log_file, 
                             message=f"GACOS atmospheric correction skipped - GACOS directory does not exist: {self.gacosdir}", mode="end")
            print(f"GACOS directory does not exist: {self.gacosdir}. Skipping GACOS atmospheric correction.")
            return

        if None in [self.topodir, self.incidence, self.ifgsroot, self.ncores]:
            missing = [name for name, val in zip(
            ["topodir", "incidence", "ifgsroot", "ncores"],
            [self.topodir, self.incidence, self.ifgsroot, self.ncores]
            ) if val is None]
            print(f"The following variables are None: {', '.join(missing)}\nUnable to perform GACOS correction")
            if self.log_file:
                process_logger(process_num=5.3, log_file=self.log_file, 
                             message=f"GACOS correction skipped - missing parameters: {', '.join(missing)}", mode="end")

        else:
            # Pass log file information to gacos function for detailed logging
            gacos(self.gacosdir, self.topodir, self.incidence, self.ifgsroot, self.ncores, log_file=self.log_file)
        

    def post_unwrap(self, ifgsroot=None):
        base_unwrap = []
        ifgsroot = self.ifgsroot if self.ifgsroot else ifgsroot
        topo_dir = self.topodir
        ref_point_ra = os.path.join(topo_dir, "ref_point.ra")
        line = None
        print(f"Reading reference point from {ref_point_ra}...")
        if os.path.exists(ref_point_ra):
            with open(ref_point_ra, 'r') as f:
                line = f.readline().strip()
        if not line:
            print("Reference point not found.")
            return

        for root, dirs, _ in os.walk(ifgsroot):
            for dirname in dirs:
                d = os.path.join(root, dirname)
                if os.path.isdir(d):
                    uwp = os.path.join(d, "unwrap.grd")
                    base_unwrap.append(uwp)

        parts = line.split()
        if len(parts) >= 2:
            x, y = parts[0], parts[1]
        else:
            x, y = None, None

        def process_unwrap_with_logging(unwrap_tuple):
            unwrap, ifg_index = unwrap_tuple
            process_num = f"5.2.{ifg_index}"  # 5.2.1, 5.2.2, etc.
            ifg_name = os.path.basename(os.path.dirname(unwrap))
            
            start_time = datetime.now()
            
            out = os.path.join(os.path.dirname(unwrap), "unwrap_pin.grd")
            if not os.path.exists(out):
                try:
                    # Use grdtrack to extract value at reference point
                    # -Z outputs only the value, no coordinates
                    result = subprocess.run(
                        ["gmt", "grdtrack", ref_point_ra, f"-G{unwrap}", "-Z"],
                        text=True,
                        capture_output=True,
                        check=True
                    )
                    
                    phase_value_str = result.stdout.strip()
                    
                    # Check if the result is NaN or invalid
                    if not phase_value_str or phase_value_str.lower() == 'nan' or phase_value_str == '*':
                        print(f"Reference point is not valid in {ifg_name} (NaN/masked area). Skipping normalization.")
                        if self.log_file:
                            process_logger_consolidated(
                                process_num=process_num, 
                                message=f"Normalization for {ifg_name} skipped - invalid reference point (NaN/masked)", 
                                log_file=self.log_file,
                                start_time=start_time
                            )
                        return
                    
                    a = float(phase_value_str)
                    
                    # Perform normalization by subtracting reference value
                    subprocess.run([
                        "gmt", "grdmath", str(unwrap), str(a), "SUB", "=", str(out)
                    ], check=True)
                    
                    print(f"{ifg_name} normalized through Reference Point (ref value: {a:.4f})")
                    if self.log_file:
                        process_logger_consolidated(
                            process_num=process_num, 
                            message=f"Normalization for interferogram {ifg_name} completed successfully (ref value: {a:.4f})", 
                            log_file=self.log_file,
                            start_time=start_time
                        )
                except Exception as e:
                    print(f"Error processing {unwrap}: {e}")
                    if self.log_file:
                        process_logger_consolidated(
                            process_num=process_num, 
                            message=f"Normalization for {ifg_name} failed: {str(e)}", 
                            log_file=self.log_file,
                            start_time=start_time
                        )
            else:
                print(f"{ifg_name} already normalized.")
                if self.log_file:
                    process_logger_consolidated(
                        process_num=process_num, 
                        message=f"Normalization for {ifg_name} skipped - already normalized", 
                        log_file=self.log_file,
                        start_time=start_time
                    )

        # Create tuples with indices for logging
        unwrap_tuples = [(unwrap, i+1) for i, unwrap in enumerate(base_unwrap)]
        
        with ThreadPool(processes=self.ncores) as pool:
            pool.map(process_unwrap_with_logging, unwrap_tuples)

    def parall_unwrap(self, threshold, ncores):
        intfdir = self.ifgsroot
        IFGs = self.ifgs if self.ifgs else [
            os.path.join(intfdir, d)
            for d in next(os.walk(intfdir))[1]
            if os.path.exists(os.path.join(intfdir, d, 'phasefilt.grd'))
        ]
        
        # Count total IFGs and existing unwrapped IFGs
        total_ifgs = len(IFGs)
        existing_unwrap = []
        for ifg_dir in IFGs:
            unwrap_file = os.path.join(ifg_dir, "unwrap.grd")
            if os.path.exists(unwrap_file):
                existing_unwrap.append(unwrap_file)
        
        existing_count = len(existing_unwrap)
        validity_exists = os.path.exists(os.path.join(self.ifgsroot, "validity_pin.grd"))
        
        print(f"Total IFGs to process: {total_ifgs}")
        print(f"Already unwrapped: {existing_count}")
        print(f"Validity raster exists: {validity_exists}")
        
        # Determine what needs to be done
        if existing_count == total_ifgs:
            if validity_exists:
                print("All interferograms already unwrapped and validity raster exists. Skipping process 5.1.")
                return
            else:
                print("All interferograms unwrapped but validity raster missing. Creating validity raster only.")
                self.create_validity_raster()
                return
        elif existing_count > 0:
            print(f"Partial unwrapping detected: {existing_count}/{total_ifgs} interferograms unwrapped.")
            print("Continuing with remaining interferograms...")
        
        # Filter IFGs to only process those not yet unwrapped
        IFGs_to_unwrap = [
            ifg_dir for ifg_dir in IFGs 
            if not os.path.exists(os.path.join(ifg_dir, "unwrap.grd"))
        ]
        
        os.chdir(intfdir)
        mask_path = os.path.join(intfdir, "mask_def.grd")
        if os.path.exists(mask_path):
            for subdir in IFGs_to_unwrap:
                link_path = os.path.join(subdir, "mask_def.grd")
                if not os.path.exists(link_path):
                    try:
                        os.symlink(mask_path, link_path)
                    except FileExistsError:
                        pass
        
        print(f"Number of IFGs to be unwrapped: {len(IFGs_to_unwrap)}/{total_ifgs}")
        
        if not IFGs_to_unwrap:
            print("No additional IFGs to unwrap.")
            # Check if validity raster needs to be created
            if not validity_exists:
                print("Creating validity raster...")
                self.create_validity_raster()
            return

        # Build unwrap commands
        unwrap_commands = []
        for i, ifg_dir in enumerate(IFGs_to_unwrap, 1):
            cmd = f"cd {ifg_dir} && snaphu_interp.csh {threshold} 0"            
            cmd += " && cd .."
            unwrap_commands.append((cmd, i))  # Include index for logging

        # Create wrapper function for logged execution
        def execute_with_logging(cmd_tuple):
            cmd, ifg_index = cmd_tuple
            process_num = f"5.1.{ifg_index}"  # 5.1.1, 5.1.2, etc.
            ifg_name = os.path.basename(IFGs_to_unwrap[ifg_index - 1])
            
            start_time = datetime.now()
            
            try:
                execute_command(cmd)
                if self.log_file:
                    process_logger_consolidated(
                        process_num=process_num, 
                        message=f"Unwrapping for interferogram {ifg_name} completed successfully", 
                        log_file=self.log_file,
                        start_time=start_time
                    )
            except Exception as e:
                if self.log_file:
                    process_logger_consolidated(
                        process_num=process_num, 
                        message=f"Unwrapping for interferogram {ifg_name} failed: {str(e)}", 
                        log_file=self.log_file,
                        start_time=start_time
                    )
                raise

        with ThreadPool(processes=ncores) as pool:
            pool.map(execute_with_logging, unwrap_commands)
        
        # Create validity raster after all unwrapping is complete
        self.create_validity_raster()

    def create_validity_raster(self):
        """Create validity_pin.grd showing count of valid pixels across all unwrapped interferograms"""
        validity_path = os.path.join(self.ifgsroot, "validity_pin.grd")
        
        if os.path.exists(validity_path):
            print(f"Validity raster already exists: {validity_path}")
            return
        
        # Find all unwrap.grd files using the known interferogram list
        unwrap_files = []
        for ifg in self.ifgs:
            unwrap_file = os.path.join(self.ifgsroot, ifg, "unwrap.grd")
            if os.path.exists(unwrap_file):
                unwrap_files.append(unwrap_file)
        
        print(f"Found {len(unwrap_files)} unwrapped interferogram files from known ifg list")
        
        if not unwrap_files:
            print("No unwrapped interferograms found for validity raster creation")
            return
        
        print(f"Creating validity raster from {len(unwrap_files)} unwrapped interferograms...")
        
        try:
            # Create binary masks in parallel
            mask_files = []
            mask_commands = []
            
            for i, uwp_file in enumerate(unwrap_files):
                mask_file = os.path.join(os.path.dirname(uwp_file), f"temp_valid_mask_{i}.grd")
                mask_files.append(mask_file)
                # Create binary mask: 1 where data exists, 0 where NaN
                cmd = f"gmt grdmath {uwp_file} ISNAN 0 EQ = {mask_file}"
                mask_commands.append(cmd)
            
            # Execute mask creation in parallel with progress tracking
            print(f"Creating {len(mask_commands)} binary masks using {self.ncores} cores...")
            try:
                with ThreadPool(processes=min(self.ncores, 4)) as pool:  # Limit cores to prevent overload
                    results = pool.map(execute_command, mask_commands)
                print("Binary mask creation completed")
            except Exception as e:
                print(f"Error in parallel mask creation: {e}")
                raise
            
            # Sum all masks to create validity count
            print("Combining binary masks...")
            if len(mask_files) == 1:
                # Only one file, just copy it
                import shutil
                print("Single mask file - copying to validity raster")
                shutil.copy2(mask_files[0], validity_path)
            else:
                # Start with first mask (copy it)
                import shutil
                print("Starting with first mask file")
                shutil.copy2(mask_files[0], validity_path)
                
                # Add remaining masks
                print(f"Adding {len(mask_files)-1} remaining masks...")
                for i, mask_file in enumerate(mask_files[1:], 1):
                    if i % 10 == 0:  # Progress every 10 files
                        print(f"Processing mask {i}/{len(mask_files)-1}")
                    temp_path = os.path.join(self.ifgsroot, "temp_validity.grd")
                    try:
                        subprocess.run([
                            "gmt", "grdmath", validity_path, mask_file, "ADD", "=", temp_path
                        ], check=True, capture_output=True)
                        # Replace the original validity file with the sum
                        shutil.move(temp_path, validity_path)
                    except subprocess.CalledProcessError as e:
                        print(f"Error adding mask {mask_file}: {e}")
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        raise
            
            # Cleanup temporary mask files
            for mask_file in mask_files:
                try:
                    os.remove(mask_file)
                except:
                    pass
            
            print(f"Validity raster created successfully: {validity_path}")
            print(f"Pixel values range from 0 to {len(unwrap_files)} representing number of valid observations")
            
        except Exception as e:
            print(f"Error creating validity raster: {e}")
            # Cleanup on error
            for mask_file in mask_files:
                try:
                    os.remove(mask_file)
                except:
                    pass

    def _create_validity_raster_only(self):
        """Create validity raster for already unwrapped interferograms"""
        try:
            # Set a default number of cores if not already set
            if not hasattr(self, 'ncores') or self.ncores is None:
                self.ncores = 4
            
            self.create_validity_raster()
            messagebox.showinfo(
                "Validity Raster Created", 
                "Validity raster created successfully!\n\nYou can now proceed with reference point selection.",
                parent=self.winfo_toplevel()
            )
            # Mark phase 1 as completed since unwrapping and validity are both done
            self._phase1_completed = True
        except Exception as e:
            messagebox.showerror(
                "Error Creating Validity Raster",
                f"Failed to create validity raster:\n{str(e)}\n\nYou may need to check the unwrapped interferograms.",
                parent=self.winfo_toplevel()
            )
    
    def _create_validity_raster_threaded(self):
        """Create validity raster in background thread to avoid blocking"""
        import threading
        
        def validity_worker():
            try:
                # Set a default number of cores if not already set
                if not hasattr(self, 'ncores') or self.ncores is None:
                    self.ncores = 4
                
                print("Starting validity raster creation in background...")
                self.create_validity_raster()
                
                # Update UI in main thread
                self.master.after(0, self._on_validity_success)
            except Exception as e:
                error_msg = str(e)
                # Update UI in main thread
                self.master.after(0, lambda: self._on_validity_error(error_msg))
        
        threading.Thread(target=validity_worker, daemon=True).start()
    
    def _on_validity_success(self):
        """Called when validity creation succeeds"""
        self.phase1_btn.config(state=tk.DISABLED, text="Phase 1 Complete ✓", bg="green")
        self._phase1_completed = True
        messagebox.showinfo(
            "Validity Raster Created", 
            "Validity raster created successfully!\n\nYou can now proceed with reference point selection.",
            parent=self.winfo_toplevel()
        )
        # Enable reference point button
        self.btn_ref.config(state=tk.NORMAL, text="Phase 2: Define Reference Point", bg="orange")
    
    def _on_validity_error(self, error_msg):
        """Called when validity creation fails"""
        self.phase1_btn.config(state=tk.NORMAL, text="Run Phase 1: Unwrap + Create Validity", bg="orange")
        messagebox.showerror(
            "Error Creating Validity Raster",
            f"Failed to create validity raster:\n{error_msg}\n\nYou may need to check the unwrapped interferograms.",
            parent=self.winfo_toplevel()
        )

    def _show_error(self, msg):
        messagebox.showerror("Input Error", msg, parent=self.winfo_toplevel())
        self._focus_window()

    def _focus_window(self):
        self.winfo_toplevel().lift()
        self.winfo_toplevel().focus_force()
