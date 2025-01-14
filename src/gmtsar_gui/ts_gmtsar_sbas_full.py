from utils.utils import *

def is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def main(
    root, 
    in_data_dir,
    node,
    gacos_dir,
    dem_file,
    pin_file,
    project_name,
    output_dir,
    mst,
    parallel_baseline,
    perpendicular_baseline,
    rng,
    az,
    filter_wavelength,
    unwrapping_threshold,
    inc_angle,
    subswath_option,
    atm_corr_option,
    console_text,
    progress_bar,
):
    """Main function to run the Time Series Analysis using GMTSAR with SBAS."""
    print("Starting Time Series Analysis using GMTSAR with SBAS...")
    # exitGUI(root, os.path.exists(in_data_dir), "Data folder does not exist.")
    # exitGUI(root, os.path.exists(gacos_dir), "GACOS folder does not exist.")
    # exitGUI(root, os.path.exists(pin_file), "pin.II file does not exist.")  
    # exitGUI(root, os.path.exists(dem_file), "DEM file does not exist.")
    # exitGUI(root, filter_wavelength.isdigit(), "Filter wavelength must be an integer.")
    # exitGUI(root, is_float(unwrapping_threshold), "Unwrapping threshold must be a float.")
    # exitGUI(root, is_float(inc_angle), "Incidence angle must be a float.")

    print("in_data_dir: ", in_data_dir)
    print("node: ", node)
    print("gacos_dir: ", gacos_dir)
    print("dem_file: ", dem_file)
    print("pin_file: ", pin_file)
    print("project_name: ", project_name)
    print("output_dir: ", output_dir)
    print("mst: ", mst)
    # print("baselines: ", baselines)
    # print("multilooking: ", multilooking)
    print("filter_wavelength: ", filter_wavelength)
    print("unwrapping_threshold: ", unwrapping_threshold)
    print("inc_angle: ", inc_angle)
    print("subswath_option: ", subswath_option)
    print("atm_corr_option: ", atm_corr_option)


if __name__ == "__main__":
    main()
