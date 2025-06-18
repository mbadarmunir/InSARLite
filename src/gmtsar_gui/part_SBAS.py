import tkinter as tk
import threading
import os
import pickle
import time
from tkinter import font, ttk, scrolledtext
from gmtsar_gui.sb_inversion import sb_inversion
from gmtsar_gui.part_output import run_gui_out
from utils.utils import update_console, add_tooltip

def run_function(
    next_button,    
    root,
    project_name, 
    output_folder,    
    incidence,
    sbas,
    cores,
    atm,
    rms,
    dem,    
    smooth,
    progress_bar,
    console_text
    ):                
    paths_file = os.path.join(output_folder, project_name, "paths.pkl")    
    log_file_path = os.path.join(output_folder, project_name, f"sbas_{time.strftime('%d%b%Y%H%M%S', time.localtime())}.log")
    
    main_start_time = time.time()
    
    update_console(console_text, 
                   f"{time.strftime('%d %b %Y %H:%M:%S', time.localtime(main_start_time))}: Starting SBAS Process...", 
                   log_file_path)   

    if os.path.exists(paths_file):
        with open(paths_file, 'rb') as pf:
            paths = pickle.load(pf)    
    
    def task_wrapper():        
        psbas = paths.get('psbas')
        if psbas and os.path.exists(psbas):
            update_console(console_text, "Running SB Inversion", log_file_path)  
            if sbas == "SBAS Parallel":
                sbas_mode = "sbas_parallel"
                os.environ["OMP_NUM_THREADS"] = cores if cores else "1"
            else:
                sbas_mode = "sbas"
        
            print(f"Using SBAS mode: {sbas}")                        
            sb_inversion(psbas, paths, incidence, atm, rms, dem, sbas_mode, smooth)
        root.after(0, on_task_complete)
    
    # Run the long-running task in a separate thread
    def on_task_complete():
        next_button.config(state=tk.NORMAL)        
        progress_bar['value'] = 100
        sbas_time = time.time()
        sbas_elapsed_time = time.strftime("%H:%M:%S", time.gmtime(sbas_time - main_start_time)) + f".{int((sbas_time - main_start_time) % 1 * 100):02d}"

        update_console(console_text, 
                    f"SBAS Process Ended in {sbas_elapsed_time}", 
                    log_file_path) 

        root.update_idletasks()
    
    progress_bar['value'] = 0
    root.update_idletasks()               

    task_thread = threading.Thread(target=task_wrapper)
    task_thread.start()

    
def next_function(
        root, project_name, output_folder
        ):
    root.destroy()
    run_gui_out(project_name, output_folder)
    
def run_gui_sb(project_name, output_folder):
    root = tk.Tk()
    root.title("Step 5: SB Inversion")

    # Create a help/info icon
    info_label = tk.Label(root, text="i", fg="blue", cursor="question_arrow", font=("Helvetica", 12, "bold"))
    info_label.grid(row=0, column=6, padx=10, pady=10, sticky="w")  # or use pack()

    # Add tooltip to it
    add_tooltip(info_label, "This is the final step of the SBAS processing.\n"
                "In this step, you can run the SB Inversion algorithm to convert\n"
                "unwrapped phase to displacement time series.\n"
                "This step will use the GACOS corrected and detrended unwrapped interferograms if available,\n"
                "or the (simple) unwrapped interferograms otherwise.\n"
                "The output will be a line of sight velocity file and a time series of displacements.\n"
                "The arguments for this step that are not asked from user are\n"
                "automatically prepared/searched/calculated from the metadata of input images or already available products.\n"
                "Actual sbas or sbas_parallel command is:\n"
                "--------------------------------------------------------\n"
                "sbas intf.tab scene.tab N S xdim ydim [-atm ni] [-smooth sf]\n"
                "[-wavelength wl] [-incidence inc] [-range -rng] [-rms] [-dem]")

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
    

    # Incidence angle entry
    incidence_angle_label = tk.Label(
        root, text="Incidence Angle (format: float):"
    )
    incidence_angle_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
    incidence_angle_entry = tk.Entry(root, width=50)
    incidence_angle_entry.grid(row=0, column=1, padx=10, pady=5)

    # Number of cores entry
    cores_label = tk.Label(root, text="Number of cores:")
    cores_label.grid(row=0, column=3, padx=10, pady=5)
    cores_entry = tk.Entry(root, width=10)
    cores_entry.grid(row=0, column=4, padx=10, pady=5)

    # Native sbas atmospheric correction
    sb_args_label = tk.Label(
        root, text="SBAS Arguments:"
    )
    sb_args_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
    
    rms_var = tk.BooleanVar(value=True)
    dem_var = tk.BooleanVar(value=True)

    # Frame to hold the checkboxes side by side
    sbas_args_frame = tk.Frame(root)
    sbas_args_frame.grid(row=1, column=1, columnspan=3, padx=10, pady=5, sticky="w")    

    rms_checkbox = tk.Checkbutton(sbas_args_frame, text="-rms", variable=rms_var)
    rms_checkbox.pack(side=tk.LEFT, padx=(0, 10))
    add_tooltip(rms_checkbox, "Check to calculate RMS of residuals (-rms).")

    dem_checkbox = tk.Checkbutton(sbas_args_frame, text="-dem", variable=dem_var)
    dem_checkbox.pack(side=tk.LEFT)
    add_tooltip(dem_checkbox, "Check to generate DEM residual error file in SB inversion (-dem).")

    smooth_var_label = tk.Label(
        root, text="Smoothing factor:"
    )
    smooth_var_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
    smooth_var_entry = tk.Entry(root, width=10)
    smooth_var_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
    smooth_var_entry.insert(0, "5.0")  # Default value for smoothing factor
    add_tooltip(
        smooth_var_entry, 
        "Enter the smoothing factor for the SBAS inversion.\n"
        "Default is 5.0, but you can adjust it based on your data."
    )

    atm_var_label = tk.Label(
        root, text="Atmospheric correction iterations:"
    )
    atm_var_label.grid(row=2, column=2, padx=10, pady=5, sticky="w")
    atm_var_entry = tk.Entry(root, width=10)
    atm_var_entry.grid(row=2, column=3, padx=10, pady=5, sticky="w")
    atm_var_entry.insert(0, "0")  # Default value for smoothing factor
    add_tooltip(
        atm_var_entry, 
        "Enter the No. of iterations for atm corrections."        
    )

    # Store the values of the checkboxes    
    rms = "-rms" if rms_var.get() else ""
    dem = "-dem" if dem_var.get() else ""
    smooth = f"-smooth {smooth_var_entry.get()}" if smooth_var_entry.get() else ""
    atm = f"-atm {atm_var_entry.get()}" if atm_var_entry.get() else "-atm 0"

    # SBAS mode selection dropdown
    sbas_mode_label = tk.Label(root, text="SBAS Mode:")
    sbas_mode_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
    sbas_mode_var = tk.StringVar(value="SBAS")
    sbas_mode_dropdown = ttk.Combobox(
        root,
        textvariable=sbas_mode_var,
        values=["SBAS", "SBAS Parallel"],
        state="readonly",
        width=20
    )
    sbas_mode_dropdown.grid(row=3, column=1, padx=10, pady=5, sticky="w")    
    add_tooltip(
        sbas_mode_dropdown,
        "Choose 'SBAS' for standard processing or 'SBAS Parallel' to use multi-core processing.\n"
         "The 'SBAS Parallel' uses GNU Parallel for implementing parallelization.\n"
         "Make sure GNU Parallel is installed and available in your PATH if you use this option."
    )    

    # sbas_label = tk.Label(
    #     root, text="sbas intf.tab scene.tab N S xdim ydim [-atm ni] [-smooth sf]"
    #             "[-wavelength wl] [-incidence inc] [-range -rng] [-rms] [-dem]"
    # )
    # sbas_label.grid(row=4, column=0, columnspan=6, padx=10, pady=5, sticky="w")

    progress_bar = ttk.Progressbar(root, mode="determinate")
    progress_bar.grid(row=5, column=0, columnspan=3, padx=10, pady=5, sticky="ew")

    console_label = tk.Label(root, text="Console Output:")
    console_label.grid(row=6, column=0, padx=10, pady=5, sticky="ew")
    console_text = scrolledtext.ScrolledText(root, height=10, width=50, state=tk.DISABLED, wrap=tk.WORD)
    console_text.grid(row=7, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
    
    # Add Run and Next buttons
    run_button = tk.Button(
        root,
        text="Run",
        command=lambda: run_function(
            next_button,               
            root,
            project_name, 
            output_folder,            
            incidence_angle_entry.get(),    
            sbas_mode_var.get(),
            cores_entry.get(),
            atm,
            rms,
            dem,
            smooth,
            progress_bar,
            console_text
        )
    )
    run_button.grid(row=8, column=0, padx=10, pady=5, sticky="ew")
    

    next_button = tk.Button(
        root,
        text="Next",
        command=lambda: next_function(
        root, project_name, output_folder
        ),
        state=tk.DISABLED
    )
    next_button.grid(row=8, column=1, padx=10, pady=5, sticky="ew")

    skip_button = tk.Button(
        root,
        text="Skip",
        command=lambda: next_function(
        root, project_name, output_folder
        )
    )
    skip_button.grid(row=8, column=2, padx=10, pady=5, sticky="ew")

    add_tooltip(
        incidence_angle_entry, 
        "Enter the incidence angle in degrees."
    )
    add_tooltip(
        cores_entry, 
        "Enter the number of CPU cores to use for processing.\n"
        "This can speed up the SB Inversion process.\n"
        "It is usable only if sbas parallel algorithm is used.\n"
        "It dynamically sets Environment Variable OMP_NUM_THREADS value equal to the user specified value.\n"
        "Users are advised to read more about OpenMP to learn about the implementation of parallelization here."
        
    )

    add_tooltip(
        run_button, 
        "Run the SB Inversion process.\n"
        "This will generate the line of sight velocity file and time series of displacements."
    )
    add_tooltip(
        next_button, 
        "Proceed to the next step after running the SB Inversion process.\n"
        "This will take you to the output visualization step."
    )
    add_tooltip(
        skip_button, 
        "Skip the SB Inversion process and proceed to the next step.\n"
        "This will take you to the output visualization step without running the SB Inversion."
    )

    # Load the defaults
    incidence_angle_entry.insert(0, "37.0")    


    root.mainloop()

if __name__ == "__main__":
    run_gui_sb()