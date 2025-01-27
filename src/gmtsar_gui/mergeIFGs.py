import os
import subprocess
from utils.utils import update_console

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


def merge_thread(pmerge, console_text, log_file_path):        
    if pmerge and os.path.exists(pmerge):        
        update_console(console_text, "Merging interferograms ...", log_file_path)
        os.chdir(pmerge)
        dir_path = '..'
        if not next(os.walk('.'))[1]:                
            with open('merge_list', 'w') as out:
                for i, line in enumerate(create_merge(dir_path)):
                    out.write(line + '\n')
                    if i > 4:
                        break
            # subprocess.call('merge_batch.csh merge_list batch_tops.config', shell=True)
            subprocess.call('merge_batch_parallel.sh merge_list batch_tops.config', shell=True)
            update_console(console_text, "Interferograms merged ...", log_file_path)