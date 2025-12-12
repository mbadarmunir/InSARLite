"""
Configuration management utilities for InSARLite.
Handles loading, saving, and managing project configurations.
"""

import os
import json
from typing import Dict, Any, Optional, List
from tkinter import messagebox


class ConfigManager:
    """Manages InSARLite project configurations."""
    
    def __init__(self):
        self.config_path: Optional[str] = None
        self.projects_file = os.path.join(os.path.expanduser('~'), ".projs.json")
    
    def load_projects_list(self) -> List[Dict[str, str]]:
        """
        Load list of previous projects.
        
        Returns:
            List of project dictionaries
        """
        projects = []
        if os.path.exists(self.projects_file):
            try:
                with open(self.projects_file, "r") as f:
                    projects = json.load(f)
            except Exception:
                projects = []
        return projects
    
    def get_valid_projects(self) -> List[Dict[str, str]]:
        """
        Get list of valid projects (those that still exist on disk).
        
        Returns:
            List of valid project dictionaries
        """
        projects = self.load_projects_list()
        valid_projects = []
        
        for entry in projects:
            out_folder = entry.get("output_folder", "")
            proj_name = entry.get("project_name", "")
            conf_path = os.path.join(out_folder, proj_name, ".config.json")
            if os.path.isdir(os.path.join(out_folder, proj_name)) and os.path.isfile(conf_path):
                valid_projects.append(entry)
        
        # Update projects file to remove invalid entries
        if valid_projects != projects:
            self.save_projects_list(valid_projects)
        
        return valid_projects
    
    def save_projects_list(self, projects: List[Dict[str, str]]) -> None:
        """
        Save projects list to disk.
        
        Args:
            projects: List of project dictionaries
        """
        try:
            with open(self.projects_file, "w") as f:
                json.dump(projects, f, indent=2)
        except Exception as e:
            print(f"Failed to update .projs.json: {e}")
    
    def add_project_to_list(self, output_folder: str, project_name: str) -> None:
        """
        Add or update a project in the projects list.
        
        Args:
            output_folder: Output folder path
            project_name: Project name
        """
        projects = self.load_projects_list()
        entry = {"output_folder": output_folder, "project_name": project_name}
        
        # Add or update entry
        found = False
        for i, e in enumerate(projects):
            if e["output_folder"] == output_folder and e["project_name"] == project_name:
                projects[i] = entry
                found = True
                break
        if not found:
            projects.append(entry)
        
        self.save_projects_list(projects)
    
    def set_config_path(self, output_folder: str, project_name: str) -> None:
        """
        Set the configuration file path.
        
        Args:
            output_folder: Output folder path
            project_name: Project name
        """
        self.config_path = os.path.join(output_folder, project_name, ".config.json")
    
    def load_config(self) -> Optional[Dict[str, Any]]:
        """
        Load configuration from file.
        
        Returns:
            Configuration dictionary or None if loading fails
        """
        if not self.config_path or not os.path.exists(self.config_path):
            return None
        
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            messagebox.showinfo("Load Config", f"Failed to load configuration.\n\n{e}")
            return None
    
    def save_config(self, config_data: Dict[str, Any]) -> bool:
        """
        Save configuration to file only if values have changed.
        
        Args:
            config_data: Configuration dictionary to save
            
        Returns:
            True if successful, False otherwise
        """
        if not self.config_path:
            return False
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Load existing config
            existing_config = {}
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, "r") as f:
                        existing_config = json.load(f)
                except Exception:
                    existing_config = {}
            
            # Check if any project config parameter has changed
            project_params_changed = False
            for key, new_val in config_data.items():
                # Skip master-related keys for this check
                if key in ['master_selection_cache', 'mst', 'align_mode', 'esd_mode']:
                    continue
                if existing_config.get(key) != new_val:
                    project_params_changed = True
                    break
            
            # If any project parameter changed, update all project parameters and clear master data
            if project_params_changed:
                # Clear existing master-related data since project params changed
                master_keys = ['master_selection_cache', 'mst', 'align_mode', 'esd_mode']
                for master_key in master_keys:
                    if master_key in existing_config:
                        del existing_config[master_key]
                
                # Update project parameters (excluding master-related keys)
                for key, val in config_data.items():
                    if key not in master_keys:
                        existing_config[key] = val
                
                # Write to file
                with open(self.config_path, "w") as f:
                    json.dump(existing_config, f, indent=2)
                
                print(f"Saved config to {self.config_path}")
                print(f"⚠️  Project parameters changed - cleared master selection cache and alignment settings")
                return True
            else:
                print(f"Project config unchanged, skipping save")
                return False
            
        except Exception as e:
            print(f"Failed to save config: {e}")
            return False
    
    def create_config_from_gui_state(
        self,
        extent_entries: Dict[str, str],
        extent_limits: Dict[str, float],
        date_vars: Dict[str, str],
        date_limits: Dict[str, Any],
        flight_direction: str,
        data_folder: str,
        polarization: str,
        subswaths: List[int],
        dem_file: str,
        output_folder: str,
        project_name: str,
        gacos_folder: str = ""
    ) -> Dict[str, Any]:
        """
        Create configuration dictionary from GUI state.
        
        Args:
            extent_entries: Dictionary with extent entry values
            extent_limits: Dictionary with extent limits
            date_vars: Dictionary with date values
            date_limits: Dictionary with date limits
            flight_direction: Flight direction setting
            data_folder: Data folder path
            polarization: Polarization setting
            subswaths: List of selected subswaths
            dem_file: DEM file path
            output_folder: Output folder path
            project_name: Project name
            gacos_folder: GACOS folder path
            
        Returns:
            Configuration dictionary
        """
        from .file_operations import clamp
        
        # Clamp extent values
        try:
            n = clamp(extent_entries.get("n", ""), extent_limits.get("s"), extent_limits.get("n"))
            s = clamp(extent_entries.get("s", ""), extent_limits.get("s"), extent_limits.get("n"))
            e = clamp(extent_entries.get("e", ""), extent_limits.get("w"), extent_limits.get("e"))
            w = clamp(extent_entries.get("w", ""), extent_limits.get("w"), extent_limits.get("e"))
        except Exception:
            n = extent_entries.get("n", "")
            s = extent_entries.get("s", "")
            e = extent_entries.get("e", "")
            w = extent_entries.get("w", "")
        
        # Clamp dates
        try:
            st = date_vars.get("start", "")
            en = date_vars.get("end", "")
            sdate = clamp(st, date_limits.get("sdate"), date_limits.get("edate"))
            edate = clamp(en, date_limits.get("sdate"), date_limits.get("edate"))
        except Exception:
            sdate = date_vars.get("start", "")
            edate = date_vars.get("end", "")
        
        return {
            "extent_clamped": {"n": n, "s": s, "e": e, "w": w},
            "extent_entries": {
                "n": extent_entries.get("n", ""),
                "s": extent_entries.get("s", ""),
                "e": extent_entries.get("e", ""),
                "w": extent_entries.get("w", "")
            },
            "dates_clamped": {"start": sdate, "end": edate},
            "dates_entries": {
                "start": date_vars.get("start", ""),
                "end": date_vars.get("end", "")
            },
            "flight_direction": flight_direction,
            "data_folder": data_folder,
            "polarization": polarization,
            "subswaths": subswaths,
            "dem_file": dem_file,
            "output_folder": output_folder,
            "project_name": project_name,
            "gacos_folder": gacos_folder
        }
    
    def apply_config_to_gui(
        self, 
        config: Dict[str, Any],
        gui_updaters: Dict[str, Any],
        skip_zip_derived: bool = False
    ) -> None:
        """
        Apply configuration to GUI elements.
        
        Args:
            config: Configuration dictionary
            gui_updaters: Dictionary of GUI update functions/variables
            skip_zip_derived: Whether to skip extent/date updates (for zip-derived values)
        """
        try:
            # Update data folder
            data_folder = config.get("data_folder", "")
            if "data_folder_entry" in gui_updaters:
                entry = gui_updaters["data_folder_entry"]
                entry.delete(0, 'end')
                entry.insert(0, data_folder)
            
            # Update extent and dates only if not skipping zip-derived values
            if not skip_zip_derived:
                # Update extent entries
                ext = config.get("extent_entries", {})
                extent_entries = gui_updaters.get("extent_entries", {})
                for coord in ["n", "s", "e", "w"]:
                    if coord in extent_entries:
                        entry = extent_entries[coord]
                        entry.delete(0, 'end')
                        entry.insert(0, ext.get(coord, ""))
                
                # Update date entries
                dates = config.get("dates_entries", {})
                if "start_var" in gui_updaters:
                    gui_updaters["start_var"].set(dates.get("start", ""))
                if "end_var" in gui_updaters:
                    gui_updaters["end_var"].set(dates.get("end", ""))
            
            # Update other settings
            if "flight_dir_var" in gui_updaters:
                gui_updaters["flight_dir_var"].set(config.get("flight_direction", "DESCENDING"))
            
            if "pol_var" in gui_updaters:
                gui_updaters["pol_var"].set(config.get("polarization", "VV").upper())
            
            # Update subswaths
            subswaths = config.get("subswaths", [])
            if "subswath_vars" in gui_updaters:
                subswath_vars = gui_updaters["subswath_vars"]
                for i, var in enumerate(subswath_vars):
                    var.set(1 if (i+1) in subswaths else 0)
            
            # Update DEM file
            dem_file = config.get("dem_file", "")
            if dem_file and os.path.exists(dem_file):
                if "dem_entry" in gui_updaters:
                    entry = gui_updaters["dem_entry"]
                    entry.config(state="normal")
                    entry.delete(0, 'end')
                    entry.insert(0, dem_file)
                    entry.config(state="disabled")
                
                # Call DEM update callback if provided
                if "dem_update_callback" in gui_updaters:
                    gui_updaters["dem_update_callback"]()
            
            # Update output folder and project name
            if "output_folder_entry" in gui_updaters:
                entry = gui_updaters["output_folder_entry"]
                entry.config(state="normal")
                entry.delete(0, 'end')
                entry.insert(0, config.get("output_folder", ""))
            
            if "project_name_entry" in gui_updaters:
                entry = gui_updaters["project_name_entry"]
                entry.config(state="normal")
                entry.delete(0, 'end')
                entry.insert(0, config.get("project_name", ""))
            
            # Update GACOS folder
            gacos_folder = config.get("gacos_folder", "")
            if "gacos_data_path" in gui_updaters:
                gui_updaters["gacos_data_path"] = gacos_folder
            
            # Call final update callbacks
            if "final_update_callback" in gui_updaters:
                gui_updaters["final_update_callback"]()
                
        except Exception as e:
            print(f"Error applying config to GUI: {e}")


# Global configuration manager instance
config_manager = ConfigManager()