"""
Data Handlers module for InSARLite.
Handles data processing, file management, and data-related operations.
"""

import os
import tkinter as tk
from tkinter import messagebox
from typing import List, Dict, Tuple, Optional, Any
from .file_operations import (
    get_safe_and_zip_files, summarize_polarizations_from_files,
    extract_zip_files_with_progress, extract_extent_from_zip_manifests
)
from .gui_helpers import disable_extent_editing, set_extent_entry_values


class DataHandlers:
    """Handles data-related operations and file management."""
    
    @staticmethod
    def handle_safe_dirs_found(app_instance, folder: str, safe_dirs: List[str], 
                              dir_pol_summary: Dict, zip_pol_summary: Dict) -> None:
        """Handle when SAFE directories are found."""
        from ..utils.utils import extr_ext_TL, add_tooltip
        
        app_instance._set_data_browse_bg("green")
        app_instance._set_controls_state("normal")
        
        # Setup controls
        app_instance._setup_subswath_controls(safe_dirs, zip_files=None)
        app_instance._setup_polarization_controls(dir_pol_summary, zip_pol_summary)
        
        # Hide buttons
        if hasattr(app_instance, "data_query_btn") and app_instance.data_query_btn is not None and app_instance.data_query_btn.winfo_exists():
            app_instance.hide_query_btn()
        app_instance.hide_download_btn()
        
        # Hide extraction button when SAFE dirs are found
        if hasattr(app_instance, 'hide_extract_btn'):
            app_instance.hide_extract_btn()

        # Extract metadata
        max_bounds, sdate, edate, fdirection = extr_ext_TL(folder)
        
        if max_bounds:
            app_instance._draw_custom_shape_and_labels(max_bounds)
        if sdate:
            app_instance.date_limits["sdate"] = sdate
            app_instance.sdate_label = tk.Label(app_instance.date_frame, text=sdate, fg="green")
            app_instance.sdate_label.grid(row=0, column=2, sticky="w", padx=(4, 0))
            # Set the start date in the GUI
            app_instance.start_var.set(str(sdate))
        if edate:
            app_instance.date_limits["edate"] = edate
            app_instance.edate_label = tk.Label(app_instance.date_frame, text=edate, fg="green")
            app_instance.edate_label.grid(row=0, column=6, sticky="w", padx=(4, 0))
            # Set the end date in the GUI
            app_instance.end_var.set(str(edate))
            app_instance.date_limits["edate"] = edate
            app_instance.edate_label = tk.Label(app_instance.date_frame, text=edate, fg="green")
            app_instance.edate_label.grid(row=0, column=6, sticky="w", padx=(4, 0))
        if fdirection:
            app_instance.flight_dir_var.set(fdirection)
            app_instance.ascending_rb.config(state="disabled")
            app_instance.descending_rb.config(state="disabled")
            
        app_instance.safe_dirs_label = tk.Label(app_instance.root, text=f"{len(safe_dirs)} imgs found", fg="green")
        app_instance.safe_dirs_label.grid(row=app_instance._get_row("data_folder"), column=3, sticky="w", padx=(0, 2))

        if sdate and edate:
            app_instance.total_imgs_label = tk.Label(app_instance.date_frame, text=f"Total IMGs: {len(safe_dirs)}", fg="green")
            app_instance.total_imgs_label.grid(row=0, column=7, sticky="w", padx=(8, 0))

        # Show DEM controls when Load button turns green with SAFE directories
        app_instance._show_dem_entry_and_browse()

    @staticmethod
    def handle_zip_files_found(app_instance, folder: str, zip_files: List[str], 
                              zip_pol_summary: Dict) -> None:
        """Handle when ZIP files are found."""
        app_instance.zip_prompted = True
        app_instance._set_data_browse_bg("yellow")
        app_instance._set_controls_state("normal")
        
        # Setup controls for user to select subswaths and polarization
        app_instance._setup_polarization_controls(dir_pol_summary=None, zip_pol_summary=zip_pol_summary)
        app_instance._setup_subswath_controls(safe_dirs=None, zip_files=zip_files)
        
        # Show data query button
        app_instance.show_query_btn()
        app_instance._update_data_query_btn_state_wrapper()
        app_instance.hide_download_btn()
        
        # Try to extract extent from ZIP files
        try:
            extent = extract_extent_from_zip_manifests(zip_files)
            if extent:
                # Store the extent limits for validation
                app_instance.extent_limits.update(extent)
                
                # Display extent information 
                app_instance._display_extent_labels(extent)
                app_instance._draw_extent_rectangle(extent)
                
                # Disable extent editing since it's derived from ZIP files
                disable_extent_editing(app_instance.n_entry, app_instance.s_entry, 
                                     app_instance.e_entry, app_instance.w_entry)
                
                # Set the extent values in the entry fields
                set_extent_entry_values(extent, app_instance.n_entry, app_instance.s_entry,
                                      app_instance.e_entry, app_instance.w_entry)
                
                # Set flag to indicate extent was derived from ZIP files
                app_instance._zip_derived_values = True
                
                print(f"Derived extent from ZIP files: {extent}")
        except Exception as e:
            print(f"Could not derive extent from ZIP files: {e}")

        # Try to extract dates from ZIP files
        try:
            date_range = app_instance._get_dates_from_zip_files(zip_files)
            if date_range:
                sdate_str = date_range['start']
                edate_str = date_range['end']
                
                # Set date limits
                from datetime import datetime
                sdate = datetime.strptime(sdate_str, '%Y-%m-%d').date()
                edate = datetime.strptime(edate_str, '%Y-%m-%d').date()
                app_instance.date_limits["sdate"] = sdate
                app_instance.date_limits["edate"] = edate
                
                # Create and display date labels
                app_instance.sdate_label = tk.Label(app_instance.date_frame, text=sdate, fg="green")
                app_instance.sdate_label.grid(row=0, column=2, sticky="w", padx=(4, 0))
                app_instance.edate_label = tk.Label(app_instance.date_frame, text=edate, fg="green")
                app_instance.edate_label.grid(row=0, column=6, sticky="w", padx=(4, 0))
                
                # Set the dates in the GUI
                app_instance.start_var.set(sdate_str)
                app_instance.end_var.set(edate_str)
                
                print(f"Derived dates from ZIP files: {sdate_str} to {edate_str}")
        except Exception as e:
            print(f"Could not derive dates from ZIP files: {e}")

        # Show extraction controls
        app_instance._show_zip_extraction_controls()

    @staticmethod  
    def handle_mixed_safe_and_zip_files(app_instance, folder: str, safe_dirs: List[str], 
                                       zip_files: List[str], dir_pol_summary: Dict, 
                                       zip_pol_summary: Dict) -> None:
        """Handle the case where both ZIP files and SAFE directories are found."""
        num_zip_files = len(zip_files)
        num_safe_dirs = len(safe_dirs)
        
        # If there are more ZIP files than SAFE directories, prompt user for choice
        if num_zip_files > num_safe_dirs:
            result = messagebox.askyesno(
                "Mixed Data Found",
                f"Found {num_safe_dirs} extracted SAFE directories and {num_zip_files} ZIP files.\n\n"
                f"Since there are more ZIP files than extracted directories, "
                f"you may want to extract the ZIP files first.\n\n"
                f"Choose 'Yes' to proceed with existing SAFE directories (Load button turns green)\n"
                f"Choose 'No' to extract ZIP files first (Load button turns yellow)",
                icon="question"
            )
            
            if result:  # User chose to proceed with SAFE directories
                DataHandlers.handle_safe_dirs_found(app_instance, folder, safe_dirs, dir_pol_summary, zip_pol_summary)
            else:  # User chose to extract ZIP files
                DataHandlers.handle_zip_files_found(app_instance, folder, zip_files, zip_pol_summary)
        else:
            # If SAFE directories >= ZIP files, default to using SAFE directories
            DataHandlers.handle_safe_dirs_found(app_instance, folder, safe_dirs, dir_pol_summary, zip_pol_summary)

    @staticmethod
    def process_data_folder_change(app_instance, folder: str) -> None:
        """Process changes to the data folder."""
        if not folder or not os.path.exists(folder):
            app_instance._set_data_browse_bg("red")
            app_instance.show_query_btn()
            app_instance._update_data_query_btn_state_wrapper()
            app_instance._set_controls_state("normal")
            app_instance._clear_extent_and_date_labels()
            app_instance.hide_download_btn()
            app_instance._clear_dynamic_widgets_and_shapes()
            app_instance._setup_subswath_controls(None, None)
            app_instance._setup_polarization_controls(None, None)
            app_instance._show_output_folder_and_project_controls()
            return

        # Get SAFE directories and ZIP files
        safe_dirs, zip_files = get_safe_and_zip_files(folder)
        
        # Analyze existing SAFE directories
        safe_dirs_tiff = []
        for safe_dir in safe_dirs:
            measurement_dir = os.path.join(safe_dir, "measurement")
            if os.path.isdir(measurement_dir):
                tiff_files = [
                    os.path.join(measurement_dir, f)
                    for f in os.listdir(measurement_dir)
                    if f.lower().endswith(".tiff") and os.path.exists(os.path.join(measurement_dir, f))
                ]
                safe_dirs_tiff.extend(tiff_files)
        
        safe_dirs_tiff = list(dict.fromkeys(safe_dirs_tiff))
        dir_pol_summary = summarize_polarizations_from_files(safe_dirs_tiff)
        zip_pol_summary = summarize_polarizations_from_files(zip_files)

        if safe_dirs:
            DataHandlers.handle_safe_dirs_found(app_instance, folder, safe_dirs, dir_pol_summary, zip_pol_summary)
            return

        if zip_files and not safe_dirs and not getattr(app_instance, "zip_prompted", False):
            DataHandlers.handle_zip_files_found(app_instance, folder, zip_files, zip_pol_summary)
            return

        app_instance.zip_prompted = False

        if not safe_dirs and not zip_files:
            app_instance._set_data_browse_bg("red")
            app_instance.show_query_btn()
            app_instance._update_data_query_btn_state_wrapper()
            app_instance._set_controls_state("normal")
            app_instance._clear_extent_and_date_labels()
            app_instance.hide_download_btn()
            app_instance._clear_dynamic_widgets_and_shapes()
            app_instance._setup_subswath_controls(None, None)
            app_instance._setup_polarization_controls(None, None)
            app_instance._show_output_folder_and_project_controls()

    @staticmethod
    def perform_zip_extraction_optimized(app_instance, folder: str, selected_subswaths: List[int], 
                                        selected_pol: str) -> None:
        """Perform zip extraction using optimized external function."""
        try:
            safe_dirs, zip_files = get_safe_and_zip_files(folder)
            
            # Show immediate progress with total count
            def update_initial_progress():
                if hasattr(app_instance, '_extract_btn') and app_instance._extract_btn and app_instance._extract_btn.winfo_exists():
                    app_instance._extract_btn.config(text=f"Extracting 1/{len(zip_files)}")
            app_instance.root.after(0, update_initial_progress)
            
            def update_progress(current, total, skipped=False):
                if skipped:
                    text = f"Processing {current}/{total} (skipped identical)"
                else:
                    text = f"Extracting {current}/{total}"
                
                def update_ui():
                    if hasattr(app_instance, '_extract_btn') and app_instance._extract_btn and app_instance._extract_btn.winfo_exists():
                        app_instance._extract_btn.config(text=text)
                
                app_instance.root.after(0, update_ui)
            
            # Use the optimized extraction function
            extracted_count, skipped_count, failed_files, zip_stats = extract_zip_files_with_progress(
                zip_files, 
                folder, 
                selected_subswaths, 
                selected_pol,
                start_date=app_instance.start_var.get() if hasattr(app_instance, 'start_var') else None,
                end_date=app_instance.end_var.get() if hasattr(app_instance, 'end_var') else None,
                progress_callback=update_progress,
                quick_comparison=True  # Use fast size+timestamp comparison
            )
            
            print(f"Extraction complete: {extracted_count} extracted, {skipped_count} skipped, {len(failed_files)} failed")
            print(f"ZIP analysis: {zip_stats['successful_zips']}/{zip_stats['total_zips']} ZIP files processed successfully")
            
            def after_extraction():
                if hasattr(app_instance, '_extract_btn') and app_instance._extract_btn and app_instance._extract_btn.winfo_exists():
                    app_instance._extract_btn.config(state="normal", text="Extract Zip Files")
                if hasattr(app_instance, 'data_folder_entry') and app_instance.data_folder_entry and app_instance.data_folder_entry.winfo_exists():
                    app_instance.data_folder_entry.config(state="normal")
                
                # Handle failed files if any
                if failed_files:
                    failed_list = "\n".join(failed_files[:10])
                    if len(failed_files) > 10:
                        failed_list += f"\n... and {len(failed_files) - 10} more files"
                    
                    result = messagebox.askyesno(
                        "Some Files Failed",
                        f"Extraction completed with {len(failed_files)} failed files:\n\n{failed_list}\n\n"
                        f"Do you want to delete the corrupted files and continue?\n\n"
                        f"Successfully extracted: {extracted_count} files\n"
                        f"Skipped identical: {skipped_count} files",
                        icon="warning"
                    )
                    
                    if result:
                        deleted_count = 0
                        for failed_file in failed_files:
                            try:
                                os.remove(failed_file)
                                deleted_count += 1
                            except Exception as e:
                                print(f"Could not delete {failed_file}: {e}")
                        
                        messagebox.showinfo(
                            "Cleanup Complete",
                            f"Deleted {deleted_count} corrupted files.\n"
                            f"Successfully extracted {extracted_count} files.\n"
                            f"Skipped {skipped_count} identical files."
                        )
                else:
                    # Show comprehensive extraction summary
                    total_zips = zip_stats['total_zips']
                    successful_zips = zip_stats['successful_zips']
                    failed_zips = zip_stats['failed_zips']
                    
                    if failed_zips > 0:
                        # Show warning about failed ZIP files with option to delete them
                        failed_details = "\n".join(zip_stats['failed_zip_details'][:5])
                        if len(zip_stats['failed_zip_details']) > 5:
                            failed_details += f"\n... and {len(zip_stats['failed_zip_details']) - 5} more"
                        
                        message = (
                            f"Extraction completed with some issues:\n\n"
                            f"✓ ZIP files processed successfully: {successful_zips}/{total_zips}\n"
                            f"⚠ ZIP files failed/skipped: {failed_zips}\n\n"
                            f"Files extracted: {extracted_count}\n"
                            f"Files skipped (identical): {skipped_count}\n\n"
                            f"Failed ZIP files:\n{failed_details}\n\n"
                            f"Do you want to delete the failed ZIP files to free up space?"
                        )
                        
                        result = messagebox.askyesno(
                            "Extraction Complete with Issues", 
                            message,
                            icon="warning"
                        )
                        
                        if result:
                            # Delete failed ZIP files
                            deleted_count = 0
                            failed_zip_paths = []
                            
                            # Extract actual ZIP file paths from failed_files list
                            for failed_entry in failed_files:
                                if " (" in failed_entry:  # Format: "path (reason)"
                                    zip_path = failed_entry.split(" (")[0]
                                    if os.path.exists(zip_path) and zip_path.endswith('.zip'):
                                        failed_zip_paths.append(zip_path)
                            
                            for zip_path in failed_zip_paths:
                                try:
                                    os.remove(zip_path)
                                    deleted_count += 1
                                    print(f"Deleted failed ZIP file: {os.path.basename(zip_path)}")
                                except Exception as e:
                                    print(f"Could not delete {zip_path}: {e}")
                            
                            messagebox.showinfo(
                                "Cleanup Complete",
                                f"Deleted {deleted_count} failed ZIP files.\n\n"
                                f"✓ Successfully extracted: {extracted_count} files\n"
                                f"✓ Skipped identical: {skipped_count} files\n"
                                f"✓ Processed successfully: {successful_zips} ZIP files"
                            )
                        else:
                            messagebox.showinfo(
                                "Extraction Complete", 
                                f"Extraction finished.\n\n"
                                f"✓ ZIP files processed: {successful_zips}/{total_zips}\n"
                                f"✓ Files extracted: {extracted_count}\n"
                                f"ℹ Failed ZIP files kept for manual review."
                            )
                    else:
                        # All ZIP files processed successfully
                        if skipped_count > 0:
                            message = (
                                f"Extraction complete!\n\n"
                                f"✓ All {total_zips} ZIP files processed successfully\n"
                                f"✓ Files extracted: {extracted_count}\n"
                                f"✓ Files skipped (identical): {skipped_count}"
                            )
                        else:
                            message = (
                                f"Extraction complete!\n\n"
                                f"✓ All {total_zips} ZIP files processed successfully\n"
                                f"✓ All {extracted_count} files extracted successfully!"
                            )
                        messagebox.showinfo("Extraction Complete", message)
                
                # Clear legend entries and download controls
                app_instance._clear_legend()
                app_instance.hide_download_btn()
                if hasattr(app_instance, 'hide_extract_btn') and app_instance.hide_extract_btn:
                    app_instance.hide_extract_btn()
                
                # Refresh the folder view (this should turn the Load button green)
                app_instance._on_data_folder_change()
            
            app_instance.root.after(0, after_extraction)
            
        except Exception as e:
            error_msg = str(e)  # Capture exception message
            def after_error():
                if hasattr(app_instance, '_extract_btn') and app_instance._extract_btn and app_instance._extract_btn.winfo_exists():
                    app_instance._extract_btn.config(state="normal", text="Extract Zip Files")
                if hasattr(app_instance, 'data_folder_entry') and app_instance.data_folder_entry and app_instance.data_folder_entry.winfo_exists():
                    app_instance.data_folder_entry.config(state="normal")
                messagebox.showerror("Extraction Error", f"Failed to extract zip files: {error_msg}")
            
            app_instance.root.after(0, after_error)

    @staticmethod
    def get_selected_files_info(app_instance) -> Optional[List[Dict]]:
        """Get information about selected files for download."""
        if hasattr(app_instance, 'selected_files_info') and app_instance.selected_files_info:
            return app_instance.selected_files_info
        return None

    @staticmethod
    def validate_download_prerequisites(app_instance) -> Tuple[bool, str]:
        """Validate that download prerequisites are met."""
        files_info = DataHandlers.get_selected_files_info(app_instance)
        if not files_info:
            return False, "No files selected for download"
        
        folder = app_instance.data_folder_entry.get().strip()
        if not folder:
            return False, "No data folder specified"
        
        if not os.path.exists(folder):
            return False, f"Data folder does not exist: {folder}"
        
        return True, ""

    @staticmethod
    def clear_data_related_widgets(app_instance) -> None:
        """Clear all data-related widgets and states."""
        # Clear labels
        attrs = [
            "n_label", "s_label", "e_label", "w_label",
            "sdate_label", "edate_label", "safe_dirs_label", "total_imgs_label"
        ]
        for attr in attrs:
            widget = getattr(app_instance, attr, None)
            if widget and hasattr(widget, 'winfo_exists') and widget.winfo_exists():
                widget.destroy()
                setattr(app_instance, attr, None)
        
        # Clear extent limits and date limits
        app_instance.extent_limits.update(dict.fromkeys("swne"))
        app_instance.date_limits.update({"sdate": None, "edate": None})

    @staticmethod
    def reset_data_state(app_instance) -> None:
        """Reset data-related state variables."""
        app_instance.zip_prompted = False
        app_instance._zip_derived_values = False
        app_instance.selected_files_info = None
        app_instance.total_expected_size = None