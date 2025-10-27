"""
Entry point for running InSARLite as a module.

This file allows InSARLite to be run using:
    python -m insarlite

Author: Muhammad Badar Munir
"""

def main():
    """Main entry point for InSARLite application."""
    import tkinter as tk
    from .main import InSARLiteApp
    
    root = tk.Tk()
    app = InSARLiteApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()