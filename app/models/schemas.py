from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field
import uuid

ApplianceAge = Literal["new", "3-5", "5-10", "10+"]
PhaseType    = Literal["1-phase", "3-phase"]

AGE_DEGRADATION: dict[ApplianceAge, float] = {
    "new":  1.00,
    "3-5":  1.05,
    "5-10": 1.15,
    "10+":  1.25,
}

AGE_OPTIONS = [
    {"value": "new",  "label": "New (2024+)"},
    {"value": "3-5",  "label": "3-5 Years Old"},
    {"value": "5-10", "label": "5-10 Years Old"},
    {"value": "10+",  "label": "10+ Years Old"},
]


class ApplianceInput(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    icon: str
    hours_per_day: float
    wattage: float          # kW
    color: str
    star_rating: int = 3   # 1-5 BEE star rating
    age: ApplianceAge = "3-5"


DEFAULT_APPLIANCES: list[ApplianceInput] = [
    ApplianceInput(id="ac",      name="Air Conditioner",   icon="❄️",  hours_per_day=8,    wattage=1.5,   color="hsl(200,90%,55%)",  star_rating=3, age="3-5"),
    ApplianceInput(id="fridge",  name="Refrigerator",      icon="🧊",  hours_per_day=24,   wattage=0.25,  color="hsl(168,80%,50%)",  star_rating=4, age="3-5"),
    ApplianceInput(id="heater",  name="Water Heater",      icon="🔥",  hours_per_day=3,    wattage=1.6,   color="hsl(25,95%,55%)",   star_rating=3, age="3-5"),
    ApplianceInput(id="washer",  name="Washing Machine",   icon="🫧",  hours_per_day=1.5,  wattage=2.0,   color="hsl(270,70%,60%)",  star_rating=3, age="3-5"),
    ApplianceInput(id="fans",    name="Ceiling Fans",      icon="🌀",  hours_per_day=12,   wattage=0.075, color="hsl(45,95%,60%)",   star_rating=5, age="5-10"),
    ApplianceInput(id="lights",  name="Lighting",          icon="💡",  hours_per_day=8,    wattage=0.1,   color="hsl(45,95%,60%)",   star_rating=4, age="3-5"),
    ApplianceInput(id="others",  name="Others",            icon="🔌",  hours_per_day=4,    wattage=0.3,   color="hsl(215,12%,50%)",  star_rating=3, age="3-5"),
]


class EnergyProfile(BaseModel):
    phase: PhaseType = "1-phase"
    appliances: list[ApplianceInput] = Field(default_factory=lambda: list(DEFAULT_APPLIANCES))
    is_configured: bool = False
    consumer_number: Optional[str] = None
    billing_period: Optional[str] = None
    section_office: Optional[str] = None
    scanned_monthly_kwh: Optional[float] = None


class ApplianceBreakdown(ApplianceInput):
    kwh: float
    percentage: float


class HourlyUsage(BaseModel):
    hour: str
    kwh: float
    cost: float
    peak_status: str


# ── Request/Response schemas ──────────────────────────────────────────────────

class UpdateApplianceRequest(BaseModel):
    hours_per_day: Optional[float] = None
    wattage: Optional[float] = None
    star_rating: Optional[int] = None
    age: Optional[ApplianceAge] = None
    name: Optional[str] = None


class BillScanData(BaseModel):
    monthly_kwh: float
    consumer_number: Optional[str] = None
    billing_period: Optional[str] = None
    section_office: Optional[str] = None


class ProfileResponse(BaseModel):
    profile: EnergyProfile
    daily_kwh: float
    monthly_kwh: float
    bill: dict
    appliance_breakdown: list[dict]
    hourly_usage: list[dict]


# ── Supabase / DB models ──────────────────────────────────────────────────────

class KSEBProfile(BaseModel):
    id: str
    user_id: str
    nickname: str = "Home"
    consumer_number: str
    mobile_number: Optional[str] = None
    section_code: Optional[str] = None
    is_active: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class BillHistory(BaseModel):
    id: str
    profile_id: str
    bill_month: str
    units_consumed: float
    energy_charge: float
    fixed_charge: float
    meter_rent: float
    electricity_duty: float
    fuel_surcharge: float
    total_amount: float
    billing_period: str = "2 Months"
    synced_at: Optional[str] = None


class UserProfile(BaseModel):
    id: str
    user_id: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
