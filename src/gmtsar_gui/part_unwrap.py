import tkinter as tk
from tkinter import font, ttk, scrolledtext
from gmtsar_gui.unwrapping import unwrap
from gmtsar_gui.part_gacos import run_gui_gacos
from gmtsar_gui.mean_corr import create_mean_grd
from gmtsar_gui.part_SBAS import run_gui_sb
from gmtsar_gui.masking import create_mask
import threading
import os
import pickle

def run_function(
    next_button,
    skip_button,    
    root,
    project_name, 
    output_folder,
    coherence_threshold,    
    ncores,
    progress_bar,
    console_text
    ):     

    masking_threshold, unwrapping_threshold = map(float, coherence_threshold.split(","))       
    skip_button.config(state=tk.DISABLED)
    paths_file = os.path.join(output_folder, project_name, "paths.pkl")    
    log_file_path = os.path.join(output_folder, project_name, "unwrapping.log")

    if os.path.exists(paths_file):
        with open(paths_file, 'rb') as pf:
            paths = pickle.load(pf)
            
    def task_wrapper():
        
        pmerge = paths.get("pmerge")
        if pmerge and os.path.exists(pmerge):            
            intfdir = pmerge        
        else:
            for key in ["pF1", "pF2", "pF3"]:
                dir_path = paths.get(key)
                if dir_path and os.path.exists(dir_path):
                    intfdir = os.path.join(dir_path, "intf_all")                               
                    break
        create_mean_grd(intfdir)
        create_mask(intfdir, masking_threshold, mask="mask_def.grd")
        unwrap(paths, unwrapping_threshold, ncores, console_text, log_file_path)
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

def gacos_function(
        root, project_name, output_folder
        ):
    root.destroy() 
    run_gui_gacos(project_name, output_folder)

    
def run_gui_uwp(project_name, output_folder):
    root = tk.Tk()
    root.title("Unwrap Interferograms")

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
    # Coherence Threshold entry
    coherence_thresholds_label = tk.Label(
        root, text="Coherence Thresholds (format: masking, unwrapping):"
    )
    coherence_thresholds_label.grid(row=0, column=0, padx=10, pady=5)
    coherence_thresholds_entry = tk.Entry(root, width=50)
    coherence_thresholds_entry.grid(row=0, column=1, padx=10, pady=5)
    coherence_thresholds_label_e = tk.Label(root, text="(e.g. 0, 0.01) where 0 for masking means no masking")
    coherence_thresholds_label_e.grid(row=0, column=2, pady=5)

    # Number of cores entry
    cores_label = tk.Label(root, text="Number of cores:")
    cores_label.grid(row=0, column=3, padx=10, pady=5)
    cores_entry = tk.Entry(root, width=10)
    cores_entry.grid(row=0, column=4, padx=10, pady=5)

    progress_bar = ttk.Progressbar(root, mode="determinate")
    progress_bar.grid(row=1, column=0, columnspan=3, padx=10, pady=5, sticky="ew")

    console_label = tk.Label(root, text="Console Output:")
    console_label.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
    console_text = scrolledtext.ScrolledText(root, height=10, width=50, state=tk.DISABLED, wrap=tk.WORD)
    console_text.grid(row=3, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
    
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
            coherence_thresholds_entry.get(), 
            cores_entry.get(),   
            progress_bar,
            console_text
        )
    )
    run_button.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
    

    next_button = tk.Button(
        root,
        text="Next",
        command=lambda: next_function(
            
        ),
        state=tk.DISABLED
    )
    next_button.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

    gacos_button = tk.Button(
        root,
        text="GACOS Correction",
        command=lambda: gacos_function(
        root, project_name, output_folder
        ),
        # state=tk.DISABLED
    )
    gacos_button.grid(row=4, column=2, padx=10, pady=5, sticky="ew")

    skip_button = tk.Button(
        root,
        text="Skip",
        command=lambda: next_function(
        root, project_name, output_folder
        )
    )
    skip_button.grid(row=4, column=3, padx=10, pady=5, sticky="ew")
    
    # Load the defaults
    coherence_thresholds_entry.insert(0, "0, 0.01")    


    root.mainloop()

if __name__ == "__main__":
    run_gui_uwp()