import subprocess
import os
from datetime import datetime, timedelta
from multiprocessing import Pool
from ..utils.utils import create_symlink, process_logger, process_logger_consolidated


def convert_date(code):
    year = int(str(code)[:4])
    day_of_year = int(str(code)[4:])
    date = datetime(year, 1, 1) + timedelta(day_of_year - 1)
    return date.strftime('%Y%m%d')

def get_value_from_rsc(file, key):
    with open(file, 'r') as f:
        for line in f:
            if line.startswith(key):
                return line.split()[1]
    return None

def operation(args):
    master_ztd, master_rsc, slave_ztd, slave_rsc, reference_point, incidence, uwp_phase = args

    print(f"Starting operation for master: {master_ztd}, slave: {slave_ztd}")
    try:
        incidence = float(incidence)
        wavelength = 0.0554658
        pi = 3.141592653589793238462

        # FIRST ZTD to grid
        x_first_d1 = get_value_from_rsc(master_rsc, 'X_FIRST')
        y_first_d1 = get_value_from_rsc(master_rsc, 'Y_FIRST')
        width_d1 = get_value_from_rsc(master_rsc, 'WIDTH')
        length_d1 = get_value_from_rsc(master_rsc, 'FILE_LENGTH')
        x_step_d1 = get_value_from_rsc(master_rsc, 'X_STEP')
        y_step_d1 = get_value_from_rsc(master_rsc, 'X_STEP')
        # date_ztd_d1 = os.path.basename(master_ztd)[:8]

        subprocess.run([
            'gmt', 'xyz2grd', master_ztd, '-Gdate1_ztd.grd',
            f'-RLT{x_first_d1}/{y_first_d1}/{width_d1}/{length_d1}',
            f'-I{x_step_d1}/{y_step_d1}', '-ZTLf', '-di0', '-r'
        ])

        # SECOND ZTD to grid
        x_first_d2 = get_value_from_rsc(slave_rsc, 'X_FIRST')
        y_first_d2 = get_value_from_rsc(slave_rsc, 'Y_FIRST')
        width_d2 = get_value_from_rsc(slave_rsc, 'WIDTH')
        length_d2 = get_value_from_rsc(slave_rsc, 'FILE_LENGTH')
        x_step_d2 = get_value_from_rsc(slave_rsc, 'X_STEP')
        y_step_d2 = get_value_from_rsc(slave_rsc, 'X_STEP')
        # date_ztd_d2 = os.path.basename(slave_ztd)[:8]

        subprocess.run([
            'gmt', 'xyz2grd', slave_ztd, '-Gdate2_ztd.grd',
            f'-RLT{x_first_d2}/{y_first_d2}/{width_d2}/{length_d2}',
            f'-I{x_step_d2}/{y_step_d2}', '-ZTLf', '-di0', '-r'
        ])

        # TIME DIFFERENCE
        subprocess.run(['gmt', 'grdmath', 'date2_ztd.grd', 'date1_ztd.grd', 'SUB', '=', 'zpddm.grd'])

        # PROJECT TO RADAR COORDINATES
        subprocess.run(['proj_ll2ra.csh', 'trans.dat', 'zpddm.grd', 'zpddm_ra.grd'])

        # RESAMPLE WITH UNWRAP GRID PARAMETERS
        unwrap_info = subprocess.run(['gmt', 'grdinfo', '-C', uwp_phase], capture_output=True, text=True).stdout.split()
        xmin, xmax, ymin, ymax, xinc, yinc = unwrap_info[1], unwrap_info[2], unwrap_info[3], unwrap_info[4], \
                                             unwrap_info[7], unwrap_info[8]

        subprocess.run([
            'gmt', 'grdsample', 'zpddm_ra.grd', '-Gresample_zpddm.grd',
            f'-R{xmin}/{xmax}/{ymin}/{ymax}', f'-I{xinc}/{yinc}', '-r'
        ])

        # REFERENCE POINT
        ref_value = subprocess.run(['gmt', 'grdtrack', reference_point, '-Gresample_zpddm.grd', '-Z'], capture_output=True,
                                   text=True).stdout.strip()

        subprocess.run(['gmt', 'grdmath', 'resample_zpddm.grd', ref_value, 'SUB', '=', 'szpddm.grd'])

        # FROM METER TO PHASE
        subprocess.run(
            ['gmt', 'grdmath', 'szpddm.grd', '4', 'MUL', str(pi), 'MUL', str(wavelength), 'DIV', '=', 'szpddm_phase.grd'])

        # PROJECTION FROM ZENITH VIEW TO LOS
        subprocess.run(['gmt', 'grdmath', 'szpddm_phase.grd', str(incidence), 'COSD', 'DIV', '=', 'szpddm_phase_LOS.grd'])

        # CORRECTION WITH GACOS DATA
        subprocess.run(['gmt', 'grdmath', uwp_phase, 'szpddm_phase_LOS.grd', 'SUB', '=', 'unwrap_GACOS_corrected.grd'])

        # DETRENDING
        subprocess.run(['gmt', 'grdtrend', 'unwrap_GACOS_corrected.grd', '-N3r', '-Dunwrap_GACOS_corrected_detrended.grd'])

        # Clean up
        os.remove('date1_ztd.grd')
        os.remove('date2_ztd.grd')
        os.remove('zpddm.grd')
        os.remove('zpddm_ra.grd')
        os.remove('resample_zpddm.grd')
        os.remove('szpddm_phase.grd')
        print(f"Completed operation for master: {master_ztd}, slave: {slave_ztd}")
    except Exception as e:
        print(f"Error in operation for {master_ztd} and {slave_ztd}: {e}")

def gacos_worker(args):
    GACOS_dir, topo_dir, incidence, intf_dir, dir, ifg_index, log_file = args
    process_num = f"5.3.{ifg_index}"  # 5.3.1, 5.3.2, etc.
    
    start_time = datetime.now()
    
    try:
        os.chdir(os.path.join(intf_dir, dir))
        fst_date = convert_date(str(int(dir.split('_')[0]) + 1))
        scd_date = convert_date(str(int(dir.split('_')[1]) + 1))

        reference_point_ra = os.path.join(topo_dir, "ref_point.ra")
        if all(os.path.isfile(os.path.join(GACOS_dir, f"{date}.ztd")) and
               os.path.isfile(os.path.join(GACOS_dir, f"{date}.ztd.rsc")) for date in [fst_date, scd_date]):
            first_ztd = os.path.join(GACOS_dir, f"{fst_date}.ztd")
            first_rsc = os.path.join(GACOS_dir, f"{fst_date}.ztd.rsc")
            second_ztd = os.path.join(GACOS_dir, f"{scd_date}.ztd")
            second_rsc = os.path.join(GACOS_dir, f"{scd_date}.ztd.rsc")

            # if os.path.basename(intf_dir) == 'merge':
            #     create_symlink(os.path.join(intf_dir, "trans.dat"), os.path.join('.',"trans.dat"))
            # else:
            create_symlink(os.path.join(topo_dir), os.path.join('.',"trans.dat"))
            if not os.path.exists('unwrap_GACOS_corrected_detrended.grd'):
                uwps = [os.path.join(root, f) for root, _, files in os.walk(intf_dir) for f in files if f == 'unwrap.grd']
                uwpn = [os.path.join(root, f) for root, _, files in os.walk(intf_dir) for f in files if f == 'unwrap_pin.grd']
                if len(uwps) == len(uwpn):
                    uwp_phase = "unwrap_pin.grd"
                else:
                    uwp_phase = "unwrap.grd"
                operation((first_ztd, first_rsc, second_ztd, second_rsc, reference_point_ra, incidence, uwp_phase))
            else:
                print('GACOS Correction already done for the current dir')
            os.remove("trans.dat")
            if log_file:
                process_logger_consolidated(
                    process_num=process_num, 
                    message=f"GACOS correction for interferogram {dir} completed successfully", 
                    log_file=log_file,
                    start_time=start_time
                )
        else:
            print("GACOS files do not exist / Wrong directory")
            if log_file:
                process_logger_consolidated(
                    process_num=process_num, 
                    message=f"GACOS correction for {dir} skipped - missing GACOS files", 
                    log_file=log_file,
                    start_time=start_time
                )
    except Exception as e:
        print(f"Error processing interferogram {dir}: {e}")
        if log_file:
            process_logger_consolidated(
                process_num=process_num, 
                message=f"GACOS correction for {dir} failed: {str(e)}", 
                log_file=log_file,
                start_time=start_time
            )

def gacos(GACOS_dir, topo_dir, incidence, intf_dir, num_cores, log_file=None):
    
    ifg_dirs = [dir for dir in os.listdir(intf_dir) if os.path.isdir(os.path.join(intf_dir, dir))]
    args_list = [
        (GACOS_dir, topo_dir, incidence, intf_dir, dir, i+1, log_file)
        for i, dir in enumerate(ifg_dirs)
    ]

    print(f"Starting GACOS correction with {num_cores} cores")
    try:
        with Pool(processes=num_cores) as pool:
            pool.map(gacos_worker, args_list)
    except Exception as e:
        print(f"Error in parallel processing: {e}")
    print("GACOS correction done")

# # Main function call
# dmerge = '/home/jovyan/SHAKEN-HDD/InSAR/Hakan/ilic_3rd_Asc_25dec/Asc3rd/asc/F3/intf_all/'
# dGACOS = '/home/jovyan/SHAKEN-HDD/InSAR/Hakan/GACOS_Asc_waoi2/'
# topodir = os.path.join(os.path.dirname(dmerge), 'topo')
# gacos(os.path.join(dmerge, 'list.txt'), dGACOS, topodir, 37, num_cores=96)
