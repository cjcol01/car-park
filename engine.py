"""
Simulation engine for the car park.
Calculates daily, weekly, monthly and yearly financials.

Fixes applied:
- Overnight cars reduce available daytime spaces
- Vehicle mix is normalised (always sums to 100%)
- Break-even only considers occupancy-dependent revenue
- Dead time between vehicles reduces effective turnover
- Overnight cars capped at total spaces
- VAT extracted from revenue (prices are VAT-inclusive)
- Employer NI and pension added to staff costs
- Card processing fees deducted
- Business rates and cleaning costs included
"""

import math
from dataclasses import dataclass

from models import CarParkConfig, VehicleType, PricingTier


@dataclass
class SimulationResult:
    """Results of a simulation run, all figures in £."""
    # Revenue (gross — VAT-inclusive, as charged to customers)
    daily_parking_revenue_gross: float = 0.0
    daily_indoor_revenue_gross: float = 0.0
    daily_outdoor_revenue_gross: float = 0.0
    daily_overnight_revenue_gross: float = 0.0
    daily_long_term_revenue_gross: float = 0.0
    daily_total_revenue_gross: float = 0.0

    # Revenue (net — after VAT and card fees removed)
    daily_vat_liability: float = 0.0
    daily_card_fees: float = 0.0
    daily_total_revenue_net: float = 0.0

    # Costs (daily)
    daily_staff_cost: float = 0.0
    daily_employer_ni: float = 0.0
    daily_employer_pension: float = 0.0
    daily_anpr_cost: float = 0.0
    daily_rent: float = 0.0
    daily_insurance: float = 0.0
    daily_utilities: float = 0.0
    daily_maintenance: float = 0.0
    daily_business_rates: float = 0.0
    daily_cleaning: float = 0.0
    daily_other: float = 0.0
    daily_mortgage: float = 0.0
    daily_total_cost: float = 0.0

    # Profit
    daily_profit: float = 0.0

    # Aggregates
    weekly_revenue: float = 0.0
    weekly_cost: float = 0.0
    weekly_profit: float = 0.0

    monthly_revenue: float = 0.0
    monthly_cost: float = 0.0
    monthly_profit: float = 0.0

    yearly_revenue: float = 0.0
    yearly_cost: float = 0.0
    yearly_profit: float = 0.0

    # Useful breakdowns
    effective_daytime_spaces: int = 0
    occupied_spaces: float = 0.0       # actual number of spaces in use at peak
    total_spaces: int = 0              # total spaces in car park
    vehicles_per_day: float = 0.0
    turnover_rate: float = 0.0  # blended turnover for display
    avg_revenue_per_vehicle: float = 0.0
    indoor_spaces: int = 0
    outdoor_spaces: int = 0
    long_term_spaces: int = 0
    overnight_spaces: int = 0

    # Commuter vs short-stay split
    commuter_spaces_count: float = 0.0
    short_stay_spaces_count: float = 0.0
    commuter_vehicles_per_day: float = 0.0
    short_stay_vehicles_per_day: float = 0.0
    commuter_turnover_rate: float = 0.0
    short_stay_turnover_rate: float = 0.0
    daily_commuter_revenue_gross: float = 0.0
    daily_short_stay_revenue_gross: float = 0.0

    # ANPR
    anpr_monthly_total: float = 0.0
    anpr_install_amortised_monthly: float = 0.0
    staff_monthly_total: float = 0.0

    # Mortgage
    mortgage_monthly_payment: float = 0.0
    mortgage_total_interest: float = 0.0
    mortgage_total_repaid: float = 0.0
    mortgage_loan_amount: float = 0.0
    mortgage_deposit: float = 0.0

    # Break-even
    break_even_occupancy: float = 0.0  # % occupancy needed to break even


def run_simulation(config: CarParkConfig) -> SimulationResult:
    """Run the simulation with the given configuration."""
    r = SimulationResult()

    # --- Space allocation ---
    overnight_cars = min(config.overnight.num_overnight_cars, config.total_spaces)
    long_term_spaces = min(
        config.long_term.num_long_term_spaces,
        config.total_spaces - overnight_cars,
    )
    reserved_spaces = overnight_cars + long_term_spaces
    short_stay_spaces = max(0, config.total_spaces - reserved_spaces)

    # Indoor/outdoor split of short-stay spaces
    indoor_spaces = min(config.indoor_outdoor.num_indoor_spaces, short_stay_spaces)
    outdoor_spaces = short_stay_spaces - indoor_spaces

    r.effective_daytime_spaces = short_stay_spaces
    r.total_spaces = config.total_spaces
    r.indoor_spaces = indoor_spaces
    r.outdoor_spaces = outdoor_spaces
    r.long_term_spaces = long_term_spaces
    r.overnight_spaces = overnight_cars

    # --- Commuter vs short-stay space split ---
    commuter_fraction = config.commuter_pct / 100.0
    ss_fraction = 1.0 - commuter_fraction
    commuter_spaces = short_stay_spaces * commuter_fraction
    ss_spaces = short_stay_spaces * ss_fraction

    r.commuter_spaces_count = commuter_spaces
    r.short_stay_spaces_count = ss_spaces

    # --- Normalised vehicle mix ---
    vehicle_mix = config.get_normalised_vehicle_mix()

    # --- Indoor / outdoor fractions (applied equally to both populations) ---
    outdoor_fraction = outdoor_spaces / short_stay_spaces if short_stay_spaces > 0 else 1.0
    indoor_fraction = indoor_spaces / short_stay_spaces if short_stay_spaces > 0 else 0.0

    indoor_tier = PricingTier(
        vehicle_type=None,
        hourly_rate=config.indoor_outdoor.indoor_hourly_rate,
        daily_rate=config.indoor_outdoor.indoor_daily_rate,
    )

    # --- Commuter population ---
    # Commuters stay all day (>= daily threshold), turnover = 1 per space per day.
    # Occupancy rate applies the same as short-stay.
    commuter_occupied = commuter_spaces * (config.occupancy_rate / 100.0)
    r.commuter_turnover_rate = 1.0
    r.commuter_vehicles_per_day = commuter_occupied  # one car per space per day

    # Cost per commuter: always hits daily rate (stay = operating_hours >= threshold)
    indoor_cost_commuter = indoor_tier.cost_for_duration(config.operating_hours)
    commuter_outdoor_rev = 0.0
    commuter_indoor_rev = 0.0
    for vtype, mix_frac in vehicle_mix.items():
        num_vehicles = r.commuter_vehicles_per_day * mix_frac
        tier = config.pricing[vtype]
        outdoor_cost = tier.cost_for_duration(config.operating_hours)
        commuter_outdoor_rev += num_vehicles * outdoor_fraction * outdoor_cost
        commuter_indoor_rev += num_vehicles * indoor_fraction * indoor_cost_commuter

    # --- Short-stay population ---
    # Use existing turnover model based on avg_stay_hours + dead_time.
    dead_time_hours = config.dead_time_minutes / 60.0
    effective_stay = config.avg_stay_hours + dead_time_hours
    if effective_stay > 0:
        ss_turnover = config.operating_hours / effective_stay
    else:
        ss_turnover = 0.0
    r.short_stay_turnover_rate = ss_turnover

    ss_occupied = ss_spaces * (config.occupancy_rate / 100.0)
    r.short_stay_vehicles_per_day = ss_occupied * ss_turnover

    indoor_cost_ss = indoor_tier.cost_for_duration(config.avg_stay_hours)
    ss_outdoor_rev = 0.0
    ss_indoor_rev = 0.0
    for vtype, mix_frac in vehicle_mix.items():
        num_vehicles = r.short_stay_vehicles_per_day * mix_frac
        tier = config.pricing[vtype]
        outdoor_cost = tier.cost_for_duration(config.avg_stay_hours)
        ss_outdoor_rev += num_vehicles * outdoor_fraction * outdoor_cost
        ss_indoor_rev += num_vehicles * indoor_fraction * indoor_cost_ss

    # --- Aggregate throughput ---
    r.occupied_spaces = commuter_occupied + ss_occupied
    r.vehicles_per_day = r.commuter_vehicles_per_day + r.short_stay_vehicles_per_day
    # Blended turnover = vehicles / occupied spaces (meaningful for display)
    r.turnover_rate = (
        r.vehicles_per_day / r.occupied_spaces if r.occupied_spaces > 0 else 0.0
    )

    # --- Aggregate revenue ---
    r.daily_commuter_revenue_gross = commuter_outdoor_rev + commuter_indoor_rev
    r.daily_short_stay_revenue_gross = ss_outdoor_rev + ss_indoor_rev
    r.daily_outdoor_revenue_gross = commuter_outdoor_rev + ss_outdoor_rev
    r.daily_indoor_revenue_gross = commuter_indoor_rev + ss_indoor_rev
    r.daily_parking_revenue_gross = r.daily_outdoor_revenue_gross + r.daily_indoor_revenue_gross

    # --- Overnight revenue (gross) ---
    r.daily_overnight_revenue_gross = overnight_cars * config.overnight.overnight_flat_fee

    # --- Long-term revenue (weekly fee spread to daily) ---
    r.daily_long_term_revenue_gross = (
        long_term_spaces * config.long_term.weekly_fee_per_vehicle / 7.0
    )

    r.daily_total_revenue_gross = (
        r.daily_parking_revenue_gross
        + r.daily_overnight_revenue_gross
        + r.daily_long_term_revenue_gross
    )

    # --- VAT: prices are inclusive, so extract VAT at 20% ---
    # VAT-inclusive means: gross = net + VAT, where VAT = net × 20%
    # So: gross = net × 1.20, therefore net = gross / 1.20
    r.daily_vat_liability = r.daily_total_revenue_gross * (20.0 / 120.0)

    # --- Card processing fees ---
    r.daily_card_fees = (
        r.daily_total_revenue_gross * (config.card_processing_fee_pct / 100.0)
    )

    # --- Net revenue (what you actually keep) ---
    r.daily_total_revenue_net = (
        r.daily_total_revenue_gross - r.daily_vat_liability - r.daily_card_fees
    )

    # --- Daily costs ---
    days_per_week = config.opening_days_per_week
    days_per_month = days_per_week * 4.33  # average weeks per month
    days_per_year = days_per_week * 52

    # Staff costs (including employer NI and pension) — always calculated
    base_wage_daily = (
        config.staff.num_staff
        * config.staff.hourly_wage
        * config.staff.hours_per_day
    )
    r.daily_staff_cost = base_wage_daily
    r.daily_employer_ni = base_wage_daily * (config.staff.employer_ni_pct / 100.0)
    r.daily_employer_pension = base_wage_daily * (config.staff.employer_pension_pct / 100.0)

    # ANPR costs (adds on top of staff, does not replace them)
    if config.anpr.enabled:
        monthly_amortised = config.anpr.install_cost / (config.anpr.amortise_years * 12)
        r.anpr_install_amortised_monthly = monthly_amortised
        r.anpr_monthly_total = monthly_amortised + config.anpr.monthly_maintenance
        r.daily_anpr_cost = r.anpr_monthly_total / days_per_month
    else:
        r.daily_anpr_cost = 0.0
        r.anpr_monthly_total = 0.0
        r.anpr_install_amortised_monthly = 0.0

    r.staff_monthly_total = (
        (r.daily_staff_cost + r.daily_employer_ni + r.daily_employer_pension)
        * days_per_month
    )

    # Fixed monthly costs spread to daily
    r.daily_rent = config.monthly_rent / days_per_month
    r.daily_insurance = config.monthly_insurance / days_per_month
    r.daily_utilities = config.monthly_utilities / days_per_month
    r.daily_maintenance = config.monthly_maintenance / days_per_month
    r.daily_business_rates = config.monthly_business_rates / days_per_month
    r.daily_cleaning = config.monthly_cleaning / days_per_month
    r.daily_other = config.monthly_other / days_per_month

    # Mortgage
    if config.mortgage.enabled:
        r.mortgage_monthly_payment = config.mortgage.monthly_payment
        r.mortgage_total_interest = config.mortgage.total_interest
        r.mortgage_total_repaid = config.mortgage.total_repaid
        r.mortgage_loan_amount = config.mortgage.loan_amount
        r.mortgage_deposit = config.mortgage.deposit_amount
        r.daily_mortgage = config.mortgage.monthly_payment / days_per_month
    else:
        r.daily_mortgage = 0.0

    r.daily_total_cost = (
        r.daily_staff_cost
        + r.daily_employer_ni
        + r.daily_employer_pension
        + r.daily_anpr_cost
        + r.daily_rent
        + r.daily_insurance
        + r.daily_utilities
        + r.daily_maintenance
        + r.daily_business_rates
        + r.daily_cleaning
        + r.daily_other
        + r.daily_mortgage
    )

    r.daily_profit = r.daily_total_revenue_net - r.daily_total_cost

    # --- Aggregates (using net revenue) ---
    r.weekly_revenue = r.daily_total_revenue_net * days_per_week
    r.weekly_cost = r.daily_total_cost * days_per_week
    r.weekly_profit = r.daily_profit * days_per_week

    r.monthly_revenue = r.daily_total_revenue_net * days_per_month
    r.monthly_cost = r.daily_total_cost * days_per_month
    r.monthly_profit = r.daily_profit * days_per_month

    r.yearly_revenue = r.daily_total_revenue_net * days_per_year
    r.yearly_cost = r.daily_total_cost * days_per_year
    r.yearly_profit = r.daily_profit * days_per_year

    # --- Per-vehicle average ---
    if r.vehicles_per_day > 0:
        r.avg_revenue_per_vehicle = r.daily_parking_revenue_gross / r.vehicles_per_day
    else:
        r.avg_revenue_per_vehicle = 0.0

    # --- Break-even occupancy ---
    # Only short-stay parking revenue scales with occupancy.
    # Overnight and long-term revenues are fixed regardless of occupancy.
    vat_card_factor = (100.0 / 120.0) * ((100.0 - config.card_processing_fee_pct) / 100.0)
    fixed_revenue_net = (
        r.daily_overnight_revenue_gross + r.daily_long_term_revenue_gross
    ) * vat_card_factor
    parking_net = r.daily_total_revenue_net - fixed_revenue_net

    if parking_net > 0 and config.occupancy_rate > 0:
        cost_minus_fixed = r.daily_total_cost - fixed_revenue_net
        if cost_minus_fixed <= 0:
            r.break_even_occupancy = 0.0
        else:
            parking_net_per_pct = parking_net / config.occupancy_rate
            r.break_even_occupancy = cost_minus_fixed / parking_net_per_pct
    else:
        r.break_even_occupancy = 100.0

    return r
