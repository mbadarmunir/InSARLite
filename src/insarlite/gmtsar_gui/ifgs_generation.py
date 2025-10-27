import os
import subprocess
from multiprocessing.pool import ThreadPool
from ..utils.utils import execute_command, process_logger


def gen_ifgs(paths, mst, filter_wavelength, rng, az, ncores, console_text=None, log_file_path=None):
    for key in ["pF1", "pF2", "pF3"]:
        dir_path = paths.get(key)
        subswath_map = {"pF1": "2.2.1", "pF2": "2.2.2", "pF3": "2.2.3"}
        process_num = subswath_map.get(key, "2.2.x")
        process_logger(process_num=process_num, log_file=paths.get("log_file_path"), message=f"Starting IFG generation for subswath {key} (process {process_num})...", mode="start")
        if dir_path and os.path.exists(dir_path):

            ind = os.path.join(dir_path, "intf.in")
            fmst = 'S1_' + mst + f'_ALL_F{key[-1]}'
            con = os.path.join(dir_path, "batch_tops.config")            
            os.chdir(dir_path)
            with open(con, 'r') as f:
                lines = f.readlines()
            with open(con, 'w') as f:
                for line in lines:
                    if 'master_image' in line:
                        line = 'master_image = ' + fmst + '\n'
                    if 'proc_stage' in line:
                        line = 'proc_stage = 1\n'
                    if 'topo_phase' in line:
                        line = 'topo_phase = 1\n'
                    if 'shift_topo' in line:
                        line = 'shift_topo = 0\n'
                    if 'filter_wavelength' in line:
                        line = f'filter_wavelength = {filter_wavelength}\n'
                    if 'range_dec' in line:
                        line = f'range_dec = {rng}\n'
                    if 'azimuth_dec' in line:
                        line = f'azimuth_dec = {az}\n'
                    if 'threshold_snaphu' in line:
                        line = 'threshold_snaphu = 0\n'
                    if 'threshold_geocode' in line:
                        line = 'threshold_geocode = 0\n'
                    f.write(line)
            print(f"Generating interferograms for {key} ...")
            # Checking if first IFG is generated
            intfdir = os.path.join(dir_path, 'intf_all')

            print('Cleaning up target directory before generating IFGs')
            if os.path.exists(intfdir):
                ld = os.listdir(intfdir)
            else:
                ld = []

            if os.path.exists(intfdir) and len(ld) > 0:
                if os.path.exists(os.path.join(intfdir, next(os.walk(intfdir))[1][0], 'phasefilt.grd')):
                    print('First IFG for {} already generated'.format(os.path.basename(dir_path)))
            else:
                # Generate IFGs
                print('Generating first interferogram for {} ...'.format(os.path.basename(dir_path)))
                subprocess.call('head -1 intf.in>one.in', shell=True)
                process_logger(process_num=f"{process_num}.1", log_file=paths.get("log_file_path"), message=f"Starting first IFG generation for subswath {key} (process {process_num}.1)...", mode="start")
                subprocess.call('intf_tops.csh one.in batch_tops.config', shell=True)
                process_logger(process_num=f"{process_num}.1", log_file=paths.get("log_file_path"), message=f"First IFG generation for subswath {key} (process {process_num}.1) generated successfully.", mode="end")

                fint = os.path.join(intfdir, next(os.walk(intfdir))[1][0], 'phasefilt.grd')
                
                if not fint and not os.path.exists(fint):
                    raise RuntimeError('Interferogram generation failed. Please check the log file for more details.')
                print("One interferogram for {} generated ".format(os.path.basename(dir_path)))

            if len(ld) > 1 and os.path.exists(os.path.join(intfdir, next(os.walk(intfdir))[1][-1], 'phasefilt.grd')):
                print('All IFGs for {} are already generated'.format(os.path.basename(dir_path)))

            else:
                print(f'Generating IFGs for {dir_path} ...')
                # Change proc_stage = 2 in batch_tops.config file
                with open(con, 'r') as f:
                    lines = f.readlines()
                with open(con, 'w') as f:
                    for line in lines:
                        if 'proc_stage' in line:
                            line = 'proc_stage = 2\n'
                        f.write(line)
                
                ain1 = []

                with open(ind, "r") as intf_file:
                    for intf in intf_file:
                        intf = intf.strip()
                        date1 = intf.split(":")[0][3:11]
                        date2 = intf.split(":")[1][3:11]
                        infile = f"intf_{date1}_{date2}.in"
                        with open(infile, "w") as in_file:
                            in_file.write(intf)
                            ain1.append(in_file.name)

                # Prepare commands for IFGs generation
                bash_commands1 = [
                    "intf_tops.csh {} batch_tops.config".format(i) for i in ain1
                ]
                process_logger(process_num=f"{process_num}.2", log_file=paths.get("log_file_path"), message=f"Starting all IFGs generation for subswath {key} (process {process_num}.2)...", mode="start")
                # Create a thread pool with a maximum of n threads
                with ThreadPool(processes=ncores) as pool:
                    # Execute bash commands in parallel
                    pool.map(execute_command, bash_commands1)

                process_logger(process_num=f"{process_num}.2", log_file=paths.get("log_file_path"), message=f"All IFGs generation for subswath {key} (process {process_num}.2) completed successfully.", mode="end")