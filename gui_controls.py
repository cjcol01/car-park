"""
Controls panel for the car park simulator.
Builds all left-side sliders, checkboxes, and sections.
"""

import tkinter as tk
from tkinter import ttk

from models import VehicleType
from gui_widgets import CollapsibleSection, make_slider, format_val


def build_controls(parent, vars_dict, on_change, sections_list):
    """Build the full controls panel into `parent`.

    Args:
        parent:       ttk.Frame to build into.
        vars_dict:    Shared dict of tk variables (populated in-place).
        on_change:    Callback to fire whenever any control changes.
        sections_list: List to append CollapsibleSection objects to
                       (for scroll-region refresh tracking).

    Returns a namespace of widget references needed externally:
        occupancy_val_label, commuter_val_label,
        rent_name_lbl, rent_slider, rent_val_lbl,
        mix_info, mortgage_summary_labels
    """

    def refresh_scroll():
        # Resolved by the orchestrator via on_toggle; sections_list is used there
        pass

    def make_section(title, row, expanded=True, sep=True):
        if sep:
            separator = ttk.Separator(parent, orient="horizontal")
            separator.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(8, 2))
            row += 1
        sec = CollapsibleSection(parent, title, expanded=expanded, on_toggle=on_change_scroll)
        sec.grid_header(row=row, column=0, columnspan=3, sticky="w", pady=(2, 2))
        row += 1
        sec.grid_content(row=row, column=0, columnspan=3, sticky="ew")
        row += 1
        sections_list.append(sec)
        return sec, sec.content_frame, row

    def ms(f, label, from_, to_, default, res=1, row=0, key=None, fmt=None, vw=10):
        return make_slider(f, label, from_, to_, default, res, row, key, fmt, vw,
                           vars_dict=vars_dict, on_change_callback=on_change)

    # on_toggle needs to call both refresh_scroll AND on_change for scroll update
    # We store a reference so make_section can use it
    on_change_scroll = on_change  # on_change already triggers _refresh_scroll via the orchestrator

    refs = {}
    row = 0

    ttk.Label(parent, text="Car Park Simulation Controls",
              style="Header.TLabel").grid(row=row, column=0, columnspan=3, pady=(0, 10))
    row += 1

    # --- Car Park Setup ---
    sec, f, row = make_section("Car Park Setup", row, expanded=True, sep=False)
    r = 0
    ms(f, "Total Spaces", 1, 100, 80, 1, r, "total_spaces", "int"); r += 1
    ms(f, "Indoor Spaces", 0, 100, 20, 1, r, "indoor_spaces", "int"); r += 1

    # --- Occupancy & Duration ---
    sec, f, row = make_section("Occupancy & Duration", row, expanded=True)
    r = 0
    _, _, _, refs["occupancy_val_label"] = ms(
        f, "Day Occupancy Rate", 0, 100, 50, 1, r, "occupancy_rate", "pct", 16); r += 1
    _, _, _, refs["commuter_val_label"] = ms(
        f, "Commuter (vs short stay) %", 0, 100, 35, 1, r, "commuter_pct", "pct", 16); r += 1
    ms(f, "Short-Stay Avg Stay (hrs)", 0.5, 11, 1.9, 0.1, r, "avg_stay_hours", "hrs"); r += 1
    ms(f, "Dead Time (mins)", 0, 30, 10, 1, r, "dead_time_minutes", "min"); r += 1
    ms(f, "Operating Days/Week", 1, 7, 7, 1, r, "days_per_week", "int"); r += 1
    ttk.Separator(f, orient="horizontal").grid(
        row=r, column=0, columnspan=3, sticky="ew", pady=4); r += 1
    ms(f, "Overnight Cars", 0, 30, 5, 1, r, "overnight_cars", "int"); r += 1
    ms(f, "Long-Term Spaces (Wates)", 0, 50, 20, 1, r, "long_term_spaces", "int"); r += 1

    # --- Vehicle Mix ---
    sec, f, row = make_section("Vehicle Mix (auto-normalised)", row, expanded=False)
    r = 0
    ms(f, "Small Cars %", 0, 100, 85, 1, r, "pct_small_car", "pct"); r += 1
    ms(f, "4x4 / Long Cars %", 0, 100, 5, 1, r, "pct_large_car", "pct"); r += 1
    ms(f, "Small/Med Vans %", 0, 100, 5, 1, r, "pct_small_van", "pct"); r += 1
    ms(f, "Large Vans %", 0, 100, 5, 5, r, "pct_large_van", "pct"); r += 1
    mix_info = ttk.Label(f, text="", foreground="#89b4fa")
    mix_info.grid(row=r, column=0, columnspan=3, sticky="w"); r += 1
    refs["mix_info"] = mix_info

    # --- Staffing ---
    sec, f, row = make_section("Staffing", row, expanded=True)
    r = 0
    ms(f, "Number of Staff", 0, 5, 1, 1, r, "num_staff", "int"); r += 1
    ms(f, "Hourly Wage (£)", 8, 25, 12, 0.5, r, "hourly_wage", "gbp2"); r += 1
    ms(f, "Employer NI %", 0, 20, 13.8, 0.1, r, "employer_ni_pct", "pct"); r += 1
    ms(f, "Employer Pension %", 0, 10, 3, 0.5, r, "employer_pension_pct", "pct"); r += 1

    # --- ANPR ---
    sec, f, row = make_section("ANPR System", row, expanded=False)
    r = 0
    vars_dict["anpr_enabled"] = tk.BooleanVar(value=False)
    ttk.Checkbutton(f, text="Enable ANPR",
                    variable=vars_dict["anpr_enabled"],
                    command=on_change).grid(row=r, column=0, columnspan=3, sticky="w"); r += 1
    ms(f, "Install Cost (£)", 5000, 50000, 15000, 1000, r, "anpr_install", "gbp"); r += 1
    ms(f, "Monthly Maintenance (£)", 50, 1000, 200, 10, r, "anpr_monthly", "gbp"); r += 1
    ms(f, "Amortise Over (years)", 1, 10, 5, 1, r, "anpr_years", "yrs"); r += 1

    # --- Mortgage ---
    sec, f, row = make_section("Mortgage / Purchase Finance", row, expanded=False)
    r = 0
    vars_dict["mortgage_enabled"] = tk.BooleanVar(value=True)
    ttk.Checkbutton(f, text="Enable Mortgage (disables Rent when on)",
                    variable=vars_dict["mortgage_enabled"],
                    command=on_change).grid(row=r, column=0, columnspan=3, sticky="w"); r += 1
    ms(f, "Purchase Price (£)", 50000, 4000000, 2500000, 10000, r, "purchase_price", "gbp"); r += 1
    ms(f, "Deposit %", 0, 100, 25, 1, r, "deposit_pct", "pct"); r += 1
    ms(f, "Interest Rate %", 0.5, 15, 7, 0.1, r, "interest_rate", "pct"); r += 1
    ms(f, "Term (years)", 1, 35, 25, 1, r, "mortgage_term", "yrs"); r += 1

    mortgage_summary_labels = {}
    for key, label_text in [
        ("deposit_amount", "Deposit Amount"),
        ("loan_amount", "Loan Amount"),
        ("monthly_payment", "Monthly Payment"),
        ("total_interest", "Total Interest Paid"),
        ("total_repaid", "Total Repaid"),
    ]:
        ttk.Label(f, text=f"  {label_text}:").grid(row=r, column=0, sticky="w", pady=1)
        lbl = ttk.Label(f, text="£0", foreground="#f9e2af", width=14, anchor="e")
        lbl.grid(row=r, column=1, columnspan=2, sticky="e")
        mortgage_summary_labels[key] = lbl
        r += 1
    refs["mortgage_summary_labels"] = mortgage_summary_labels

    # --- Fixed Costs ---
    sec, f, row = make_section("Monthly Fixed Costs", row, expanded=True)
    r = 0
    _, rent_name_lbl, rent_slider, rent_val_lbl = ms(
        f, "Rent (£/month)", 0, 10000, 2000, 100, r, "monthly_rent", "gbp"); r += 1
    refs["rent_name_lbl"] = rent_name_lbl
    refs["rent_slider"] = rent_slider
    refs["rent_val_lbl"] = rent_val_lbl
    ms(f, "Insurance (£/month)", 0, 2000, 300, 50, r, "monthly_insurance", "gbp"); r += 1
    ms(f, "Utilities (£/month)", 0, 1000, 150, 10, r, "monthly_utilities", "gbp"); r += 1
    ms(f, "Maintenance (£/month)", 0, 1000, 200, 10, r, "monthly_maintenance", "gbp"); r += 1
    ms(f, "Business Rates (£/month)", 0, 3000, 800, 50, r, "monthly_business_rates", "gbp"); r += 1
    ms(f, "Cleaning (£/month)", 0, 500, 100, 10, r, "monthly_cleaning", "gbp"); r += 1
    ms(f, "Card Processing Fee %", 0, 5, 2.5, 0.1, r, "card_processing_fee_pct", "pct"); r += 1
    ms(f, "Other (£/month)", 0, 5000, 0, 50, r, "monthly_other", "gbp"); r += 1

    # --- Pricing ---
    sec, f, row = make_section("Pricing (£/hour | £/day)", row, expanded=False)
    r = 0
    for vtype, defaults in [
        (VehicleType.SMALL_CAR, (5, 25)),
        (VehicleType.LARGE_CAR_4X4, (6, 30)),
        (VehicleType.SMALL_MEDIUM_VAN, (6, 30)),
        (VehicleType.LARGE_VAN, (10, 50)),
    ]:
        key_h = f"price_hourly_{vtype.name}"
        key_d = f"price_daily_{vtype.name}"
        ttk.Label(f, text=f"{vtype.value}:").grid(row=r, column=0, sticky="w", pady=1); r += 1
        ms(f, "  Hourly", 1, 20, defaults[0], 0.5, r, key_h, "gbp2"); r += 1
        ms(f, "  Daily", 5, 100, defaults[1], 1, r, key_d, "gbp"); r += 1
    ttk.Separator(f, orient="horizontal").grid(
        row=r, column=0, columnspan=3, sticky="ew", pady=4); r += 1
    ttk.Label(f, text="Indoor Rates:").grid(row=r, column=0, sticky="w", pady=1); r += 1
    ms(f, "  Indoor Hourly (£)", 1, 30, 6, 0.5, r, "indoor_hourly", "gbp2"); r += 1
    ms(f, "  Indoor Daily (£)", 5, 100, 30, 1, r, "indoor_daily", "gbp"); r += 1
    ttk.Separator(f, orient="horizontal").grid(
        row=r, column=0, columnspan=3, sticky="ew", pady=4); r += 1
    ttk.Label(f, text="Other Rates:").grid(row=r, column=0, sticky="w", pady=1); r += 1
    ms(f, "  Overnight Fee (£)", 5, 50, 15, 1, r, "overnight_fee", "gbp"); r += 1
    ms(f, "  Long-Term Weekly Fee (£)", 10, 200, 105, 5, r, "long_term_weekly_fee", "gbp"); r += 1

    return refs
