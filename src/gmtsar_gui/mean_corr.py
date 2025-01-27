
import os
import subprocess
import sys
from utils.utils import run_command

def compute_mean_and_std(list_file, scale, outmean, outstd):
    print("computing the mean of the grids ..")

    grid_files = list_file

    if not all(os.path.isfile(name) for name in grid_files):
        missing_files = [name for name in grid_files if not os.path.isfile(name)]
        for name in missing_files:
            print(f" Error: file not found: {name} ")
            print("")
        sys.exit(1)

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
        # std = float(tmp[12])
        run_command(f"gmt makecpt -Cseis -I -Z -T{limitL}/{limitU}/0.1 -D > {name}.cpt")
        (float(subprocess.check_output(f"gmt grdinfo {name}.grd -C", shell=True).decode().strip().split()[2]) -
                  float(subprocess.check_output(f"gmt grdinfo {name}.grd -C", shell=True).decode().strip().split()[
                            1])) / 4
        (float(subprocess.check_output(f"gmt grdinfo {name}.grd -C", shell=True).decode().strip().split()[4]) -
                  float(subprocess.check_output(f"gmt grdinfo {name}.grd -C", shell=True).decode().strip().split()[
                            3])) / 4
        run_command(
            f"gmt grdimage {name}.grd -I{name}.grad.grd -C{name}.cpt -JX6.5i -Bxaf+lRange -Byaf+lAzimuth -BWSen "
            f"-X1.3i -Y3i -P -K > {name}.ps")
        run_command(f"gmt psscale -R{name}.grd -J -DJTC+w5/0.2+h+e -C{name}.cpt -Bxaf+l'{label}' -By -O >> {name}.ps")
        run_command(f"gmt psconvert -Tf -P -A -Z {name}.ps")
        print(f"Mean of stack map: {name}.pdf")
        for file in [f"{name}.cpt", f"{name}.grad.grd"]:
            if os.path.exists(file):
                os.remove(file)

def create_ref_point_ra(topodir, outmean):
    output = subprocess.check_output(f"gmt grdinfo -M {outmean}", shell=True).decode().strip().split()
    v_max = output.index('v_max:')
    x = output[v_max + 5]
    y = output[v_max + 8]
    
    with open(os.path.join(topodir, "ref_point.ra"), 'w') as f:
        f.write(f"{x} {y}\n")

def create_mean_grd(ifgsroot):
    os.chdir(ifgsroot)

    list_file = [os.path.join(root, file) for root, _, files in os.walk('.') for file in files if
                 file.endswith('corr.grd')]
    scale = 1
    outmean = 'corr_stack.grd'
    outstd = 'std.grd'

    # Execute the check
    if not os.path.exists(os.path.join(ifgsroot, outmean)):
        print(f'Calculating mean coherence grd for {ifgsroot}')
        compute_mean_and_std(list_file, scale, outmean, outstd)
        create_ref_point_ra(os.path.join(os.path.dirname(ifgsroot), 'topo'), outmean)
    else:
        print('Mean grid already calculated')