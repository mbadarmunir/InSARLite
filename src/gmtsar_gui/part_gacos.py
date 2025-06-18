import tkinter as tk
from tkinter import font, ttk, scrolledtext
from gmtsar_gui.gacos_atm_corr import gacos
from gmtsar_gui.part_SBAS import run_gui_sb
from utils.utils import browse_folder, update_console, add_tooltip
import threading
import os
import pickle
import time

def run_function(
    next_button,    
    root,
    project_name, 
    output_folder,
    gacos_dir,
    incidence,    
    ncores,
    progress_bar,
    console_text
    ):                
    paths_file = os.path.join(output_folder, project_name, "paths.pkl")    
    log_file_path = os.path.join(output_folder, project_name, f"gacos_{time.strftime('%d%b%Y%H%M%S', time.localtime())}.log")
    
    main_start_time = time.time()


    if os.path.exists(paths_file):
        with open(paths_file, 'rb') as pf:
            paths = pickle.load(pf)
            
    def task_wrapper():
        pmerge = paths.get("pmerge")
        if pmerge and os.path.exists(pmerge):
            IFGs = next(os.walk(pmerge))[1]
            intfdir = pmerge        
        else:
            for key in ["pF1", "pF2", "pF3"]:
                dir_path = paths.get(key)
                if dir_path and os.path.exists(dir_path):
                    intfdir = os.path.join(dir_path, "intf_all")
                    IFGs = next(os.walk(intfdir))[1]                
                    break
        os.chdir(intfdir)
        if gacos_dir and os.path.exists(gacos_dir):
            update_console(console_text, "Performing GACOS correction ...", log_file_path)
            tdir = os.path.join(os.path.dirname(intfdir), 'topo')                
        gacos(IFGs, gacos_dir, tdir, incidence, intfdir, num_cores=ncores)
        gacos_time = time.time()        
        gacos_elapsed_time = time.strftime("%H:%M:%S", time.gmtime(gacos_time - main_start_time)) + f".{int((gacos_time - main_start_time) % 1 * 100):02d}"
        update_console(
            console_text,
            f"GACOS atmospheric correction completed in {gacos_elapsed_time}",
            log_file_path
        )
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

def next_function(
        root, project_name, output_folder
        ):
    root.destroy()    
    run_gui_sb(project_name, output_folder)
    
def run_gui_gacos(project_name, output_folder):
    root = tk.Tk()
    root.title("Step 4: GACOS atmospheric correction (Optional)")

    # Create a help/info icon
    info_label = tk.Label(root, text="i", fg="blue", cursor="question_arrow", font=("Helvetica", 12, "bold"))
    info_label.grid(row=0, column=5, padx=10, pady=10, sticky="w")  # or use pack()

    # Add tooltip to it
    add_tooltip(info_label, "Using this part of the tool, you can apply GACOS atmospheric correction to the unwrapped interferograms.\n"
        "You can select the GACOS data folder, specify the incidence angle, and the number of cores to use for processing.\n"
        "The GACOS data folder should contain the GACOS data files in binary format for the area of interest matching\n" \
        "with the acquisition timestamps of the whole input time series.\n"
        "The incidence angle is used to adjust the atmospheric correction based on the geometry of the interferograms.\n"
        "The number of cores can be adjusted to speed up the processing.")

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
    
    gacos_folder_label = tk.Label(root, text="Select GACOS Data Folder:")
    gacos_folder_label.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
    gacos_folder_entry = tk.Entry(root, width=50)
    gacos_folder_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
    browse_buttong = tk.Button(root, text="Browse", command=lambda: browse_folder(gacos_folder_entry, "gacos_data_dir"))
    browse_buttong.grid(row=0, column=2, padx=10, pady=5, sticky="ew")

    # Incidence angle entry
    incidence_angle_label = tk.Label(
        root, text="Incidence Angle (format: float):"
    )
    incidence_angle_label.grid(row=1, column=0, padx=10, pady=5)
    incidence_angle_entry = tk.Entry(root, width=50)
    incidence_angle_entry.grid(row=1, column=1, padx=10, pady=5)

    # Number of cores entry
    cores_label = tk.Label(root, text="Number of cores:")
    cores_label.grid(row=1, column=3, padx=10, pady=5)
    cores_entry = tk.Entry(root, width=10)
    cores_entry.grid(row=1, column=4, padx=10, pady=5)

    progress_bar = ttk.Progressbar(root, mode="determinate")
    progress_bar.grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky="ew")

    console_label = tk.Label(root, text="Console Output:")
    console_label.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
    console_text = scrolledtext.ScrolledText(root, height=10, width=50, state=tk.DISABLED, wrap=tk.WORD)
    console_text.grid(row=4, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
    
    # Add Run and Next buttons
    run_button = tk.Button(
        root,
        text="Run",
        command=lambda: run_function(
            next_button,               
            root,
            project_name, 
            output_folder,
            gacos_folder_entry.get(),
            incidence_angle_entry.get(), 
            cores_entry.get(),   
            progress_bar,
            console_text
        )
    )
    run_button.grid(row=5, column=0, padx=10, pady=5, sticky="ew")
    

    next_button = tk.Button(
        root,
        text="Next",
        command=lambda: next_function(
            
        ),
        state=tk.DISABLED
    )
    next_button.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

    gacos_button = tk.Button(
        root,
        text="GACOS Correction",
        command=lambda: next_function(root),
        state=tk.DISABLED
    )
    gacos_button.grid(row=5, column=2, padx=10, pady=5, sticky="ew")

    add_tooltip(
        gacos_folder_entry,
        "Select the folder containing GACOS atmospheric data in binary\n\".ztd\" format matching acquisition timestamps of input SLC images."
    )
    add_tooltip(
        browse_buttong,
        "Browse for the GACOS data folder containing atmospheric correction files."
    )
    
    add_tooltip(
        incidence_angle_entry,
        "Enter the incidence angle in degrees (e.g., 37.0). This is used for atmospheric correction."
    )
    add_tooltip(
        cores_entry,
        "Specify the number of CPU cores to use for parallel GACOS correction processing."
    )
    add_tooltip(
        run_button,
        "Run the GACOS correction process with the provided inputs."
    )    
    add_tooltip(
        next_button,
        "Proceed to the next step after the GACOS correction process is complete."
    )
    # Load the defaults
    incidence_angle_entry.insert(0, "37.0")    


    root.mainloop()

if __name__ == "__main__":
    run_gui_gacos()