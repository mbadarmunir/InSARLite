def main(
    in_data_dir,
    gacos_dir,
    dem_file,
    pin_file,
    project_name,
    output_dir,
    mst,
    baselines,
    multilooking,
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
    print("in_data_dir: ", in_data_dir)
    print("gacos_dir: ", gacos_dir)
    print("dem_file: ", dem_file)
    print("pin_file: ", pin_file)
    print("project_name: ", project_name)
    print("output_dir: ", output_dir)
    print("mst: ", mst)
    print("baselines: ", baselines)
    print("multilooking: ", multilooking)
    print("filter_wavelength: ", filter_wavelength)
    print("unwrapping_threshold: ", unwrapping_threshold)
    print("inc_angle: ", inc_angle)
    print("subswath_option: ", subswath_option)
    print("atm_corr_option: ", atm_corr_option)


if __name__ == "__main__":
    main(
        in_data_dir,
        gacos_dir,
        dem_file,
        pin_file,
        project_name,
        output_dir,
        mst,
        baselines,
        multilooking,
        filter_wavelength,
        unwrapping_threshold,
        inc_angle,
        subswath_option,
        atm_corr_option,
        console_text,
        progress_bar,
    )
