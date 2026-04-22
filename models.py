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
    vehicle_type: VehicleType
    hourly_rate: float       # £ per hour
    daily_rate: float        # £ per day (over 5 hours)
    daily_threshold_hours: int = 5

    def cost_for_duration(self, hours: float) -> float:
        if hours <= 0:
            return 0.0
        # minimum charge: £4 for up to 30 minutes
        if hours <= 0.5:
            return 4.0
        if hours >= self.daily_threshold_hours:
            return self.daily_rate
        # hourly, rounded up to whole hours
        whole_hours = math.ceil(hours)
        return max(4.0, self.hourly_rate * whole_hours)


# default pricing from the sign (inclusive of VAT)
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
    num_staff: int = 1
    hourly_wage: float = 12.0       # £ per hour per staff member
    hours_per_day: float = 11.0     # 7:30am - 6:30pm
    employer_ni_pct: float = 13.8
    employer_pension_pct: float = 3.0


@dataclass
class ANPRConfig:
    enabled: bool = False
    install_cost: float = 15000.0       # one-off installation
    monthly_maintenance: float = 200.0
    amortise_years: int = 5             # spread install cost over N years


@dataclass
class MortgageConfig:
    enabled: bool = False
    purchase_price: float = 250000.0
    deposit_pct: float = 25.0
    interest_rate: float = 5.5
    term_years: int = 25

    @property
    def deposit_amount(self) -> float:
        return self.purchase_price * (self.deposit_pct / 100.0)

    @property
    def loan_amount(self) -> float:
        return self.purchase_price - self.deposit_amount

    @property
    def monthly_payment(self) -> float:
        P = self.loan_amount
        if P <= 0:
            return 0.0
        r = (self.interest_rate / 100.0) / 12.0  # monthly rate
        n = self.term_years * 12
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
    num_overnight_cars: int = 0
    overnight_flat_fee: float = 15.0  # £ per overnight vehicle


@dataclass
class IndoorOutdoorConfig:
    num_indoor_spaces: int = 0          # 0 = no indoor section
    indoor_hourly_rate: float = 6.0
    indoor_daily_rate: float = 30.0


@dataclass
class LongTermConfig:
    num_long_term_spaces: int = 0
    weekly_fee_per_vehicle: float = 50.0  # £ per vehicle per week


@dataclass
class CarParkConfig:
    total_spaces: int = 64
    operating_hours: float = 11.0       # 7:30am to 6:30pm
    opening_days_per_week: int = 6

    occupancy_rate: float = 70.0        # % of spaces occupied on average
    avg_stay_hours: float = 2.5

    # time between one car leaving and the next arriving (realistic: 10-20 min)
    dead_time_minutes: float = 10.0

    # 0 = all short-stay/retail, 100 = all commuters
    commuter_pct: float = 0.0

    # vehicle mix percentages (normalised to sum to 100)
    pct_small_car: float = 60.0
    pct_large_car: float = 20.0
    pct_small_van: float = 15.0
    pct_large_van: float = 5.0

    staff: StaffConfig = field(default_factory=StaffConfig)
    anpr: ANPRConfig = field(default_factory=ANPRConfig)
    mortgage: MortgageConfig = field(default_factory=MortgageConfig)
    overnight: OvernightConfig = field(default_factory=OvernightConfig)
    indoor_outdoor: IndoorOutdoorConfig = field(default_factory=IndoorOutdoorConfig)
    long_term: LongTermConfig = field(default_factory=LongTermConfig)
    pricing: dict = field(default_factory=lambda: dict(DEFAULT_PRICING))

    monthly_rent: float = 0.0
    monthly_insurance: float = 300.0
    monthly_utilities: float = 150.0    # lighting, CCTV power, etc.
    monthly_maintenance: float = 200.0  # line painting, surface repair, etc.
    monthly_business_rates: float = 800.0
    card_processing_fee_pct: float = 2.5
    monthly_cleaning: float = 100.0
    monthly_other: float = 0.0

    def get_normalised_vehicle_mix(self) -> dict:
        # if all zeros, defaults to 100% small cars
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
        reserved = (
            min(self.overnight.num_overnight_cars, self.total_spaces)
            + min(self.long_term.num_long_term_spaces, self.total_spaces)
        )
        return max(0, self.total_spaces - min(reserved, self.total_spaces))
