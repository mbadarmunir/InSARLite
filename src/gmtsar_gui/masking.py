import os
from utils.utils import run_command, create_symlink, rm_symlink

def create_mask(intfdir, masking_threshold, mask="mask_def.grd"):
    if masking_threshold != 0:
        run_command(f"gmt grdmath corr_stack.grd {masking_threshold} GE 0 NAN = {mask}")
        print(f"Mask created: {mask}\n Please check the mask and adjust the threshold if needed.")    
        [rm_symlink(os.path.join(d, mask)) for d in next(os.walk('.'))[1]]
        [create_symlink(os.path.join(intfdir, mask), os.path.join(d, mask)) for d in next(os.walk('.'))[1]]
        print(f"Mask linked to all IFGs directories.")