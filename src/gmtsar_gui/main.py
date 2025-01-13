import tkinter as tk
from gmtsar_gui import workflow
import gmtsar_gui.part as part


def open_next_window(root, selection):
    """Opens the appropriate GUI window based on user selection."""
    root.destroy()  # Close the current window
    if selection == 1:
        workflow.run_gui()
    elif selection == 2:
        part.run_gui()


def run_gui():
    root = tk.Tk()
    root.title("GMTSAR Workflow")

    # Description Paragraph
    description = tk.Label(
        root,
        text="If you want to run SBAS using the default parameters, the whole process can be automatically run "
        "by selecting the following Automated SBAS process. Sometimes a user may want to modify some parameters"
        "during different steps of SBAS workflow. For that step-by-step processing option below is available",
        justify="left",
        wraplength=400,
    )
    description.pack(pady=10)

    # Radio buttons for options
    gmt_selection = tk.IntVar(value=1)  # Default: Option-1 pre-selected

    gmt_option1_rb = tk.Radiobutton(
        root, text="Automated SBAS", variable=gmt_selection, value=1, state="normal"
    )
    gmt_option1_rb.pack(anchor="w")

    gmt_option2_rb = tk.Radiobutton(
        root,
        text="Step-be-step SBAS",
        variable=gmt_selection,
        value=2,
        state="disabled",
    )
    gmt_option2_rb.pack(anchor="w")

    # Next Button
    gmt_next_button = tk.Button(
        root, text="Next", command=lambda: open_next_window(root, gmt_selection.get())
    )
    gmt_next_button.pack(pady=20)

    # Enable other options dynamically (if required, call this function)
    # enable_other_options()

    root.mainloop()
