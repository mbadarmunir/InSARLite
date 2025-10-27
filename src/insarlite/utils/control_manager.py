"""
Control Manager module for InSARLite.
Handles UI control state management and widget interactions.
"""

import tkinter as tk
from typing import Dict, List, Optional, Any


class ControlManager:
    """Manages UI control states and interactions."""
    
    @staticmethod
    def set_controls_state(controls: Dict[str, tk.Widget], state: str) -> None:
        """Set state for multiple controls."""
        for control_name, control in controls.items():
            if control and hasattr(control, 'winfo_exists') and control.winfo_exists():
                try:
                    control.config(state=state)
                except tk.TclError:
                    # Some widgets may not support state changes
                    pass

    @staticmethod
    def setup_subswath_controls(parent: tk.Widget, safe_dirs: List[str], zip_files: List[str], 
                               row_func, existing_frame=None) -> tuple:
        """Setup subswath selection controls."""
        import os
        
        # Clear existing frame if provided
        if existing_frame and existing_frame.winfo_exists():
            existing_frame.destroy()
        
        if safe_dirs:
            # Get unique subswaths from SAFE directories
            subswaths = set()
            for safe_dir in safe_dirs:
                measurement_dir = os.path.join(safe_dir, "measurement")
                if os.path.isdir(measurement_dir):
                    for f in os.listdir(measurement_dir):
                        if f.lower().endswith(".tiff"):
                            parts = f.split('-')
                            if len(parts) >= 2 and parts[1].startswith('iw'):
                                try:
                                    sw_num = int(parts[1][2])
                                    if 1 <= sw_num <= 3:
                                        subswaths.add(sw_num)
                                except (ValueError, IndexError):
                                    continue
        elif zip_files:
            # For ZIP files, assume all subswaths are available
            subswaths = {1, 2, 3}
        else:
            subswaths = set()
        
        if subswaths:
            from ..utils.utils import add_tooltip
            
            # Create subswath frame
            subswath_frame = tk.Frame(parent)
            subswath_frame.grid(row=row_func("subswath"), column=0, columnspan=6, sticky="ew", padx=5, pady=5)
            
            subswath_label = tk.Label(subswath_frame, text="Subswaths:")
            subswath_label.pack(side="left", padx=(0, 10))
            add_tooltip(subswath_label, "Select Sentinel-1 subswaths to process\nIW1, IW2, IW3 correspond to different swath positions")
            
            subswath_vars = {}
            checkboxes = {}
            
            for i in sorted(subswaths):
                var = tk.BooleanVar()
                var.set(True)  # Default to selected
                cb = tk.Checkbutton(subswath_frame, text=f"IW{i}", variable=var)
                cb.pack(side="left", padx=(0, 10))
                add_tooltip(cb, f"Interferometric Wide swath {i}\nEach subswath covers different ground area")
                
                subswath_vars[i] = var
                checkboxes[i] = cb
            
            return subswath_frame, subswath_vars, checkboxes
        
        return None, {}, {}

    @staticmethod
    def setup_polarization_controls(parent: tk.Widget, dir_pol_summary: Dict, zip_pol_summary: Dict,
                                   row_func, existing_widgets=None) -> tuple:
        """Setup polarization selection controls."""
        from ..utils.utils import add_tooltip
        
        # Remove existing polarization controls if they exist
        if existing_widgets:
            for widget in existing_widgets:
                if widget and hasattr(widget, 'winfo_exists') and widget.winfo_exists():
                    widget.destroy()
        
        # Combine polarization info from both sources
        combined_summary = {}
        if dir_pol_summary:
            combined_summary.update(dir_pol_summary)
        if zip_pol_summary:
            for pol, count in zip_pol_summary.items():
                combined_summary[pol] = combined_summary.get(pol, 0) + count
        
        if combined_summary:
            pol_frame = tk.Frame(parent)
            pol_frame.grid(row=row_func("polarization"), column=0, columnspan=6, sticky="ew", padx=5, pady=5)
            
            pol_label = tk.Label(pol_frame, text="Polarization:")
            pol_label.pack(side="left", padx=(0, 10))
            add_tooltip(pol_label, "Select radar polarization mode\nDifferent polarizations provide different information about targets")
            
            pol_var = tk.StringVar()
            
            # Set default polarization
            available_pols = list(combined_summary.keys())
            if 'VV' in available_pols:
                pol_var.set('VV')
            else:
                pol_var.set(available_pols[0])
            
            pol_controls = {}
            for pol in available_pols:
                count = combined_summary[pol]
                rb = tk.Radiobutton(pol_frame, text=f"{pol} ({count})", variable=pol_var, value=pol)
                rb.pack(side="left", padx=(0, 10))
                
                tooltip_text = {
                    'VV': "Vertical transmit, Vertical receive\nGood for surface roughness and vegetation",
                    'VH': "Vertical transmit, Horizontal receive\nSensitive to volume scattering",
                    'HH': "Horizontal transmit, Horizontal receive\nGood for surface features",
                    'HV': "Horizontal transmit, Vertical receive\nSensitive to vegetation structure"
                }.get(pol, f"{pol} polarization")
                
                add_tooltip(rb, f"{tooltip_text}\n{count} images available")
                pol_controls[pol] = rb
            
            return pol_frame, pol_var, pol_controls
        
        return None, None, {}

    @staticmethod
    def get_selected_subswaths(subswath_vars: Dict[int, tk.BooleanVar]) -> List[int]:
        """Get list of selected subswaths."""
        return [i for i, var in subswath_vars.items() if var.get()]

    @staticmethod
    def set_pol_controls_state(pol_controls: Dict[str, tk.Widget], state: str) -> None:
        """Set state for polarization controls."""
        for control in pol_controls.values():
            if control and hasattr(control, 'winfo_exists') and control.winfo_exists():
                try:
                    control.config(state=state)
                except tk.TclError:
                    pass

    @staticmethod
    def get_pol_controls_state(pol_controls: Dict[str, tk.Widget]) -> Dict[str, str]:
        """Get current state of polarization controls."""
        states = {}
        for pol, control in pol_controls.items():
            if control and hasattr(control, 'winfo_exists') and control.winfo_exists():
                try:
                    states[pol] = control.cget('state')
                except tk.TclError:
                    states[pol] = 'normal'
        return states

    @staticmethod
    def clear_dynamic_widgets_and_shapes(widgets_to_clear: List[tk.Widget], shapes_to_clear: List[Any]) -> None:
        """Clear dynamic widgets and map shapes."""
        # Clear widgets
        for widget in widgets_to_clear:
            if widget and hasattr(widget, 'winfo_exists') and widget.winfo_exists():
                widget.destroy()
        
        # Clear shapes
        for shape in shapes_to_clear:
            if shape and hasattr(shape, 'delete'):
                try:
                    shape.delete()
                except:
                    pass

    @staticmethod
    def show_query_btn(query_btn: tk.Button) -> None:
        """Show the data query button."""
        if query_btn and hasattr(query_btn, 'winfo_exists') and query_btn.winfo_exists():
            query_btn.grid(row=0, column=0, padx=5, pady=5)

    @staticmethod
    def hide_query_btn(query_btn: tk.Button) -> None:
        """Hide the data query button."""
        if query_btn and hasattr(query_btn, 'winfo_exists') and query_btn.winfo_exists():
            query_btn.grid_remove()

    @staticmethod
    def show_download_btn(download_btn: tk.Button) -> None:
        """Show the download button."""
        if download_btn and hasattr(download_btn, 'winfo_exists') and download_btn.winfo_exists():
            download_btn.grid(row=0, column=1, padx=5, pady=5)

    @staticmethod
    def hide_download_btn(download_btn: tk.Button) -> None:
        """Hide the download button."""
        if download_btn and hasattr(download_btn, 'winfo_exists') and download_btn.winfo_exists():
            download_btn.grid_remove()

    @staticmethod
    def update_data_query_btn_state(query_btn: tk.Button, extent_entries: List[tk.Entry], 
                                   data_browse_bg: str, show_query_func, hide_query_func) -> None:
        """Update data query button state based on extent validity."""
        if not query_btn or not query_btn.winfo_exists():
            return
            
        entries = [entry.get() for entry in extent_entries]
        valid = False
        if all(entries):
            try:
                n, s, e, w = map(float, entries)
                valid = (n > s) and (e > w)
            except ValueError:
                pass
        
        # Check if extent entries are disabled (meaning extent is set from zip files)
        extent_disabled = False
        if extent_entries and hasattr(extent_entries[0], 'cget'):
            try:
                extent_disabled = extent_entries[0].cget('state') == 'disabled'
            except:
                pass
        
        # If extent is disabled but has valid values (from zip files), allow querying
        if extent_disabled and valid:
            valid = True
        
        if data_browse_bg == "red":
            query_btn.config(state="normal" if valid else "disabled")
            show_query_func()
        else:
            hide_query_func()

    @staticmethod
    def create_output_folder_and_project_controls(parent: tk.Widget, row_func) -> tuple:
        """Create output folder and project name controls."""
        from ..utils.utils import add_tooltip, browse_folder
        
        # Output folder
        output_frame = tk.Frame(parent)
        output_frame.grid(row=row_func("output"), column=0, columnspan=6, sticky="ew", padx=5, pady=5)
        
        output_label = tk.Label(output_frame, text="Output Folder:")
        output_label.grid(row=0, column=0, sticky="e", padx=(0, 5))
        add_tooltip(output_label, "Directory where processing results will be saved")
        
        output_folder_entry = tk.Entry(output_frame, width=60)
        output_folder_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        output_frame.columnconfigure(1, weight=1)
        add_tooltip(output_folder_entry, "Choose output directory for InSAR processing results")
        
        browse_output = tk.Button(
            output_frame, 
            text="Browse", 
            command=lambda: browse_folder(output_folder_entry, "output_dir")
        )
        browse_output.grid(row=0, column=2, padx=(5, 0))
        add_tooltip(browse_output, "Browse and select output folder")
        
        # Project name
        project_frame = tk.Frame(parent)
        project_frame.grid(row=row_func("project"), column=0, columnspan=6, sticky="ew", padx=5, pady=5)
        
        project_label = tk.Label(project_frame, text="Project Name:")
        project_label.grid(row=0, column=0, sticky="e", padx=(0, 5))
        add_tooltip(project_label, "Unique identifier for this InSAR processing project")
        
        project_name_entry = tk.Entry(project_frame, width=30)
        project_name_entry.grid(row=0, column=1, sticky="w", padx=(0, 5))
        add_tooltip(project_name_entry, "Enter a descriptive name for your project\nUsed for organizing output files")
        
        return (output_frame, output_folder_entry, browse_output, 
                project_frame, project_name_entry)