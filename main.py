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
    app = CarParkSimulatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
