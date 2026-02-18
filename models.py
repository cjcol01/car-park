"""
Data models for the car park simulation.
Defines vehicle types, pricing tiers, and cost structures.
"""

import math
from dataclasses import dataclass, field
from enum import Enum


class VehicleType(Enum):
    SMALL_CAR = "Small Car"
    LARGE_CAR_4X4 = "4x4 / Long Car"
    SMALL_MEDIUM_VAN = "Small & Medium Van"
    LARGE_VAN = "Large Van"


@dataclass
class PricingTier:
    """Pricing for a vehicle type, matching the sign rates."""
    vehicle_type: VehicleType
    hourly_rate: float       # £ per hour
    daily_rate: float        # £ per day (over 5 hours)
    daily_threshold_hours: int = 5  # hours before daily rate kicks in

    def cost_for_duration(self, hours: float) -> float:
        """Calculate parking cost for a given duration in hours."""
        if hours <= 0:
            return 0.0
        # Minimum charge: £4 for up to 30 minutes
        if hours <= 0.5:
            return 4.0
        # If over the daily threshold, charge the daily rate
        if hours >= self.daily_threshold_hours:
            return self.daily_rate
        # Otherwise charge hourly (rounded up to whole hours)
        whole_hours = math.ceil(hours)
        return max(4.0, self.hourly_rate * whole_hours)


# Default pricing from the sign (inclusive of VAT)
DEFAULT_PRICING = {
    VehicleType.SMALL_CAR: PricingTier(
        vehicle_type=VehicleType.SMALL_CAR,
        hourly_rate=5.0,
        daily_rate=25.0,
    ),
    VehicleType.LARGE_CAR_4X4: PricingTier(
        vehicle_type=VehicleType.LARGE_CAR_4X4,
        hourly_rate=6.0,
        daily_rate=30.0,
    ),
    VehicleType.SMALL_MEDIUM_VAN: PricingTier(
        vehicle_type=VehicleType.SMALL_MEDIUM_VAN,
        hourly_rate=6.0,
        daily_rate=30.0,
    ),
    VehicleType.LARGE_VAN: PricingTier(
        vehicle_type=VehicleType.LARGE_VAN,
        hourly_rate=10.0,
        daily_rate=50.0,
    ),
}


@dataclass
class StaffConfig:
    """Staff and operational cost configuration."""
    num_staff: int = 1
    hourly_wage: float = 12.0  # £ per hour per staff member
    hours_per_day: float = 11.0  # 7:30am - 6:30pm
    employer_ni_pct: float = 13.8  # employer national insurance %
    employer_pension_pct: float = 3.0  # employer pension contribution %


@dataclass
class ANPRConfig:
    """ANPR system configuration."""
    enabled: bool = False
    install_cost: float = 15000.0       # one-off installation
    monthly_maintenance: float = 200.0  # monthly maintenance/subscription
    amortise_years: int = 5             # spread install cost over N years


@dataclass
class MortgageConfig:
    """Mortgage / purchase finance configuration."""
    enabled: bool = False
    purchase_price: float = 250000.0   # £ purchase price of the car park
    deposit_pct: float = 25.0          # % deposit
    interest_rate: float = 5.5         # annual interest rate %
    term_years: int = 25               # mortgage term in years

    @property
    def deposit_amount(self) -> float:
        return self.purchase_price * (self.deposit_pct / 100.0)

    @property
    def loan_amount(self) -> float:
        return self.purchase_price - self.deposit_amount

    @property
    def monthly_payment(self) -> float:
        """Calculate monthly mortgage payment using standard annuity formula."""
        P = self.loan_amount
        if P <= 0:
            return 0.0
        r = (self.interest_rate / 100.0) / 12.0  # monthly rate
        n = self.term_years * 12  # total payments
        if r <= 0:
            return P / n if n > 0 else 0.0
        return P * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

    @property
    def total_repaid(self) -> float:
        return self.monthly_payment * self.term_years * 12

    @property
    def total_interest(self) -> float:
        return self.total_repaid - self.loan_amount


@dataclass
class OvernightConfig:
    """Overnight parking configuration."""
    num_overnight_cars: int = 0
    overnight_flat_fee: float = 15.0  # £ per overnight vehicle


@dataclass
class IndoorOutdoorConfig:
    """Indoor vs outdoor space split, each with separate pricing."""
    num_indoor_spaces: int = 0          # 0 = no indoor section
    indoor_hourly_rate: float = 6.0     # £/hr for indoor spaces
    indoor_daily_rate: float = 30.0     # £/day for indoor spaces


@dataclass
class LongTermConfig:
    """Long-term permit parking (reserved spaces, fixed weekly fee)."""
    num_long_term_spaces: int = 0
    weekly_fee_per_vehicle: float = 50.0  # £ per vehicle per week


@dataclass
class CarParkConfig:
    """Top-level configuration for the car park."""
    total_spaces: int = 64
    operating_hours: float = 11.0  # 7:30am to 6:30pm
    opening_days_per_week: int = 6  # Mon-Sat typical

    # Occupancy & vehicle mix (percentages 0-100)
    occupancy_rate: float = 70.0  # % of spaces occupied on average
    avg_stay_hours: float = 2.5   # average parking duration

    # Dead time between vehicles (minutes) — time a space sits empty
    # between one car leaving and the next arriving (realistic: 10-20 min)
    dead_time_minutes: float = 10.0

    # Vehicle mix percentages (will be normalised to sum to 100)
    pct_small_car: float = 60.0
    pct_large_car: float = 20.0
    pct_small_van: float = 15.0
    pct_large_van: float = 5.0

    # Sub-configs
    staff: StaffConfig = field(default_factory=StaffConfig)
    anpr: ANPRConfig = field(default_factory=ANPRConfig)
    mortgage: MortgageConfig = field(default_factory=MortgageConfig)
    overnight: OvernightConfig = field(default_factory=OvernightConfig)
    indoor_outdoor: IndoorOutdoorConfig = field(default_factory=IndoorOutdoorConfig)
    long_term: LongTermConfig = field(default_factory=LongTermConfig)
    pricing: dict = field(default_factory=lambda: dict(DEFAULT_PRICING))

    # Additional costs
    monthly_rent: float = 0.0
    monthly_insurance: float = 300.0
    monthly_utilities: float = 150.0   # lighting, CCTV power, etc.
    monthly_maintenance: float = 200.0  # line painting, surface repair, etc.
    monthly_business_rates: float = 800.0  # council business rates
    card_processing_fee_pct: float = 2.5  # % of revenue lost to card fees
    monthly_cleaning: float = 100.0  # litter, cleaning
    monthly_other: float = 0.0      # catch-all for other costs

    def get_normalised_vehicle_mix(self) -> dict:
        """Return vehicle mix fractions that always sum to 1.0.
        If all zeros, defaults to 100% small cars."""
        raw = {
            VehicleType.SMALL_CAR: self.pct_small_car,
            VehicleType.LARGE_CAR_4X4: self.pct_large_car,
            VehicleType.SMALL_MEDIUM_VAN: self.pct_small_van,
            VehicleType.LARGE_VAN: self.pct_large_van,
        }
        total = sum(raw.values())
        if total <= 0:
            return {VehicleType.SMALL_CAR: 1.0, VehicleType.LARGE_CAR_4X4: 0.0,
                    VehicleType.SMALL_MEDIUM_VAN: 0.0, VehicleType.LARGE_VAN: 0.0}
        return {k: v / total for k, v in raw.items()}

    def get_effective_daytime_spaces(self) -> int:
        """Return number of spaces available for daytime short-stay use,
        accounting for overnight cars, long-term, and indoor/outdoor split."""
        reserved = (
            min(self.overnight.num_overnight_cars, self.total_spaces)
            + min(self.long_term.num_long_term_spaces, self.total_spaces)
        )
        return max(0, self.total_spaces - min(reserved, self.total_spaces))
