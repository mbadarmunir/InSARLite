import os
import shutil
import subprocess
from utils.utils import update_console, run_command
from concurrent.futures import ThreadPoolExecutor

def update_prm(file, param, value):
    """Update a parameter in a PRM file."""
    with open(file, 'r') as f:
        lines = f.readlines()
    
    with open(file, 'w') as f:
        for line in lines:
            if line.startswith(param):
                f.write(f"{param} {value}\n")
            else:
                f.write(line)

# Functions to create merge list for merging interferograms
def get_merge_text(intf_path, suffix):
    lines = next(os.walk(intf_path))[1]
    merge_texts = []
    for line in lines:
        line = line.strip()
        path = f"{intf_path}/{line}/*{suffix}.PRM"
        pth, f1, f2 = get_first_two_files(path)
        if pth and f1 and f2:
            merge_texts.append(f"{pth}:{f1}:{f2}")
    return merge_texts

def create_merge(dir_path):
    f1intf = f"{dir_path}/F1/intf_all"
    f2intf = f"{dir_path}/F2/intf_all"
    f3intf = f"{dir_path}/F3/intf_all"

    txt1 = get_merge_text(f1intf, "F1") if os.path.exists(f1intf) else []
    txt2 = get_merge_text(f2intf, "F2") if os.path.exists(f2intf) else []
    txt3 = get_merge_text(f3intf, "F3") if os.path.exists(f3intf) else []

    max_len = max(len(txt1), len(txt2), len(txt3))

    for i in range(max_len):
        line = []
        if i < len(txt1):
            line.append(txt1[i])
        if i < len(txt2):
            line.append(txt2[i])
        if i < len(txt3):
            line.append(txt3[i])
        yield ",".join(line)

def get_first_two_files(path):
    try:
        files = subprocess.check_output(f"ls {path}", shell=True).decode('utf-8').split()
        pth = os.path.dirname(files[0]) + '/'
        f1 = os.path.basename(files[0])
        f2 = os.path.basename(files[1])
        return pth, f1, f2
    except IndexError:
        return None, None, None

def process_line(pmerge, line):
    line = line.strip()
    dir_name = line.split(',')[0].split(':')[0].split('/')[-2]
    os.mkdir(dir_name)
    os.chdir(dir_name)
    
    with open("tmp.filelist", 'w') as tmpf:
        for entry in line.split(','):
            tmpf.write(f"../{entry}\n")
    
    with open("tmp", 'w') as outf:
        with open("tmp.filelist", 'r') as tmpf:
            for l in tmpf:
                # mm, rest = l.strip().split(',', 1)
                pth, f1, f2 = l.split(':')
                mm = os.path.join(pth, f1)
                shutil.copy(mm, os.path.join(pmerge, dir_name, "supermaster.PRM"))
                rshift = run_command(f"grep rshift {pth}{f1} | tail -1 | awk '{{print $3}}'")
                update_prm(os.path.join(pmerge, dir_name, "supermaster.PRM"), "rshift", rshift)
                
                fs1 = run_command("grep first_sample supermaster.PRM | awk '{print $3}'")
                fs2 = run_command(f"grep first_sample {pth}{f1} | awk '{{print $3}}'")
                if int(fs2) > int(fs1):
                    update_prm(os.path.join(pth, "supermaster.PRM"), "first_sample", fs2)
                shutil.copy(os.path.join(pmerge, dir_name, "supermaster.PRM"), pth)
                outf.write(f"{pth}:supermaster.PRM:{f2}\n")
    
    for filename in ["trans.dat", "raln.grd", "ralt.grd", "landmask_ra.grd", "dem.grd", "batch_tops.config"]:
        if os.path.exists(f"../{filename}") and not os.path.exists(filename):
            os.symlink(f"../{filename}", filename)
    
    run_command(f"merge_unwrap_geocode_tops.csh tmp.filelist batch_tops.config")
    
    for filename in ["trans.dat", "landmask_ra.grd", "raln.grd", "ralt.grd", "dem.grd", "batch_tops.config"]:
        if not os.path.exists(f"../{filename}") and os.path.exists(filename):
            shutil.move(filename, f"../{filename}")
            os.symlink(f"../{filename}", filename)
            
            os.chdir(pmerge)

def merge_thread(pmerge, ncores, console_text, log_file_path):        
    if pmerge and os.path.exists(pmerge):        
        update_console(console_text, "Merging interferograms ...", log_file_path)
        os.chdir(pmerge)
        dir_path = '..'
        # print("Starting interferogram merging ...1")
        # print(next(os.walk('.')))
        if not next(os.walk('.'))[1]:                
            with open('merge_list', 'w') as out:
                for i, line in enumerate(create_merge(dir_path)):
                    out.write(line + '\n')
                    if i > 4:
                        break
            # subprocess.call('merge_batch.csh merge_list batch_tops.config', shell=True)
            subprocess.call('merge_batch_parallel.sh merge_list batch_tops.config', shell=True)
            # with open('merge_list', 'r') as f:
            #     lines = f.readlines()
            
            # print("Starting interferogram merging ...2")
            # lines = []
            # [lines.append(line) for line in create_merge(dir_path)]
            # # with ThreadPoolExecutor(max_workers=ncores) as executor:
            # #     executor.map(lambda line: process_line(pmerge, line), lines)
            # for line in lines:
            #     print(line)
            #     line = line.strip()
            #     dir_name = line.split(',')[0].split(':')[0].split('/')[-2]
            #     os.mkdir(dir_name)
            #     os.chdir(dir_name)
                
            #     with open("tmp.filelist", 'w') as tmpf:
            #         for entry in line.split(','):
            #             tmpf.write(f"../{entry}\n")
                
            #     with open("tmp", 'w') as outf:
            #         with open("tmp.filelist", 'r') as tmpf:
            #             for l in tmpf:
            #                 # mm, rest = l.strip().split(',', 1)
            #                 pth, f1, f2 = l.split(':')
            #                 mm = os.path.join(pth, f1)
            #                 shutil.copy(mm, os.path.join(pmerge, dir_name, "supermaster.PRM"))
            #                 rshift = run_command(f"grep rshift {pth}{f1} | tail -1 | awk '{{print $3}}'")
            #                 update_prm(os.path.join(pmerge, dir_name, "supermaster.PRM"), "rshift", rshift)
                            
            #                 fs1 = run_command("grep first_sample supermaster.PRM | awk '{print $3}'")
            #                 fs2 = run_command(f"grep first_sample {pth}{f1} | awk '{{print $3}}'")
            #                 if int(fs2) > int(fs1):
            #                     update_prm(os.path.join(pth, "supermaster.PRM"), "first_sample", fs2)
            #                 shutil.copy(os.path.join(pmerge, dir_name, "supermaster.PRM"), pth)
            #                 outf.write(f"{pth}:supermaster.PRM:{f2}\n")
                
            #     for filename in ["trans.dat", "raln.grd", "ralt.grd", "landmask_ra.grd", "dem.grd", "batch_tops.config"]:
            #         if os.path.exists(f"../{filename}") and not os.path.exists(filename):
            #             os.symlink(f"../{filename}", filename)
                
            #     run_command(f"merge_unwrap_geocode_tops.csh tmp.filelist batch_tops.config")
                
            #     for filename in ["trans.dat", "landmask_ra.grd", "raln.grd", "ralt.grd", "dem.grd", "batch_tops.config"]:
            #         if not os.path.exists(f"../{filename}") and os.path.exists(filename):
            #             shutil.move(filename, f"../{filename}")
            #             os.symlink(f"../{filename}", filename)
                        
            #             os.chdir(pmerge)
        update_console(console_text, "Interferograms merged ...", log_file_path)