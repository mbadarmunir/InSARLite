import os
import subprocess
from ..utils.utils import run_command

def get_grd_dimensions(grd_file):
    output = subprocess.check_output(f"gmt grdinfo -C {grd_file}", shell=True).decode().strip()
    dimensions = output.split()[1:5]  # Extracting the dimensions part of the output
    return dimensions

def get_highest_occurrence_files(files):
    if not files:
        return []

    dimensions_dict = {}
    for file in files:
        dimensions = tuple(get_grd_dimensions(file))
        if dimensions in dimensions_dict:
            dimensions_dict[dimensions].append(file)
        else:
            dimensions_dict[dimensions] = [file]

    unique_dimensions = list(dimensions_dict.keys())
    if len(unique_dimensions) == 1:
        print("All .grd files have the same dimensions.")
    else:
        print(f"There are {len(unique_dimensions)} different grd sizes. \n Skipping the invalid files")

    highest_occurrence = max(dimensions_dict.items(), key=lambda x: len(x[1]))
    return highest_occurrence[1]

def compute_mean_and_std(grid_files, scale, outmean, outstd):
    print("computing the mean of the grids ..")

    # Compute the mean
    for num, name in enumerate(grid_files, start=1):            
        if num == 1:
            run_command(f"gmt grdmath {name} = sum.grd")
        else:               
            run_command(f"gmt grdmath {name} sum.grd ADD = sumtmp.grd")
            os.rename('sumtmp.grd', 'sum.grd')
            
    num = len(grid_files)
    run_command(f"gmt grdmath sum.grd {num} DIV = {outmean}")

    # Compute the standard deviation
    print("compute the standard deviation ..")
    for num, name in enumerate(grid_files, start=1):
        if num == 1:
            run_command(f"gmt grdmath {name} {outmean} SUB SQR = sum2.grd")
        else:
            run_command(f"gmt grdmath {name} {outmean} SUB SQR sum2.grd ADD = sum2tmp.grd")
            os.rename('sum2tmp.grd', 'sum2.grd')

    num = len(grid_files)
    run_command(f"gmt grdmath sum2.grd {num} DIV SQRT = {outstd}")

    # Scale the results
    run_command(f"gmt grdmath {outmean} {scale} MUL = tmp.grd")
    os.rename('tmp.grd', outmean)
    run_command(f"gmt grdmath {outstd} {scale} MUL = tmp.grd")
    os.rename('tmp.grd', outstd)

    # Clean up
    for file in ['sum.grd', 'sum2.grd']:
        if os.path.exists(file):
            os.remove(file)

    # Plot the results
    for fname in [outmean, outstd]:
        if fname == outmean:
            label = "Mean of Image Stack"
        else:
            label = "Std. Dev. of Image Stack"

        name = os.path.splitext(os.path.basename(fname))[0]
        run_command(f"gmt grdgradient {name}.grd -Nt.9 -A0. -G{name}.grad.grd")
        tmp = subprocess.check_output(f"gmt grdinfo -C -L2 {name}.grd", shell=True).decode().strip().split()
        limitU = float(tmp[6])
        limitL = float(tmp[5])
        run_command(f"gmt makecpt -Cseis -I -Z -T{limitL}/{limitU}/0.1 -D > {name}.cpt")
        run_command(
            f"gmt grdimage {name}.grd -I{name}.grad.grd -C{name}.cpt -JX6.5i -Bxaf+lRange -Byaf+lAzimuth -BWSen "
            f"-X1.3i -Y3i -P -K > {name}.ps")
        run_command(f"gmt psscale -R{name}.grd -J -DJTC+w5/0.2+h+e -C{name}.cpt -Bxaf+l'{label}' -By -O >> {name}.ps")
        run_command(f"gmt psconvert -Tf -P -A -Z {name}.ps")
        
        for file in [f"{name}.cpt", f"{name}.grad.grd"]:
            if os.path.exists(file):
                os.remove(file)

def create_mean_grd(ifgsroot):
    os.chdir(ifgsroot)

    list_file = [os.path.join(root, file) for root, _, files in os.walk(ifgsroot) for file in files if
                 file.endswith('corr.grd')]
    scale = 1
    outmean = 'corr_stack.grd'
    outstd = 'std.grd'

    # Execute the check
    if not os.path.exists(os.path.join(ifgsroot, outmean)):
        print(f'Calculating mean coherence grd for {ifgsroot}')  
        grdfiles = get_highest_occurrence_files(list_file)
        compute_mean_and_std(grdfiles, scale, outmean, outstd)
    else:
        print('Mean grid already calculated')
