import os
import subprocess
from ..utils.utils import run_command

def sb_prep(intf, btable, intfdir, uwp):    
    if not os.path.exists('intf.tab') and not os.path.exists('scene.tab'):
        subprocess.call(
            f'prep_sbas.csh {intf} {btable} {intfdir} {uwp} corr.grd',
            shell=True)
        
def sb_inversion(sdir, paths, inc_angle, atm="", rms=" -rms", dem=" -dem", sbas="sbas", smooth=" -smooth 5.0"):
    os.chdir(sdir)
    pmerge = paths.get("pmerge")
   
    for key in ["pF1", "pF2", "pF3"]:
        dir_path = paths.get(key)
        if dir_path and os.path.exists(dir_path):
            intf = os.path.join(dir_path, 'intf.in')
            btable = os.path.join(dir_path, 'baseline_table.dat')
            if pmerge and os.path.exists(pmerge):
                intfdir = pmerge
            else:
                intfdir = os.path.join(dir_path, 'intf_all')
            break
    uwp = 'unwrap.grd'
    for subfolder in os.listdir(intfdir):
        if os.path.exists(os.path.join(intfdir, subfolder, 'unwrap_GACOS_corrected_detrended.grd')):
            uwp = 'unwrap_GACOS_corrected_detrended.grd'
            break    
    print(f"Creating required files for sbas using uwp: {uwp}, intf.in: {intf}, btable: {btable}, intfdir: {intfdir}")
    sb_prep(intf, btable, intfdir, uwp)

    if os.path.exists('intf.tab') and os.path.exists('scene.tab'):
        with open('intf.tab') as file:     
            intf_count = sum(1 for line in file)
        with open('intf.tab') as file:
            for line in file:
                grd = line.strip().split()[0]
                break
        with open('scene.tab') as file:
            scene_count = sum(1 for line in file)

        grdinfo = subprocess.check_output(f"gmt grdinfo {grd}", shell=True).decode().strip().split()
        x = grdinfo.index('x')
        y = grdinfo.index('y')
        xval = grdinfo[x + 2]
        yval = grdinfo[y + 2]
        xmin = float(grdinfo[grdinfo.index('x_min:') + 1])
        xmax = float(grdinfo[grdinfo.index('x_max:') + 1])
        c = 3 * 10 ** 8
        grdir = os.path.dirname(grd)
        prm = next((os.path.join(rootx, f) for rootx, _, files in os.walk(grdir) for f in files if f.endswith('.PRM')), os.path.join(grdir, 'supermaster.PRM'))
        with open(prm) as file:
            for line in file:
                if 'near_range' in line:
                    nr = float(line.split('=')[1].strip())
                if 'rng_samp_rate' in line:
                    rs = float(line.split('=')[1].strip())
                if 'radar_wavelength' in line:
                    rw = float(line.split('=')[1].strip())
        range = c / rs / 2 * (xmin + xmax) / 2 + nr
        print('Starting SBAS process')
        
        sb_command = f"{sbas} intf.tab scene.tab {intf_count} {scene_count} {xval} {yval} -range {range} -incidence {inc_angle} -wavelength {rw} {smooth} {atm} {rms} {dem}".rstrip()

        if sbas == 'sbas_parallel':
            sb_command = sb_command + ' -mmap'
        
        print(sb_command)
        run_command(sb_command)
            


        # if not os.path.exists(os.path.join(dsbas, 'vel_ll.kml')):
        #     velkml(dsbas, dmerge)
        #     update_console('KML generated', track_time=True)
        #     projgrd(dsbas)
        #     update_console('Projection in LatLon coordinates completed', track_time=True)
        # progress_bar['value'] = 100
        # root.update_idletasks()