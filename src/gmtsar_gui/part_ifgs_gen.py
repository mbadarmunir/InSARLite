import tkinter as tk
from tkinter import font, ttk, scrolledtext
from gmtsar_gui.ifgs_generation import gen_ifgs
from gmtsar_gui.part_unwrap import run_gui_uwp
from gmtsar_gui.mergeIFGs import merge_thread
from utils.utils import add_tooltip, update_console
import threading
import os
import pickle
import time

def run_function(
    next_button,
    skip_button,
    root,
    project_name, 
    output_folder,
    multilooking_entry,      
    filter_wavelength_entry,
    cores_entry,
    progress_bar,
    console_text
    ):      
    skip_button.config(state=tk.DISABLED)      
    rng, az = map(int, multilooking_entry.get().split(","))
    filter_wavelength = filter_wavelength_entry.get()
    ncores = int(cores_entry.get())
    paths_file = os.path.join(output_folder, project_name, "paths.pkl")
    mst_file = os.path.join(output_folder, project_name, "mst.pkl")
    log_file_path = os.path.join(output_folder, project_name, f"ifgs_{time.strftime('%d%b%Y%H%M%S', time.localtime())}.log")
    
    main_start_time = time.time()

    if os.path.exists(paths_file) and os.path.exists(mst_file):
        with open(paths_file, 'rb') as pf, open(mst_file, 'rb') as mf:
            paths = pickle.load(pf)
            mst = pickle.load(mf)

    def task_wrapper():
        gen_ifgs(paths, mst, filter_wavelength, rng, az, ncores, console_text, log_file_path)
        progress_bar['value'] = 50
        ifgs_time = time.time()
        ifgs_elapsed_time = time.strftime("%H:%M:%S", time.gmtime(ifgs_time - main_start_time)) + f".{int((ifgs_time - main_start_time) % 1 * 100):02d}"

        update_console(console_text, 
                    f"IFGs generated in {ifgs_elapsed_time}", 
                    log_file_path) 

        root.update_idletasks()
        pmerge = paths.get("pmerge")
        if pmerge and os.path.exists(pmerge):
            merge_thread(pmerge, ncores, console_text, log_file_path)
        mrg_time = time.time()
        mrg_elapsed_time = time.strftime("%H:%M:%S", time.gmtime(mrg_time - ifgs_time)) + f".{int((mrg_time - ifgs_time) % 1 * 100):02d}"
        
        step2_elapsed_time = time.strftime("%H:%M:%S", time.gmtime(mrg_time - main_start_time)) + f".{int((mrg_time - main_start_time) % 1 * 100):02d}"

        update_console(console_text, 
                    f"IFGs merged in {mrg_elapsed_time}", 
                    log_file_path) 
        
        update_console(console_text, 
                    f"Step 2 completed in {step2_elapsed_time}", 
                    log_file_path)

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
        root,
        project_name, 
        output_folder        
    ):
    root.destroy()    
    run_gui_uwp(project_name, output_folder)
    
def run_gui_ifg(project_name, output_folder):
    root = tk.Tk()
    root.title("Step 2: Interferograms Generation")

    # Create a help/info icon
    info_label = tk.Label(root, text="i", fg="blue", cursor="question_arrow", font=("Helvetica", 12, "bold"))
    info_label.grid(row=0, column=5, padx=10, pady=10, sticky="w")  # or use pack()

    # Add tooltip to it
    add_tooltip(info_label, "In this step, you can generate interferograms for the pairs\n"
            "defined by the interferogram network plot generated in previous step.\n"
            "One interferogram of (each) subswath will be generated using single core irrespective of the defined \"Number of cores\"\n"
            "to convert elevation values from DEM into corresponding phase values.\n"
            "Once the elevation phase is calculated, all subsequent interferograms\n"
            "per subswath will be generated in parallel utilizing the defined number of cores.\n"
            "Additionally:\n"
            "1. The coherence grid for each interferogram will be generated\n"
            "2. Golden filter will be applied to the interferograms and \n"
            "   corresponding filtererd phase files will be generated\n"
            "3. The filtered interferograms per subswath will be merged if applicable\n"
            "4. Mean coherence grid will be generated for all interferograms.")

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
    # Multilooking entry
    multilooking_label = tk.Label(root, text="Multilooking (format: rng, az):")
    multilooking_label.grid(row=0, column=0, padx=10, pady=5)
    multilooking_entry = tk.Entry(root, width=50)
    multilooking_entry.grid(row=0, column=1, padx=10, pady=5)

    # Filter wavelength entry
    filter_wavelength_label = tk.Label(root, text="Filter Wavelength (format: int):")
    filter_wavelength_label.grid(row=1, column=0, padx=10, pady=5)
    filter_wavelength_entry = tk.Entry(root, width=50)
    filter_wavelength_entry.grid(row=1, column=1, padx=10, pady=5)

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
            skip_button,
            root,
            project_name, 
            output_folder,
            multilooking_entry,      
            filter_wavelength_entry,
            cores_entry,
            progress_bar,
            console_text
        )
    )
    run_button.grid(row=5, column=0, padx=10, pady=5, sticky="ew")
    

    next_button = tk.Button(
        root,
        text="Next",
        command=lambda: next_function(        
            root,
            project_name, 
            output_folder        
        ),
        state=tk.DISABLED
    )
    next_button.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

    skip_button = tk.Button(
        root,
        text="Skip",
        command=lambda: next_function(        
            root,
            project_name, 
            output_folder        
        )
    )
    skip_button.grid(row=5, column=2, padx=10, pady=5, sticky="ew")

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
        "This will speed up the interferograms generation process by\n"
        "utilizing the defined cores for parallelization."
    )

    add_tooltip(
        run_button,
        "Run the Interferograms generation process with the provided inputs."
    )    
    add_tooltip(
        next_button,
        "Proceed to the next step after the interferograms have been generated and merged if applicable."
    )
    add_tooltip(
        skip_button,
        "Skip everything and move on to the next step for the currently defined inputs."
    )
    
    # Load the defaults
    multilooking_entry.insert(0, "8, 2")
    filter_wavelength_entry.insert(0, "200")


    root.mainloop()

if __name__ == "__main__":
    run_gui_ifg()