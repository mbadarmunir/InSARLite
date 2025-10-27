import os
import shutil
import subprocess
from ..utils.utils import process_logger


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
    lines.sort()
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

    txt1.sort()
    txt2.sort()
    txt3.sort()

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

def merge_thread(pmerge, log_file_path, mst=None):        
    if pmerge and os.path.exists(pmerge):      

        print("Merging interferograms ...")
        # print(f"The current release will ignore defined {ncores} cores and utilize all available cores for merging")
        os.chdir(pmerge)

        dir_path = '..'

        if not next(os.walk('.'))[1]:
            with open('merge_list', 'w') as out:
                for line in create_merge(dir_path):
                    out.write(line + '\n')
            with open('merge_list', 'r') as f:
                lines = f.readlines()
            # Troubleshooting: Split the line into smaller parts
            # Find the line containing mst in the first file name
            filtered_lines = list(filter(lambda x: mst in x.split(',')[0].split(':')[1], lines))
            if not filtered_lines:
                filtered_lines = list(filter(lambda x: mst in x.split(',')[0].split(':')[2], lines))
            print(f"Filtered lines containing mst '{mst}': {filtered_lines}")
            # Get the index of that line
            if filtered_lines:
                mst_line = filtered_lines[0]
                mst_index = lines.index(mst_line)
                # Remove the line from its current position
                popped_line = lines.pop(mst_index)
                # Insert it at the beginning
                lines.insert(0, popped_line)
            # Original line (commented out):
            # lines.insert(0, lines.pop(lines.index(list(filter(lambda x: mst in x.split(',')[0].split(':')[1], lines))[0])))
            with open('merge_list', 'w') as f:
                for line in lines:
                    f.write(line)
            if os.path.exists('batch_tops.config'):
                os.remove('batch_tops.config')
                shutil.copy(f"{dir_path}/F2/batch_tops.config", 'batch_tops.config')
            process_logger(process_num="2.3", log_file=log_file_path, message=f"Starting merging process...", mode="start")
            subprocess.call('merge_batch.csh merge_list batch_tops.config', shell=True)
            process_logger(process_num="2.3", log_file=log_file_path, message=f"Merging process completed...", mode="end")

        print("Interferograms merged ...")