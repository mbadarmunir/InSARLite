"""
Enhanced interactive baseline plotting using matplotlib
with advanced zoom, pan, and editing capabilities.
"""

import os
import numpy as np
import matplotlib
matplotlib.use('TkAgg')  # Set backend before importing pyplot
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox
import json


class InteractiveBaselinePlotter:
    """
    Advanced interactive baseline plotter with matplotlib backend.
    Features:
    - Native zoom/pan with matplotlib navigation toolbar
    - Interactive node and edge editing
    - Real-time constraint visualization
    - Efficient rendering for large datasets
    - Professional plotting aesthetics
    """
    
    def __init__(self, parent_frame, baseline_table_path, figsize=(12, 8)):
        self.parent_frame = parent_frame
        self.baseline_table_path = baseline_table_path
        
        # Data storage
        self.dates = []
        self.perp_baselines = []
        self.file_ids = []
        self.points = []
        self.edges = []
        self.original_edges = []
        
        # Interactive state
        self.edit_mode = False
        self.selected_points = []
        self.selected_edge = None
        self.constraint_lines = []
        
        # UI components
        self.figure = None
        self.canvas = None
        self.toolbar = None
        self.ax = None
        
        # Callbacks
        self.on_edge_changed = None
        self.on_point_selected = None
        
        self._load_and_parse_data()
        self._create_plot()
        
    def _load_and_parse_data(self):
        """Load and parse baseline table data."""
        try:
            with open(self.baseline_table_path, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) < 5:
                        continue
                    
                    file_id = parts[0]
                    date_str = file_id.split('_')[1]  # Extract yyyymmdd
                    try:
                        date = datetime.strptime(date_str, "%Y%m%d")
                    except ValueError:
                        continue
                    
                    perp_baseline = float(parts[4])
                    self.dates.append(date)
                    self.perp_baselines.append(perp_baseline)
                    self.file_ids.append(file_id)
                    
            # Create point data structure
            for i, (date, baseline, file_id) in enumerate(zip(self.dates, self.perp_baselines, self.file_ids)):
                self.points.append({
                    'idx': i,
                    'date': date,
                    'baseline': baseline,
                    'file_id': file_id,
                    'selected': False
                })
                
        except Exception as e:
            print(f"Error loading baseline data: {e}")
            
    def _create_plot(self):
        """Create the main matplotlib plot with interactive features."""
        # Create figure and axis
        self.figure = Figure(figsize=(12, 8), dpi=100, facecolor='white')
        self.ax = self.figure.add_subplot(111)
        
        # Embed in Tkinter
        self.canvas = FigureCanvasTkAgg(self.figure, self.parent_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add navigation toolbar
        toolbar_frame = tk.Frame(self.parent_frame)
        toolbar_frame.pack(fill=tk.X)
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()
        
        # Set up the plot
        self._setup_plot_aesthetics()
        self._plot_baseline_points()
        self._setup_event_handlers()
        
        # Initial draw
        self.canvas.draw()
        
    def _setup_plot_aesthetics(self):
        """Configure plot appearance and styling."""
        # Set labels and title
        self.ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        self.ax.set_ylabel('Perpendicular Baseline (m)', fontsize=12, fontweight='bold')
        self.ax.set_title('Interactive Baseline Plot - InSAR Network Design', 
                         fontsize=14, fontweight='bold', pad=20)
        
        # Smart date axis formatting with optimal label density
        self._setup_smart_date_axis()
        
        # Rotate date labels for better readability
        self.figure.autofmt_xdate(rotation=45)
        
        # Grid
        self.ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        self.ax.set_axisbelow(True)
        
        # Styling
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_linewidth(1.2)
        self.ax.spines['bottom'].set_linewidth(1.2)
        
        # Set margins
        self.ax.margins(x=0.02, y=0.1)
        
    def _setup_smart_date_axis(self):
        """Configure intelligent date axis with optimal label density."""
        if not self.dates:
            return
            
        # Calculate optimal number of labels based on figure width
        fig_width_inches = self.figure.get_figwidth()
        # Aim for maximum 6-8 labels for optimal readability
        max_labels = min(8, max(4, int(fig_width_inches * 0.8)))
        
        date_range = max(self.dates) - min(self.dates)
        total_days = date_range.days
        
        if total_days <= 60:  # Less than 2 months
            # Weekly intervals
            interval = max(1, total_days // max_labels)
            locator = mdates.DayLocator(interval=interval*7)  # Use DayLocator with weekly intervals
            formatter = mdates.DateFormatter('%d/%m')
        elif total_days <= 365:  # Less than 1 year
            # Monthly intervals
            interval = max(1, total_days // (max_labels * 30))
            locator = mdates.MonthLocator(interval=interval)
            formatter = mdates.DateFormatter('%m/%y')
        elif total_days <= 1095:  # Less than 3 years
            # Quarterly intervals
            interval = max(1, total_days // (max_labels * 90))
            locator = mdates.MonthLocator(interval=interval*3)
            formatter = mdates.DateFormatter('%m/%y')
        else:  # More than 3 years
            # Yearly intervals
            interval = max(1, total_days // (max_labels * 365))
            locator = mdates.YearLocator(base=interval)  # Use 'base' parameter for YearLocator
            formatter = mdates.DateFormatter('%Y')
        
        self.ax.xaxis.set_major_locator(locator)
        self.ax.xaxis.set_major_formatter(formatter)
        
        # Ensure consistent label rotation after setting locator/formatter
        for label in self.ax.get_xticklabels():
            label.set_rotation(45)
            label.set_ha('right')  # Right alignment for diagonal labels
        
        # Set minor locators for better granularity
        if total_days <= 60:
            self.ax.xaxis.set_minor_locator(mdates.DayLocator(interval=max(1, total_days // 20)))
        elif total_days <= 365:
            self.ax.xaxis.set_minor_locator(mdates.DayLocator(interval=7))  # Weekly minor ticks
        else:
            self.ax.xaxis.set_minor_locator(mdates.MonthLocator())
        
    def _plot_baseline_points(self):
        """Plot the baseline points with enhanced styling for vector graphics."""
        if not self.dates or not self.perp_baselines:
            self.ax.text(0.5, 0.5, 'No valid data to plot', 
                        transform=self.ax.transAxes, ha='center', va='center',
                        fontsize=16, color='red')
            return
            
        # Plot points optimized for vector graphics
        dates_np = np.array(self.dates)
        baselines_np = np.array(self.perp_baselines)
        
        # Create scatter plot with vector-friendly settings
        self.point_scatter = self.ax.scatter(dates_np, baselines_np, 
                                           s=50, c='steelblue', alpha=1.0,  # Full opacity for vectors
                                           edgecolors='navy', linewidths=1.2,
                                           zorder=10, label='Image dates',
                                           marker='o',  # Explicit circle marker
                                           rasterized=False)  # Ensure vector rendering
        
        # Add date labels with vector-friendly text
        for i, (date, baseline) in enumerate(zip(self.dates, self.perp_baselines)):
            self.ax.annotate(date.strftime('%d/%m'), 
                           (date, baseline), 
                           xytext=(3, 3), textcoords='offset points',
                           fontsize=7, alpha=0.8, ha='left',  # Higher alpha for vectors
                           family='sans-serif',  # Explicit font family
                           rasterized=False)  # Ensure vector text
        
        # Add legend with vector settings
        legend = self.ax.legend(loc='upper right', framealpha=0.9)
        legend.set_rasterized(False)  # Ensure vector legend
        
    def _setup_event_handlers(self):
        """Set up matplotlib event handlers for interactivity."""
        # Use only button_press_event for unified selection handling
        self.canvas.mpl_connect('button_press_event', self._on_unified_click)
        self.canvas.mpl_connect('key_press_event', self._on_key_press)
        
        # View change events for dynamic axis updates (using draw_event as fallback)
        self.canvas.mpl_connect('draw_event', self._on_draw_event)
        
        # Store previous limits to detect changes
        self._prev_xlims = None
        
        # Make canvas focusable for key events
        self.canvas.get_tk_widget().focus_set()
        
    def _on_unified_click(self, event):
        """Unified click handler for both nodes and edges with proper priority."""
        if not self.edit_mode or event.inaxes != self.ax:
            return
            
        if event.button != 1:  # Only handle left clicks
            return
            
        # First check for node selection (higher priority due to smaller targets)
        node_clicked = self._check_node_click(event)
        
        if node_clicked is not None:
            # Universal Rule 1: Clear any edge selection first
            if self.selected_edge:
                self._deselect_edge()
            
            # Handle node selection logic
            self._handle_node_selection(node_clicked)
            
        else:
            # No node clicked, check for edge selection
            edge_clicked = self._check_edge_click(event)
            
            if edge_clicked:
                # Universal Rule 1: Clear all node selections first
                self._clear_all_node_selections()
                self._select_edge(edge_clicked)
            else:
                # Clear all selections when clicking empty space
                self._clear_all_selections()
                
    def _check_node_click(self, event):
        """Check if a node was clicked using improved detection."""
        if not self.points or event.xdata is None or event.ydata is None:
            return None
            
        try:
            click_x = mdates.num2date(event.xdata).replace(tzinfo=None)
            click_y = event.ydata
        except:
            return None
        
        # Check each point for proximity
        node_threshold = 25  # pixels for node selection
        
        for i, point in enumerate(self.points):
            # Calculate distance in display coordinates
            point_display = self.ax.transData.transform([(mdates.date2num(point['date']), point['baseline'])])[0]
            click_display = self.ax.transData.transform([(mdates.date2num(click_x), click_y)])[0]
            
            distance = np.sqrt((point_display[0] - click_display[0])**2 + 
                             (point_display[1] - click_display[1])**2)
            
            if distance <= node_threshold:
                return i
                
        return None
        
    def _handle_node_selection(self, node_idx):
        """Handle node selection with universal rules."""
        point = self.points[node_idx]
        
        # Check if this point is already selected
        if point['selected']:
            # Clicking an already selected point deselects it
            self._deselect_point(node_idx)
        else:
            # Check if we have exactly one other point selected
            selected_indices = [i for i, p in enumerate(self.points) if p['selected']]
            
            if len(selected_indices) == 1:
                # Universal Rule 2: Second node selection creates edge and deselects both
                other_idx = selected_indices[0]
                
                # Check if edge already exists
                edge_exists = any(
                    (e['idx1'] == node_idx and e['idx2'] == other_idx) or 
                    (e['idx1'] == other_idx and e['idx2'] == node_idx)
                    for e in self.edges
                )
                
                if not edge_exists:
                    self._create_edge(other_idx, node_idx)
                
                # Always deselect both points after attempting edge creation
                self._deselect_point(other_idx)
                # Don't select the clicked point since we're deselecting both
                
            elif len(selected_indices) == 0:
                # No points selected, select this one
                self._select_point(node_idx)
            else:
                # Multiple points selected (shouldn't happen with new rules)
                # Clear all and select only this one
                self._clear_all_node_selections()
                self._select_point(node_idx)
                
    def _clear_all_selections(self):
        """Clear all selections (nodes and edges)."""
        self._clear_all_node_selections()
        if self.selected_edge:
            self._deselect_edge()
                
    def _on_key_press(self, event):
        """Handle keyboard events."""
        if event.key == 'delete' and self.selected_edge:
            self._delete_selected_edge()
        elif event.key == 'escape':
            self._clear_selection()
            
    def _on_draw_event(self, event):
        """Handle draw events to detect axis limit changes."""
        if not self.dates or not hasattr(self, 'ax'):
            return
            
        current_xlims = self.ax.get_xlim()
        
        # Check if x-limits have changed significantly
        if (self._prev_xlims is None or 
            abs(current_xlims[0] - self._prev_xlims[0]) > 0.01 or 
            abs(current_xlims[1] - self._prev_xlims[1]) > 0.01):
            
            self._prev_xlims = current_xlims
            self._update_date_axis_for_current_view()
            
    def _ensure_label_rotation(self):
        """Ensure all x-axis labels have consistent 45-degree rotation."""
        try:
            for label in self.ax.get_xticklabels():
                label.set_rotation(45)
                label.set_ha('right')  # Right alignment for diagonal labels
        except:
            # Silently handle any label formatting errors
            pass
            
    def _draw_with_rotation(self):
        """Draw canvas and ensure consistent label rotation."""
        self.canvas.draw_idle()
        self._ensure_label_rotation()
            
    def _update_date_axis_for_current_view(self):
        """Update date axis formatting for the current view without triggering redraw."""
        if not self.dates:
            return
            
        # Get current visible date range
        xlims = self.ax.get_xlim()
        start_date = mdates.num2date(xlims[0]).replace(tzinfo=None)
        end_date = mdates.num2date(xlims[1]).replace(tzinfo=None)
        
        # Update date axis formatting based on current zoom level
        date_range = end_date - start_date
        total_days = max(1, date_range.days)
        
        # Calculate optimal number of labels for current view
        fig_width_inches = self.figure.get_figwidth()
        max_labels = min(8, max(4, int(fig_width_inches * 0.8)))
        
        if total_days <= 7:  # Less than a week - show daily
            locator = mdates.DayLocator(interval=max(1, total_days // max_labels))
            formatter = mdates.DateFormatter('%d/%m')
        elif total_days <= 60:  # Less than 2 months - show weekly
            interval = max(1, total_days // (max_labels * 7))
            locator = mdates.DayLocator(interval=interval*7)  # Use DayLocator with weekly intervals
            formatter = mdates.DateFormatter('%d/%m')
        elif total_days <= 365:  # Less than 1 year - show monthly
            interval = max(1, total_days // (max_labels * 30))
            locator = mdates.MonthLocator(interval=interval)
            formatter = mdates.DateFormatter('%m/%y')
        elif total_days <= 1095:  # Less than 3 years - show quarterly
            interval = max(1, total_days // (max_labels * 90))
            locator = mdates.MonthLocator(interval=interval*3)
            formatter = mdates.DateFormatter('%m/%y')
        else:  # More than 3 years - show yearly
            interval = max(1, total_days // (max_labels * 365))
            locator = mdates.YearLocator(base=interval)  # Use 'base' parameter for YearLocator
            formatter = mdates.DateFormatter('%Y')
        
        # Only update if different from current
        try:
            self.ax.xaxis.set_major_locator(locator)
            self.ax.xaxis.set_major_formatter(formatter)
            # Ensure consistent label rotation after any axis update
            for label in self.ax.get_xticklabels():
                label.set_rotation(45)
                label.set_ha('right')  # Right alignment for diagonal labels
        except:
            # Silently handle any formatting errors
            pass
            
    def _select_point(self, idx):
        """Select a point for editing."""
        self.points[idx]['selected'] = True
        # Update point appearance
        self._update_point_colors()
        
    def _deselect_point(self, idx):
        """Deselect a point."""
        self.points[idx]['selected'] = False
        # Update point appearance
        self._update_point_colors()
        
    def _update_point_colors(self):
        """Update point colors based on selection state."""
        colors = []
        sizes = []
        for point in self.points:
            if point['selected']:
                colors.append('red')
                sizes.append(70)  # Slightly larger when selected, but not too big
            else:
                colors.append('steelblue')
                sizes.append(50)  # Optimized base size
                
        self.point_scatter.set_color(colors)
        self.point_scatter.set_sizes(sizes)
        self._draw_with_rotation()
        
    def _create_edge(self, idx1, idx2):
        """Create an edge between two points optimized for vector graphics."""
        # Check if edge already exists
        for edge in self.edges:
            if (edge['idx1'] == idx1 and edge['idx2'] == idx2) or \
               (edge['idx1'] == idx2 and edge['idx2'] == idx1):
                return  # Edge already exists
                
        point1 = self.points[idx1]
        point2 = self.points[idx2]
        
        # Create line object optimized for vector graphics
        line, = self.ax.plot([point1['date'], point2['date']], 
                           [point1['baseline'], point2['baseline']], 
                           'k-', linewidth=1.0, alpha=1.0,  # Full opacity for vectors
                           zorder=1,  # Lower zorder than points
                           solid_capstyle='round',  # Vector-friendly line caps
                           solid_joinstyle='round',  # Vector-friendly line joins
                           rasterized=False)  # Ensure vector rendering
        
        # Store edge data
        edge = {
            'idx1': idx1,
            'idx2': idx2,
            'line': line,
            'selected': False
        }
        self.edges.append(edge)
        
        self.canvas.draw_idle()
        
        # Trigger callback if set
        if self.on_edge_changed:
            self.on_edge_changed(self.edges)
            
    def _clear_all_node_selections(self):
        """Clear all node selections while preserving edge selections."""
        for point in self.points:
            point['selected'] = False
        self._update_point_colors()
            
    def _check_edge_click(self, event):
        """Check if mouse click is near an edge with consistent, reliable detection."""
        if not self.edges:
            return None
            
        # Ensure we have valid coordinates
        if event.xdata is None or event.ydata is None:
            return None
            
        # Convert event coordinates to data coordinates
        try:
            click_x = mdates.num2date(event.xdata).replace(tzinfo=None)
            click_y = event.ydata
        except:
            return None
        
        min_distance = float('inf')
        closest_edge = None
        edge_threshold = 20  # pixels - consistent threshold
        
        for edge in self.edges:
            point1 = self.points[edge['idx1']]
            point2 = self.points[edge['idx2']]
            
            # Calculate distance in display coordinates for consistency
            try:
                # Convert line endpoints to display coordinates
                p1_display = self.ax.transData.transform([(mdates.date2num(point1['date']), point1['baseline'])])[0]
                p2_display = self.ax.transData.transform([(mdates.date2num(point2['date']), point2['baseline'])])[0]
                click_display = self.ax.transData.transform([(mdates.date2num(click_x), click_y)])[0]
                
                # Calculate distance from click to line segment in display coordinates
                distance = self._point_to_line_distance_display(
                    click_display[0], click_display[1],
                    p1_display[0], p1_display[1],
                    p2_display[0], p2_display[1]
                )
                
                if distance < min_distance:
                    min_distance = distance
                    closest_edge = edge
                    
            except Exception:
                continue
                
        if min_distance <= edge_threshold:
            return closest_edge
                
        return None
        
    def _point_to_line_distance_display(self, px, py, x1, y1, x2, y2):
        """Calculate distance from point to line segment in display coordinates."""
        # Vector from line start to end
        line_vec = np.array([x2 - x1, y2 - y1])
        # Vector from line start to point
        point_vec = np.array([px - x1, py - y1])
        
        # Calculate the length of the line segment
        line_len_sq = np.dot(line_vec, line_vec)
        
        if line_len_sq == 0:
            # Line segment is actually a point
            return np.sqrt(np.dot(point_vec, point_vec))
        
        # Project point onto the line, constrained to the segment
        t = max(0, min(1, np.dot(point_vec, line_vec) / line_len_sq))
        
        # Find the closest point on the line segment
        closest_point = np.array([x1, y1]) + t * line_vec
        
        # Calculate distance from point to closest point on line
        distance_vec = np.array([px, py]) - closest_point
        return np.sqrt(np.dot(distance_vec, distance_vec))
        
    def _select_edge(self, edge):
        """Select an edge for editing with refined styling."""
        # Deselect previous edge
        if self.selected_edge:
            self._deselect_edge()
            
        self.selected_edge = edge
        edge['selected'] = True
        edge['line'].set_color('red')
        edge['line'].set_linewidth(2.0)  # More moderate highlight thickness
        self.canvas.draw_idle()
        
    def _deselect_edge(self):
        """Deselect the currently selected edge."""
        if self.selected_edge:
            self.selected_edge['selected'] = False
            self.selected_edge['line'].set_color('black')
            self.selected_edge['line'].set_linewidth(1.0)  # Return to optimized thickness
            self.selected_edge = None
            self.canvas.draw_idle()
            
    def _delete_selected_edge(self):
        """Delete the currently selected edge."""
        if not self.selected_edge:
            return
            
        # Remove line from plot
        self.selected_edge['line'].remove()
        
        # Remove from edges list
        self.edges.remove(self.selected_edge)
        self.selected_edge = None
        
        self.canvas.draw_idle()
        
        # Trigger callback if set
        if self.on_edge_changed:
            self.on_edge_changed(self.edges)
            
    def _clear_selection(self):
        """Clear all selections."""
        # Deselect all points
        for point in self.points:
            point['selected'] = False
        self._update_point_colors()
        
        # Deselect edge
        if self.selected_edge:
            self._deselect_edge()
            
    def connect_baseline_nodes(self, perp_constraint, temp_constraint):
        """
        Connect nodes within specified constraints.
        
        Args:
            perp_constraint: Maximum perpendicular baseline difference (meters)
            temp_constraint: Maximum temporal baseline (days)
        """
        # Clear existing edges
        self.clear_edges()
        
        n = len(self.points)
        for i in range(n):
            for j in range(i + 1, n):
                point1 = self.points[i]
                point2 = self.points[j]
                
                # Calculate temporal difference
                temp_diff = abs((point2['date'] - point1['date']).days)
                
                # Calculate perpendicular baseline difference
                perp_diff = abs(point2['baseline'] - point1['baseline'])
                
                # Check constraints
                if temp_diff <= temp_constraint and perp_diff <= perp_constraint:
                    self._create_edge(i, j)
                    
        # Store original edges for comparison
        self.original_edges = [(e['idx1'], e['idx2']) for e in self.edges]
        
    def clear_edges(self):
        """Clear all edges from the plot."""
        for edge in self.edges:
            edge['line'].remove()
        self.edges.clear()
        self.selected_edge = None
        self.canvas.draw_idle()
        
    def set_edit_mode(self, enabled):
        """Enable or disable edit mode."""
        self.edit_mode = enabled
        
        if enabled:
            self.ax.set_title('Interactive Baseline Plot - EDIT MODE (Click points to connect, click edges to select)', 
                            fontsize=14, fontweight='bold', color='red')
        else:
            self.ax.set_title('Interactive Baseline Plot - InSAR Network Design', 
                            fontsize=14, fontweight='bold', color='black')
            self._clear_selection()
            
        self.canvas.draw_idle()
        
    def show_constraints(self, perp_constraint, temp_constraint):
        """
        Visualize constraint boundaries on the plot.
        
        Args:
            perp_constraint: Perpendicular baseline constraint (meters)
            temp_constraint: Temporal constraint (days)
        """
        # Remove existing constraint lines
        for line in self.constraint_lines:
            line.remove()
        self.constraint_lines.clear()
        
        if not self.dates or not self.perp_baselines:
            return
            
        # Add perpendicular baseline constraint lines
        min_baseline = min(self.perp_baselines)
        max_baseline = max(self.perp_baselines)
        
        y_min = min_baseline - perp_constraint
        y_max = max_baseline + perp_constraint
        
        # Temporal constraint visualization (example: highlight valid temporal windows)
        min_date = min(self.dates)
        max_date = max(self.dates)
        
        # Add constraint indicator text
        constraint_text = f"Constraints: ±{perp_constraint}m perp., {temp_constraint} days temp."
        self.ax.text(0.02, 0.98, constraint_text, transform=self.ax.transAxes,
                    bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7),
                    verticalalignment='top', fontsize=10)
        
        self._draw_with_rotation()
        
    def get_edge_list(self):
        """
        Get list of edges in format suitable for export.
        
        Returns:
            List of tuples (file_id1, file_id2) for each edge
        """
        edge_list = []
        for edge in self.edges:
            file_id1 = self.points[edge['idx1']]['file_id']
            file_id2 = self.points[edge['idx2']]['file_id']
            edge_list.append((file_id1, file_id2))
        return edge_list
        
    def save_plot(self, filepath, dpi=300, save_vector=True):
        """
        Save the current plot to file with true vector graphics support.
        
        Args:
            filepath: Output file path (PNG)
            dpi: Resolution for raster formats
            save_vector: If True, also save vector formats (PDF, EPS, SVG)
        """
        import matplotlib
        import matplotlib.pyplot as plt
        
        # Save PNG file with high quality
        self.figure.savefig(filepath, dpi=dpi, bbox_inches='tight', 
                          facecolor='white', edgecolor='none')
        
        # Save vector files with true vector graphics if requested
        if save_vector:
            base_path = os.path.splitext(filepath)[0]
            
            # Store original rcParams to restore later
            original_rcParams = {}
            
            # Configure matplotlib for optimal vector output
            vector_rcParams = {
                'pdf.use14corefonts': True,     # Use PDF core fonts
                'pdf.fonttype': 42,             # Embed fonts as TrueType (scalable)
                'ps.fonttype': 42,              # Embed fonts as TrueType in PostScript
                'svg.fonttype': 'none',         # Don't convert text to paths in SVG
                'text.usetex': False,           # Avoid LaTeX complexity
                'ps.useafm': True,              # Better font handling
                'font.size': 10,                # Readable font size
                'axes.linewidth': 0.8,          # Clean line rendering
                'lines.linewidth': 1.0         # Proper line thickness
            }
            
            # Temporarily set vector-optimized parameters
            for key, value in vector_rcParams.items():
                if key in plt.rcParams:
                    original_rcParams[key] = plt.rcParams.get(key)
                    plt.rcParams[key] = value
            
            vector_formats = [
                ('pdf', 'PDF', 'pdf'),
                ('svg', 'SVG', 'svg'),
                ('eps', 'EPS', 'eps'),
                ('ps', 'PostScript', 'ps')
            ]
            
            for fmt, name, ext in vector_formats:
                vector_path = f"{base_path}.{ext}"
                try:
                    # Configure specific format settings
                    save_kwargs = {
                        'format': fmt,
                        'bbox_inches': 'tight',
                        'facecolor': 'white',
                        'edgecolor': 'none',
                        'transparent': False,
                        'pad_inches': 0.1
                    }
                    
                    # Add format-specific optimizations
                    if fmt == 'pdf':
                        save_kwargs.update({
                            'metadata': {
                                'Creator': 'InSARLite',
                                'Title': 'Baseline Network Plot',
                                'Subject': 'InSAR Baseline Analysis'
                            }
                        })
                    elif fmt == 'svg':
                        save_kwargs.update({
                            'metadata': {
                                'Creator': 'InSARLite',
                                'Date': None  # Use current date
                            }
                        })
                    elif fmt in ['eps', 'ps']:
                        # Determine optimal orientation and paper size
                        fig_width, fig_height = self.figure.get_size_inches()
                        if fig_width > fig_height:
                            orientation = 'landscape'
                            papertype = 'a3' if (fig_width > 11 or fig_height > 8.5) else 'letter'
                        else:
                            orientation = 'portrait' 
                            papertype = 'a3' if (fig_height > 11 or fig_width > 8.5) else 'letter'
                        
                        save_kwargs.update({
                            'orientation': orientation,
                            'papertype': papertype
                        })
                    
                    self.figure.savefig(vector_path, **save_kwargs)
                    
                    # Verify file was created and is not empty
                    if os.path.exists(vector_path) and os.path.getsize(vector_path) > 0:
                        print(f"Vector plot ({name}) saved to {vector_path}")
                    else:
                        print(f"Warning: {name} file creation failed or is empty")
                        
                except Exception as e:
                    print(f"Warning: Could not save {name} format: {e}")
            
            # Restore original rcParams
            for key, value in original_rcParams.items():
                if value is not None:
                    plt.rcParams[key] = value
        
    def get_statistics(self):
        """Get network statistics."""
        if not self.edges or not self.points:
            return {}
            
        total_points = len(self.points)
        total_edges = len(self.edges)
        
        # Calculate average temporal and perpendicular baselines
        temp_baselines = []
        perp_baselines = []
        
        for edge in self.edges:
            point1 = self.points[edge['idx1']]
            point2 = self.points[edge['idx2']]
            
            temp_diff = abs((point2['date'] - point1['date']).days)
            perp_diff = abs(point2['baseline'] - point1['baseline'])
            
            temp_baselines.append(temp_diff)
            perp_baselines.append(perp_diff)
            
        stats = {
            'total_points': total_points,
            'total_edges': total_edges,
            'avg_temporal_baseline': np.mean(temp_baselines) if temp_baselines else 0,
            'max_temporal_baseline': max(temp_baselines) if temp_baselines else 0,
            'avg_perp_baseline': np.mean(perp_baselines) if perp_baselines else 0,
            'max_perp_baseline': max(perp_baselines) if perp_baselines else 0,
            'connectivity': total_edges / (total_points * (total_points - 1) / 2) if total_points > 1 else 0
        }
        
        return stats


def create_interactive_baseline_plot(parent_frame, baseline_table_path, **kwargs):
    """
    Factory function to create an interactive baseline plotter.
    
    Args:
        parent_frame: Tkinter parent frame
        baseline_table_path: Path to baseline table file
        **kwargs: Additional arguments for plotter
        
    Returns:
        InteractiveBaselinePlotter instance
    """
    return InteractiveBaselinePlotter(parent_frame, baseline_table_path, **kwargs)