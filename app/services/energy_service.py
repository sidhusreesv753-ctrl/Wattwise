"""
Energy profile service — Python port of useEnergyProfile.ts
Handles appliance-based energy calculations, bill estimation,
and stochastic hourly load profile generation.
"""

import math
import random
from app.models.schemas import (
    ApplianceInput, ApplianceBreakdown, EnergyProfile, HourlyUsage,
    AGE_DEGRADATION, DEFAULT_APPLIANCES
)
from app.services.kseb_tariff import calculate_kseb_bill, KSEBBillResult


# ── Seeded pseudo-random (deterministic, matches JS implementation) ────────────
def _seeded_random(seed: int):
    s = seed
    def _next():
        nonlocal s
        s = (s * 16807) % 2_147_483_647
        return s / 2_147_483_647
    return _next


def generate_stochastic_profile(daily_kwh: float, effective_rate: float) -> list[HourlyUsage]:
    """
    Generate a realistic stochastic residential load profile.
    Total area under the curve equals daily_kwh.
    """
    rand = _seeded_random(42)

    shape_factors = [
        # 00-05: deep night
        0.25, 0.22, 0.20, 0.18, 0.20, 0.30,
        # 06-11: morning activity
        0.55, 0.80, 0.70, 0.50, 0.45, 0.40,
        # 12-17: afternoon
        0.50, 0.45, 0.42, 0.48, 0.55, 0.70,
        # 18-23: evening peak
        0.95, 1.00, 0.90, 0.75, 0.55, 0.35,
    ]

    raw_load = []
    for i, f in enumerate(shape_factors):
        spike = 0.0
        if rand() > 0.6:
            spike += rand() * 0.4
        if (6 <= i <= 8) or (18 <= i <= 20):
            if rand() > 0.5:
                spike += rand() * 0.6
        raw_load.append(f + spike)

    raw_sum = sum(raw_load)
    scale = daily_kwh / raw_sum if raw_sum > 0 else 0

    result = []
    for i, v in enumerate(raw_load):
        kwh = round(v * scale, 2)
        hour = f"{i:02d}:00"
        if 18 <= i < 22:
            peak_status = "Peak"
        elif i >= 22 or i < 6:
            peak_status = "Off-Peak"
        else:
            peak_status = "Normal"
        result.append(HourlyUsage(
            hour=hour,
            kwh=kwh,
            cost=round(kwh * effective_rate, 2),
            peak_status=peak_status,
        ))
    return result


# ── Core calculation helpers ──────────────────────────────────────────────────

def compute_daily_kwh(appliances: list[ApplianceInput]) -> float:
    total = 0.0
    for a in appliances:
        deg = AGE_DEGRADATION.get(a.age, 1.0)
        total += a.hours_per_day * a.wattage * deg
    return round(total, 2)


def compute_appliance_breakdown(
    appliances: list[ApplianceInput],
    daily_kwh: float
) -> list[dict]:
    breakdown = []
    for a in appliances:
        deg = AGE_DEGRADATION.get(a.age, 1.0)
        kwh = round(a.hours_per_day * a.wattage * deg, 2)
        pct = round((kwh / daily_kwh) * 100) if daily_kwh > 0 else 0
        d = a.model_dump()
        d["kwh"] = kwh
        d["percentage"] = pct
        breakdown.append(d)
    return breakdown


def get_energy_summary(profile: EnergyProfile) -> dict:
    """Return the full computed energy summary for a profile."""
    daily_kwh = compute_daily_kwh(profile.appliances)
    monthly_kwh = profile.scanned_monthly_kwh or round(daily_kwh * 30)
    bill = calculate_kseb_bill(monthly_kwh, profile.phase)
    appliance_breakdown = compute_appliance_breakdown(profile.appliances, daily_kwh)
    hourly_usage = generate_stochastic_profile(daily_kwh, bill.effective_rate)

    return {
        "profile": profile.model_dump(),
        "daily_kwh": daily_kwh,
        "monthly_kwh": monthly_kwh,
        "bill": {
            "billing_type":      bill.billing_type,
            "fixed_charge":      bill.fixed_charge,
            "energy_charge":     bill.energy_charge,
            "electricity_duty":  bill.electricity_duty,
            "fuel_surcharge":    bill.fuel_surcharge,
            "meter_rent":        bill.meter_rent,
            "total":             bill.total,
            "effective_rate":    bill.effective_rate,
            "near_slab_cliff":   bill.near_slab_cliff,
            "cliff_savings":     bill.cliff_savings,
            "monthly_kwh":       bill.monthly_kwh,
            "slab_breakdown": [
                {
                    "slab":  s.slab,
                    "units": s.units,
                    "rate":  s.rate,
                    "cost":  s.cost,
                }
                for s in bill.slab_breakdown
            ],
        },
        "appliance_breakdown": appliance_breakdown,
        "hourly_usage": [u.model_dump() for u in hourly_usage],
    }


# ── Recommendation engine (port of getSmartRecommendations) ──────────────────
from app.services.kseb_tariff import TELESCOPIC_LIMIT

def get_smart_recommendations(monthly_kwh: float) -> list[dict]:
    recs = [
        {"id": 1, "title": "Reduce AC by 1 hour daily",       "savings": 320, "impact": "high",   "category": "behavior",   "slab_saver": False},
        {"id": 2, "title": "Switch to LED lighting",           "savings": 180, "impact": "medium", "category": "upgrade",    "slab_saver": False},
        {"id": 3, "title": "Run washing machine off-peak",     "savings": 150, "impact": "medium", "category": "scheduling", "slab_saver": False},
        {"id": 4, "title": "Upgrade to 5-star fridge",         "savings": 450, "impact": "high",   "category": "upgrade",    "slab_saver": False},
        {"id": 5, "title": "Set AC to 24°C instead of 22°C",  "savings": 280, "impact": "high",   "category": "behavior",   "slab_saver": False},
    ]

    dist_to_cliff = monthly_kwh - TELESCOPIC_LIMIT
    if 0 < dist_to_cliff <= 80:
        recs[0]["slab_saver"] = True
        recs[0]["title"] = "Reduce AC by 1 hour daily — Slab Saver!"
        recs[4]["slab_saver"] = True
        recs[4]["title"] = "Set AC to 24°C — drop below 250 units!"
        recs.sort(key=lambda r: (not r["slab_saver"], -r["savings"]))
    else:
        recs.sort(key=lambda r: -r["savings"])

    return recs


# ── Efficiency insights (port of getEfficiencyInsights) ──────────────────────

def get_efficiency_insights(appliance_breakdown: list[dict]) -> list[dict]:
    insights = []
    for a in appliance_breakdown:
        deg = AGE_DEGRADATION.get(a["age"], 1.0)
        if deg > 1.1:
            extra_pct = round((deg - 1) * 100)
            new_kwh = round(a["hours_per_day"] * a["wattage"], 2)
            saving = round((a["kwh"] - new_kwh) * 30, 2)
            age_label = "10+ year old" if a["age"] == "10+" else f"{a['age']} year old"
            insights.append({
                "id": a["id"],
                "name": a["name"],
                "icon": a["icon"],
                "message": f"Your {age_label} {a['name']} is consuming ~{extra_pct}% extra energy",
                "savings_percent": extra_pct,
                "recommendation": f"Upgrading to a new 5-star model could save ~{saving} kWh/month",
            })
        if a["star_rating"] <= 2 and a["kwh"] > 0.5:
            insights.append({
                "id": a["id"] + "-star",
                "name": a["name"],
                "icon": a["icon"],
                "message": f"Your {a['name']} has only a {a['star_rating']}-star rating — below the 5-star benchmark",
                "savings_percent": round((5 - a["star_rating"]) * 8),
                "recommendation": "A 5-star rated replacement would be significantly more efficient",
            })
    return insights
