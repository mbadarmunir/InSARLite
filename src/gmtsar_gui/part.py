import tkinter as tk
from tkinter import font, ttk, scrolledtext
from utils.utils import load_config_part, browse_folder, browse_file, save_config_part, exitGUI
from gmtsar_gui.part_network import p_start_network
import threading

def run_function(
    next_button,
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
            next_button.config(state=tk.NORMAL)
            save_config_part(config_part) 
            
        task_thread = threading.Thread(target=task_wrapper)
        task_thread.start()
        
    
    except Exception as e:
        exitGUI(root, not e, f"Error reading user inputs: {e}")

def next_function(
        folder1_entry,
        sort_order,
        dem_file_entry,
        pin_file_entry,
        project_name_entry,
        output_folder_entry,
        mst_entry,
        baselines_entry,
        processing_option
        ):
    print("Next button clicked")

    in_data_dir = folder1_entry.get()
    node = sort_order.get()        
    dem_file = dem_file_entry.get()
    pin_file = pin_file_entry.get()
    project_name = project_name_entry.get()
    output_dir = output_folder_entry.get()
    mst = mst_entry.get()
    baselines = baselines_entry.get()        
    subswath_option = processing_option.get()    

    print(in_data_dir, node, dem_file, pin_file, project_name, output_dir, mst, baselines, subswath_option)

def run_gui():
    root = tk.Tk()
    root.title("GMTSAR step-by-step Automated Workflow")

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
    
    # Add Run and Next buttons
    run_button = tk.Button(
        root,
        text="Run",
        command=lambda: run_function(
            next_button,
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

    next_button = tk.Button(
        root,
        text="Next",
        command=lambda: next_function(
            folder1_entry,
            sort_order,
            dem_file_entry,
            pin_file_entry,
            project_name_entry,
            output_folder_entry,
            mst_entry,
            baselines_entry,
            processing_option
        ),
        state=tk.DISABLED
    )
    next_button.grid(row=11, column=1, padx=10, pady=5, sticky="ew")


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

    root.mainloop()

if __name__ == "__main__":
    run_gui()