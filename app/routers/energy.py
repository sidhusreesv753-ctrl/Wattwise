"""
Energy & Bill API routes
GET  /api/energy/summary          — compute energy summary from posted profile
POST /api/energy/bill             — calculate KSEB bill for given kWh + phase
POST /api/energy/recommendations  — get smart saving recommendations
POST /api/energy/insights         — appliance efficiency insights
GET  /api/energy/simulator        — bill comparison simulator
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.models.schemas import EnergyProfile, ApplianceInput, BillScanData, AGE_OPTIONS
from app.services.energy_service import (
    get_energy_summary,
    get_smart_recommendations,
    get_efficiency_insights,
    compute_appliance_breakdown,
    compute_daily_kwh,
)
from app.services.kseb_tariff import (
    calculate_kseb_bill,
    TELESCOPIC_LIMIT,
    TELESCOPIC_SLABS,
    NON_TELESCOPIC_SLABS,
)

router = APIRouter(prefix="/api/energy", tags=["energy"])


# ── Summary ───────────────────────────────────────────────────────────────────

@router.post("/summary")
def energy_summary(profile: EnergyProfile):
    """Full energy summary — bill, breakdown, hourly usage."""
    return get_energy_summary(profile)


# ── Bill calculator ───────────────────────────────────────────────────────────

class BillRequest(BaseModel):
    monthly_kwh: float
    phase: str = "1-phase"

@router.post("/bill")
def calculate_bill(req: BillRequest):
    """Calculate KSEB bill for given monthly kWh and phase."""
    bill = calculate_kseb_bill(req.monthly_kwh, req.phase)  # type: ignore
    return {
        "billing_type":     bill.billing_type,
        "fixed_charge":     bill.fixed_charge,
        "energy_charge":    bill.energy_charge,
        "electricity_duty": bill.electricity_duty,
        "fuel_surcharge":   bill.fuel_surcharge,
        "meter_rent":       bill.meter_rent,
        "total":            bill.total,
        "effective_rate":   bill.effective_rate,
        "near_slab_cliff":  bill.near_slab_cliff,
        "cliff_savings":    bill.cliff_savings,
        "monthly_kwh":      bill.monthly_kwh,
        "slab_breakdown": [
            {"slab": s.slab, "units": s.units, "rate": s.rate, "cost": s.cost}
            for s in bill.slab_breakdown
        ],
    }


# ── Recommendations ───────────────────────────────────────────────────────────

class RecsRequest(BaseModel):
    monthly_kwh: float

@router.post("/recommendations")
def recommendations(req: RecsRequest):
    return {"recommendations": get_smart_recommendations(req.monthly_kwh)}


# ── Insights ──────────────────────────────────────────────────────────────────

class InsightsRequest(BaseModel):
    profile: EnergyProfile

@router.post("/insights")
def insights(req: InsightsRequest):
    daily_kwh = compute_daily_kwh(req.profile.appliances)
    breakdown = compute_appliance_breakdown(req.profile.appliances, daily_kwh)
    return {"insights": get_efficiency_insights(breakdown)}


# ── Simulator ────────────────────────────────────────────────────────────────-

class SimulatorRequest(BaseModel):
    base_monthly_kwh: float
    new_monthly_kwh: float
    solar_kw: float = 0
    virtual_battery: bool = False
    phase: str = "1-phase"

SOLAR_GENERATION_PER_KW = 4   # kWh/kW/day for Kerala
CO2_PER_UNIT = 0.82            # kg CO2 per kWh (India grid)

SOLAR_COSTS = {
    1: {"total_cost": 65000,  "subsidy": 30000, "net_cost": 35000},
    2: {"total_cost": 120000, "subsidy": 60000, "net_cost": 60000},
    3: {"total_cost": 180000, "subsidy": 78000, "net_cost": 102000},
    5: {"total_cost": 300000, "subsidy": 78000, "net_cost": 222000},
}

@router.post("/simulator")
def simulator(req: SimulatorRequest):
    base_bill = calculate_kseb_bill(req.base_monthly_kwh, req.phase)  # type: ignore
    new_bill  = calculate_kseb_bill(req.new_monthly_kwh, req.phase)   # type: ignore

    solar_monthly_gen = req.solar_kw * SOLAR_GENERATION_PER_KW * 30
    battery_bonus     = solar_monthly_gen * 0.15 if req.virtual_battery else 0
    effective_solar   = min(req.new_monthly_kwh, solar_monthly_gen + battery_bonus)
    net_kwh           = max(0, req.new_monthly_kwh - effective_solar)
    solar_bill        = calculate_kseb_bill(net_kwh, req.phase) if req.solar_kw > 0 else None  # type: ignore

    savings    = base_bill.total - new_bill.total
    co2_saved  = round((req.base_monthly_kwh - req.new_monthly_kwh) * CO2_PER_UNIT, 2)

    # Find closest solar panel size
    solar_info = None
    if req.solar_kw > 0:
        sizes = sorted(SOLAR_COSTS.keys())
        closest = min(sizes, key=lambda s: abs(s - req.solar_kw))
        sc = SOLAR_COSTS[closest]
        monthly_solar_savings = base_bill.total - (solar_bill.total if solar_bill else new_bill.total)
        payback_months = sc["net_cost"] / monthly_solar_savings if monthly_solar_savings > 0 else None
        solar_info = {
            **sc,
            "size_kw": closest,
            "monthly_generation_kwh": round(solar_monthly_gen),
            "payback_months": round(payback_months) if payback_months else None,
        }

    return {
        "base_bill":  {"total": base_bill.total, "billing_type": base_bill.billing_type, "monthly_kwh": base_bill.monthly_kwh},
        "new_bill":   {"total": new_bill.total,  "billing_type": new_bill.billing_type,  "monthly_kwh": new_bill.monthly_kwh},
        "solar_bill": {"total": solar_bill.total, "billing_type": solar_bill.billing_type} if solar_bill else None,
        "savings":    round(savings),
        "co2_saved":  co2_saved,
        "solar_info": solar_info,
    }


# ── Tariff reference ──────────────────────────────────────────────────────────

@router.get("/tariff")
def tariff_info():
    return {
        "telescopic_limit":    TELESCOPIC_LIMIT,
        "telescopic_slabs":    TELESCOPIC_SLABS,
        "non_telescopic_slabs": [
            {**s, "to": str(s["to"]) if s["to"] == float("inf") else s["to"]}
            for s in NON_TELESCOPIC_SLABS
        ],
        "age_options":         AGE_OPTIONS,
    }
