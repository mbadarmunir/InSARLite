"""
GUI helper utilities for InSARLite.
Contains validation functions, widget management, and UI utility functions.
"""

import os
import math
import datetime
import tkinter as tk
from typing import Optional, List, Tuple, Callable, Any


def validate_float(value: str) -> bool:
    """
    Validate if a string can be converted to float.
    
    Args:
        value: String value to validate
        
    Returns:
        True if valid float, False otherwise
    """
    if value in ("", "-", "."):
        return True
    try:
        float(value)
        return True
    except ValueError:
        return False


def validate_path_syntax(entry_widget: tk.Entry, folder: str) -> None:
    """
    Validate path syntax and update entry background color.
    
    Args:
        entry_widget: Entry widget to update
        folder: Folder path to validate
    """
    if folder and not os.path.exists(folder):
        entry_widget.config(bg="#ffcccc")
    else:
        entry_widget.config(bg="white")


def clear_entry_focus(root: tk.Tk, data_folder_entry: Optional[tk.Entry] = None) -> None:
    """
    Safely clear focus from entry widgets to prevent map interference.
    
    Args:
        root: Root Tkinter window
        data_folder_entry: Optional data folder entry widget
    """
    try:
        # Clear selection from data folder entry
        if data_folder_entry and data_folder_entry.winfo_exists():
            data_folder_entry.selection_clear()
        
        # Set focus to the main window to prevent interference with map widget
        root.focus_set()
        
        # Force update to ensure focus change takes effect
        root.update_idletasks()
    except Exception:
        pass  # Ignore any focus-related errors


def validate_dates_gentle(
    start_var: tk.StringVar, 
    end_var: tk.StringVar, 
    start_date_widget: tk.Widget,
    root: tk.Tk,
    date_limits: dict = None,
    query_btn_active: bool = False
) -> None:
    """
    Gentle date validation that doesn't auto-correct invalid dates.
    
    Args:
        start_var: StringVar for start date
        end_var: StringVar for end date
        start_date_widget: Start date widget for focus detection
        root: Root window for focus detection
        date_limits: Optional dictionary with date bounds (sdate, edate)
        query_btn_active: If True, skip date limit enforcement to allow free date selection
    """
    today = datetime.date.today()
    
    # Check if dates are valid format but don't auto-correct them
    start_text = start_var.get().strip()
    end_text = end_var.get().strip()
    
    start_valid = False
    end_valid = False
    
    # Validate start date format
    if start_text:
        try:
            start_date = datetime.datetime.strptime(start_text, "%Y-%m-%d").date()
            start_valid = True
            # Only enforce limits if date is complete and valid, and query button is not active
            if start_date > today:
                start_var.set(today.strftime("%Y-%m-%d"))
            elif not query_btn_active and date_limits:
                # Enforce date limits only when query button is not active
                sdate_limit = date_limits.get("sdate")
                if sdate_limit and start_date < sdate_limit:
                    start_var.set(sdate_limit.strftime("%Y-%m-%d"))
        except ValueError:
            # Don't auto-correct during typing, just mark as invalid
            pass
    
    # Validate end date format
    if end_text:
        try:
            end_date = datetime.datetime.strptime(end_text, "%Y-%m-%d").date()
            end_valid = True
            # Only enforce limits if date is complete and valid, and query button is not active
            if end_date > today:
                end_var.set(today.strftime("%Y-%m-%d"))
            elif not query_btn_active and date_limits:
                # Enforce date limits only when query button is not active
                edate_limit = date_limits.get("edate")
                if edate_limit and end_date > edate_limit:
                    end_var.set(edate_limit.strftime("%Y-%m-%d"))
        except ValueError:
            # Don't auto-correct during typing, just mark as invalid
            pass
    
    # Only check date order if both dates are valid and complete
    if start_valid and end_valid and start_text and end_text:
        try:
            start_date = datetime.datetime.strptime(start_text, "%Y-%m-%d").date()
            end_date = datetime.datetime.strptime(end_text, "%Y-%m-%d").date()
            
            if start_date > end_date:
                # Determine which field was edited last and adjust the other
                focused_widget = root.focus_get()
                if focused_widget == start_date_widget:
                    # User edited start date, adjust end date
                    end_var.set(start_date.strftime("%Y-%m-%d"))
                else:
                    # User edited end date or unknown, adjust start date
                    start_var.set(end_date.strftime("%Y-%m-%d"))
        except ValueError:
            pass


def validate_dates_strict(
    start_var: tk.StringVar, 
    end_var: tk.StringVar, 
    start_date_widget: tk.Widget,
    root: tk.Tk
) -> None:
    """
    Strict date validation with auto-correction.
    
    Args:
        start_var: StringVar for start date
        end_var: StringVar for end date
        start_date_widget: Start date widget for focus detection
        root: Root window for focus detection
    """
    today = datetime.date.today()
    default_start = today - datetime.timedelta(days=30)
    st, en = start_var.get(), end_var.get()
    
    try:
        st = datetime.datetime.strptime(st, "%Y-%m-%d").date()
    except ValueError:
        st = default_start
        start_var.set(st.strftime("%Y-%m-%d"))
    
    try:
        en = datetime.datetime.strptime(en, "%Y-%m-%d").date()
    except ValueError:
        en = today
        end_var.set(en.strftime("%Y-%m-%d"))
    
    if st > today:
        st = today
        start_var.set(st.strftime("%Y-%m-%d"))
    if en > today:
        en = today
        end_var.set(en.strftime("%Y-%m-%d"))
    
    if st > en:
        widget = root.focus_get()
        if widget == start_date_widget:
            en = st
            end_var.set(en.strftime("%Y-%m-%d"))
        else:
            st = en
            start_var.set(st.strftime("%Y-%m-%d"))


def enforce_extent_limits(
    n_entry: tk.Entry, s_entry: tk.Entry, e_entry: tk.Entry, w_entry: tk.Entry,
    extent_limits: dict
) -> None:
    """
    Enforce extent limits on coordinate entries.
    
    Args:
        n_entry, s_entry, e_entry, w_entry: Coordinate entry widgets
        extent_limits: Dictionary with extent bounds
    """
    from .file_operations import clamp
    
    if all(v is not None for v in extent_limits.values()):
        try:
            n = clamp(n_entry.get(), extent_limits["s"], extent_limits["n"])
            s = clamp(s_entry.get(), extent_limits["s"], extent_limits["n"])
            e = clamp(e_entry.get(), extent_limits["w"], extent_limits["e"])
            w = clamp(w_entry.get(), extent_limits["w"], extent_limits["e"])
            if n < s:
                n, s = s, n
            if e < w:
                e, w = w, e
            for entry, val in zip([n_entry, s_entry, e_entry, w_entry], [n, s, e, w]):
                entry.delete(0, tk.END)
                entry.insert(0, str(round(val, 6)))
        except Exception:
            pass


def enforce_date_limits(
    start_var: tk.StringVar, end_var: tk.StringVar, date_limits: dict
) -> None:
    """
    Enforce date limits on date variables.
    
    Args:
        start_var: StringVar for start date
        end_var: StringVar for end date
        date_limits: Dictionary with date bounds
    """
    sdate = date_limits.get("sdate")
    edate = date_limits.get("edate")
    if sdate and edate:
        if start_var.get():
            st = datetime.datetime.strptime(start_var.get(), "%Y-%m-%d").date()
        else:
            st = sdate
        if end_var.get():
            en = datetime.datetime.strptime(end_var.get(), "%Y-%m-%d").date()
        else:
            en = edate
        if st < sdate:
            st = sdate
        if st > edate:
            st = edate
        if en < sdate:
            en = sdate
        if en > edate:
            en = edate
        if st > en:
            st = en
        start_var.set(st.strftime("%Y-%m-%d"))
        end_var.set(en.strftime("%Y-%m-%d"))


def try_draw_from_entries(
    n_entry: tk.Entry, s_entry: tk.Entry, e_entry: tk.Entry, w_entry: tk.Entry,
    draw_callback: Callable[[float, float, float, float], None]
) -> None:
    """
    Try to draw rectangle from coordinate entries.
    
    Args:
        n_entry, s_entry, e_entry, w_entry: Coordinate entry widgets
        draw_callback: Function to call with coordinates (s, w, n, e)
    """
    try:
        n, s, e, w = map(float, (n_entry.get(), s_entry.get(), e_entry.get(), w_entry.get()))
        if n > s and e > w:
            draw_callback(s, w, n, e)
    except ValueError:
        pass


def update_data_query_btn_state(
    n_entry: tk.Entry, s_entry: tk.Entry, e_entry: tk.Entry, w_entry: tk.Entry,
    data_query_btn: Optional[tk.Button], data_browse_btn: tk.Button,
    show_query_callback: Callable[[], None], hide_query_callback: Callable[[], None]
) -> None:
    """
    Update data query button state based on extent entries and browse button state.
    
    Args:
        n_entry, s_entry, e_entry, w_entry: Coordinate entry widgets
        data_query_btn: Query button widget
        data_browse_btn: Browse button widget
        show_query_callback: Function to show query button
        hide_query_callback: Function to hide query button
    """
    entries = [n_entry.get(), s_entry.get(), e_entry.get(), w_entry.get()]
    valid = False
    if all(entries):
        try:
            n, s, e, w = map(float, entries)
            valid = (n > s) and (e > w)
        except ValueError:
            pass
    
    # Check if extent entries are disabled (meaning extent is set from zip files)
    extent_disabled = False
    if hasattr(n_entry, 'cget'):
        try:
            extent_disabled = n_entry.cget('state') == 'disabled'
        except:
            pass
    
    # If extent is disabled but has valid values (from zip files), allow querying
    if extent_disabled and valid:
        valid = True
    
    if data_query_btn is not None and data_query_btn.winfo_exists():
        browse_bg = data_browse_btn.cget("bg")
        if browse_bg == "red":
            # Red folder (empty): enable query only if extent is valid
            data_query_btn.config(state="normal" if valid else "disabled")
            show_query_callback()
        elif browse_bg == "yellow":
            # Yellow folder (ZIP files): always enable query
            data_query_btn.config(state="normal")
            show_query_callback()
        else:
            # Green folder (SAFE dirs): hide query button
            hide_query_callback()


def draw_rectangle_on_map(
    map_widget, rect_shape: List, data_browse_btn: tk.Button,
    s: float, w: float, n: float, e: float
) -> None:
    """
    Draw a rectangle on the map widget.
    
    Args:
        map_widget: Map widget to draw on
        rect_shape: List containing current rectangle shape
        data_browse_btn: Browse button for color checking
        s, w, n, e: Rectangle coordinates
    """
    if rect_shape[0]:
        rect_shape[0].delete()
    rect_shape[0] = map_widget.set_path(
        [(n, w), (n, e), (s, e), (s, w), (n, w)], color="red", width=2
    )
    if not hasattr(map_widget, "_red_rect_zoomed") or data_browse_btn.cget("bg") != "red":
        map_widget.set_position((n + s) / 2, (e + w) / 2)
        max_diff = max(abs(n - s), abs(e - w))
        zoom = 15 if max_diff < 0.0001 else int(max(2, min(15, 8 - math.log(max_diff + 1e-6, 2))))
        map_widget.set_zoom(zoom)
        if data_browse_btn.cget("bg") == "red":
            map_widget._red_rect_zoomed = True
    elif data_browse_btn.cget("bg") != "red":
        if hasattr(map_widget, "_red_rect_zoomed"):
            delattr(map_widget, "_red_rect_zoomed")


def update_extent_entries_from_map(
    bounds: Tuple[float, float, float, float],
    n_entry: tk.Entry, s_entry: tk.Entry, w_entry: tk.Entry, e_entry: tk.Entry,
    draw_callback: Callable[[float, float, float, float], None]
) -> None:
    """
    Update extent entries from map bounds.
    
    Args:
        bounds: Tuple of (s, w, n, e) coordinates
        n_entry, s_entry, w_entry, e_entry: Coordinate entry widgets
        draw_callback: Function to redraw rectangle
    """
    s, w, n, e = bounds
    for entry, val in zip([n_entry, s_entry, w_entry, e_entry], [n, s, w, e]):
        entry.delete(0, tk.END)
        entry.insert(0, str(round(val, 6)))
    draw_callback(s, w, n, e)


def on_map_click_with_limits(
    coords: Tuple[float, float], extent_limits: dict,
    map_widget, click_start_attr: str = "_map_click_start"
) -> Optional[Tuple[float, float, float, float]]:
    """
    Handle map click with coordinate limits.
    
    Args:
        coords: Click coordinates (lat, lon)
        extent_limits: Dictionary with extent bounds
        map_widget: Map widget
        click_start_attr: Attribute name for storing click start
        
    Returns:
        Bounds tuple if rectangle completed, None otherwise
    """
    lat, lon = coords
    if all(v is not None for v in extent_limits.values()):
        lat = min(max(lat, extent_limits["s"]), extent_limits["n"])
        lon = min(max(lon, extent_limits["w"]), extent_limits["e"])
    
    if not hasattr(map_widget, click_start_attr):
        setattr(map_widget, click_start_attr, (lat, lon))
        return None
    else:
        lat0, lon0 = getattr(map_widget, click_start_attr)
        lat1, lon1 = lat, lon
        if all(v is not None for v in extent_limits.values()):
            lat0 = min(max(lat0, extent_limits["s"]), extent_limits["n"])
            lon0 = min(max(lon0, extent_limits["w"]), extent_limits["e"])
            lat1 = min(max(lat1, extent_limits["s"]), extent_limits["n"])
            lon1 = min(max(lon1, extent_limits["w"]), extent_limits["e"])
        n, s = max(lat0, lat1), min(lat0, lat1)
        e, w = max(lon0, lon1), min(lon0, lon1)
        delattr(map_widget, click_start_attr)
        return (s, w, n, e)


def disable_extent_editing(n_entry: tk.Entry, s_entry: tk.Entry, e_entry: tk.Entry, w_entry: tk.Entry) -> None:
    """
    Disable extent entry widgets to prevent user modification.
    
    Args:
        n_entry, s_entry, e_entry, w_entry: Coordinate entry widgets
    """
    extent_widgets = [n_entry, s_entry, e_entry, w_entry]
    for widget in extent_widgets:
        if hasattr(widget, 'config'):
            try:
                widget.config(state="disabled")
            except:
                pass


def enable_extent_editing(n_entry: tk.Entry, s_entry: tk.Entry, e_entry: tk.Entry, w_entry: tk.Entry) -> None:
    """
    Enable extent entry widgets to allow user modification.
    
    Args:
        n_entry, s_entry, e_entry, w_entry: Coordinate entry widgets
    """
    extent_widgets = [n_entry, s_entry, e_entry, w_entry]
    for widget in extent_widgets:
        if hasattr(widget, 'config'):
            try:
                widget.config(state="normal")
            except:
                pass


def set_default_date_range_if_empty(start_var: tk.StringVar, end_var: tk.StringVar, update_callback: Callable[[], None]) -> None:
    """
    Set default date range (last 30 days) if date entries are empty.
    
    Args:
        start_var: StringVar for start date
        end_var: StringVar for end date
        update_callback: Function to call after setting dates
    """
    if not start_var.get().strip() and not end_var.get().strip():
        today = datetime.date.today()
        default_start = today - datetime.timedelta(days=30)
        start_var.set(default_start.strftime("%Y-%m-%d"))
        end_var.set(today.strftime("%Y-%m-%d"))
        print(f"Set default date range: {default_start.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}")
        # Update query button state after setting default dates
        if update_callback:
            update_callback()


def display_extent_labels(extent: dict, extent_frame: tk.Frame, labels_dict: dict) -> None:
    """
    Display extent labels for the given extent.
    
    Args:
        extent: Dictionary with extent bounds
        extent_frame: Frame to place labels in
        labels_dict: Dictionary to store label references
    """
    if not extent or not extent_frame:
        return
    
    # Clear existing labels
    for attr in ["n_label", "s_label", "e_label", "w_label"]:
        if attr in labels_dict and labels_dict[attr]:
            labels_dict[attr].destroy()
            labels_dict[attr] = None
    
    # Create new labels with red color to indicate derived from zip files
    n = f"N: {extent['n']:.6f}°"
    s = f"S: {extent['s']:.6f}°"
    e = f"E: {extent['e']:.6f}°"
    w = f"W: {extent['w']:.6f}°"
    
    labels_dict["n_label"] = tk.Label(extent_frame, text=n, fg="red")
    labels_dict["n_label"].grid(row=0, column=4, sticky="w", padx=(4, 0))
    labels_dict["s_label"] = tk.Label(extent_frame, text=s, fg="red")
    labels_dict["s_label"].grid(row=2, column=4, sticky="w", padx=(4, 0))
    labels_dict["e_label"] = tk.Label(extent_frame, text=e, fg="red")
    labels_dict["e_label"].grid(row=1, column=6, sticky="w", padx=(4, 0))
    labels_dict["w_label"] = tk.Label(extent_frame, text=w, fg="red")
    labels_dict["w_label"].grid(row=1, column=2, sticky="w", padx=(4, 0))


def set_extent_entry_values(
    extent: dict,
    n_entry: tk.Entry, s_entry: tk.Entry, e_entry: tk.Entry, w_entry: tk.Entry
) -> None:
    """
    Set extent entry values and temporarily enable them.
    
    Args:
        extent: Dictionary with extent bounds
        n_entry, s_entry, e_entry, w_entry: Coordinate entry widgets
    """
    extent_widgets = [n_entry, s_entry, e_entry, w_entry]
    extent_values = [extent['n'], extent['s'], extent['e'], extent['w']]
    
    for widget, value in zip(extent_widgets, extent_values):
        try:
            # Temporarily enable to ensure value setting works
            widget.config(state="normal")
            widget.delete(0, tk.END)
            widget.insert(0, str(value))
            # Re-disable after setting value
            widget.config(state="disabled")
        except Exception as e:
            print(f"Warning: Could not set extent entry value: {e}")


def get_aoi_wkt(n_entry: tk.Entry, s_entry: tk.Entry, e_entry: tk.Entry, w_entry: tk.Entry) -> Optional[str]:
    """
    Get Area of Interest as Well-Known Text (WKT) format.
    
    Args:
        n_entry, s_entry, e_entry, w_entry: Coordinate entry widgets
        
    Returns:
        WKT string or None if invalid coordinates
    """
    try:
        n, s, e, w = map(float, (n_entry.get(), s_entry.get(), e_entry.get(), w_entry.get()))
        coords = [(w, s), (e, s), (e, n), (w, n), (w, s)]
        return "POLYGON((" + ",".join(f"{x} {y}" for x, y in coords) + "))"
    except Exception:
        return None


def is_extent_valid(n_entry: tk.Entry, s_entry: tk.Entry, e_entry: tk.Entry, w_entry: tk.Entry) -> bool:
    """
    Check if extent entries contain valid coordinates.
    
    Args:
        n_entry: North latitude entry widget
        s_entry: South latitude entry widget
        e_entry: East longitude entry widget
        w_entry: West longitude entry widget
        
    Returns:
        True if extent is valid, False otherwise
    """
    try:
        n, s, e, w = map(float, (n_entry.get(), s_entry.get(), e_entry.get(), w_entry.get()))
        return (n > s) and (e > w)
    except (ValueError, AttributeError):
        return False


def is_dates_valid(start_var: tk.StringVar, end_var: tk.StringVar) -> bool:
    """
    Check if date entries contain valid dates.
    
    Args:
        start_var: Start date variable
        end_var: End date variable
        
    Returns:
        True if dates are valid, False otherwise
    """
    try:
        start_text = start_var.get().strip()
        end_text = end_var.get().strip()
        
        if not start_text or not end_text:
            return False
            
        start_date = datetime.datetime.strptime(start_text, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_text, "%Y-%m-%d").date()
        
        return start_date <= end_date
    except (ValueError, AttributeError):
        return False


def add_map_layer(map_widget, layer_data: dict, layer_type: str = "polygon") -> Any:
    """
    Add a layer to the map widget.
    
    Args:
        map_widget: TkinterMapView widget
        layer_data: Data for the layer (coordinates, styling, etc.)
        layer_type: Type of layer ("polygon", "path", "marker")
        
    Returns:
        Map layer object or None if failed
    """
    try:
        if layer_type == "polygon" and "coordinates" in layer_data:
            coords = layer_data["coordinates"]
            if isinstance(coords, list) and len(coords) > 2:
                points = [(lat, lon) for lat, lon in coords]
                return map_widget.set_polygon(
                    points,
                    outline_color=layer_data.get("outline_color", "blue"),
                    fill_color=layer_data.get("fill_color", ""),
                    border_width=layer_data.get("border_width", 2)
                )
        elif layer_type == "path" and "coordinates" in layer_data:
            coords = layer_data["coordinates"]
            if isinstance(coords, list) and len(coords) > 1:
                points = [(lat, lon) for lat, lon in coords]
                return map_widget.set_path(
                    points,
                    color=layer_data.get("color", "red"),
                    width=layer_data.get("width", 2)
                )
        elif layer_type == "marker" and "position" in layer_data:
            lat, lon = layer_data["position"]
            return map_widget.set_marker(
                lat, lon,
                text=layer_data.get("text", ""),
                marker_color_circle=layer_data.get("color", "red")
            )
    except Exception as e:
        print(f"Error adding map layer: {e}")
        return None


def update_search_area_on_map(
    map_widget,
    search_area_layer: list,
    n_entry: tk.Entry,
    s_entry: tk.Entry,
    e_entry: tk.Entry,
    w_entry: tk.Entry
) -> None:
    """
    Update the search area rectangle on the map.
    
    Args:
        map_widget: TkinterMapView widget
        search_area_layer: List containing current search area layer (modified in place)
        n_entry: North latitude entry widget
        s_entry: South latitude entry widget
        e_entry: East longitude entry widget
        w_entry: West longitude entry widget
    """
    try:
        # Remove existing search area layer
        if search_area_layer and search_area_layer[0]:
            try:
                search_area_layer[0].delete()
            except Exception:
                pass
            search_area_layer[0] = None
        
        # Check if we have valid coordinates
        if not is_extent_valid(n_entry, s_entry, e_entry, w_entry):
            return
        
        # Get coordinates
        n, s, e, w = map(float, (n_entry.get(), s_entry.get(), e_entry.get(), w_entry.get()))
        
        # Create new search area rectangle
        layer_data = {
            "coordinates": [(n, w), (n, e), (s, e), (s, w), (n, w)],
            "color": "red",
            "width": 2
        }
        
        search_area_layer[0] = add_map_layer(map_widget, layer_data, "path")
        
    except Exception as e:
        print(f"Error updating search area on map: {e}")
        if search_area_layer:
            search_area_layer[0] = None