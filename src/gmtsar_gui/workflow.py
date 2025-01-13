import tkinter as tk
from utils.utils import *
from gmtsar_gui.ts_gmtsar_sbas_full import main
from tkinter import scrolledtext, ttk


def run_gui():
    root = tk.Tk()
    root.title("GMTSAR Fully Automated Workflow")

    # Create the first folder selection textbox and browse button
    folder1_label = tk.Label(root, text="Select Data Folder:")
    folder1_label.grid(row=0, column=0, padx=10, pady=5)
    folder1_entry = tk.Entry(root, width=50)
    folder1_entry.grid(row=0, column=1, padx=10, pady=5)
    browse_button2 = tk.Button(
        root,
        text="Browse",
        command=lambda: browse_folder(folder1_entry, "last_folder1_dir"),
    )
    browse_button2.grid(row=0, column=2, padx=10, pady=5)

    # Create a StringVar to store the value of the radio button
    sort_order = tk.StringVar()
    sort_order.set("Descending")  # Set "Descending" as the default option

    # Create the radio buttons for "Ascending" and "Descending"
    ascending_rb = tk.Radiobutton(
        root, text="Ascending", variable=sort_order, value="Ascending"
    )
    ascending_rb.grid(row=0, column=3, padx=10, pady=5)

    descending_rb = tk.Radiobutton(
        root, text="Descending", variable=sort_order, value="Descending"
    )
    descending_rb.grid(row=0, column=4, padx=10, pady=5)

    # List of processing options
    atm_options = [
        "No atmospheric correction",
        "GACOS Atmospheric correction",
        "SBAS Atmospheric correction",
    ]

    # Dropdown menu using OptionMenu
    atm_option = tk.StringVar(value=atm_options[0])

    atm_option_menu = tk.OptionMenu(root, atm_option, *atm_options)
    atm_option_menu.grid(row=1, column=3, padx=10, pady=5, sticky="w")

    # Create the second folder selection textbox and browse button
    folder2_label = tk.Label(root, text="Select GACOS Data Folder:")
    folder2_label.grid(row=1, column=0, padx=10, pady=5)
    folder2_entry = tk.Entry(root, width=50, state=tk.DISABLED)
    folder2_entry.grid(row=1, column=1, padx=10, pady=5)
    browse_button3 = tk.Button(
        root,
        text="Browse",
        command=lambda: browse_folder(folder2_entry, "last_folder2_dir"),
        state=tk.DISABLED,
    )
    browse_button3.grid(row=1, column=2, padx=10, pady=5)

    atm_option.trace_add(
        "write",
        lambda *args: toggle_gacos_folder(atm_option, folder2_entry, browse_button3),
    )

    # Start with correct widget state (in case default selection isn't 1)
    # update_widgets()
    toggle_gacos_folder(atm_option, folder2_entry, browse_button3)

    # Create the dem file selection textbox and browse button
    dem_file_label = tk.Label(root, text="Select DEM file:")
    dem_file_label.grid(row=2, column=0, padx=10, pady=5)
    dem_file_entry = tk.Entry(root, width=50)
    dem_file_entry.grid(row=2, column=1, padx=10, pady=5)

    browse_button_dem = tk.Button(
        root,
        text="Browse",
        command=lambda: browse_file(
            dem_file_entry, "last_dem_file_dir", [("DEM files", "*.grd")]
        ),
    )

    browse_button_dem.grid(row=2, column=2, padx=10, pady=5)

    # Create the pin.II file selection textbox and browse button
    pin_file_label = tk.Label(root, text="Select pin.II file:")
    pin_file_label.grid(row=3, column=0, padx=10, pady=5)
    pin_file_entry = tk.Entry(root, width=50)
    pin_file_entry.grid(row=3, column=1, padx=10, pady=5)

    browse_button_pin = tk.Button(
        root,
        text="Browse",
        command=lambda: browse_file(
            pin_file_entry, "last_pin_file_dir", [("pin files", "*.II")]
        ),
    )

    browse_button_pin.grid(row=3, column=2, padx=10, pady=5)

    # Create the Project Name entry textbox
    project_name_label = tk.Label(root, text="Project Name:")
    project_name_label.grid(row=4, column=0, padx=10, pady=5)
    project_name_entry = tk.Entry(root, width=50)
    project_name_entry.grid(row=4, column=1, padx=10, pady=5)

    # Create the output folder selection textbox and browse button
    output_folder_label = tk.Label(root, text="Select Output Folder:")
    output_folder_label.grid(row=5, column=0, padx=10, pady=5)
    output_folder_entry = tk.Entry(root, width=50)
    output_folder_entry.grid(row=5, column=1, padx=10, pady=5)
    browse_button4 = tk.Button(
        root,
        text="Browse",
        command=lambda: browse_folder(output_folder_entry, "last_output_folder"),
    )
    browse_button4.grid(row=5, column=2, padx=10, pady=5)

    # Custom master image entry textbox
    mst_label = tk.Label(root, text="Custom Master Image (format:yyyymmdd):*")
    mst_label.grid(row=6, column=0, padx=10, pady=5)
    mst_entry = tk.Entry(root, width=50)
    mst_entry.grid(row=6, column=1, padx=10, pady=5)
    mst_label_e = tk.Label(root, text="*(Optional)")
    mst_label_e.grid(row=6, column=2, pady=5)

    # Baselines entry
    baselines_label = tk.Label(
        root, text="Baselines (format: tmp_baseline, perp_baseline):"
    )
    baselines_label.grid(row=7, column=0, padx=10, pady=5)
    baselines_entry = tk.Entry(root, width=50)
    baselines_entry.grid(row=7, column=1, padx=10, pady=5)

    # Multilooking entry
    multilooking_label = tk.Label(root, text="Multilooking (format: rng, az):")
    multilooking_label.grid(row=8, column=0, padx=10, pady=5)
    multilooking_entry = tk.Entry(root, width=50)
    multilooking_entry.grid(row=8, column=1, padx=10, pady=5)

    # Filter wavelength entry
    filter_wavelength_label = tk.Label(root, text="Filter Wavelength (format: int):")
    filter_wavelength_label.grid(row=9, column=0, padx=10, pady=5)
    filter_wavelength_entry = tk.Entry(root, width=50)
    filter_wavelength_entry.grid(row=9, column=1, padx=10, pady=5)

    # Unwrapping Threshold entry
    unwrapping_threshold_label = tk.Label(
        root, text="Unwrapping Threshold (format: float):"
    )
    unwrapping_threshold_label.grid(row=11, column=0, padx=10, pady=5)
    unwrapping_threshold_entry = tk.Entry(root, width=50)
    unwrapping_threshold_entry.grid(row=11, column=1, padx=10, pady=5)

    # Incidence angle entry
    inc_angle_label = tk.Label(root, text="Incidence Angle (format: float):")
    inc_angle_label.grid(row=12, column=0, padx=10, pady=5)
    inc_angle_entry = tk.Entry(root, width=50)
    inc_angle_entry.grid(row=12, column=1, padx=10, pady=5)

    # Dropdown menu for processing options at row 13
    processing_option_label = tk.Label(root, text="Select processing options:")
    processing_option_label.grid(row=13, column=0, padx=10, pady=5)

    # List of processing options
    processing_options = [
        "All 3 subswaths",
        "First and second subswaths only",
        "Second and third subswaths only",
        "First subswath only",
        "Second subswath only",
        "Third subswath only",
    ]

    # Dropdown menu using OptionMenu
    processing_option = tk.StringVar(value=processing_options[0])

    processing_option_menu = tk.OptionMenu(root, processing_option, *processing_options)
    processing_option_menu.grid(row=13, column=1, padx=10, pady=5)

    # Create progress bar
    progress_bar = ttk.Progressbar(root, mode="determinate")
    progress_bar.grid(row=15, column=0, columnspan=5, padx=10, pady=5, sticky="ew")
    # root.grid_columnconfigure(0, weight=1)
    # root.grid_columnconfigure(1, weight=1)
    # root.grid_columnconfigure(2, weight=1)
    # root.grid_columnconfigure(3, weight=1)
    # root.grid_columnconfigure(4, weight=1)

    # Create the console text area
    console_label = tk.Label(root, text="Console Output:")
    console_label.grid(row=16, column=0, columnspan=5, padx=10, pady=5)
    console_text = scrolledtext.ScrolledText(
        root, height=10, width=175, state=tk.DISABLED, wrap=tk.WORD
    )
    console_text.grid(row=17, column=0, columnspan=5, padx=10, pady=5)

    config = load_config()

    # Load the textboxes with last-used values or defaults

    folder1_entry.insert(0, config.get("last_folder1_dir", ""))
    dem_file_entry.insert(0, config.get("last_dem_file_dir", ""))
    pin_file_entry.insert(0, config.get("last_pin_file_dir", ""))
    project_name_entry.insert(0, config.get("project_name", ""))
    output_folder_entry.insert(0, config.get("last_output_folder", ""))

    if config.get("baselines", ""):
        baselines_entry.insert(0, config.get("baselines", ""))
    else:
        baselines_entry.insert(0, "50, 100")
    if config.get("multilooking", ""):
        multilooking_entry.insert(0, config.get("multilooking", ""))
    else:
        multilooking_entry.insert(0, "8, 2")
    if config.get("filter_wavelength", ""):
        filter_wavelength_entry.insert(0, config.get("filter_wavelength", ""))
    else:
        filter_wavelength_entry.insert(0, "200")
    if config.get("unwrapping_threshold", ""):
        unwrapping_threshold_entry.insert(0, config.get("unwrapping_threshold", ""))
    else:
        unwrapping_threshold_entry.insert(0, "0.01")
    processing_option.set(
        config.get("last_used_processing_option", processing_options[0])
    )
    atm_option.set(config.get("last_used_atm_option", atm_options[0]))
    # update_widgets(atm_option, folder2_entry, browse_button3)
    toggle_gacos_folder(atm_option, folder2_entry, browse_button3)
    folder2_entry.insert(0, config.get("last_folder2_dir", ""))
    if config.get("inc_angle"):
        inc_angle_entry.insert(0, config.get("inc_angle"))
    else:
        inc_angle_entry.insert(0, "37.0;")

    # Read all user inputs into appropriate variables
    in_data_dir = folder1_entry.get()
    gacos_dir = folder2_entry.get()
    dem_file = dem_file_entry.get()
    pin_file = pin_file_entry.get()
    project_name = project_name_entry.get()
    output_dir = output_folder_entry.get()
    mst = mst_entry.get()
    baselines = baselines_entry.get()
    multilooking = multilooking_entry.get()
    filter_wavelength = filter_wavelength_entry.get()
    unwrapping_threshold = unwrapping_threshold_entry.get()
    inc_angle = inc_angle_entry.get()
    subswath_option = processing_option.get()
    atm_corr_option = atm_option.get()

    # Create the Run button
    run_button = tk.Button(
        root,
        text="Run",
        command=lambda: main(
            in_data_dir,
            gacos_dir,
            dem_file,
            pin_file,
            project_name,
            output_dir,
            mst,
            baselines,
            multilooking,
            filter_wavelength,
            unwrapping_threshold,
            inc_angle,
            subswath_option,
            atm_corr_option,
            console_text,
            progress_bar,
        ),
    )
    run_button.grid(row=18, column=1, padx=10, pady=20)

    # Start the main loop
    root.mainloop()
