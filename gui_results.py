"""
Results panel for the car park simulator.
Builds the right-side results display and handles all update logic.
"""

import tkinter as tk
from tkinter import ttk

from models import (
    CarParkConfig, VehicleType, PricingTier, StaffConfig, ANPRConfig,
    OvernightConfig, MortgageConfig, IndoorOutdoorConfig, LongTermConfig,
)
from engine import run_simulation
from gui_widgets import CollapsibleSection, format_val


# ---------------------------------------------------------------------------
# Section definitions — (section_key, title, expanded, summary_key, items, collapsible)
# items are (result_key, label_text); result_key=None inserts a separator row.
# ---------------------------------------------------------------------------
RESULT_SECTIONS = [
    ("capacity", "Capacity & Throughput", True, "occupancy_display", [
        ("space_summary",               "Space Summary"),
        ("occupancy_display",           "Day Occupancy"),
        (None, None),
        ("commuter_vehicles_per_day",   "Commuter Vehicles/Day"),
        ("short_stay_vehicles_per_day", "Short-Stay Vehicles/Day"),
        ("vehicles_per_day",            "Total Vehicles/Day"),
        ("commuter_turnover_rate",      "Commuter Turnover"),
        ("short_stay_turnover_rate",    "Short-Stay Turnover"),
        ("avg_revenue_per_vehicle",     "Avg Revenue / Vehicle"),
    ], True),
    ("revenue", "Daily Revenue", True, "daily_total_revenue_gross", [
        ("daily_commuter_revenue_gross",  "Commuter Parking"),
        ("daily_short_stay_revenue_gross","Short-Stay Parking"),
        ("daily_parking_revenue_gross",   "Parking Total"),
        (None, None),
        ("daily_overnight_revenue_gross", "Overnight"),
        ("daily_long_term_revenue_gross", "Long-Term"),
        (None, None),
        ("daily_total_revenue_gross",     "Total Gross Revenue"),
    ], True),
    ("costs", "Daily Costs", False, "daily_total_cost", [
        ("daily_vat_liability",    "VAT (20%)"),
        ("daily_card_fees",        "Card Processing Fees"),
        (None, None),
        ("daily_staff_cost",       "Staff Wages"),
        ("daily_employer_ni",      "Employer NI"),
        ("daily_employer_pension", "Employer Pension"),
        ("daily_anpr_cost",        "ANPR Cost"),
        (None, None),
        ("daily_rent",             "Rent"),
        ("daily_insurance",        "Insurance"),
        ("daily_utilities",        "Utilities"),
        ("daily_maintenance",      "Maintenance"),
        ("daily_business_rates",   "Business Rates"),
        ("daily_cleaning",         "Cleaning"),
        ("daily_other",            "Other"),
        ("daily_mortgage",         "Mortgage"),
        (None, None),
        ("daily_total_cost",       "TOTAL COST"),
    ], True),
    ("daily_profit", "Daily Profit", True, "daily_profit", [], False),
    ("weekly", "Weekly", False, "weekly_profit", [
        ("weekly_revenue", "Net Revenue"),
        ("weekly_cost",    "Cost"),
        ("weekly_profit",  "PROFIT"),
    ], True),
    ("monthly", "Monthly", False, "monthly_profit", [
        ("monthly_revenue",          "Net Revenue"),
        ("monthly_cost",             "Cost"),
        (None, None),
        ("staff_monthly_total",      "Staff (inc NI/pension)"),
        ("anpr_monthly_total",       "ANPR Total"),
        ("mortgage_monthly_payment", "Mortgage Payment"),
        (None, None),
        ("monthly_profit",           "PROFIT"),
    ], True),
    ("yearly", "Yearly", True, "yearly_profit", [
        ("yearly_revenue", "Net Revenue"),
        ("yearly_cost",    "Cost"),
        ("yearly_profit",  "PROFIT"),
    ], True),
    ("mortgage_summary", "Mortgage Summary", False, "mortgage_monthly_payment", [
        ("mortgage_monthly_payment_hdr", "Monthly Payment"),
        ("mortgage_loan_amount",    "Loan Amount"),
        ("mortgage_deposit",        "Deposit"),
        ("mortgage_total_interest", "Total Interest"),
        ("mortgage_total_repaid",   "Total Repaid"),
    ], True),
    ("analysis", "Break-even Occupancy", True, "break_even_occupancy", [
        ("break_even_occupancy", "Break-even Occupancy"),
    ], False),
]

MONEY_KEYS = {
    "daily_parking_revenue_gross",
    "daily_commuter_revenue_gross", "daily_short_stay_revenue_gross",
    "daily_outdoor_revenue_gross", "daily_indoor_revenue_gross",
    "daily_overnight_revenue_gross", "daily_long_term_revenue_gross",
    "daily_total_revenue_gross", "daily_vat_liability", "daily_card_fees",
    "daily_total_revenue_net",
    "daily_staff_cost", "daily_employer_ni", "daily_employer_pension",
    "daily_anpr_cost", "daily_rent", "daily_insurance",
    "daily_utilities", "daily_maintenance", "daily_business_rates",
    "daily_cleaning", "daily_other", "daily_mortgage", "daily_total_cost",
    "daily_profit",
    "weekly_revenue", "weekly_cost", "weekly_profit",
    "monthly_revenue", "monthly_cost", "monthly_profit",
    "yearly_revenue", "yearly_cost", "yearly_profit",
    "avg_revenue_per_vehicle", "staff_monthly_total", "anpr_monthly_total",
    "mortgage_monthly_payment", "mortgage_monthly_payment_hdr",
    "mortgage_loan_amount", "mortgage_deposit",
    "mortgage_total_interest", "mortgage_total_repaid",
}
PROFIT_KEYS = {"daily_profit", "weekly_profit", "monthly_profit", "yearly_profit"}
COST_KEYS   = {"daily_vat_liability", "daily_card_fees", "daily_total_cost"}
CUSTOM_KEYS = {"occupancy_display", "space_summary"}
KEY_ALIASES = {"mortgage_monthly_payment_hdr": "mortgage_monthly_payment"}


def build_results(parent, on_toggle):
    """Build the results panel into `parent`.

    Returns:
        result_labels   — dict of key -> ttk.Label for value display
        result_sections — dict of key -> (CollapsibleSection, summary_key)
    """
    ttk.Label(parent, text="Simulation Results",
              style="Header.TLabel").grid(row=0, column=0, columnspan=2, pady=(0, 10))

    result_labels = {}
    result_sections = {}

    row = 1
    for sec_key, title, expanded, summary_key, items, collapsible in RESULT_SECTIONS:
        sec = CollapsibleSection(
            parent, title, expanded=expanded,
            on_toggle=on_toggle,
            collapsible=collapsible,
        )
        if row > 1:
            ttk.Separator(parent, orient="horizontal").grid(
                row=row, column=0, columnspan=2, sticky="ew", pady=(5, 2))
            row += 1
        sec.grid_header(row=row, column=0, columnspan=2, sticky="ew", pady=(2, 2))
        row += 1
        sec.grid_content(row=row, column=0, columnspan=2, sticky="ew")
        row += 1
        result_sections[sec_key] = (sec, summary_key)

        cf = sec.content_frame
        cf.columnconfigure(1, weight=1)
        cr = 0
        for key, label_text in items:
            if key is None:
                ttk.Separator(cf, orient="horizontal").grid(
                    row=cr, column=0, columnspan=2, sticky="ew", pady=(3, 3))
            else:
                ttk.Label(cf, text=label_text).grid(
                    row=cr, column=0, sticky="w", padx=(10, 5))
                lbl = ttk.Label(cf, text="", style="Neutral.TLabel", width=22, anchor="e")
                lbl.grid(row=cr, column=1, sticky="e")
                result_labels[key] = lbl
            cr += 1

    return result_labels, result_sections


def update_results(vars_dict, result_labels, result_sections,
                   occupancy_val_label, commuter_val_label,
                   rent_name_lbl, rent_slider, rent_val_lbl,
                   mix_info, mortgage_summary_labels):
    """Read all tkinter variables, run the simulation, and refresh all result labels."""

    total_spaces = int(vars_dict["total_spaces"].get())
    mortgage_on = vars_dict["mortgage_enabled"].get()

    cfg = CarParkConfig(
        total_spaces=total_spaces,
        operating_hours=11.0,
        opening_days_per_week=int(vars_dict["days_per_week"].get()),
        occupancy_rate=vars_dict["occupancy_rate"].get(),
        avg_stay_hours=vars_dict["avg_stay_hours"].get(),
        dead_time_minutes=vars_dict["dead_time_minutes"].get(),
        commuter_pct=vars_dict["commuter_pct"].get(),
        pct_small_car=vars_dict["pct_small_car"].get(),
        pct_large_car=vars_dict["pct_large_car"].get(),
        pct_small_van=vars_dict["pct_small_van"].get(),
        pct_large_van=vars_dict["pct_large_van"].get(),
        staff=StaffConfig(
            num_staff=int(vars_dict["num_staff"].get()),
            hourly_wage=vars_dict["hourly_wage"].get(),
            employer_ni_pct=vars_dict["employer_ni_pct"].get(),
            employer_pension_pct=vars_dict["employer_pension_pct"].get(),
        ),
        anpr=ANPRConfig(
            enabled=vars_dict["anpr_enabled"].get(),
            install_cost=vars_dict["anpr_install"].get(),
            monthly_maintenance=vars_dict["anpr_monthly"].get(),
            amortise_years=max(1, int(vars_dict["anpr_years"].get())),
        ),
        mortgage=MortgageConfig(
            enabled=mortgage_on,
            purchase_price=vars_dict["purchase_price"].get(),
            deposit_pct=vars_dict["deposit_pct"].get(),
            interest_rate=vars_dict["interest_rate"].get(),
            term_years=max(1, int(vars_dict["mortgage_term"].get())),
        ),
        overnight=OvernightConfig(
            num_overnight_cars=int(vars_dict["overnight_cars"].get()),
            overnight_flat_fee=vars_dict["overnight_fee"].get(),
        ),
        indoor_outdoor=IndoorOutdoorConfig(
            num_indoor_spaces=int(vars_dict["indoor_spaces"].get()),
            indoor_hourly_rate=vars_dict["indoor_hourly"].get(),
            indoor_daily_rate=vars_dict["indoor_daily"].get(),
        ),
        long_term=LongTermConfig(
            num_long_term_spaces=int(vars_dict["long_term_spaces"].get()),
            weekly_fee_per_vehicle=vars_dict["long_term_weekly_fee"].get(),
        ),
        monthly_rent=0.0 if mortgage_on else vars_dict["monthly_rent"].get(),
        monthly_insurance=vars_dict["monthly_insurance"].get(),
        monthly_utilities=vars_dict["monthly_utilities"].get(),
        monthly_maintenance=vars_dict["monthly_maintenance"].get(),
        monthly_business_rates=vars_dict["monthly_business_rates"].get(),
        monthly_cleaning=vars_dict["monthly_cleaning"].get(),
        monthly_other=vars_dict["monthly_other"].get(),
        card_processing_fee_pct=vars_dict["card_processing_fee_pct"].get(),
    )

    # Pricing from sliders
    for vtype in VehicleType:
        key_h = f"price_hourly_{vtype.name}"
        key_d = f"price_daily_{vtype.name}"
        cfg.pricing[vtype] = PricingTier(
            vehicle_type=vtype,
            hourly_rate=vars_dict[key_h].get(),
            daily_rate=vars_dict[key_d].get(),
        )

    # Vehicle mix info label
    raw_total = (cfg.pct_small_car + cfg.pct_large_car +
                 cfg.pct_small_van + cfg.pct_large_van)
    if raw_total > 0:
        mix_info.config(
            text=f"Raw sum: {raw_total:.0f}% → normalised to 100%",
            foreground="#89b4fa",
        )
    else:
        mix_info.config(text="⚠ All zero — defaulting to 100% small cars",
                        foreground="#f38ba8")

    # Mortgage summary in controls panel
    mort = cfg.mortgage
    mortgage_summary_labels["deposit_amount"].config(text=f"£{mort.deposit_amount:,.0f}")
    mortgage_summary_labels["loan_amount"].config(text=f"£{mort.loan_amount:,.0f}")
    mortgage_summary_labels["monthly_payment"].config(text=f"£{mort.monthly_payment:,.2f}")
    mortgage_summary_labels["total_interest"].config(text=f"£{mort.total_interest:,.0f}")
    mortgage_summary_labels["total_repaid"].config(text=f"£{mort.total_repaid:,.0f}")

    # Rent greyed-out state
    grey   = "#6c7086"
    normal = "#cdd6f4"
    if mortgage_on:
        rent_name_lbl.configure(foreground=grey)
        rent_val_lbl.configure(foreground=grey, text="£0 (n/a)")
        rent_slider.state(["disabled"])
    else:
        rent_name_lbl.configure(foreground=normal)
        rent_val_lbl.configure(
            foreground=normal,
            text=format_val(vars_dict["monthly_rent"].get(), "gbp"),
        )
        rent_slider.state(["!disabled"])

    # Run simulation
    result = run_simulation(cfg)

    # Dynamic occupancy label text
    total_ss_spaces = result.effective_daytime_spaces
    total_occupied  = int(round(result.occupied_spaces))
    comm_occupied   = int(round(result.commuter_vehicles_per_day))
    ss_occupied     = int(round(
        result.short_stay_vehicles_per_day / result.short_stay_turnover_rate
        if result.short_stay_turnover_rate > 0 else 0
    ))

    occupancy_val_label.config(
        text=f"{cfg.occupancy_rate:.0f}% ({total_occupied}/{total_ss_spaces})"
    )
    commuter_val_label.config(
        text=f"{cfg.commuter_pct:.0f}% ({comm_occupied}c / {ss_occupied}ss)"
    )

    # --- Format helpers ---
    fmt_money = lambda v: f"£{v:,.2f}"
    fmt_pct   = lambda v: f"{v:.1f}%"
    fmt_float = lambda v: f"{v:.1f}"

    custom_values = {
        "occupancy_display": (
            f"{cfg.occupancy_rate:.0f}% ({total_occupied}/{total_ss_spaces} spaces)"
        ),
        "space_summary": (
            f"{result.outdoor_spaces} out / {result.indoor_spaces} in / "
            f"{result.long_term_spaces} long / {result.overnight_spaces} night"
        ),
    }

    def format_value(key):
        if key in CUSTOM_KEYS:
            return custom_values[key], None
        attr = KEY_ALIASES.get(key, key)
        val = getattr(result, attr, 0)
        if key in MONEY_KEYS:
            return fmt_money(val), val
        if key == "break_even_occupancy":
            return fmt_pct(val), val
        if key in {"vehicles_per_day", "turnover_rate",
                   "commuter_vehicles_per_day", "short_stay_vehicles_per_day",
                   "commuter_turnover_rate", "short_stay_turnover_rate"}:
            return fmt_float(val), val
        return str(val), val

    # Update all result label rows
    for key, lbl in result_labels.items():
        text, val = format_value(key)
        if key in PROFIT_KEYS:
            style = "Result.TLabel" if (val or 0) >= 0 else "Loss.TLabel"
            lbl.configure(style=style, font=("Helvetica", 11, "bold"))
        elif key in COST_KEYS:
            lbl.configure(style="Loss.TLabel", font=("Helvetica", 10, ""))
        elif key == "daily_total_cost":
            lbl.configure(style="Loss.TLabel", font=("Helvetica", 10, "bold"))
        else:
            lbl.configure(style="Neutral.TLabel", font=("Helvetica", 10, ""))
        lbl.config(text=text)

    # Update section header summaries
    p = result.daily_profit
    section_summaries = {
        "capacity":         (custom_values["occupancy_display"], "Neutral.TLabel"),
        "revenue":          (fmt_money(result.daily_total_revenue_gross), "Neutral.TLabel"),
        "costs":            (fmt_money(result.daily_total_cost), "Loss.TLabel"),
        "daily_profit":     (fmt_money(p),
                             "Result.TLabel" if p >= 0 else "Loss.TLabel"),
        "weekly":           (fmt_money(result.weekly_profit),
                             "Result.TLabel" if result.weekly_profit >= 0 else "Loss.TLabel"),
        "monthly":          (fmt_money(result.monthly_profit),
                             "Result.TLabel" if result.monthly_profit >= 0 else "Loss.TLabel"),
        "yearly":           (fmt_money(result.yearly_profit),
                             "Result.TLabel" if result.yearly_profit >= 0 else "Loss.TLabel"),
        "mortgage_summary": (fmt_money(result.mortgage_monthly_payment), "Neutral.TLabel"),
        "analysis":         (fmt_pct(result.break_even_occupancy), "Neutral.TLabel"),
    }
    for sec_key, (sec, _summary_key) in result_sections.items():
        if sec_key in section_summaries:
            text, style = section_summaries[sec_key]
            sec.set_summary(text, style)
