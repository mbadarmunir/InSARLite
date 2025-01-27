from utils.utils import update_console
import os
import shutil
from gmtsar_gui.structuring import orchestrate_structure_and_copy
from gmtsar_gui.masterselection import select_mst
from gmtsar_gui.orbitsdownload import process_files
from gmtsar_gui.mean_corr import create_mean_grd
from gmtsar_gui.gacos_atm_corr import gacos
from gmtsar_gui.sb_inversion import sb_inversion
from gmtsar_gui.ifgs_generation import gen_ifgs
from gmtsar_gui.mergeIFGs import merge_thread
from gmtsar_gui.baselines_gen import preprocess
from gmtsar_gui.alignment import align_sec_imgs
from gmtsar_gui.pair_generation import gen_pairs
from gmtsar_gui.unwrapping import unwrap
import threading



# Core function to run the Time Series Analysis using GMTSAR with SBAS
def run_analysis(
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
    unwrapping_threshold,
    inc_angle,
    subswath_option,
    atm_corr_option,
    console_text,
    progress_bar,
):
    """Function to run the Time Series Analysis using GMTSAR with SBAS."""
    log_file_path = os.path.join(output_dir, "log.txt")
    update_console(console_text, f"Starting Time Series Analysis using GMTSAR with SBAS after {atm_corr_option}...", log_file_path)

    # Access the batch_tops.config file so that it can be copied to the required directories
    # Read the GMTSAR environment variable and construct the path
    gmtsar_path = os.getenv('GMTSAR')
    if gmtsar_path is None:
        raise EnvironmentError("GMTSAR environment variable is not set.")
    
    btconfig = os.path.join(gmtsar_path, 'gmtsar', 'csh', 'batch_tops.config')
    update_console(console_text, f"Using batch_tops.config at: {btconfig}", log_file_path)
    
    paths = None
    structure = None
    def structuring():
        nonlocal paths, structure
        paths, structure = orchestrate_structure_and_copy(
            output_dir, project_name, node, subswath_option, dem_file, pin_file, in_data_dir, btconfig, console_text, log_file_path
        )
    structuring_thread = threading.Thread(target=structuring)
    structuring_thread.start()
    structuring_thread.join()  # Ensure the thread completes and values are assigned

    progress_bar['value'] = 1
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
            while thread_mst.is_alive() and progress_bar['value'] < 2:
                progress_bar['value'] += 0.1
                root.update_idletasks()
            progress_bar['value'] = 2
            root.update_idletasks()

        progress_thread_mst = threading.Thread(target=update_progress_mst)
        progress_thread_mst.start()
        thread_mst.join()
        progress_thread_mst.join()

    update_console(console_text, f"master: {mst}", log_file_path)

    # Download orbits and create data.in file
    update_console(console_text, "Downloading orbits and creating data.in file...", log_file_path)  
    
    pref = paths.get("pref")
    def process_files_thread():        
        process_files(in_data_dir, os.path.dirname(pref))        

    thread_process = threading.Thread(target=process_files_thread)
    thread_process.start()

    def update_progress_process():
        while thread_process.is_alive() and progress_bar['value'] < 5:
            progress_bar['value'] += 0.1
            root.update_idletasks()
        progress_bar['value'] = 5
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
        while thread_preprocess.is_alive() and progress_bar['value'] < 8:
            progress_bar['value'] += 0.1
            root.update_idletasks()
        progress_bar['value'] = 8
        root.update_idletasks()

    progress_thread_preprocess = threading.Thread(target=update_progress_preprocess)
    progress_thread_preprocess.start()
    thread_preprocess.join()
    progress_thread_preprocess.join()

    update_console(console_text, "Baselines and data.in file(s) generated ...", log_file_path)

    update_console(console_text, "Starting alignment of secondary images w.r.t. master ...", log_file_path)
    def align_thread():        
        align_sec_imgs(paths, mst, console_text, log_file_path)   

    
    thread_align = threading.Thread(target=align_thread)
    thread_align.start()    

    def update_progress_align():
        while thread_align.is_alive() and progress_bar['value'] < 25:
            progress_bar['value'] += 0.1
            root.update_idletasks()
        progress_bar['value'] = 20
        root.update_idletasks()
    
    progress_thread_align = threading.Thread(target=update_progress_align)
    progress_thread_align.start()
    thread_align.join()
    progress_thread_align.join()

    update_console(console_text, "Alignment completed...", log_file_path)


    update_console(console_text, "Generating pairs of interferograms ...", log_file_path)
    def gen_pairs_thread():
        gen_pairs(paths, parallel_baseline, perpendicular_baseline, console_text, log_file_path)

    thread_gen_pairs = threading.Thread(target=gen_pairs_thread)
    thread_gen_pairs.start()

    def update_progress_gen_pairs():
        while thread_gen_pairs.is_alive() and progress_bar['value'] < 30:
            progress_bar['value'] += 0.1
            root.update_idletasks()
        progress_bar['value'] = 30
        root.update_idletasks()

    progress_thread_gen_pairs = threading.Thread(target=update_progress_gen_pairs)
    progress_thread_gen_pairs.start()
    thread_gen_pairs.join()
    progress_thread_gen_pairs.join()
        

    # Perform preparations for generating interferograms and create IFGs
    update_console(console_text, "Generating interferograms ...", log_file_path)
    def ifg_thread():
        gen_ifgs(paths, mst, filter_wavelength, rng, az)
    
    thread_ifg = threading.Thread(target=ifg_thread)
    thread_ifg.start()

    def update_progress_ifg():
        while thread_ifg.is_alive() and progress_bar['value'] < 35:
            progress_bar['value'] += 0.1
            root.update_idletasks()
        progress_bar['value'] = 35
        root.update_idletasks()

    progress_thread_ifg = threading.Thread(target=update_progress_ifg)
    progress_thread_ifg.start()
    thread_ifg.join()
    progress_thread_ifg.join()

    update_console(console_text, "Interferograms generated ...", log_file_path)       

    # Start merging interferograms
    pmerge = paths.get("pmerge")
    if pmerge and os.path.exists(pmerge):
        shutil.copy(btconfig, pmerge)
        shutil.copy(dem_file, pmerge) 

    def merge_ifgs_thread():
        merge_thread(pmerge, console_text, log_file_path)

    thread_merge = threading.Thread(target=merge_ifgs_thread)
    thread_merge.start()

    def update_progress_merge():
        while thread_merge.is_alive() and progress_bar['value'] < 45:
            progress_bar['value'] += 0.1
            root.update_idletasks()
        progress_bar['value'] = 65
        root.update_idletasks()

    progress_thread_merge = threading.Thread(target=update_progress_merge)
    progress_thread_merge.start()
    thread_merge.join()
    progress_thread_merge.join()    
    
    
    def unwrap_thread():
        unwrap(paths, unwrapping_threshold, console_text, log_file_path)

    thread_unwrap = threading.Thread(target=unwrap_thread)
    thread_unwrap.start()

    def update_progress_unwrap():
        while thread_unwrap.is_alive() and progress_bar['value'] < 75:
            progress_bar['value'] += 0.1
            root.update_idletasks()
        progress_bar['value'] = 75
        root.update_idletasks()

    progress_thread_unwrap = threading.Thread(target=update_progress_unwrap)
    progress_thread_unwrap.start()
    thread_unwrap.join()
    progress_thread_unwrap.join()

    update_console(console_text, "Interferograms unwrapped ...", log_file_path)

    # Create mean coherence grid
    update_console(console_text, "Creating mean coherence grid ...", log_file_path)
    def mean_coherence_thread():
        create_mean_grd(intfdir)

    thread_mean_coherence = threading.Thread(target=mean_coherence_thread)
    thread_mean_coherence.start()

    def update_progress_mean_coherence():
        while thread_mean_coherence.is_alive() and progress_bar['value'] < 85:
            progress_bar['value'] += 0.1
            root.update_idletasks()
        progress_bar['value'] = 85
        root.update_idletasks()

    progress_thread_mean_coherence = threading.Thread(target=update_progress_mean_coherence)
    progress_thread_mean_coherence.start()
    thread_mean_coherence.join()
    progress_thread_mean_coherence.join()

    update_console(console_text, "Mean coherence grid created ...", log_file_path)
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

    # Perform GACOS correction if selected
    def gacos_thread():
        if gacos_dir and os.path.exists(gacos_dir):
            update_console(console_text, "Performing GACOS correction ...", log_file_path)
            tdir = os.path.join(os.path.dirname(intfdir), 'topo')                        
            gacos(IFGs, gacos_dir, tdir, inc_angle, intfdir, num_cores=96)            
            update_console(console_text, "GACOS correction completed ...", log_file_path)

    thread_gacos = threading.Thread(target=gacos_thread)
    thread_gacos.start()

    def update_progress_gacos():
        while thread_gacos.is_alive() and progress_bar['value'] < 95:
            progress_bar['value'] += 0.1
            root.update_idletasks()
        progress_bar['value'] = 95
        root.update_idletasks()

    progress_thread_gacos = threading.Thread(target=update_progress_gacos)
    progress_thread_gacos.start()
    thread_gacos.join()
    progress_thread_gacos.join()

    # Perform SB inversion
    update_console(console_text, "Performing SB inversion ...", log_file_path)
    def sb_inversion_thread():
        sb_inversion(paths.get('psbas'), paths, inc_angle)

    thread_sb_inversion = threading.Thread(target=sb_inversion_thread)
    thread_sb_inversion.start()

    def update_progress_sb_inversion():
        while thread_sb_inversion.is_alive() and progress_bar['value'] < 100:
            progress_bar['value'] += 0.1
            root.update_idletasks()
        progress_bar['value'] = 100
        root.update_idletasks()

    progress_thread_sb_inversion = threading.Thread(target=update_progress_sb_inversion)
    progress_thread_sb_inversion.start()
    thread_sb_inversion.join()
    progress_thread_sb_inversion.join()

    update_console(console_text, "SB inversion completed ...", log_file_path)    

def main(
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
    unwrapping_threshold,
    inc_angle,
    subswath_option,
    atm_corr_option,
    console_text,
    progress_bar,
):
    """Main function to run the Time Series Analysis using GMTSAR with SBAS."""
    analysis_thread = threading.Thread(target=run_analysis, args=(
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
        unwrapping_threshold,
        inc_angle,
        subswath_option,
        atm_corr_option,
        console_text,
        progress_bar,
    ))
    analysis_thread.start()

if __name__ == "__main__":
    main()