"""
GUI for the car park simulation using tkinter.
All controls are sliders/checkboxes with live-updating results.
Sections are collapsible to simplify the UI.
"""

import tkinter as tk
from tkinter import ttk

from models import (
    CarParkConfig, VehicleType, StaffConfig, ANPRConfig,
    OvernightConfig, MortgageConfig,
)
from engine import run_simulation


class CollapsibleSection:
    """A section with a clickable header that toggles visibility of its content."""

    def __init__(self, parent, title, style="SubHeader.TLabel", expanded=True,
                 on_toggle=None):
        self.parent = parent
        self.expanded = expanded
        self.on_toggle = on_toggle

        # Header frame (clickable)
        self.header_frame = ttk.Frame(parent)
        self.arrow_var = tk.StringVar(value="▼" if expanded else "▶")
        self.arrow_label = ttk.Label(
            self.header_frame, textvariable=self.arrow_var,
            font=("Helvetica", 10), cursor="hand2",
        )
        self.arrow_label.pack(side="left", padx=(0, 5))
        self.title_label = ttk.Label(
            self.header_frame, text=title, style=style, cursor="hand2",
        )
        self.title_label.pack(side="left")

        # Content frame
        self.content_frame = ttk.Frame(parent)

        # Bind click to toggle
        for widget in (self.header_frame, self.arrow_label, self.title_label):
            widget.bind("<Button-1>", self._toggle)

        if not expanded:
            self.content_frame.grid_remove()

    def grid_header(self, **kwargs):
        self.header_frame.grid(**kwargs)

    def grid_content(self, **kwargs):
        self._content_grid_kwargs = kwargs
        self.content_frame.grid(**kwargs)
        if not self.expanded:
            self.content_frame.grid_remove()

    def _toggle(self, event=None):
        self.expanded = not self.expanded
        self.arrow_var.set("▼" if self.expanded else "▶")
        if self.expanded:
            self.content_frame.grid(**self._content_grid_kwargs)
        else:
            self.content_frame.grid_remove()
        if self.on_toggle:
            self.on_toggle()


class CarParkSimulatorGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Car Park Simulator - 64 Space Car Park")
        self.root.configure(bg="#1e1e2e")

        self.config = CarParkConfig()
        self.vars = {}
        self.sections = []  # track CollapsibleSections for scroll update

        self._build_ui()
        self._update_results()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#1e1e2e")
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4",
                         font=("Helvetica", 10))
        style.configure("Header.TLabel", background="#1e1e2e", foreground="#f5c2e7",
                         font=("Helvetica", 13, "bold"))
        style.configure("SubHeader.TLabel", background="#1e1e2e", foreground="#89b4fa",
                         font=("Helvetica", 11, "bold"))
        style.configure("Result.TLabel", background="#1e1e2e", foreground="#a6e3a1",
                         font=("Helvetica", 10))
        style.configure("Loss.TLabel", background="#1e1e2e", foreground="#f38ba8",
                         font=("Helvetica", 10))
        style.configure("Neutral.TLabel", background="#1e1e2e", foreground="#cdd6f4",
                         font=("Helvetica", 10))
        style.configure("TCheckbutton", background="#1e1e2e", foreground="#cdd6f4",
                         font=("Helvetica", 10))
        style.configure("TScale", background="#1e1e2e")
        style.configure("TSeparator", background="#45475a")

        # Scrollable canvas
        self.canvas = tk.Canvas(self.root, bg="#1e1e2e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.main_frame = ttk.Frame(self.canvas)

        self.main_frame.bind("<Configure>",
                             lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.main_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mousewheel
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))

        # Two-column layout
        left = ttk.Frame(self.main_frame)
        left.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        right = ttk.Frame(self.main_frame)
        right.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self._build_controls(left)
        self._build_results(right)

    def _refresh_scroll(self):
        """Update scroll region after a section collapses/expands."""
        self.main_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _make_section(self, parent, title, row, expanded=True):
        """Create a collapsible section and return (section, content_frame, next_row)."""
        sep = ttk.Separator(parent, orient="horizontal")
        sep.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(8, 2))
        row += 1

        section = CollapsibleSection(
            parent, title, expanded=expanded, on_toggle=self._refresh_scroll,
        )
        section.grid_header(row=row, column=0, columnspan=3, sticky="w", pady=(2, 2))
        row += 1
        section.grid_content(row=row, column=0, columnspan=3, sticky="ew")
        row += 1

        self.sections.append(section)
        return section, section.content_frame, row

    def _make_slider(self, parent, label, from_, to_, default, resolution=1,
                     row=0, var_key=None, fmt=None):
        """Create a labeled slider that updates on change."""
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)

        var = tk.DoubleVar(value=default)
        if var_key:
            self.vars[var_key] = var

        val_label = ttk.Label(parent, text=self._format_val(default, fmt), width=10)
        val_label.grid(row=row, column=2, sticky="e", padx=(5, 0))

        def on_change(val):
            val_label.config(text=self._format_val(float(val), fmt))
            self._update_results()

        slider = ttk.Scale(parent, from_=from_, to=to_, variable=var,
                           orient="horizontal", length=250, command=on_change)
        slider.grid(row=row, column=1, sticky="ew", padx=5)
        return var

    @staticmethod
    def _format_val(val, fmt):
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

    # ---------------------------------------------------------- Controls
    def _build_controls(self, parent):
        row = 0

        ttk.Label(parent, text="Car Park Simulation Controls",
                  style="Header.TLabel").grid(row=row, column=0, columnspan=3, pady=(0, 10))
        row += 1

        # --- Occupancy & Duration ---
        sec, f, row = self._make_section(parent, "Occupancy & Duration", row, expanded=True)
        r = 0
        self._make_slider(f, "Occupancy Rate", 0, 100, 70, 1, r, "occupancy_rate", "pct"); r += 1
        self._make_slider(f, "Avg Stay (hours)", 0.5, 11, 2.5, 0.5, r, "avg_stay_hours", "hrs"); r += 1
        self._make_slider(f, "Dead Time (mins)", 0, 30, 10, 1, r, "dead_time_minutes", "min"); r += 1
        self._make_slider(f, "Operating Days/Week", 1, 7, 6, 1, r, "days_per_week", "int"); r += 1

        # --- Vehicle Mix ---
        sec, f, row = self._make_section(parent, "Vehicle Mix (auto-normalised)", row, expanded=False)
        r = 0
        self._make_slider(f, "Small Cars %", 0, 100, 60, 1, r, "pct_small_car", "pct"); r += 1
        self._make_slider(f, "4x4 / Long Cars %", 0, 100, 20, 1, r, "pct_large_car", "pct"); r += 1
        self._make_slider(f, "Small/Med Vans %", 0, 100, 15, 1, r, "pct_small_van", "pct"); r += 1
        self._make_slider(f, "Large Vans %", 0, 100, 5, 1, r, "pct_large_van", "pct"); r += 1
        self.mix_info = ttk.Label(f, text="", foreground="#89b4fa")
        self.mix_info.grid(row=r, column=0, columnspan=3, sticky="w"); r += 1

        # --- Staff ---
        sec, f, row = self._make_section(parent, "Staffing", row, expanded=True)
        r = 0
        self._make_slider(f, "Number of Staff", 0, 5, 1, 1, r, "num_staff", "int"); r += 1
        self._make_slider(f, "Hourly Wage (£)", 8, 25, 12, 0.5, r, "hourly_wage", "gbp2"); r += 1
        self._make_slider(f, "Employer NI %", 0, 20, 13.8, 0.1, r, "employer_ni_pct", "pct"); r += 1
        self._make_slider(f, "Employer Pension %", 0, 10, 3, 0.5, r, "employer_pension_pct", "pct"); r += 1

        # --- ANPR ---
        sec, f, row = self._make_section(parent, "ANPR System", row, expanded=False)
        r = 0
        self.vars["anpr_enabled"] = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Enable ANPR (replaces all staff)",
                        variable=self.vars["anpr_enabled"],
                        command=self._update_results).grid(row=r, column=0, columnspan=3, sticky="w"); r += 1
        self._make_slider(f, "Install Cost (£)", 5000, 50000, 15000, 1000, r, "anpr_install", "gbp"); r += 1
        self._make_slider(f, "Monthly Maintenance (£)", 50, 1000, 200, 10, r, "anpr_monthly", "gbp"); r += 1
        self._make_slider(f, "Amortise Over (years)", 1, 10, 5, 1, r, "anpr_years", "yrs"); r += 1

        # --- Mortgage ---
        sec, f, row = self._make_section(parent, "Mortgage / Purchase Finance", row, expanded=False)
        r = 0
        self.vars["mortgage_enabled"] = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Enable Mortgage (adds to monthly costs)",
                        variable=self.vars["mortgage_enabled"],
                        command=self._update_results).grid(row=r, column=0, columnspan=3, sticky="w"); r += 1
        self._make_slider(f, "Purchase Price (£)", 50000, 4000000, 250000, 10000, r, "purchase_price", "gbp"); r += 1
        self._make_slider(f, "Deposit %", 0, 100, 25, 1, r, "deposit_pct", "pct"); r += 1
        self._make_slider(f, "Interest Rate %", 0.5, 15, 5.5, 0.1, r, "interest_rate", "pct"); r += 1
        self._make_slider(f, "Term (years)", 1, 35, 25, 1, r, "mortgage_term", "yrs"); r += 1

        # Mortgage summary labels (updated dynamically)
        self.mortgage_summary_labels = {}
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
            self.mortgage_summary_labels[key] = lbl
            r += 1

        # --- Overnight ---
        sec, f, row = self._make_section(parent, "Overnight Parking", row, expanded=False)
        r = 0
        self._make_slider(f, "Overnight Cars", 0, 30, 0, 1, r, "overnight_cars", "int"); r += 1
        self._make_slider(f, "Overnight Fee (£)", 5, 50, 15, 1, r, "overnight_fee", "gbp"); r += 1

        # --- Fixed Costs ---
        sec, f, row = self._make_section(parent, "Monthly Fixed Costs", row, expanded=True)
        r = 0
        self._make_slider(f, "Rent (£/month)", 0, 10000, 2000, 100, r, "monthly_rent", "gbp"); r += 1
        self._make_slider(f, "Insurance (£/month)", 0, 2000, 300, 50, r, "monthly_insurance", "gbp"); r += 1
        self._make_slider(f, "Utilities (£/month)", 0, 1000, 150, 10, r, "monthly_utilities", "gbp"); r += 1
        self._make_slider(f, "Maintenance (£/month)", 0, 1000, 200, 10, r, "monthly_maintenance", "gbp"); r += 1
        self._make_slider(f, "Business Rates (£/month)", 0, 3000, 800, 50, r, "monthly_business_rates", "gbp"); r += 1
        self._make_slider(f, "Cleaning (£/month)", 0, 500, 100, 10, r, "monthly_cleaning", "gbp"); r += 1
        self._make_slider(f, "Card Processing Fee %", 0, 5, 2.5, 0.1, r, "card_processing_fee_pct", "pct"); r += 1

        # --- Pricing ---
        sec, f, row = self._make_section(parent, "Pricing (£/hour | £/day)", row, expanded=False)
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
            self._make_slider(f, "  Hourly", 1, 20, defaults[0], 0.5, r, key_h, "gbp2"); r += 1
            self._make_slider(f, "  Daily", 5, 100, defaults[1], 1, r, key_d, "gbp"); r += 1

    # ---------------------------------------------------------- Results
    def _build_results(self, parent):
        ttk.Label(parent, text="Simulation Results",
                  style="Header.TLabel").grid(row=0, column=0, columnspan=2, pady=(0, 10))

        self.result_labels = {}
        self.result_sections = []  # track for scroll refresh

        sections = [
            ("Capacity & Throughput", True, [
                ("effective_daytime_spaces", "Daytime Spaces Available"),
                ("vehicles_per_day", "Vehicles per Day"),
                ("turnover_rate", "Turnover per Space"),
                ("avg_revenue_per_vehicle", "Avg Revenue / Vehicle"),
            ]),
            ("Daily Revenue", True, [
                ("daily_parking_revenue_gross", "Parking (gross inc. VAT)"),
                ("daily_overnight_revenue_gross", "Overnight (gross)"),
                ("daily_total_revenue_gross", "Total Gross Revenue"),
                ("daily_vat_liability", "VAT Liability (20%)"),
                ("daily_card_fees", "Card Processing Fees"),
                ("daily_total_revenue_net", "NET Revenue (yours to keep)"),
            ]),
            ("Daily Costs", True, [
                ("daily_staff_cost", "Staff Wages"),
                ("daily_employer_ni", "Employer NI"),
                ("daily_employer_pension", "Employer Pension"),
                ("daily_anpr_cost", "ANPR Cost"),
                ("daily_rent", "Rent"),
                ("daily_insurance", "Insurance"),
                ("daily_utilities", "Utilities"),
                ("daily_maintenance", "Maintenance"),
                ("daily_business_rates", "Business Rates"),
                ("daily_cleaning", "Cleaning"),
                ("daily_mortgage", "Mortgage"),
                ("daily_total_cost", "TOTAL COST"),
            ]),
            ("Daily Profit", True, [
                ("daily_profit", "DAILY PROFIT"),
            ]),
            ("Weekly", False, [
                ("weekly_revenue", "Net Revenue"),
                ("weekly_cost", "Cost"),
                ("weekly_profit", "PROFIT"),
            ]),
            ("Monthly", True, [
                ("monthly_revenue", "Net Revenue"),
                ("monthly_cost", "Cost"),
                ("staff_monthly_total", "Staff Total (inc NI/pension)"),
                ("anpr_monthly_total", "ANPR Total"),
                ("mortgage_monthly_payment", "Mortgage Payment"),
                ("monthly_profit", "PROFIT"),
            ]),
            ("Yearly", True, [
                ("yearly_revenue", "Net Revenue"),
                ("yearly_cost", "Cost"),
                ("yearly_profit", "PROFIT"),
            ]),
            ("Mortgage Summary", False, [
                ("mortgage_loan_amount", "Loan Amount"),
                ("mortgage_deposit", "Deposit"),
                ("mortgage_total_interest", "Total Interest"),
                ("mortgage_total_repaid", "Total Repaid"),
            ]),
            ("Analysis", True, [
                ("break_even_occupancy", "Break-even Occupancy"),
            ]),
        ]

        row = 1
        for section_title, expanded, items in sections:
            sec = CollapsibleSection(
                parent, section_title, expanded=expanded,
                on_toggle=self._refresh_scroll,
            )
            sep = ttk.Separator(parent, orient="horizontal")
            sep.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(5, 2))
            row += 1
            sec.grid_header(row=row, column=0, columnspan=2, sticky="w", pady=(2, 2))
            row += 1
            sec.grid_content(row=row, column=0, columnspan=2, sticky="ew")
            row += 1
            self.result_sections.append(sec)

            cf = sec.content_frame
            cr = 0
            for key, label_text in items:
                ttk.Label(cf, text=label_text).grid(row=cr, column=0, sticky="w", padx=(10, 5))
                lbl = ttk.Label(cf, text="£0.00", style="Result.TLabel", width=18, anchor="e")
                lbl.grid(row=cr, column=1, sticky="e")
                self.result_labels[key] = lbl
                cr += 1

    # ------------------------------------------------------------ Update
    def _update_results(self, *_args):
        from models import PricingTier

        cfg = CarParkConfig(
            total_spaces=64,
            operating_hours=11.0,
            opening_days_per_week=int(self.vars["days_per_week"].get()),
            occupancy_rate=self.vars["occupancy_rate"].get(),
            avg_stay_hours=self.vars["avg_stay_hours"].get(),
            dead_time_minutes=self.vars["dead_time_minutes"].get(),
            pct_small_car=self.vars["pct_small_car"].get(),
            pct_large_car=self.vars["pct_large_car"].get(),
            pct_small_van=self.vars["pct_small_van"].get(),
            pct_large_van=self.vars["pct_large_van"].get(),
            staff=StaffConfig(
                num_staff=int(self.vars["num_staff"].get()),
                hourly_wage=self.vars["hourly_wage"].get(),
                employer_ni_pct=self.vars["employer_ni_pct"].get(),
                employer_pension_pct=self.vars["employer_pension_pct"].get(),
            ),
            anpr=ANPRConfig(
                enabled=self.vars["anpr_enabled"].get(),
                install_cost=self.vars["anpr_install"].get(),
                monthly_maintenance=self.vars["anpr_monthly"].get(),
                amortise_years=max(1, int(self.vars["anpr_years"].get())),
            ),
            mortgage=MortgageConfig(
                enabled=self.vars["mortgage_enabled"].get(),
                purchase_price=self.vars["purchase_price"].get(),
                deposit_pct=self.vars["deposit_pct"].get(),
                interest_rate=self.vars["interest_rate"].get(),
                term_years=max(1, int(self.vars["mortgage_term"].get())),
            ),
            overnight=OvernightConfig(
                num_overnight_cars=int(self.vars["overnight_cars"].get()),
                overnight_flat_fee=self.vars["overnight_fee"].get(),
            ),
            monthly_rent=self.vars["monthly_rent"].get(),
            monthly_insurance=self.vars["monthly_insurance"].get(),
            monthly_utilities=self.vars["monthly_utilities"].get(),
            monthly_maintenance=self.vars["monthly_maintenance"].get(),
            monthly_business_rates=self.vars["monthly_business_rates"].get(),
            monthly_cleaning=self.vars["monthly_cleaning"].get(),
            card_processing_fee_pct=self.vars["card_processing_fee_pct"].get(),
        )

        # Update pricing from sliders
        for vtype in VehicleType:
            key_h = f"price_hourly_{vtype.name}"
            key_d = f"price_daily_{vtype.name}"
            cfg.pricing[vtype] = PricingTier(
                vehicle_type=vtype,
                hourly_rate=self.vars[key_h].get(),
                daily_rate=self.vars[key_d].get(),
            )

        # Vehicle mix info
        raw_total = (cfg.pct_small_car + cfg.pct_large_car +
                     cfg.pct_small_van + cfg.pct_large_van)
        if raw_total > 0:
            self.mix_info.config(
                text=f"Raw sum: {raw_total:.0f}% → normalised to 100%",
                foreground="#89b4fa",
            )
        else:
            self.mix_info.config(text="⚠ All zero — defaulting to 100% small cars",
                                foreground="#f38ba8")

        # Update mortgage summary in the controls panel
        mort = cfg.mortgage
        self.mortgage_summary_labels["deposit_amount"].config(
            text=f"£{mort.deposit_amount:,.0f}")
        self.mortgage_summary_labels["loan_amount"].config(
            text=f"£{mort.loan_amount:,.0f}")
        self.mortgage_summary_labels["monthly_payment"].config(
            text=f"£{mort.monthly_payment:,.2f}")
        self.mortgage_summary_labels["total_interest"].config(
            text=f"£{mort.total_interest:,.0f}")
        self.mortgage_summary_labels["total_repaid"].config(
            text=f"£{mort.total_repaid:,.0f}")

        # Run simulation
        result = run_simulation(cfg)

        # Format and display results
        money_fields = {
            "daily_parking_revenue_gross", "daily_overnight_revenue_gross",
            "daily_total_revenue_gross", "daily_vat_liability", "daily_card_fees",
            "daily_total_revenue_net",
            "daily_staff_cost", "daily_employer_ni", "daily_employer_pension",
            "daily_anpr_cost", "daily_rent", "daily_insurance",
            "daily_utilities", "daily_maintenance", "daily_business_rates",
            "daily_cleaning", "daily_mortgage", "daily_total_cost", "daily_profit",
            "weekly_revenue", "weekly_cost", "weekly_profit",
            "monthly_revenue", "monthly_cost", "monthly_profit",
            "yearly_revenue", "yearly_cost", "yearly_profit",
            "avg_revenue_per_vehicle", "staff_monthly_total", "anpr_monthly_total",
            "mortgage_monthly_payment", "mortgage_loan_amount", "mortgage_deposit",
            "mortgage_total_interest", "mortgage_total_repaid",
        }
        pct_fields = {"break_even_occupancy"}
        float_fields = {"vehicles_per_day", "turnover_rate"}
        int_fields = {"effective_daytime_spaces"}
        profit_fields = {"daily_profit", "weekly_profit", "monthly_profit", "yearly_profit"}
        cost_highlight = {"daily_vat_liability", "daily_card_fees", "daily_total_cost"}

        for key, lbl in self.result_labels.items():
            val = getattr(result, key, 0)
            if key in money_fields:
                text = f"£{val:,.2f}"
            elif key in pct_fields:
                text = f"{val:.1f}%"
            elif key in float_fields:
                text = f"{val:.1f}"
            elif key in int_fields:
                text = f"{int(val)}"
            else:
                text = f"{val}"

            if key in profit_fields:
                lbl.configure(style="Result.TLabel" if val >= 0 else "Loss.TLabel",
                              font=("Helvetica", 11, "bold"))
            elif key in cost_highlight:
                lbl.configure(style="Loss.TLabel", font=("Helvetica", 10, ""))
            else:
                lbl.configure(style="Neutral.TLabel", font=("Helvetica", 10, ""))

            lbl.config(text=text)
