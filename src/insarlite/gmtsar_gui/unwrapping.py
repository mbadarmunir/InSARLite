import os
from multiprocessing.pool import ThreadPool
from ..utils.utils import execute_command, update_console


def unwrap(paths, unwrapping_threshold, ncores, console_text, log_file_path):
    pmerge = paths.get("pmerge")
    if pmerge and os.path.exists(pmerge):
        IFGs = [d for d in next(os.walk(pmerge))[1] if not os.path.exists(os.path.join(pmerge, d, "unwrap.grd"))]
        intfdir = pmerge        
    else:
        for key in ["pF1", "pF2", "pF3"]:
            dir_path = paths.get(key)
            if dir_path and os.path.exists(dir_path):
                intfdir = os.path.join(dir_path, "intf_all")
                IFGs = [d for d in next(os.walk(intfdir))[1] if not os.path.exists(os.path.join(intfdir, d, "unwrap.grd"))]                
                break
    os.chdir(intfdir)
    print(IFGs)
    update_console(console_text, f"Number of IFGs to be unwrapped: {len(IFGs)}/{len(next(os.walk(intfdir))[1])}", log_file_path)
    if os.path.exists(os.path.join(IFGs[0], 'phasefilt.grd')) and not os.path.exists(os.path.join(IFGs[0], 'unwrap.grd')):
        print("Starting unwrapping...")
        unwrap_commands = [
            f"cd {i} && snaphu_interp.csh {unwrapping_threshold} 0 && cd .." for i in IFGs
        ]

        # Create a thread pool with n threads
        with ThreadPool(processes=ncores) as pool:
            # Execute bash commands in parallel
            pool.map(execute_command, unwrap_commands)
    else:
        update_console(console_text, "Error in unwrapping: Skipped process ...", log_file_path)
