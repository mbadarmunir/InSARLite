import tkinter as tk
import os
from utils.utils import exitGUI, toggle_gacos_folder, load_config, save_config, browse_folder, browse_file, add_tooltip
from gmtsar_gui.ts_gmtsar_sbas_full import main
from tkinter import scrolledtext, ttk, messagebox, font

def validate_entries(
    folder1_entry, dem_file_entry, pin_file_entry, folder2_entry, atm_option, 
    baselines_entry, multilooking_entry, filter_wavelength_entry, 
    coherence_thresholds_entry, inc_angle_entry, cores_entry
):
    errors = []

    # Check if folders and files exist
    if not os.path.exists(folder1_entry.get()):
        errors.append("Input data directory does not exist.")
    if not os.path.exists(dem_file_entry.get()):
        errors.append("DEM file does not exist.")
    if not os.path.exists(pin_file_entry.get()):
        errors.append("PIN file does not exist.")
    if not os.path.exists(folder2_entry.get()) and atm_option.get() == "GACOS Atmospheric correction":
        errors.append("GACOS directory does not exist.")

    # Check for mismatched entries in the textboxes
    try:
        list(map(int, baselines_entry.get().split(',')))
    except ValueError:
        errors.append("Baselines entry is not valid.")
    
    try:
        list(map(int, multilooking_entry.get().split(',')))
    except ValueError:
        errors.append("Multilooking entry is not valid.")
    
    try:
        int(filter_wavelength_entry.get())
    except ValueError:
        errors.append("Filter wavelength entry is not valid.")
    
    try:
        list(map(float, coherence_thresholds_entry.get().split(',')))
    except ValueError:
        errors.append("Coherence thresholds entry is not valid.")
    
    try:
        float(inc_angle_entry.get())
    except ValueError:
        errors.append("Incidence angle entry is not valid.")

    try:
        int(cores_entry.get())
    except ValueError:
        errors.append("No. of cores entry is not valid.")

    return errors

def on_run_button_click(
    root, 
    folder1_entry, 
    sort_order, 
    dem_file_entry, 
    pin_file_entry, 
    project_name_entry,
    output_folder_entry,
    mst_entry, 
    folder2_entry, 
    processing_option,
    atm_option,
    console_text,
    progress_bar, 
    baselines_entry, 
    multilooking_entry, 
    filter_wavelength_entry, 
    coherence_thresholds_entry, 
    inc_angle_entry,
    cores_entry,
    sbas,
    atm,
    rms,
    dem,
    smooth
):
    errors = validate_entries(
        folder1_entry, 
        dem_file_entry, 
        pin_file_entry, 
        folder2_entry, 
        atm_option, 
        baselines_entry, 
        multilooking_entry, 
        filter_wavelength_entry, 
        coherence_thresholds_entry, 
        inc_angle_entry,
        cores_entry
    )
    if errors:
        messagebox.showerror("Validation Error", "\n".join(errors))
    else:
        # Proceed with the current setup
        run_main(
            root,
            folder1_entry,
            sort_order,
            folder2_entry,
            dem_file_entry,
            pin_file_entry,
            project_name_entry,
            output_folder_entry,
            mst_entry,
            baselines_entry,
            multilooking_entry,
            filter_wavelength_entry,
            coherence_thresholds_entry,
            inc_angle_entry,
            processing_option,
            atm_option,
            cores_entry,
            sbas,
            atm,
            rms,
            dem,
            smooth,
            console_text,
            progress_bar
        )


def run_gui():
    root = tk.Tk()
    root.title("GMTSAR Fully Automated Workflow")

    # Define a function to update the font size based on the window size
    def update_font_size(new_size):
        new_font = font.Font(size=new_size)
        for widget in root.winfo_children():
            try:
                widget.configure(font=new_font)
            except tk.TclError:
                pass  # Ignore widgets that don't support the font option

    # Define a function to handle mouse wheel events
    def on_mouse_wheel(event):
        if event.state & 0x0004:  # Check if Ctrl key is pressed
            if event.delta > 0 or event.num == 4:  # Mouse wheel up
                new_size = min(root.font_size + 1, 50)  # Increase font size
            elif event.delta < 0 or event.num == 5:  # Mouse wheel down
                new_size = max(root.font_size - 1, 8)  # Decrease font size
            root.font_size = new_size
            update_font_size(root.font_size)

    # Define a function to handle Ctrl + '+' and Ctrl + '-' events
    def on_key_press(event):
        if event.state & 0x0004:  # Check if Ctrl key is pressed
            if event.keysym in ['plus', 'equal', 'KP_Add']:  # Ctrl + '+'
                new_size = min(root.font_size + 1, 50)  # Increase font size
            elif event.keysym in ['minus', 'KP_Subtract']:  # Ctrl + '-'
                new_size = max(root.font_size - 1, 8)  # Decrease font size
            root.font_size = new_size
            update_font_size(root.font_size)

    # Initialize font size
    root.font_size = 12
    update_font_size(root.font_size)

    # Bind the mouse wheel event to the on_mouse_wheel function
    root.bind_all("<MouseWheel>", on_mouse_wheel)  # For Windows
    root.bind_all("<Button-4>", on_mouse_wheel)    # For Linux
    root.bind_all("<Button-5>", on_mouse_wheel)    # For Linux

    # Bind the key press events to the on_key_press function
    root.bind_all("<Control-plus>", on_key_press)
    root.bind_all("<Control-minus>", on_key_press)
    root.bind_all("<Control-equal>", on_key_press)  # For handling Ctrl + '=' as well
    root.bind_all("<Control-KP_Add>", on_key_press)  # For handling Ctrl + '+' on numeric keypad
    root.bind_all("<Control-KP_Subtract>", on_key_press)  # For handling Ctrl + '-' on numeric keypad

    # Create the first folder selection textbox and browse button
    folder1_label = tk.Label(root, text="Select Data Folder:")
    folder1_label.grid(row=0, column=0, padx=10, pady=5)
    folder1_entry = tk.Entry(root, width=50)
    folder1_entry.grid(row=0, column=1, padx=10, pady=5)
    browse_button1 = tk.Button(
        root,
        text="Browse",
        command=lambda: browse_folder(folder1_entry, "in_data_dir"),
    )
    browse_button1.grid(row=0, column=2, padx=10, pady=5)

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
    browse_button2 = tk.Button(
        root,
        text="Browse",
        command=lambda: browse_folder(folder2_entry, "gacos_dir"),
        state=tk.DISABLED,
    )
    browse_button2.grid(row=1, column=2, padx=10, pady=5)

    atm_option.trace_add(
        "write",
        lambda *args: toggle_gacos_folder(atm_option, folder2_entry, browse_button2),
    )

    # Start with correct widget state (in case default selection isn't 1)
    toggle_gacos_folder(atm_option, folder2_entry, browse_button2)

    # Create the dem file selection textbox and browse button
    dem_file_label = tk.Label(root, text="Select DEM file:")
    dem_file_label.grid(row=2, column=0, padx=10, pady=5)
    dem_file_entry = tk.Entry(root, width=50)
    dem_file_entry.grid(row=2, column=1, padx=10, pady=5)

    browse_button_dem = tk.Button(
        root,
        text="Browse",
        command=lambda: browse_file(
            dem_file_entry, "dem_file", [("DEM files", "*.grd")]
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
            pin_file_entry, "pin_file", [("pin files", "*.II")]
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
    browse_button3 = tk.Button(
        root,
        text="Browse",
        command=lambda: browse_folder(output_folder_entry, "output_dir"),
    )
    browse_button3.grid(row=5, column=2, padx=10, pady=5)

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

    # Coherence Threshold entry
    coherence_thresholds_label = tk.Label(
        root, text="Coherence Thresholds (format: masking, unwrapping):"
    )
    coherence_thresholds_label.grid(row=11, column=0, padx=10, pady=5)
    coherence_thresholds_entry = tk.Entry(root, width=50)
    coherence_thresholds_entry.grid(row=11, column=1, padx=10, pady=5)
    coherence_thresholds_label_e = tk.Label(root, text="(e.g. 0, 0.01) where 0 for masking means no masking")
    coherence_thresholds_label_e.grid(row=11, column=2, pady=5)

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

    # Number of cores entry
    cores_label = tk.Label(root, text="Number of cores:")
    cores_label.grid(row=13, column=3, padx=10, pady=5)
    cores_entry = tk.Entry(root, width=10)
    cores_entry.grid(row=13, column=4, padx=10, pady=5)

    # Native sbas atmospheric correction and related controls in a single horizontal frame
    sbas_args_frame = tk.Frame(root)
    sbas_args_frame.grid(row=14, column=0, columnspan=6, padx=10, pady=5, sticky="w")

    # SBAS Arguments label
    sb_args_label = tk.Label(sbas_args_frame, text="SBAS Arguments:")
    sb_args_label.pack(side=tk.LEFT, padx=(0, 10))

    atm_var = tk.BooleanVar(value=False)
    rms_var = tk.BooleanVar(value=True)
    dem_var = tk.BooleanVar(value=True)

    atm_checkbox = tk.Checkbutton(sbas_args_frame, text="-atm", variable=atm_var)
    atm_checkbox.pack(side=tk.LEFT, padx=(0, 10))
    add_tooltip(atm_checkbox, "Check to apply native SBAS atmospheric correction (-atm).")

    rms_checkbox = tk.Checkbutton(sbas_args_frame, text="-rms", variable=rms_var)
    rms_checkbox.pack(side=tk.LEFT, padx=(0, 10))
    add_tooltip(rms_checkbox, "Check to calculate RMS of residuals (-rms).")

    dem_checkbox = tk.Checkbutton(sbas_args_frame, text="-dem", variable=dem_var)
    dem_checkbox.pack(side=tk.LEFT, padx=(0, 10))
    add_tooltip(dem_checkbox, "Check to generate DEM residual error file in SB inversion (-dem).")

    # Smoothing factor label and entry
    smooth_var_label = tk.Label(sbas_args_frame, text="Smoothing factor:")
    smooth_var_label.pack(side=tk.LEFT, padx=(0, 5))
    smooth_var_entry = tk.Entry(sbas_args_frame, width=10)
    smooth_var_entry.pack(side=tk.LEFT, padx=(0, 10))
    smooth_var_entry.insert(0, "5.0")  # Default value for smoothing factor
    add_tooltip(
        smooth_var_entry, 
        "Enter the smoothing factor for the SBAS inversion.\n"
        "Default is 5.0, but you can adjust it based on your data."
    )

    # SBAS mode selection dropdown
    sbas_mode_label = tk.Label(sbas_args_frame, text="SBAS Mode:")
    sbas_mode_label.pack(side=tk.LEFT, padx=(0, 5))
    sbas_mode_var = tk.StringVar(value="SBAS")
    sbas_mode_dropdown = ttk.Combobox(
        sbas_args_frame,
        textvariable=sbas_mode_var,
        values=["SBAS", "SBAS Parallel"],
        state="readonly",
        width=20
    )
    sbas_mode_dropdown.pack(side=tk.LEFT, padx=(0, 10))

    add_tooltip(
        sbas_mode_dropdown,
        "Choose 'SBAS' for standard processing or 'SBAS Parallel' to use multi-core processing.\n"
         "The 'SBAS Parallel' uses GNU Parallel for implementing parallelization.\n"
         "Make sure GNU Parallel is installed and available in your PATH if you use this option."
    )
    if sbas_mode_var.get() == "SBAS Parallel":
        sbas= "sbas_parallel"
    else:
        sbas = "sbas"    
    
    os.environ["OMP_NUM_THREADS"] = cores_entry.get() if cores_entry.get() else "1"


    # sbas_label = tk.Label(
    #     root, text="sbas intf.tab scene.tab N S xdim ydim [-atm ni] [-smooth sf]"
    #             "[-wavelength wl] [-incidence inc] [-range -rng] [-rms] [-dem]"
    # )
    # sbas_label.grid(row=4, column=0, columnspan=6, padx=10, pady=5, sticky="w")

    # Create progress bar
    progress_bar = ttk.Progressbar(root, mode="determinate")
    progress_bar.grid(row=15, column=0, columnspan=5, padx=10, pady=5, sticky="ew")

    # Create the console text area
    console_label = tk.Label(root, text="Console Output:")
    console_label.grid(row=16, column=0, columnspan=5, padx=10, pady=5)
    console_text = scrolledtext.ScrolledText(
        root, height=10, width=175, state=tk.DISABLED, wrap=tk.WORD
    )
    console_text.grid(row=17, column=0, columnspan=5, padx=10, pady=5)

    # Add tooltips to all widgets
    add_tooltip(
        folder1_entry,
        "Select the data folder containing Sentinel-1 images .SAFE folders."
    )
    add_tooltip(
        browse_button1,
        "Browse for the data folder. \nYou should move into the data folder and then click ok to select it."
    )
    add_tooltip(
        ascending_rb,
        "This selection creates \"asc\" folder such that \"Output Folder>Project Name>asc\"."
    )
    add_tooltip(
        descending_rb,
        "This selection creates \"des\" folder such that \"Output Folder>Project Name>des\"."
    )
    add_tooltip(
        browse_button2,
        "Browse for the GACOS data folder containing atmospheric correction files."
    )
    add_tooltip(
        dem_file_entry,
        "Select the DEM file to be used for processing. It should be in GMT format (.grd).\n"
        "GMTSAR make_dem.csh script can be used to generate the DEM file from SRTM data."
    )
    add_tooltip(
        browse_button_dem,
        "Browse for the DEM file."
    )
    add_tooltip(
        pin_file_entry,
        "This pin.II file is a text file containing the coordinates of 2 pins encompassing your AOI."
    )
    add_tooltip(
        browse_button_pin,
        "Browse for the pin.II file."
    )
    add_tooltip(
        project_name_entry,
        "A folder with your defined name here will be created in the \"Output Folder\"."
    )
    add_tooltip(
        output_folder_entry,
        "Select the folder where the output files will be saved."
    )
    add_tooltip(
        browse_button3,
        "Browse for the output folder."
    )
    add_tooltip(
        mst_entry,
        "Enter the custom master image date in the format yyyymmdd (optional).\n"
        "If not provided, the optimum master image will be selected automatically following the ESA-SNAP selection criteria."
    )
    add_tooltip(
        baselines_entry,
        "Enter the temporal and perpendicular baselines thresholds.\n"
        "No interferograms will be generated for images with baselines exceeding these thresholds."
    )
    add_tooltip(
        processing_option_menu,
        "Select the processing option for subswaths.\n"
        "You can choose to process all subswaths or only specific combinations of them.\n"
        "If more than one subswath is selected, those will be merged during the interferogram generation step."
    )    
    add_tooltip(
        multilooking_entry,
        "Define the multilooking values in range and azimuth directions.\n" 
        "This process will result in lower resolution interferograms while\n"
        "reducing the noise and improving coherence. The values should be integers.\n"
    )
    add_tooltip(
        filter_wavelength_entry,
        "Define the filter wavelength value in meters.\n"
        "This value will be used to filter the interferograms to reduce noise."
    )
    add_tooltip(
        cores_entry,
        "Define the number of cores to be used for parallel processing.\n"
        "This will speed up the different steps of the process by\n"
        "utilizing the defined cores for parallelization."
    )
    add_tooltip(
        coherence_thresholds_entry,
        "Enter coherence thresholds for masking and unwrapping, separated by a comma.\n"
        "Masking allows you to exclude areas with overall low coherence throughout the time series.\n"
        "Unwrapping threshold defines the absolute value of coherence for each interferogram."
    )
    add_tooltip(
        folder2_entry,
        "Select the folder containing GACOS atmospheric data in binary\n\".ztd\" format matching acquisition timestamps of input SLC images."
    )   
    add_tooltip(
        inc_angle_entry,
        "Enter the incidence angle in degrees (e.g., 37.0). This is used for atmospheric correction."
    )

    atm = " -atm" if atm_var.get() else ""
    rms = " -rms" if rms_var.get() else ""
    dem = " -dem" if dem_var.get() else ""
    smooth = f" -smooth {smooth_var_entry.get()}" if smooth_var_entry.get() else ""
    

    config = load_config()

    # # Load the last-used values or defaults
    
    folder1_entry.insert(0, config.get("in_data_dir", ""))
    if config.get("node"):
        sort_order.set(config.get("node", ""))
    dem_file_entry.insert(0, config.get("dem_file", ""))
    pin_file_entry.insert(0, config.get("pin_file", ""))
    project_name_entry.insert(0, config.get("project_name", ""))
    output_folder_entry.insert(0, config.get("output_dir", ""))

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
    if config.get("coherence_thresholds", ""):
        coherence_thresholds_entry.insert(0, config.get("coherence_thresholds", ""))
    else:
        coherence_thresholds_entry.insert(0, "0, 0.01")
    processing_option.set(
        config.get("subswath_option", processing_options[0])
    )
    if not config.get("atm_corr_option"):
        atm_option.set(atm_options[0])  # Set the initial value
    else:
        atm_option.set(config.get("atm_corr_option", ""))    # Set the value from previous run if present
    toggle_gacos_folder(atm_option, folder2_entry, browse_button2)
    
    folder2_entry.insert(0, config.get("gacos_dir", ""))
    if config.get("inc_angle"):
        inc_angle_entry.insert(0, config.get("inc_angle"))
    else:
        inc_angle_entry.insert(0, "37.0")
    
    # Create the Run button
    run_button = tk.Button(
        root,
        text="Run",
        command=lambda: on_run_button_click(
                root, 
                folder1_entry, 
                sort_order, 
                dem_file_entry, 
                pin_file_entry, 
                project_name_entry,
                output_folder_entry,
                mst_entry, 
                folder2_entry, 
                processing_option,
                atm_option,
                console_text,
                progress_bar, 
                baselines_entry, 
                multilooking_entry, 
                filter_wavelength_entry, 
                coherence_thresholds_entry, 
                inc_angle_entry,
                cores_entry,
                sbas,
                atm,
                rms,
                dem,
                smooth
            ),
    )
    run_button.grid(row=18, column=1, padx=10, pady=20)   
    add_tooltip(
        run_button,
        "Run the InSAR time series analysis with the provided inputs."
    )   
    
    
    # # Start the main loop
    root.mainloop()
    
    
def run_main(
    root,
    folder1_entry,
    sort_order,
    folder2_entry,
    dem_file_entry,
    pin_file_entry,
    project_name_entry,
    output_folder_entry,
    mst_entry,
    baselines_entry,
    multilooking_entry,
    filter_wavelength_entry,
    coherence_thresholds_entry,
    inc_angle_entry,
    processing_option,
    atm_option,
    cores_entry,
    sbas,
    atm,
    rms,
    dem,
    smooth,
    console_text,
    progress_bar
):
    try:
        in_data_dir = folder1_entry.get()

        node = sort_order.get()
        gacos_dir = folder2_entry.get()
        dem_file = dem_file_entry.get()
        pin_file = pin_file_entry.get()
        project_name = project_name_entry.get()
        output_dir = output_folder_entry.get()
        mst = mst_entry.get()
        baselines = baselines_entry.get()
        parallel_baseline, perpendicular_baseline = map(int, baselines.split(","))
        multilooking = multilooking_entry.get()
        rng, az = map(int, multilooking.split(","))
        filter_wavelength = filter_wavelength_entry.get()
        coherence_thresholds = coherence_thresholds_entry.get()
        masking_threshold = float(coherence_thresholds.split(",")[0])
        unwrapping_threshold = float(coherence_thresholds.split(",")[1])
        inc_angle = inc_angle_entry.get()
        subswath_option = processing_option.get()
        atm_corr_option = atm_option.get()
        ncores = int(cores_entry.get())

        config = load_config()
        config.update({
            'in_data_dir': in_data_dir,
            'node': node,
            'gacos_dir': gacos_dir,
            'dem_file': dem_file,
            'pin_file': pin_file,
            'project_name': project_name,
            'output_dir': output_dir,
            'baselines': baselines,
            'multilooking': multilooking,
            'filter_wavelength': filter_wavelength,
            'coherence_thresholds': coherence_thresholds,
            'inc_angle': inc_angle,
            'subswath_option': subswath_option,
            'atm_corr_option': atm_corr_option,
            'ncores': ncores,
            'sbas': sbas,
            'atm': atm,
            'rms': rms,
            'dem': dem,
            'smooth': smooth
        })
        save_config(config)
    except Exception as e:
        exitGUI(root, e, f"Error reading user inputs: {e}")

    # main function call from gmtsar_gui/ts_gmtsar_sbas_full.py
    main(
        root,
        in_data_dir,
        node,
        gacos_dir,
        dem_file,
        pin_file,
        project_name,
        output_dir,
        mst,
        parallel_baseline,
        perpendicular_baseline,
        rng,
        az,
        filter_wavelength,
        masking_threshold,
        unwrapping_threshold,
        inc_angle,
        subswath_option,
        atm_corr_option,
        ncores,
        sbas,
        atm,
        rms,
        dem,
        smooth,
        console_text,
        progress_bar
    )