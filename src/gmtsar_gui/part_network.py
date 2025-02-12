from utils.utils import update_console
import os
from gmtsar_gui.structuring import orchestrate_structure_and_copy
from gmtsar_gui.masterselection import select_mst
from gmtsar_gui.orbitsdownload import process_files
from gmtsar_gui.baselines_gen import preprocess
from gmtsar_gui.pair_generation import gen_pairs
import threading
import pickle

def p_start_network(
    root,
    in_data_dir, node, dem_file, pin_file, project_name, output_dir, mst, baselines, subswath_option,
    progress_bar,
    console_text
    ):
    """Function to run the Time Series Analysis using GMTSAR with SBAS."""
    log_file_path = os.path.join(output_dir, "Network_creation.log")    

    # Access the batch_tops.config file so that it can be copied to the required directories
    # Read the GMTSAR environment variable and construct the path
    gmtsar_path = os.getenv('GMTSAR')
    if gmtsar_path is None:
        raise EnvironmentError("GMTSAR environment variable is not set.")
    
    btconfig = os.path.join(gmtsar_path, 'gmtsar', 'csh', 'batch_tops.config')
    update_console(console_text, f"Using batch_tops.config at: {btconfig}", log_file_path)
    parallel_baseline, perpendicular_baseline = map(int, baselines.split(","))    
    paths = None
    structure = None
    paths_file = os.path.join(output_dir, project_name, "paths.pkl")    

    def structuring():
        nonlocal paths, structure
        paths, structure = orchestrate_structure_and_copy(
            output_dir, project_name, node, subswath_option, dem_file, pin_file, in_data_dir, btconfig, console_text, log_file_path
        )           

    structuring_thread = threading.Thread(target=structuring)
    structuring_thread.start()
    structuring_thread.join()  # Ensure the thread completes and values are assigned

    with open(paths_file, 'wb') as pf:
        pickle.dump(paths, pf)

    progress_bar['value'] = 5
    root.update_idletasks()

    pdata = paths.get("pdata")

    # Select the master scene
    if not mst:
        def select_mst_thread():
            nonlocal mst
            mst = select_mst(pdata)

        thread_mst = threading.Thread(target=select_mst_thread)
        thread_mst.start()

        def update_progress_mst():
            while thread_mst.is_alive() and progress_bar['value'] < 20:
                progress_bar['value'] += 0.1
                root.update_idletasks()
            progress_bar['value'] = 20
            root.update_idletasks()

        progress_thread_mst = threading.Thread(target=update_progress_mst)
        progress_thread_mst.start()
        thread_mst.join()
        progress_thread_mst.join()
    mst_file = os.path.join(output_dir, project_name, "mst.pkl")
    with open(mst_file, 'wb') as mf:
        pickle.dump(mst, mf)
                

    update_console(console_text, f"master: {mst}", log_file_path)

    # Download orbits and create data.in file
    update_console(console_text, "Downloading orbits and creating data.in file...", log_file_path)  
    
    pref = paths.get("pref")
    def process_files_thread():        
        process_files(in_data_dir, os.path.dirname(pref))        

    thread_process = threading.Thread(target=process_files_thread)
    thread_process.start()

    def update_progress_process():
        while thread_process.is_alive() and progress_bar['value'] < 50:
            progress_bar['value'] += 0.1
            root.update_idletasks()
        progress_bar['value'] = 50
        root.update_idletasks()

    progress_thread_process = threading.Thread(target=update_progress_process)
    progress_thread_process.start()
    thread_process.join()
    progress_thread_process.join()
    update_console(console_text, "Downloaded orbits and created data.in file...", log_file_path)

    update_console(console_text, "Creating baselines table(s) and plot(s) ...", log_file_path)  

    def preprocess_thread():        
        preprocess(paths, console_text, log_file_path)

    thread_preprocess = threading.Thread(target=preprocess_thread)
    thread_preprocess.start()

    def update_progress_preprocess():
        while thread_preprocess.is_alive() and progress_bar['value'] < 80:
            progress_bar['value'] += 0.1
            root.update_idletasks()
        progress_bar['value'] = 80
        root.update_idletasks()

    progress_thread_preprocess = threading.Thread(target=update_progress_preprocess)
    progress_thread_preprocess.start()
    thread_preprocess.join()
    progress_thread_preprocess.join()

    update_console(console_text, "Baselines and data.in file(s) generated ...", log_file_path)
    
    update_console(console_text, "Generating pairs of interferograms ...", log_file_path)
    def gen_pairs_thread():
        gen_pairs(paths, parallel_baseline, perpendicular_baseline, console_text, log_file_path)

    thread_gen_pairs = threading.Thread(target=gen_pairs_thread)
    thread_gen_pairs.start()

    def update_progress_gen_pairs():
        while thread_gen_pairs.is_alive() and progress_bar['value'] < 100:
            progress_bar['value'] += 0.1
            root.update_idletasks()
        progress_bar['value'] = 100
        root.update_idletasks()

    progress_thread_gen_pairs = threading.Thread(target=update_progress_gen_pairs)
    progress_thread_gen_pairs.start()
    thread_gen_pairs.join()
    progress_thread_gen_pairs.join()
    update_console(console_text, "Generated pairs of interferograms ...", log_file_path)

    for key in ["pF1", "pF2", "pF3"]:
        dir_path = paths.get(key)                  
        if dir_path and os.path.exists(dir_path):     
            ind = os.path.join(dir_path, "intf.in")
            update_console(
                console_text, 
                "If you want to drop some pairs/IFGs, you may want to do it now by going to \n"
                f"{ind}\n"
                "and removing rows. \n"
                "This will skip aligning images that don't make a valid pair", 
                log_file_path
            )
    

# def main(
#     root,
#     in_data_dir, node, dem_file, pin_file, project_name, output_dir, mst, baselines, subswath_option,
#     progress_bar,
#     console_text,
# ):
#     """Main function to run the Time Series Analysis using GMTSAR with SBAS."""
#     analysis_thread = threading.Thread(target=p_start_network, args=(
#         root,
#         in_data_dir, node, dem_file, pin_file, project_name, output_dir, mst, baselines, subswath_option,
#         progress_bar,
#         console_text,
#         ))
#     analysis_thread.start()

# if __name__ == "__main__":
#     main()