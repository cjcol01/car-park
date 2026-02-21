"""
Reusable GUI widgets for the car park simulator.
Contains CollapsibleSection and shared formatting/slider helpers.
"""

import tkinter as tk
from tkinter import ttk


class CollapsibleSection:
    """A section with a clickable header that toggles visibility of its content.
    Optionally shows a summary value on the right of the header (always visible)."""

    def __init__(self, parent, title, style="SubHeader.TLabel", expanded=True,
                 on_toggle=None, collapsible=True):
        self.parent = parent
        self.expanded = expanded
        self.on_toggle = on_toggle
        self.collapsible = collapsible

        # Header frame (clickable) — spans full width
        self.header_frame = ttk.Frame(parent)
        self.header_frame.columnconfigure(1, weight=1)

        if collapsible:
            self.arrow_var = tk.StringVar(value="▼" if expanded else "▶")
            self.arrow_label = ttk.Label(
                self.header_frame, textvariable=self.arrow_var,
                font=("Helvetica", 10), cursor="hand2",
            )
            self.arrow_label.grid(row=0, column=0, sticky="w", padx=(0, 5))
        else:
            # Non-collapsible: use a spacer instead of arrow to keep alignment
            spacer = ttk.Label(self.header_frame, text="  ")
            spacer.grid(row=0, column=0, sticky="w", padx=(0, 5))

        self.title_label = ttk.Label(
            self.header_frame, text=title, style=style,
            cursor="hand2" if collapsible else "",
        )
        self.title_label.grid(row=0, column=1, sticky="w")

        # Summary label — shown on right, always visible (updated externally)
        self.summary_label = ttk.Label(
            self.header_frame, text="", style="Result.TLabel",
            font=("Helvetica", 10, "bold"), width=16, anchor="e",
        )
        self.summary_label.grid(row=0, column=2, sticky="e", padx=(5, 0))

        # Content frame
        self.content_frame = ttk.Frame(parent)

        # Bind click to toggle only if collapsible
        if collapsible:
            for widget in (self.header_frame, self.arrow_label, self.title_label):
                widget.bind("<Button-1>", self._toggle)

        if not expanded:
            self.content_frame.grid_remove()

    def set_summary(self, text, style="Result.TLabel"):
        self.summary_label.configure(text=text, style=style)

    def grid_header(self, **kwargs):
        self.header_frame.grid(**kwargs)

    def grid_content(self, **kwargs):
        self._content_grid_kwargs = kwargs
        self.content_frame.grid(**kwargs)
        if not self.expanded:
            self.content_frame.grid_remove()

    def _toggle(self, event=None):
        if not self.collapsible:
            return
        self.expanded = not self.expanded
        self.arrow_var.set("▼" if self.expanded else "▶")
        if self.expanded:
            self.content_frame.grid(**self._content_grid_kwargs)
        else:
            self.content_frame.grid_remove()
        if self.on_toggle:
            self.on_toggle()


def format_val(val, fmt):
    if fmt == "pct":
        return f"{val:.0f}%"
    elif fmt == "gbp":
        return f"£{val:,.0f}"
    elif fmt == "gbp2":
        return f"£{val:,.2f}"
    elif fmt == "hrs":
        return f"{val:.1f}h"
    elif fmt == "int":
        return f"{int(val)}"
    elif fmt == "yrs":
        return f"{int(val)} yrs"
    elif fmt == "min":
        return f"{val:.0f} min"
    else:
        return f"{val:.1f}"


def make_slider(parent, label, from_, to_, default, resolution=1,
                row=0, var_key=None, fmt=None, val_width=10, vars_dict=None,
                on_change_callback=None):
    """Create a labeled slider that updates on change.
    Returns (var, name_label, slider, val_label)."""
    name_lbl = ttk.Label(parent, text=label)
    name_lbl.grid(row=row, column=0, sticky="w", pady=2)

    var = tk.DoubleVar(value=default)
    if var_key and vars_dict is not None:
        vars_dict[var_key] = var

    val_label = ttk.Label(parent, text=format_val(default, fmt), width=val_width)
    val_label.grid(row=row, column=2, sticky="e", padx=(5, 0))

    def on_change(val):
        val_label.config(text=format_val(float(val), fmt))
        if on_change_callback:
            on_change_callback()

    slider = ttk.Scale(parent, from_=from_, to=to_, variable=var,
                       orient="horizontal", length=250, command=on_change)
    slider.grid(row=row, column=1, sticky="ew", padx=5)
    return var, name_lbl, slider, val_label
