"""
Car Park Simulator - Main entry point.

A simulation tool for evaluating the financial viability of a 64-space car park.
Pricing based on actual posted rates. Supports ANPR system modelling.

Usage:
    python main.py
"""

import tkinter as tk
from gui import CarParkSimulatorGUI


def main():
    root = tk.Tk()
    root.geometry("1100x800")
    root.minsize(900, 600)
    # Start maximised (platform-aware)
    ws = root.tk.call("tk", "windowingsystem")
    if ws == "win32":
        root.state("zoomed")
    elif ws == "x11":
        root.attributes("-zoomed", True)
    else:  # aqua (macOS) — no -zoomed; use screen size
        root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0")
    app = CarParkSimulatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
