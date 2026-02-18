"""
Comprehensive tests for the car park simulation.
Tests both code correctness AND logic/business sanity.

Run:  python3 -m pytest test_simulation.py -v
  or: python3 test_simulation.py
"""

import math
import sys
import pytest

from models import (
    CarParkConfig, PricingTier, VehicleType, StaffConfig,
    ANPRConfig, OvernightConfig, MortgageConfig, DEFAULT_PRICING,
)
from engine import run_simulation, SimulationResult


# =====================================================================
# SECTION 1: PRICING LOGIC TESTS
# =====================================================================

class TestPricingTier:
    """Test that pricing matches the sign exactly."""

    def _tier(self, vtype):
        return DEFAULT_PRICING[vtype]

    # -- Minimum charge --
    def test_minimum_charge_zero_hours(self):
        """0 hours should cost nothing (no parking happened)."""
        tier = self._tier(VehicleType.SMALL_CAR)
        assert tier.cost_for_duration(0) == 0.0

    def test_minimum_charge_negative(self):
        tier = self._tier(VehicleType.SMALL_CAR)
        assert tier.cost_for_duration(-1) == 0.0

    def test_minimum_charge_10_minutes(self):
        """10 minutes = £4 minimum."""
        tier = self._tier(VehicleType.SMALL_CAR)
        assert tier.cost_for_duration(10 / 60) == 4.0

    def test_minimum_charge_30_minutes(self):
        """Exactly 30 min = £4 minimum."""
        tier = self._tier(VehicleType.SMALL_CAR)
        assert tier.cost_for_duration(0.5) == 4.0

    def test_minimum_applies_to_all_vehicle_types(self):
        """The sign says minimum charge £4 — applies regardless of vehicle."""
        for vtype in VehicleType:
            tier = self._tier(vtype)
            assert tier.cost_for_duration(0.25) == 4.0, f"Min charge wrong for {vtype.value}"

    # -- Hourly rates --
    def test_small_car_1_hour(self):
        tier = self._tier(VehicleType.SMALL_CAR)
        assert tier.cost_for_duration(1.0) == 5.0

    def test_small_car_2_hours(self):
        tier = self._tier(VehicleType.SMALL_CAR)
        assert tier.cost_for_duration(2.0) == 10.0

    def test_small_car_just_over_1_hour(self):
        """1h01m should round up to 2 hours = £10."""
        tier = self._tier(VehicleType.SMALL_CAR)
        assert tier.cost_for_duration(1.02) == 10.0

    def test_large_van_3_hours(self):
        tier = self._tier(VehicleType.LARGE_VAN)
        assert tier.cost_for_duration(3.0) == 30.0

    def test_4x4_hourly_rate(self):
        tier = self._tier(VehicleType.LARGE_CAR_4X4)
        assert tier.cost_for_duration(2.0) == 12.0

    # -- Daily cap --
    def test_small_car_daily_at_5_hours(self):
        tier = self._tier(VehicleType.SMALL_CAR)
        assert tier.cost_for_duration(5.0) == 25.0

    def test_small_car_daily_at_8_hours(self):
        tier = self._tier(VehicleType.SMALL_CAR)
        assert tier.cost_for_duration(8.0) == 25.0

    def test_large_van_daily(self):
        tier = self._tier(VehicleType.LARGE_VAN)
        assert tier.cost_for_duration(6.0) == 50.0

    def test_daily_rate_is_cheaper_than_hourly_extrapolation(self):
        for vtype in VehicleType:
            tier = self._tier(vtype)
            hourly_cost_at_5h = tier.hourly_rate * 5
            assert tier.daily_rate <= hourly_cost_at_5h

    def test_31_minutes_charges_hourly_not_minimum(self):
        tier = self._tier(VehicleType.SMALL_CAR)
        assert tier.cost_for_duration(0.52) == 5.0

    def test_just_under_5_hours(self):
        tier = self._tier(VehicleType.SMALL_CAR)
        assert tier.cost_for_duration(4.9) == 25.0


# =====================================================================
# SECTION 2: VEHICLE MIX NORMALISATION (was a bug, now fixed)
# =====================================================================

class TestVehicleMixNormalisation:
    """Test that vehicle mix is always normalised to sum to 100%."""

    def test_default_mix_sums_to_100(self):
        cfg = CarParkConfig()
        mix = cfg.get_normalised_vehicle_mix()
        assert sum(mix.values()) == pytest.approx(1.0, abs=0.001)

    def test_mix_over_100_is_normalised(self):
        """Mix of 100+100+0+0 = 200% should normalise to 50/50."""
        cfg = CarParkConfig(
            pct_small_car=100, pct_large_car=100, pct_small_van=0, pct_large_van=0
        )
        mix = cfg.get_normalised_vehicle_mix()
        assert mix[VehicleType.SMALL_CAR] == pytest.approx(0.5, abs=0.001)
        assert mix[VehicleType.LARGE_CAR_4X4] == pytest.approx(0.5, abs=0.001)
        assert sum(mix.values()) == pytest.approx(1.0, abs=0.001)

    def test_inflated_mix_does_not_inflate_revenue(self):
        """Revenue should be the same whether mix is 60/20/15/5 or 120/40/30/10."""
        cfg_normal = CarParkConfig(
            pct_small_car=60, pct_large_car=20, pct_small_van=15, pct_large_van=5
        )
        cfg_doubled = CarParkConfig(
            pct_small_car=120, pct_large_car=40, pct_small_van=30, pct_large_van=10
        )
        r_normal = run_simulation(cfg_normal)
        r_doubled = run_simulation(cfg_doubled)
        assert r_normal.daily_parking_revenue_gross == pytest.approx(
            r_doubled.daily_parking_revenue_gross, rel=0.01
        )

    def test_all_zero_mix_defaults_to_small_cars(self):
        cfg = CarParkConfig(
            pct_small_car=0, pct_large_car=0, pct_small_van=0, pct_large_van=0
        )
        mix = cfg.get_normalised_vehicle_mix()
        assert mix[VehicleType.SMALL_CAR] == 1.0

    def test_all_zero_mix_still_generates_revenue(self):
        """Even with all-zero mix (defaults to small cars), revenue should work."""
        cfg = CarParkConfig(
            pct_small_car=0, pct_large_car=0, pct_small_van=0, pct_large_van=0
        )
        r = run_simulation(cfg)
        assert r.daily_parking_revenue_gross > 0


# =====================================================================
# SECTION 3: OVERNIGHT PARKING (was buggy, now fixed)
# =====================================================================

class TestOvernightParking:
    """Test overnight parking revenue and capacity reduction."""

    def test_overnight_revenue(self):
        cfg = CarParkConfig(
            overnight=OvernightConfig(num_overnight_cars=10, overnight_flat_fee=15)
        )
        r = run_simulation(cfg)
        assert r.daily_overnight_revenue_gross == pytest.approx(150.0, abs=0.01)

    def test_zero_overnight(self):
        cfg = CarParkConfig()
        r = run_simulation(cfg)
        assert r.daily_overnight_revenue_gross == 0.0

    def test_overnight_cars_reduce_daytime_capacity(self):
        """10 overnight cars should reduce available spaces from 64 to 54."""
        cfg = CarParkConfig(
            overnight=OvernightConfig(num_overnight_cars=10)
        )
        r = run_simulation(cfg)
        assert r.effective_daytime_spaces == 54

    def test_overnight_cars_reduce_daytime_vehicles(self):
        """With overnight cars, fewer daytime vehicles should fit."""
        cfg_no = CarParkConfig(occupancy_rate=100, dead_time_minutes=0)
        cfg_ov = CarParkConfig(
            occupancy_rate=100, dead_time_minutes=0,
            overnight=OvernightConfig(num_overnight_cars=10)
        )
        r_no = run_simulation(cfg_no)
        r_ov = run_simulation(cfg_ov)
        assert r_ov.vehicles_per_day < r_no.vehicles_per_day

    def test_overnight_cars_capped_at_total_spaces(self):
        """100 overnight cars in a 64-space park should cap at 64."""
        cfg = CarParkConfig(
            overnight=OvernightConfig(num_overnight_cars=100, overnight_flat_fee=15)
        )
        r = run_simulation(cfg)
        # Revenue should be capped at 64 × £15 = £960
        assert r.daily_overnight_revenue_gross == pytest.approx(64 * 15, abs=0.01)
        assert r.effective_daytime_spaces == 0

    def test_all_spaces_overnight_means_no_daytime_revenue(self):
        """If all 64 spaces are overnight, no daytime parking possible."""
        cfg = CarParkConfig(
            overnight=OvernightConfig(num_overnight_cars=64)
        )
        r = run_simulation(cfg)
        assert r.effective_daytime_spaces == 0
        assert r.vehicles_per_day == 0
        assert r.daily_parking_revenue_gross == 0


# =====================================================================
# SECTION 4: VEHICLE THROUGHPUT / DEAD TIME
# =====================================================================

class TestThroughput:
    """Test vehicle throughput with dead time modelling."""

    def test_vehicles_per_day_with_dead_time(self):
        """64 spaces × 70% occ, 2.5h stay + 10min dead time.
        Effective stay = 2.667h, turnover = 11/2.667 = 4.125.
        Vehicles = 44.8 × 4.125 = 184.8."""
        cfg = CarParkConfig(dead_time_minutes=10)
        r = run_simulation(cfg)
        effective_stay = 2.5 + 10/60
        expected_turnover = 11.0 / effective_stay
        expected_vehicles = 64 * 0.7 * expected_turnover
        assert r.vehicles_per_day == pytest.approx(expected_vehicles, abs=0.5)

    def test_zero_dead_time_gives_max_throughput(self):
        """With 0 dead time, throughput should be higher."""
        cfg_0 = CarParkConfig(dead_time_minutes=0)
        cfg_10 = CarParkConfig(dead_time_minutes=10)
        r_0 = run_simulation(cfg_0)
        r_10 = run_simulation(cfg_10)
        assert r_0.vehicles_per_day > r_10.vehicles_per_day

    def test_space_hours_never_exceed_capacity(self):
        """Total space-hours used should never exceed total available."""
        for occ in [30, 50, 70, 90, 100]:
            for stay in [0.5, 1, 2, 3, 5, 8, 11]:
                cfg = CarParkConfig(
                    occupancy_rate=occ, avg_stay_hours=stay, dead_time_minutes=0
                )
                r = run_simulation(cfg)
                space_hours_used = r.vehicles_per_day * cfg.avg_stay_hours
                space_hours_available = cfg.total_spaces * cfg.operating_hours
                assert space_hours_used <= space_hours_available + 0.01

    def test_100pct_occupancy_11h_stay_zero_dead_time(self):
        """Each space used once = exactly 64 vehicles."""
        cfg = CarParkConfig(occupancy_rate=100, avg_stay_hours=11.0, dead_time_minutes=0)
        r = run_simulation(cfg)
        assert r.vehicles_per_day == pytest.approx(64.0, abs=0.1)

    def test_zero_occupancy(self):
        cfg = CarParkConfig(occupancy_rate=0)
        r = run_simulation(cfg)
        assert r.vehicles_per_day == 0
        assert r.daily_parking_revenue_gross == 0

    def test_zero_stay_hours_no_crash(self):
        cfg = CarParkConfig(avg_stay_hours=0, dead_time_minutes=0)
        r = run_simulation(cfg)
        assert r.vehicles_per_day == 0


# =====================================================================
# SECTION 5: VAT AND CARD FEES
# =====================================================================

class TestVATAndFees:
    """Test VAT extraction and card processing fee deductions."""

    def test_vat_extracted_correctly(self):
        """Gross £120 → VAT = £20, net before fees = £100."""
        cfg = CarParkConfig(card_processing_fee_pct=0)
        r = run_simulation(cfg)
        expected_vat = r.daily_total_revenue_gross * (20.0 / 120.0)
        assert r.daily_vat_liability == pytest.approx(expected_vat, abs=0.01)

    def test_net_revenue_less_than_gross(self):
        """Net revenue should always be less than gross (VAT + card fees)."""
        cfg = CarParkConfig()
        r = run_simulation(cfg)
        assert r.daily_total_revenue_net < r.daily_total_revenue_gross

    def test_vat_is_one_sixth_of_gross(self):
        """VAT at 20% on a VAT-inclusive price = gross / 6."""
        cfg = CarParkConfig()
        r = run_simulation(cfg)
        assert r.daily_vat_liability == pytest.approx(
            r.daily_total_revenue_gross / 6.0, abs=0.01
        )

    def test_card_fees_calculation(self):
        """Card fees at 2.5% of gross revenue."""
        cfg = CarParkConfig(card_processing_fee_pct=2.5)
        r = run_simulation(cfg)
        expected_fees = r.daily_total_revenue_gross * 0.025
        assert r.daily_card_fees == pytest.approx(expected_fees, abs=0.01)

    def test_zero_card_fees(self):
        """With 0% card fee, no deduction."""
        cfg = CarParkConfig(card_processing_fee_pct=0)
        r = run_simulation(cfg)
        assert r.daily_card_fees == 0.0

    def test_net_equals_gross_minus_vat_minus_fees(self):
        cfg = CarParkConfig()
        r = run_simulation(cfg)
        expected_net = (r.daily_total_revenue_gross
                        - r.daily_vat_liability
                        - r.daily_card_fees)
        assert r.daily_total_revenue_net == pytest.approx(expected_net, abs=0.01)


# =====================================================================
# SECTION 6: COST CALCULATIONS
# =====================================================================

class TestCosts:
    """Test cost calculations including employer NI and pension."""

    def test_staff_base_wage(self):
        """1 staff × £12/hr × 11h = £132/day."""
        cfg = CarParkConfig(staff=StaffConfig(num_staff=1, hourly_wage=12.0))
        r = run_simulation(cfg)
        assert r.daily_staff_cost == pytest.approx(132.0, abs=0.01)

    def test_employer_ni(self):
        """NI at 13.8% of £132 = £18.22."""
        cfg = CarParkConfig(staff=StaffConfig(
            num_staff=1, hourly_wage=12.0, employer_ni_pct=13.8
        ))
        r = run_simulation(cfg)
        assert r.daily_employer_ni == pytest.approx(132.0 * 0.138, abs=0.01)

    def test_employer_pension(self):
        """Pension at 3% of £132 = £3.96."""
        cfg = CarParkConfig(staff=StaffConfig(
            num_staff=1, hourly_wage=12.0, employer_pension_pct=3.0
        ))
        r = run_simulation(cfg)
        assert r.daily_employer_pension == pytest.approx(132.0 * 0.03, abs=0.01)

    def test_staff_monthly_includes_ni_and_pension(self):
        """Monthly staff total should include wages + NI + pension."""
        cfg = CarParkConfig(staff=StaffConfig(
            num_staff=1, hourly_wage=12.0,
            employer_ni_pct=13.8, employer_pension_pct=3.0
        ))
        r = run_simulation(cfg)
        daily_total = r.daily_staff_cost + r.daily_employer_ni + r.daily_employer_pension
        days_per_month = cfg.opening_days_per_week * 4.33
        assert r.staff_monthly_total == pytest.approx(daily_total * days_per_month, abs=1.0)

    def test_3_staff_cost(self):
        cfg = CarParkConfig(staff=StaffConfig(num_staff=3, hourly_wage=12.0))
        r = run_simulation(cfg)
        assert r.daily_staff_cost == pytest.approx(396.0, abs=0.01)

    def test_zero_staff(self):
        cfg = CarParkConfig(staff=StaffConfig(num_staff=0))
        r = run_simulation(cfg)
        assert r.daily_staff_cost == 0.0
        assert r.daily_employer_ni == 0.0
        assert r.daily_employer_pension == 0.0

    def test_anpr_replaces_staff(self):
        cfg = CarParkConfig(
            staff=StaffConfig(num_staff=5, hourly_wage=20.0),
            anpr=ANPRConfig(enabled=True),
        )
        r = run_simulation(cfg)
        assert r.daily_staff_cost == 0.0
        assert r.daily_employer_ni == 0.0

    def test_anpr_cost_calculation(self):
        """£15,000/60mo = £250 + £200 maint = £450/month."""
        cfg = CarParkConfig(anpr=ANPRConfig(
            enabled=True, install_cost=15000, monthly_maintenance=200, amortise_years=5
        ))
        r = run_simulation(cfg)
        assert r.anpr_install_amortised_monthly == pytest.approx(250.0, abs=0.01)
        assert r.anpr_monthly_total == pytest.approx(450.0, abs=0.01)

    def test_business_rates_included(self):
        """Business rates should appear in daily costs."""
        cfg = CarParkConfig(monthly_business_rates=800)
        r = run_simulation(cfg)
        days_per_month = cfg.opening_days_per_week * 4.33
        assert r.daily_business_rates == pytest.approx(800 / days_per_month, abs=0.01)

    def test_cleaning_costs_included(self):
        cfg = CarParkConfig(monthly_cleaning=100)
        r = run_simulation(cfg)
        days_per_month = cfg.opening_days_per_week * 4.33
        assert r.daily_cleaning == pytest.approx(100 / days_per_month, abs=0.01)

    def test_total_cost_is_sum_of_all_components(self):
        cfg = CarParkConfig()
        r = run_simulation(cfg)
        expected = (r.daily_staff_cost + r.daily_employer_ni + r.daily_employer_pension +
                    r.daily_anpr_cost + r.daily_rent + r.daily_insurance +
                    r.daily_utilities + r.daily_maintenance +
                    r.daily_business_rates + r.daily_cleaning)
        assert r.daily_total_cost == pytest.approx(expected, abs=0.01)

    def test_anpr_vs_staff_savings(self):
        """ANPR should be significantly cheaper than 1 staff member."""
        cfg_staff = CarParkConfig(
            staff=StaffConfig(num_staff=1, hourly_wage=12.0),
            anpr=ANPRConfig(enabled=False),
        )
        cfg_anpr = CarParkConfig(
            anpr=ANPRConfig(enabled=True, install_cost=15000,
                            monthly_maintenance=200, amortise_years=5),
        )
        r_staff = run_simulation(cfg_staff)
        r_anpr = run_simulation(cfg_anpr)
        assert r_anpr.monthly_cost < r_staff.monthly_cost


# =====================================================================
# SECTION 7: PROFIT AND AGGREGATION
# =====================================================================

class TestProfitAggregation:
    """Test profit calculations and time aggregation."""

    def test_daily_profit_is_net_revenue_minus_cost(self):
        cfg = CarParkConfig()
        r = run_simulation(cfg)
        assert r.daily_profit == pytest.approx(
            r.daily_total_revenue_net - r.daily_total_cost, abs=0.01
        )

    def test_weekly_is_daily_times_days(self):
        cfg = CarParkConfig(opening_days_per_week=6)
        r = run_simulation(cfg)
        assert r.weekly_revenue == pytest.approx(r.daily_total_revenue_net * 6, abs=0.01)
        assert r.weekly_profit == pytest.approx(r.daily_profit * 6, abs=0.01)

    def test_monthly_calculation(self):
        cfg = CarParkConfig(opening_days_per_week=6)
        r = run_simulation(cfg)
        days_per_month = 6 * 4.33
        assert r.monthly_revenue == pytest.approx(
            r.daily_total_revenue_net * days_per_month, abs=1.0
        )

    def test_yearly_calculation(self):
        cfg = CarParkConfig(opening_days_per_week=6)
        r = run_simulation(cfg)
        days_per_year = 6 * 52
        assert r.yearly_revenue == pytest.approx(
            r.daily_total_revenue_net * days_per_year, abs=1.0
        )

    def test_loss_scenario(self):
        """Low occupancy + high costs = loss."""
        cfg = CarParkConfig(
            occupancy_rate=5,
            monthly_rent=5000,
            staff=StaffConfig(num_staff=3, hourly_wage=15),
        )
        r = run_simulation(cfg)
        assert r.daily_profit < 0
        assert r.yearly_profit < 0


# =====================================================================
# SECTION 8: BREAK-EVEN ANALYSIS (was buggy, now fixed)
# =====================================================================

class TestBreakEven:
    """Test break-even occupancy calculation."""

    def test_break_even_below_current_when_profitable(self):
        cfg = CarParkConfig()
        r = run_simulation(cfg)
        assert r.daily_profit > 0
        assert r.break_even_occupancy < cfg.occupancy_rate

    def test_break_even_above_current_when_losing(self):
        cfg = CarParkConfig(
            occupancy_rate=5,
            monthly_rent=5000,
            staff=StaffConfig(num_staff=3, hourly_wage=20),
        )
        r = run_simulation(cfg)
        assert r.daily_profit < 0
        assert r.break_even_occupancy > cfg.occupancy_rate

    def test_break_even_verification_no_overnight(self):
        """At break-even occupancy, profit should be ~£0."""
        cfg = CarParkConfig()
        r = run_simulation(cfg)
        be = r.break_even_occupancy

        cfg_be = CarParkConfig(occupancy_rate=be)
        r_be = run_simulation(cfg_be)
        assert abs(r_be.daily_profit) < 1.0, (
            f"At break-even {be:.1f}%, profit = £{r_be.daily_profit:.2f}"
        )

    def test_break_even_verification_with_overnight(self):
        """Break-even should be accurate even with overnight revenue.
        This was a bug — overnight revenue doesn't scale with occupancy,
        so break-even calc must separate it out."""
        cfg = CarParkConfig(
            overnight=OvernightConfig(num_overnight_cars=10, overnight_flat_fee=15)
        )
        r = run_simulation(cfg)
        be = r.break_even_occupancy

        cfg_be = CarParkConfig(
            occupancy_rate=be,
            overnight=OvernightConfig(num_overnight_cars=10, overnight_flat_fee=15)
        )
        r_be = run_simulation(cfg_be)
        assert abs(r_be.daily_profit) < 2.0, (
            f"At break-even {be:.1f}% with overnight, profit = £{r_be.daily_profit:.2f}"
        )

    def test_zero_revenue_break_even(self):
        cfg = CarParkConfig(occupancy_rate=0)
        r = run_simulation(cfg)
        assert r.break_even_occupancy == 100.0


# =====================================================================
# SECTION 9: REVENUE SANITY CHECKS
# =====================================================================

class TestRevenueSanity:
    """Sanity checks on revenue figures."""

    def test_revenue_scales_linearly_with_occupancy(self):
        cfg_50 = CarParkConfig(occupancy_rate=50)
        cfg_100 = CarParkConfig(occupancy_rate=100)
        r_50 = run_simulation(cfg_50)
        r_100 = run_simulation(cfg_100)
        ratio = r_100.daily_parking_revenue_gross / r_50.daily_parking_revenue_gross
        assert ratio == pytest.approx(2.0, abs=0.01)

    def test_manual_revenue_calculation(self):
        """64 spaces, 100% occ, 100% small cars, 1h stay, 0 dead time.
        Turnover = 11, vehicles = 704, revenue = 704 × £5 = £3,520 gross."""
        cfg = CarParkConfig(
            occupancy_rate=100, avg_stay_hours=1.0, dead_time_minutes=0,
            pct_small_car=100, pct_large_car=0, pct_small_van=0, pct_large_van=0,
        )
        r = run_simulation(cfg)
        assert r.vehicles_per_day == pytest.approx(704.0, abs=0.1)
        assert r.daily_parking_revenue_gross == pytest.approx(3520.0, abs=1.0)

    def test_revenue_per_space_more_realistic_now(self):
        """With dead time and VAT, revenue per space should be lower
        than before. Previously was ~£15k/space, should now be more
        like £5k-£10k range."""
        cfg = CarParkConfig()  # defaults with 10min dead time
        r = run_simulation(cfg)
        revenue_per_space = r.yearly_revenue / cfg.total_spaces
        # Net revenue per space (after VAT and fees) should be reasonable
        assert revenue_per_space < 15000, (
            f"£{revenue_per_space:,.0f}/space still seems high"
        )

    def test_profit_margin_more_realistic_now(self):
        """With all costs included, profit margin should be lower than 90%."""
        cfg = CarParkConfig()
        r = run_simulation(cfg)
        if r.yearly_revenue > 0:
            margin = (r.yearly_profit / r.yearly_revenue) * 100
            assert margin < 90, f"Margin {margin:.0f}% still seems too high"


# =====================================================================
# SECTION 10: EDGE CASES & ROBUSTNESS
# =====================================================================

class TestEdgeCases:
    """Edge cases that shouldn't crash the simulation."""

    def test_all_zeros(self):
        cfg = CarParkConfig(
            occupancy_rate=0, monthly_rent=0, monthly_insurance=0,
            monthly_utilities=0, monthly_maintenance=0,
            monthly_business_rates=0, monthly_cleaning=0,
            staff=StaffConfig(num_staff=0),
        )
        r = run_simulation(cfg)
        assert r.daily_profit == 0.0

    def test_max_turnover(self):
        """0.5h stay with 0 dead time = max turnover of 22."""
        cfg = CarParkConfig(
            occupancy_rate=100, avg_stay_hours=0.5, dead_time_minutes=0,
            pct_small_car=0, pct_large_car=0, pct_small_van=0, pct_large_van=100,
        )
        r = run_simulation(cfg)
        assert r.vehicles_per_day == pytest.approx(1408.0, abs=1.0)

    def test_1_day_per_week(self):
        cfg = CarParkConfig(opening_days_per_week=1)
        r = run_simulation(cfg)
        assert r.weekly_revenue == pytest.approx(r.daily_total_revenue_net, abs=0.01)

    def test_7_days_per_week(self):
        cfg = CarParkConfig(opening_days_per_week=7)
        r = run_simulation(cfg)
        assert r.weekly_revenue == pytest.approx(r.daily_total_revenue_net * 7, abs=0.01)

    def test_result_consistency(self):
        """Same config → same results."""
        cfg = CarParkConfig()
        r1 = run_simulation(cfg)
        r2 = run_simulation(cfg)
        assert r1.yearly_profit == r2.yearly_profit

    def test_model_config_helper_effective_spaces(self):
        """Test the effective daytime spaces helper."""
        cfg = CarParkConfig(overnight=OvernightConfig(num_overnight_cars=20))
        assert cfg.get_effective_daytime_spaces() == 44

        cfg2 = CarParkConfig(overnight=OvernightConfig(num_overnight_cars=0))
        assert cfg2.get_effective_daytime_spaces() == 64

        cfg3 = CarParkConfig(overnight=OvernightConfig(num_overnight_cars=100))
        assert cfg3.get_effective_daytime_spaces() == 0


# =====================================================================
# SECTION 11: COMPARISON — BEFORE vs AFTER FIXES
# =====================================================================

class TestBeforeVsAfterFixes:
    """Document how the fixes change the numbers."""

    def test_default_scenario_summary(self):
        """Print a summary comparing the realistic model to expectations."""
        cfg = CarParkConfig()
        r = run_simulation(cfg)

        print("\n" + "=" * 60)
        print("  DEFAULT SCENARIO SUMMARY (70% occ, 10min dead time)")
        print("=" * 60)
        print(f"  Effective spaces:     {r.effective_daytime_spaces}")
        print(f"  Vehicles/day:         {r.vehicles_per_day:.0f}")
        print(f"  Gross revenue/day:    £{r.daily_total_revenue_gross:,.2f}")
        print(f"  VAT liability/day:    £{r.daily_vat_liability:,.2f}")
        print(f"  Card fees/day:        £{r.daily_card_fees:,.2f}")
        print(f"  Net revenue/day:      £{r.daily_total_revenue_net:,.2f}")
        print(f"  Total costs/day:      £{r.daily_total_cost:,.2f}")
        print(f"  Daily profit:         £{r.daily_profit:,.2f}")
        print(f"  Monthly profit:       £{r.monthly_profit:,.2f}")
        print(f"  Yearly profit:        £{r.yearly_profit:,.2f}")
        print(f"  Break-even occupancy: {r.break_even_occupancy:.1f}%")
        profit_margin = (r.yearly_profit / r.yearly_revenue * 100) if r.yearly_revenue > 0 else 0
        print(f"  Profit margin:        {profit_margin:.1f}%")
        print(f"  Revenue/space/year:   £{r.yearly_revenue / 64:,.0f}")
        print("=" * 60)

        # Basic sanity — should be profitable
        # Note: even with all fixes, a car park with these rates at 70% occupancy
        # is genuinely very profitable. The remaining gap vs real-world is costs
        # like pay machine leases, accountancy, surface resurfacing reserves, etc.
        # that vary hugely by site and are hard to default.
        assert r.yearly_profit > 0
        assert r.yearly_profit < 800_000


# =====================================================================
# SECTION 12: MORTGAGE CALCULATIONS
# =====================================================================

class TestMortgage:
    """Test mortgage / purchase finance calculations."""

    def test_mortgage_monthly_payment_formula(self):
        """£250,000 purchase, 25% deposit = £187,500 loan.
        5.5% interest, 25 years.
        Standard annuity formula should give ~£1,150/month."""
        m = MortgageConfig(
            enabled=True, purchase_price=250000,
            deposit_pct=25, interest_rate=5.5, term_years=25,
        )
        assert m.deposit_amount == pytest.approx(62500.0, abs=0.01)
        assert m.loan_amount == pytest.approx(187500.0, abs=0.01)
        # Verify via manual calculation:
        # r = 0.055/12 = 0.004583, n = 300
        # Payment = 187500 * (0.004583 * 1.004583^300) / (1.004583^300 - 1)
        # ≈ £1,150.56
        assert m.monthly_payment == pytest.approx(1150.56, abs=1.0)

    def test_mortgage_zero_interest(self):
        """With 0% interest, monthly payment = loan / months."""
        m = MortgageConfig(
            enabled=True, purchase_price=120000,
            deposit_pct=0, interest_rate=0, term_years=10,
        )
        assert m.loan_amount == 120000.0
        assert m.monthly_payment == pytest.approx(1000.0, abs=0.01)
        assert m.total_interest == pytest.approx(0.0, abs=0.01)

    def test_mortgage_100_pct_deposit(self):
        """100% deposit = no loan, no payments."""
        m = MortgageConfig(
            enabled=True, purchase_price=250000,
            deposit_pct=100, interest_rate=5.5, term_years=25,
        )
        assert m.loan_amount == 0.0
        assert m.monthly_payment == 0.0
        assert m.total_interest == 0.0

    def test_mortgage_total_interest(self):
        """Total interest = total repaid - loan amount."""
        m = MortgageConfig(
            enabled=True, purchase_price=250000,
            deposit_pct=25, interest_rate=5.5, term_years=25,
        )
        assert m.total_repaid == pytest.approx(m.monthly_payment * 300, abs=0.01)
        assert m.total_interest == pytest.approx(m.total_repaid - m.loan_amount, abs=0.01)
        # Total interest should be substantial at 5.5% over 25 years
        assert m.total_interest > 100000

    def test_mortgage_disabled_no_cost(self):
        """When mortgage is disabled, it shouldn't add to costs."""
        cfg_no = CarParkConfig(mortgage=MortgageConfig(enabled=False))
        cfg_yes = CarParkConfig(mortgage=MortgageConfig(
            enabled=True, purchase_price=250000,
            deposit_pct=25, interest_rate=5.5, term_years=25,
        ))
        r_no = run_simulation(cfg_no)
        r_yes = run_simulation(cfg_yes)
        assert r_no.daily_mortgage == 0.0
        assert r_yes.daily_mortgage > 0
        assert r_yes.daily_total_cost > r_no.daily_total_cost

    def test_mortgage_appears_in_total_cost(self):
        """Mortgage payment should be included in daily total cost."""
        cfg = CarParkConfig(mortgage=MortgageConfig(
            enabled=True, purchase_price=250000,
            deposit_pct=25, interest_rate=5.5, term_years=25,
        ))
        r = run_simulation(cfg)
        days_per_month = cfg.opening_days_per_week * 4.33
        expected_daily = cfg.mortgage.monthly_payment / days_per_month
        assert r.daily_mortgage == pytest.approx(expected_daily, abs=0.01)

    def test_mortgage_reduces_profit(self):
        """Enabling mortgage should reduce profit by the payment amount."""
        cfg_no = CarParkConfig()
        cfg_yes = CarParkConfig(mortgage=MortgageConfig(
            enabled=True, purchase_price=500000,
            deposit_pct=25, interest_rate=6.0, term_years=25,
        ))
        r_no = run_simulation(cfg_no)
        r_yes = run_simulation(cfg_yes)
        assert r_yes.yearly_profit < r_no.yearly_profit
        # Difference should be approximately 12 months of mortgage payments
        yearly_mortgage = cfg_yes.mortgage.monthly_payment * 12
        profit_diff = r_no.yearly_profit - r_yes.yearly_profit
        # Won't be exact due to days_per_year vs 12*months, but close
        assert profit_diff == pytest.approx(yearly_mortgage, rel=0.05)

    def test_mortgage_with_high_price_causes_loss(self):
        """A very expensive car park with mortgage and low occupancy = loss."""
        cfg = CarParkConfig(
            occupancy_rate=20,
            mortgage=MortgageConfig(
                enabled=True, purchase_price=2000000,
                deposit_pct=10, interest_rate=7.0, term_years=25,
            ),
        )
        r = run_simulation(cfg)
        # £1.8M loan at 7% = ~£12,700/month mortgage
        assert r.mortgage_monthly_payment > 12000
        # Low occupancy + huge mortgage = loss
        assert r.yearly_profit < 0

    def test_shorter_term_higher_payments(self):
        """Shorter mortgage term = higher monthly payments but less interest."""
        m_long = MortgageConfig(
            enabled=True, purchase_price=250000,
            deposit_pct=25, interest_rate=5.5, term_years=25,
        )
        m_short = MortgageConfig(
            enabled=True, purchase_price=250000,
            deposit_pct=25, interest_rate=5.5, term_years=10,
        )
        assert m_short.monthly_payment > m_long.monthly_payment
        assert m_short.total_interest < m_long.total_interest

    def test_higher_deposit_lower_payments(self):
        """Higher deposit = lower monthly payments."""
        m_low = MortgageConfig(
            enabled=True, purchase_price=250000,
            deposit_pct=10, interest_rate=5.5, term_years=25,
        )
        m_high = MortgageConfig(
            enabled=True, purchase_price=250000,
            deposit_pct=50, interest_rate=5.5, term_years=25,
        )
        assert m_high.monthly_payment < m_low.monthly_payment
        assert m_high.loan_amount < m_low.loan_amount


# =====================================================================
# RUN
# =====================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
