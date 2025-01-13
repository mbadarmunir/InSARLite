import tkinter as tk
from gmtsar_gui import main as gmtsar_main
import bridge.bridge as bridge
import licsbas.main as gui_licsbas


def open_next_window(selection):
    """Opens the appropriate GUI window based on user selection."""
    root.destroy()  # Close the current window
    if selection == 1:
        gmtsar_main.run_gui()
    elif selection == 2:
        bridge.run_gui()
    elif selection == 3:
        gui_licsbas.run_gui()


def enable_other_options():
    """Enable other options if required."""
    for rb in [option2_rb, option3_rb]:
        rb.config(state="normal")


def main():
    global root, option1_rb, option2_rb, option3_rb
    root = tk.Tk()
    root.title("InSAR Time Series Analysis")

    # Description Paragraph
    description = tk.Label(
        root,
        text="Welcome! Please select one of the following options for InSAR time series analysis using SBAS:\n"
        "1. GMTSAR Workflow: Requires Sentinel-1 images already extracted. The input data folder should contain '*SAFE' Folders.\n"
        "2. GMTSAR Workflow enriched with LiCSBAS: It processes Sentinel-1 using GMTSAR scripts but also uses different Quality checks available in LiCSBAS.\n"
        "3. LiCSBAS Workflow: An alternative of batch_LiCSBAS.sh script for automating the LiCSBAS workflow using a GUI.",
        justify="left",
        wraplength=400,
    )
    description.pack(pady=10)

    # Radio buttons for options
    user_selection = tk.IntVar(value=1)  # Default: Option-1 pre-selected

    option1_rb = tk.Radiobutton(
        root, text="GMTSAR Workflow", variable=user_selection, value=1, state="normal"
    )
    option1_rb.pack(anchor="w")

    option2_rb = tk.Radiobutton(
        root,
        text="GMTSAR Workflow enriched with LiCSBAS",
        variable=user_selection,
        value=2,
        state="disabled",
    )
    option2_rb.pack(anchor="w")

    option3_rb = tk.Radiobutton(
        root,
        text="LiCSBAS Workflow",
        variable=user_selection,
        value=3,
        state="disabled",
    )
    option3_rb.pack(anchor="w")

    # Next Button
    next_button = tk.Button(
        root, text="Next", command=lambda: open_next_window(user_selection.get())
    )
    next_button.pack(pady=20)

    # Enable other options dynamically (if required, call this function)
    # enable_other_options()

    root.mainloop()


if __name__ == "__main__":
    main()
