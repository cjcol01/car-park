"""
GUI orchestrator for the car park simulator.
Wires together the controls panel, results panel, and scroll canvas.
"""

import tkinter as tk
from tkinter import ttk

from gui_controls import build_controls
from gui_results import build_results, update_results


class CarParkSimulatorGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Car Park Simulator")
        self.root.configure(bg="#1e1e2e")

        self.vars = {}
        self.sections = []  # CollapsibleSections — used for scroll refresh

        self._build_ui()
        self._update_results()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame",      background="#1e1e2e")
        style.configure("TLabel",      background="#1e1e2e", foreground="#cdd6f4",
                        font=("Helvetica", 10))
        style.configure("Header.TLabel",    background="#1e1e2e", foreground="#f5c2e7",
                        font=("Helvetica", 13, "bold"))
        style.configure("SubHeader.TLabel", background="#1e1e2e", foreground="#89b4fa",
                        font=("Helvetica", 11, "bold"))
        style.configure("Result.TLabel",    background="#1e1e2e", foreground="#a6e3a1",
                        font=("Helvetica", 10))
        style.configure("Loss.TLabel",      background="#1e1e2e", foreground="#f38ba8",
                        font=("Helvetica", 10))
        style.configure("Neutral.TLabel",   background="#1e1e2e", foreground="#cdd6f4",
                        font=("Helvetica", 10))
        style.configure("TCheckbutton",     background="#1e1e2e", foreground="#cdd6f4",
                        font=("Helvetica", 10))
        style.configure("TScale",      background="#1e1e2e")
        style.configure("TSeparator",  background="#45475a")

        # Scrollable canvas
        self.canvas = tk.Canvas(self.root, bg="#1e1e2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.main_frame = ttk.Frame(self.canvas)

        self.main_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.main_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mousewheel — delta units differ by platform
        ws = self.root.tk.call("tk", "windowingsystem")
        if ws == "aqua":
            def _on_mousewheel(event):
                self.canvas.yview_scroll(-1 * event.delta, "units")
        else:
            def _on_mousewheel(event):
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))

        # Two-column layout
        left  = ttk.Frame(self.main_frame)
        left.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        right = ttk.Frame(self.main_frame)
        right.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # Build controls — populates self.vars and self.sections, returns widget refs
        ctrl_refs = build_controls(
            left, self.vars, self._update_results, self.sections
        )
        self._occupancy_val_label    = ctrl_refs["occupancy_val_label"]
        self._commuter_val_label     = ctrl_refs["commuter_val_label"]
        self._rent_name_lbl          = ctrl_refs["rent_name_lbl"]
        self._rent_slider            = ctrl_refs["rent_slider"]
        self._rent_val_lbl           = ctrl_refs["rent_val_lbl"]
        self._mix_info               = ctrl_refs["mix_info"]
        self._mortgage_summary_labels = ctrl_refs["mortgage_summary_labels"]

        # Build results panel
        self._result_labels, self._result_sections = build_results(
            right, self._refresh_scroll
        )

    def _refresh_scroll(self):
        self.main_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _update_results(self, *_args):
        update_results(
            vars_dict=self.vars,
            result_labels=self._result_labels,
            result_sections=self._result_sections,
            occupancy_val_label=self._occupancy_val_label,
            commuter_val_label=self._commuter_val_label,
            rent_name_lbl=self._rent_name_lbl,
            rent_slider=self._rent_slider,
            rent_val_lbl=self._rent_val_lbl,
            mix_info=self._mix_info,
            mortgage_summary_labels=self._mortgage_summary_labels,
        )
        self._refresh_scroll()
