"""
KSEB (Kerala State Electricity Board) Tariff FY 2025-26
Implements Telescopic (≤250 units) and Non-Telescopic (>250 units) billing
"""

from dataclasses import dataclass, field
from typing import Literal

PhaseType = Literal["1-phase", "3-phase"]

# --- Telescopic Slabs (applied when monthly units ≤ 250) ---
TELESCOPIC_SLABS = [
    {"from": 0,   "to": 50,  "rate": 3.35},
    {"from": 51,  "to": 100, "rate": 4.25},
    {"from": 101, "to": 150, "rate": 5.35},
    {"from": 151, "to": 200, "rate": 7.20},
    {"from": 201, "to": 250, "rate": 8.50},
]

# --- Non-Telescopic Flat Rates (applied when monthly units > 250) ---
NON_TELESCOPIC_SLABS = [
    {"from": 251, "to": 300,   "rate": 6.40},
    {"from": 301, "to": 350,   "rate": 7.25},
    {"from": 351, "to": 400,   "rate": 7.80},
    {"from": 401, "to": 500,   "rate": 8.20},
    {"from": 501, "to": float("inf"), "rate": 9.20},
]

KSEB_ELECTRICITY_DUTY = 0.10        # 10%
KSEB_FUEL_SURCHARGE_PER_UNIT = 0.15  # ₹0.15/unit
TELESCOPIC_LIMIT = 250

KSEB_FIXED_CHARGE: dict[str, float] = {"1-phase": 110, "3-phase": 220}
KSEB_METER_RENT: dict[str, float]   = {"1-phase": 20,  "3-phase": 40}


@dataclass
class SlabBreakdownItem:
    slab: str
    units: int
    rate: float
    cost: float


@dataclass
class KSEBBillResult:
    billing_type: str          # "telescopic" | "non-telescopic"
    fixed_charge: float
    energy_charge: float
    electricity_duty: float
    fuel_surcharge: float
    meter_rent: float
    total: float
    slab_breakdown: list[SlabBreakdownItem]
    monthly_kwh: int
    effective_rate: float
    near_slab_cliff: bool
    cliff_savings: float


def _telescopic_charge(units: int) -> tuple[float, list[SlabBreakdownItem]]:
    remaining = units
    charge = 0.0
    breakdown: list[SlabBreakdownItem] = []
    for slab in TELESCOPIC_SLABS:
        if remaining <= 0:
            break
        slab_width = slab["to"] - slab["from"] + 1
        consumed = min(remaining, slab_width)
        cost = consumed * slab["rate"]
        charge += cost
        breakdown.append(SlabBreakdownItem(
            slab=f"{slab['from']}–{slab['to']}",
            units=round(consumed),
            rate=slab["rate"],
            cost=round(cost),
        ))
        remaining -= consumed
    return charge, breakdown


def _non_telescopic_rate(units: int) -> float:
    for slab in NON_TELESCOPIC_SLABS:
        if units <= slab["to"]:
            return slab["rate"]
    return NON_TELESCOPIC_SLABS[-1]["rate"]


def _bill_internal(units: int, phase: PhaseType) -> float:
    charge, _ = _telescopic_charge(units)
    duty = charge * KSEB_ELECTRICITY_DUTY
    fac  = units * KSEB_FUEL_SURCHARGE_PER_UNIT
    return KSEB_FIXED_CHARGE[phase] + charge + duty + fac + KSEB_METER_RENT[phase]


def calculate_kseb_bill(monthly_kwh: float, phase: PhaseType = "1-phase") -> KSEBBillResult:
    units = max(0, round(monthly_kwh))
    is_telescopic = units <= TELESCOPIC_LIMIT
    near_slab_cliff = 240 <= units <= 260

    if is_telescopic:
        energy_charge, slab_breakdown = _telescopic_charge(units)
    else:
        rate = _non_telescopic_rate(units)
        energy_charge = units * rate
        slab_breakdown = [SlabBreakdownItem(
            slab=f"1–{units} (flat)", units=units, rate=rate, cost=round(energy_charge)
        )]

    electricity_duty = energy_charge * KSEB_ELECTRICITY_DUTY
    fuel_surcharge   = units * KSEB_FUEL_SURCHARGE_PER_UNIT
    fixed_charge     = KSEB_FIXED_CHARGE[phase]
    meter_rent       = KSEB_METER_RENT[phase]
    total            = fixed_charge + energy_charge + electricity_duty + fuel_surcharge + meter_rent

    cliff_savings = 0.0
    if not is_telescopic:
        cliff_savings = round(total - _bill_internal(250, phase))

    return KSEBBillResult(
        billing_type="telescopic" if is_telescopic else "non-telescopic",
        fixed_charge=fixed_charge,
        energy_charge=round(energy_charge),
        electricity_duty=round(electricity_duty),
        fuel_surcharge=round(fuel_surcharge),
        meter_rent=meter_rent,
        total=round(total),
        slab_breakdown=slab_breakdown,
        monthly_kwh=units,
        effective_rate=round(total / units, 2) if units > 0 else 0.0,
        near_slab_cliff=near_slab_cliff,
        cliff_savings=cliff_savings,
    )


def effective_rate(monthly_kwh: float) -> float:
    if monthly_kwh <= 0:
        return 0.0
    return calculate_kseb_bill(monthly_kwh).effective_rate


def units_to_drop_to_telescopic(monthly_kwh: float) -> int:
    if monthly_kwh <= TELESCOPIC_LIMIT:
        return 0
    return int(monthly_kwh - TELESCOPIC_LIMIT) + 1
