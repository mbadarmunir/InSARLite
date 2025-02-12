import tkinter as tk
from tkinter import font, ttk, scrolledtext
from gmtsar_gui.out_turn import velkml, projgrd 
from utils.utils import update_console
import threading
import os
import pickle

# def run_function(
#     next_button,    
#     root,
#     project_name, 
#     output_folder,    
#     incidence,    
#     progress_bar,
#     console_text
#     ):                
#     paths_file = os.path.join(output_folder, project_name, "paths.pkl")    
#     log_file_path = os.path.join(output_folder, project_name, "sbas.log")

#     if os.path.exists(paths_file):
#         with open(paths_file, 'rb') as pf:
#             paths = pickle.load(pf)
            
#     def task_wrapper():        
#         psbas = paths.get('psbas')
#         if psbas and os.path.exists(psbas):
#             update_console(console_text, "Running SB Inversion", log_file_path)                          
#         sb_inversion(psbas, paths, incidence)
#         root.after(0, on_task_complete)

#     # Run the long-running task in a separate thread
#     def on_task_complete():
#         next_button.config(state=tk.NORMAL)        
#         progress_bar['value'] = 100
#         root.update_idletasks()
    
#     progress_bar['value'] = 0
#     root.update_idletasks()               

#     task_thread = threading.Thread(target=task_wrapper)
#     task_thread.start()

def create_velocity_kml(root, project_name, output_folder, progress_bar, console_text, log_file_path):    
    paths_file = os.path.join(output_folder, project_name, "paths.pkl")        

    if os.path.exists(paths_file):
        with open(paths_file, 'rb') as pf:
            paths = pickle.load(pf)
            
    def task_wrapper():        
        psbas = paths.get('psbas')
        pmerge = paths.get("pmerge")
        if pmerge and os.path.exists(pmerge):            
            intfdir = pmerge        
        else:
            for key in ["pF1", "pF2", "pF3"]:
                dir_path = paths.get(key)
                if dir_path and os.path.exists(dir_path):
                    intfdir = os.path.join(dir_path, "intf_all")                               
                    break
        if psbas and os.path.exists(psbas):
            update_console(console_text, "Creating Velocity KML... ", log_file_path)
            velkml(psbas, intfdir, paths)
        root.after(0, on_task_complete)

    # Run the long-running task in a separate thread
    def on_task_complete():               
        progress_bar['value'] = 100
        root.update_idletasks()
    
    progress_bar['value'] = 0
    root.update_idletasks()               

    task_thread = threading.Thread(target=task_wrapper)
    task_thread.start()

def generate_ts_files(root, project_name, output_folder, progress_bar, console_text, log_file_path):
    paths_file = os.path.join(output_folder, project_name, "paths.pkl")        

    if os.path.exists(paths_file):
        with open(paths_file, 'rb') as pf:
            paths = pickle.load(pf)
            
    def task_wrapper():        
        psbas = paths.get('psbas')        
        update_console(console_text, "Projecting time series from radar coordinates to lat-lon ... ", log_file_path)
        projgrd(psbas)
        root.after(0, on_task_complete)

    # Run the long-running task in a separate thread
    def on_task_complete():               
        progress_bar['value'] = 100
        root.update_idletasks()
    
    progress_bar['value'] = 0
    root.update_idletasks()               

    task_thread = threading.Thread(target=task_wrapper)
    task_thread.start()

def visualize(root, project_name, output_folder):
    paths_file = os.path.join(output_folder, project_name, "paths.pkl")        

    if os.path.exists(paths_file):
        with open(paths_file, 'rb') as pf:
            paths = pickle.load(pf)

    root.destroy()    

    # run_gui_sb(paths)

    
def run_gui_out(project_name, output_folder):
    root = tk.Tk()
    root.title("Run SB Inversion...")
    log_file_path = os.path.join(output_folder, project_name, "out_turn.log")

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

    progress_bar = ttk.Progressbar(root, mode="determinate")
    progress_bar.grid(row=3, column=0, columnspan=3, padx=10, pady=5, sticky="ew")

    console_label = tk.Label(root, text="Console Output:")
    console_label.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
    console_text = scrolledtext.ScrolledText(root, height=10, width=50, state=tk.DISABLED, wrap=tk.WORD)
    console_text.grid(row=5, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
    
    
    # Create the required input fields    
    # Create the buttons
    create_velocity_kml_button = tk.Button(
        root, 
        text="Create Velocity KML", 
        command=lambda: create_velocity_kml(
            root, 
            project_name, 
            output_folder, 
            progress_bar, 
            console_text, 
            log_file_path
        )
    )
    create_velocity_kml_button.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

    generate_ts_files_button = tk.Button(
        root, 
        text="Generate TS files", 
        command=lambda: generate_ts_files(
            root, 
            project_name, 
            output_folder, 
            progress_bar, 
            console_text, 
            log_file_path
        )
    )
    generate_ts_files_button.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

    visualize_button = tk.Button(root, text="Visualize", command=lambda: visualize(            
            root, project_name, output_folder
        )
    )
    visualize_button.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

    root.mainloop()

if __name__ == "__main__":
    run_gui_out()