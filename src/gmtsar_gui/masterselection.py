import os
import numpy as np
import asf_search as asf
from copy import deepcopy
from datetime import datetime


def extract_date(folder_name):
    try:
        date_str0 = folder_name.split('_')[5]
        date_str = date_str0.split('T')[0]
        return datetime.strptime(date_str, "%Y%m%d")
    except (IndexError, ValueError):
        return None


# Calculate the temporal baseline for each date
def calculate_temporal_baseline(dates):
    baselines = []
    for i, (folder, date) in enumerate(dates):
        total_baseline = sum(abs((date - other_date).days) for _, other_date in dates if other_date != date)
        baselines.append((folder, date, total_baseline))
    return baselines


def calc_center(main_folder):
    # Get a list of subfolders and extract dates
    subfolders = [f for f in os.listdir(main_folder) if os.path.isdir(os.path.join(main_folder, f))]
    dates = [(folder, extract_date(folder)) for folder in subfolders]

    # Filter out subfolders where date extraction failed
    dates = [item for item in dates if item[1] is not None]

    # Get the baselines and find the one with the shortest temporal baseline
    baselines = calculate_temporal_baseline(dates)
    baselines.sort(key=lambda x: x[2])

    # The subfolder with the shortest temporal baseline
    center_folder = baselines[0][0]

    return center_folder


def select_mst(ddata):



    # Use the super master scene that is just in the middle of the temporal baseline
    granule = [calc_center(ddata).split('.')[0]]
    results = asf.granule_search(granule)

    reference = results[0]
    stack_org = reference.stack()

    # %% Make a deep copy of the stack
    stack = deepcopy(stack_org)

    frames_nan = []
    for i in stack:
        pp_bl = i.properties['perpendicularBaseline']
        tm_pl = i.properties['temporalBaseline']
        if pp_bl is None or tm_pl is None:
            frames_nan.append(i)

    # Remove the scenes with None/zeros perpendicular or/and temporal baselines
    for i in frames_nan:
        stack.remove(i)

    frame = reference.properties['frameNumber']
    rel_orb = reference.properties['pathNumber']
    frames_out = []
    for i in stack:
        fr = i.properties['frameNumber']
        rel = i.properties['pathNumber']
        if fr != frame or rel != rel_orb:
            frames_out.append(i)

    for i in frames_out:
        stack.remove(i)

    data_files = [x for x in os.listdir(ddata) if x.endswith('.SAFE')]
    data_analysis = []

    for s in stack:
        for f in data_files:
            f_name = (f.split("/")[-1]).replace('SAFE', 'zip')
            # print(f_name)
            if f_name == s.properties['fileName']:
                data_analysis.append(s.properties['fileName'])
    frames_out_lim = []
    for s in stack:
        if s.properties['fileName'] not in data_analysis:
            frames_out_lim.append(s)

    for i in frames_out_lim:
        stack.remove(i)

    print(f'Stack: {len(stack)}, Data: {len(data_files)}')

    inter_pairs = []
    for i in stack:
        for j in stack:
            if i != j:
                slave_1 = i.properties['fileID']
                t_bl_s1 = i.properties['temporalBaseline']
                p_bl_s1 = i.properties['perpendicularBaseline']
                geo_s1 = i.geometry

                slave_2 = j.properties['fileID']
                t_bl_s2 = j.properties['temporalBaseline']
                p_bl_s2 = j.properties['perpendicularBaseline']
                geo_s2 = j.geometry

                t_bl = np.abs(t_bl_s1 - t_bl_s2)
                p_bl = np.abs(p_bl_s1 - p_bl_s2)

                # Double check to prevent creating list between two identical frames
                if slave_1 != slave_2:
                    inter_pairs.append([slave_1, slave_2, t_bl, p_bl, t_bl_s1,
                                        p_bl_s1, t_bl_s2, p_bl_s2, geo_s1, geo_s2])
                else:
                    print("Super master frame: %s %s" % (slave_1, slave_2))

    # 1. Calculate the temporal baseline between all image pairs
    tbl_pbl_lst = []
    for i in stack:
        tbl_val = 0
        pbl_val = 0
        for j in stack:
            if i != j:
                slave_1 = i.properties['fileID']
                t_bl_s1 = i.properties['temporalBaseline']
                p_bl_s1 = i.properties['perpendicularBaseline']

                slave_2 = j.properties['fileID']
                t_bl_s2 = j.properties['temporalBaseline']
                p_bl_s2 = j.properties['perpendicularBaseline']

                t_bl = np.abs(t_bl_s1 - t_bl_s2)
                p_bl = np.abs(p_bl_s1 - p_bl_s2)

                # Double check to prevent creating list between two identical frames
                if slave_1 != slave_2:
                    tbl_val += t_bl
                    pbl_val += p_bl

        tbl_pbl_lst.append([tbl_val, pbl_val, i.properties['fileID']])

    # Get the minimum temporal + perpendicular baseline
    tbl_pbl_arr = np.array(tbl_pbl_lst)
    sums = tbl_pbl_arr[:, 0].astype('float') + tbl_pbl_arr[:, 1].astype('float')
    ranks = np.argsort(np.argsort(sums)) + 1  # Rank starts from 1
    tbl_pbl_arr_sort = np.column_stack((tbl_pbl_arr, ranks))
    tbl_pbl_arr_sort = tbl_pbl_arr_sort[tbl_pbl_arr_sort[:, -1].argsort()]  # Sort by rank column
    # min_idx = np.argmin(sums)
    # master = tbl_pbl_arr[min_idx, 2]    
    # mst = master[17:25]

    return tbl_pbl_arr_sort

def main(ddata):
    
    master = select_mst(ddata)
    print(f"Selected master: {master}")

if __name__ == "__main__":
    main()