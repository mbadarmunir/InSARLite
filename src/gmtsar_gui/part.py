import tkinter as tk
from tkinter import font, ttk, scrolledtext
from utils.utils import load_config_part, browse_folder, browse_file, save_config_part, exitGUI, add_tooltip, save_highres_gui_image
from gmtsar_gui.part_network import p_start_network
from gmtsar_gui.masterselection import select_mst
from gmtsar_gui.structuring import orchestrate_structure_and_copy
from gmtsar_gui.alignment import align_sec_imgs
from gmtsar_gui.part_ifgs_gen import run_gui_ifg
import threading
import os
import pickle
import shutil

def run_function(
    start_alignment_button,
    skip_button,
    root,        
    folder1_entry,
    sort_order,
    dem_file_entry,
    pin_file_entry,
    project_name_entry,
    output_folder_entry,
    mst_entry,
    baselines_entry,
    processing_option,
    progress_bar,
    console_text
    ):    
    try:
        in_data_dir = folder1_entry.get()
        node = sort_order.get()        
        dem_file = dem_file_entry.get()
        pin_file = pin_file_entry.get()
        project_name = project_name_entry.get()
        output_dir = output_folder_entry.get()
        mst = mst_entry.get()
        baselines = baselines_entry.get()        
        subswath_option = processing_option.get()        

        config_part = load_config_part()
        config_part.update({
            'in_data_dir': in_data_dir,
            'node': node,            
            'dem_file': dem_file,
            'pin_file': pin_file,
            'project_name': project_name,
            'output_dir': output_dir,
            'baselines': baselines,            
            'subswath_option': subswath_option            
        })
        
        if os.path.exists(os.path.join(output_dir, project_name)):
            shutil.rmtree(os.path.join(output_dir, project_name))

        def task_wrapper():
            p_start_network(
            root,
            in_data_dir, node, dem_file, pin_file, project_name, output_dir, mst, baselines, subswath_option,
            progress_bar,
            console_text
            )
            root.after(0, on_task_complete)

        # Run the long-running task in a separate thread
        def on_task_complete():
            start_alignment_button.config(state=tk.NORMAL)
            skip_button.config(state=tk.DISABLED)
            save_config_part(config_part)                  

        task_thread = threading.Thread(target=task_wrapper)
        task_thread.start()
        
    
    except Exception as e:
        exitGUI(root, not e, f"Error reading user inputs: {e}")

def start_alignment_function(
            root,
            progress_bar,
            console_text,
            next_button,  
            project_name_entry,          
            output_folder_entry            
        ):
    paths_file = os.path.join(output_folder_entry.get(), project_name_entry.get(), "paths.pkl")
    mst_file = os.path.join(output_folder_entry.get(), project_name_entry.get(), "mst.pkl")
    log_file_path = os.path.join(output_folder_entry.get(), project_name_entry.get(), "alignment.log")

    if os.path.exists(paths_file) and os.path.exists(mst_file):
        with open(paths_file, 'rb') as pf, open(mst_file, 'rb') as mf:
            paths = pickle.load(pf)
            mst = pickle.load(mf)

    def task_wrapper():
        align_sec_imgs(paths, mst, console_text, log_file_path)
        root.after(0, on_task_complete)

    # Run the long-running task in a separate thread
    def on_task_complete():
        next_button.config(state=tk.NORMAL)
        progress_bar['value'] = 100
        root.update_idletasks()
         
    
    progress_bar['value'] = 0
    root.update_idletasks()
    task_thread = threading.Thread(target=task_wrapper)
    task_thread.start()

def next_function(root, project_name, output_folder):
    config_part = load_config_part()
    gmtsar_path = os.getenv('GMTSAR')
    if gmtsar_path is None:
        raise EnvironmentError("GMTSAR environment variable is not set.")
    
    btconfig = os.path.join(gmtsar_path, 'gmtsar', 'csh', 'batch_tops.config')      
    output_dir = config_part['output_dir']
    node = config_part['node']
    subswath_option = config_part['subswath_option']
    dem_file = config_part['dem_file']
    pin_file = config_part['pin_file']
    in_data_dir = config_part['in_data_dir']
    project_name = config_part['project_name']      
    paths_file = os.path.join(output_dir, project_name, "paths.pkl")
    mst_file = os.path.join(output_dir, project_name, "mst.pkl")

    paths, structure = orchestrate_structure_and_copy(
            output_dir, project_name, node, subswath_option, dem_file, pin_file, in_data_dir, btconfig, 
        )           
    pdata = paths.get("pdata")
    with open(paths_file, 'wb') as pf:
        pickle.dump(paths, pf)
    with open(mst_file, 'wb') as mf:
        pickle.dump(select_mst(pdata), mf)
    root.destroy()    
    run_gui_ifg(project_name, output_folder)    

def run_gui():
    root = tk.Tk()
    root.title("Step 1: Interferogram Network Generation")

    # Create a help/info icon
    info_label = tk.Label(root, text="i", fg="blue", cursor="question_arrow", font=("Helvetica", 12, "bold"))
    info_label.grid(row=0, column=5, padx=10, pady=10, sticky="w")  # or use pack()

    # Add tooltip to it
    add_tooltip(info_label, "This step lets you generate the interferogram network for the selected Sentinel-1 images.\n"
                        "You can choose different baselines thresholds and analyze the connectivity of the network.\n"
                        "You may want to avoid longer baselines (edges/lines in the plot) to ensure better coherence.\n"
                        "you may on the other hand want to include baselines longer enough to ensure better graph connectivity.\n"
                        "Once satisfied with the generated graph, you may align all images w.r.t. the master image.\n"
                        "You can then proceed to the next step to generate the interferograms and coherence maps.")


    # Configure the grid to be scalable
    for i in range(20):
        root.grid_rowconfigure(i, weight=1)
        root.grid_columnconfigure(i, weight=1)

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

    # Create the required input fields
    folder1_label = tk.Label(root, text="Select Data Folder:")
    folder1_label.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
    folder1_entry = tk.Entry(root, width=50)
    folder1_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
    browse_button1 = tk.Button(root, text="Browse", command=lambda: browse_folder(folder1_entry, "data_dir"))
    browse_button1.grid(row=0, column=2, padx=10, pady=5, sticky="ew")

    sort_order = tk.StringVar()
    sort_order.set("Descending")  # Set "Descending" as the default option
    ascending_rb = tk.Radiobutton(root, text="Ascending", variable=sort_order, value="Ascending")
    ascending_rb.grid(row=0, column=3, padx=10, pady=5, sticky="ew")
    descending_rb = tk.Radiobutton(root, text="Descending", variable=sort_order, value="Descending")
    descending_rb.grid(row=0, column=4, padx=10, pady=5, sticky="ew")

    dem_file_label = tk.Label(root, text="Select DEM file:")
    dem_file_label.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
    dem_file_entry = tk.Entry(root, width=50)
    dem_file_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")    
    browse_button_dem = tk.Button(
        root,
        text="Browse",
        command=lambda: browse_file(
            dem_file_entry, "dem_file", [("DEM files", "*.grd")]
        ),
    )
    browse_button_dem.grid(row=1, column=2, padx=10, pady=5, sticky="ew")

    pin_file_label = tk.Label(root, text="Select pin.II file:")
    pin_file_label.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
    pin_file_entry = tk.Entry(root, width=50)
    pin_file_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
    browse_button_pin = tk.Button(
        root,
        text="Browse",
        command=lambda: browse_file(
            pin_file_entry, "pin_file", [("pin files", "*.II")]
        ),
    )

    browse_button_pin.grid(row=2, column=2, padx=10, pady=5, sticky="ew")

    project_name_label = tk.Label(root, text="Project Name:")
    project_name_label.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
    project_name_entry = tk.Entry(root, width=50)
    project_name_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

    output_folder_label = tk.Label(root, text="Select Output Folder:")
    output_folder_label.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
    output_folder_entry = tk.Entry(root, width=50)
    output_folder_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
    browse_button_output = tk.Button(root, text="Browse", command=lambda: browse_folder(output_folder_entry, "output_dir"))
    browse_button_output.grid(row=4, column=2, padx=10, pady=5, sticky="ew")

    # Custom master image entry textbox
    mst_label = tk.Label(root, text="Custom Master Image (format:yyyymmdd):*")
    mst_label.grid(row=5, column=0, padx=10, pady=5)
    mst_entry = tk.Entry(root, width=50)
    mst_entry.grid(row=5, column=1, padx=10, pady=5)
    mst_label_e = tk.Label(root, text="*(Optional)")
    mst_label_e.grid(row=5, column=2, pady=5)

    # Baselines entry
    baselines_label = tk.Label(
        root, text="Baselines (format: tmp_baseline, perp_baseline):"
    )    
    baselines_label.grid(row=6, column=0, padx=10, pady=5, sticky="ew")
    baselines_entry = tk.Entry(root, width=50)
    baselines_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

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
    processing_option_menu.grid(row=7, column=1, padx=10, pady=5)

    progress_bar = ttk.Progressbar(root, mode="determinate")
    progress_bar.grid(row=8, column=0, columnspan=3, padx=10, pady=5, sticky="ew")

    console_label = tk.Label(root, text="Console Output:")
    console_label.grid(row=9, column=0, padx=10, pady=5, sticky="ew")
    console_text = scrolledtext.ScrolledText(root, height=10, width=50, state=tk.DISABLED, wrap=tk.WORD)
    console_text.grid(row=10, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
    
    # Add Run, start alignment and Next buttons
    run_button = tk.Button(
        root,
        text="Run",
        command=lambda: run_function(
            start_alignment_button,
            skip_button,
            root,            
            folder1_entry,
            sort_order,
            dem_file_entry,
            pin_file_entry,
            project_name_entry,
            output_folder_entry,
            mst_entry,
            baselines_entry,
            processing_option,
            progress_bar,
            console_text
        )
    )
    run_button.grid(row=11, column=0, padx=10, pady=5, sticky="ew")

    start_alignment_button = tk.Button(
        root,
        text="Start Alignment",
        command=lambda: start_alignment_function(
            root,
            progress_bar,
            console_text,
            next_button,  
            project_name_entry,          
            output_folder_entry
        ),
        state=tk.DISABLED
    )
    start_alignment_button.grid(row=11, column=1, padx=10, pady=5, sticky="ew")

    next_button = tk.Button(
        root,
        text="Next",
        command=lambda: (
            next_function(root, project_name_entry.get(), output_folder_entry.get())
        ),
        state=tk.DISABLED
    )
    next_button.grid(row=11, column=2, padx=10, pady=5, sticky="ew")

    skip_button = tk.Button(
        root,
        text="Skip",
        command=lambda: (
            (
                lambda: (
                    (
                        lambda: (
                            config_part := load_config_part(),
                            config_part.update({
                                'in_data_dir': folder1_entry.get(),
                                'node': sort_order.get(),
                                'dem_file': dem_file_entry.get(),
                                'pin_file': pin_file_entry.get(),
                                'project_name': project_name_entry.get(),
                                'output_dir': output_folder_entry.get(),
                                'baselines': baselines_entry.get(),
                                'subswath_option': processing_option.get()
                            })
                        )
                    )()
                )
            )(),
            next_function(root, project_name_entry.get(), output_folder_entry.get()))
    )
    skip_button.grid(row=11, column=3, padx=10, pady=5, sticky="ew")

    config = load_config_part()

    # Load the last-used values or defaults
    folder1_entry.insert(0, config.get("in_data_dir", ""))
    sort_order.set(config.get("node", ""))
    dem_file_entry.insert(0, config.get("dem_file", ""))
    pin_file_entry.insert(0, config.get("pin_file", ""))
    project_name_entry.insert(0, config.get("project_name", ""))
    output_folder_entry.insert(0, config.get("output_dir", ""))
    mst_entry.insert(0, config.get("mst", ""))
    baselines_entry.insert(0, config.get("baselines", ""))
    processing_option.set(
        config.get("subswath_option", processing_options[0])
    )

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
        browse_button_output,
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
        run_button,
        "Run the Interferograms network generation process with the provided inputs."
    )
    add_tooltip(
        start_alignment_button,
        "Start the alignment process after the Interferograms network generation\nis completed and you are satisfied with the connectivity."
    )
    add_tooltip(
        next_button,
        "Proceed to the next step after the alignment process is complete."
    )
    add_tooltip(
        skip_button,
        "Skip everything and move on to the next step for the currently defined inputs."
    )
    # root.after(3000, lambda: save_highres_gui_image(root))  # Save after 3 seconds
    root.mainloop()

if __name__ == "__main__":
    run_gui()