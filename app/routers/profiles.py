"""
KSEB Profiles & Bill History routes
GET    /api/profiles                 — list user's KSEB profiles
POST   /api/profiles                 — create a new KSEB profile
PUT    /api/profiles/{id}            — update profile
DELETE /api/profiles/{id}            — delete profile
POST   /api/profiles/{id}/activate   — set as active profile
GET    /api/profiles/{id}/bills      — get bill history for a profile
POST   /api/profiles/{id}/bills      — add a bill history record
GET    /api/profiles/{id}/sync       — manual sync from KSEB portal
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional

from app.services.supabase_client import get_supabase

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


def get_token(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return authorization.split(" ", 1)[1]


def get_user_id(token: str = Depends(get_token)) -> str:
    sb = get_supabase()
    user = sb.auth.get_user(token)
    if not user or not user.user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user.user.id


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateProfileRequest(BaseModel):
    consumer_number: str
    nickname: str = "Home"
    mobile_number: Optional[str] = None
    section_code: Optional[str] = None

class UpdateProfileRequest(BaseModel):
    nickname: Optional[str] = None
    mobile_number: Optional[str] = None
    section_code: Optional[str] = None

class AddBillRequest(BaseModel):
    bill_month: str
    units_consumed: float
    energy_charge: float = 0
    fixed_charge: float = 0
    meter_rent: float = 0
    electricity_duty: float = 0
    fuel_surcharge: float = 0
    total_amount: float
    billing_period: str = "2 Months"


# ── KSEB Profiles ─────────────────────────────────────────────────────────────

@router.get("")
def list_profiles(user_id: str = Depends(get_user_id)):
    sb = get_supabase()
    res = (
        sb.table("kseb_profiles")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at")
        .execute()
    )
    return {"profiles": res.data}


@router.post("")
def create_profile(req: CreateProfileRequest, user_id: str = Depends(get_user_id)):
    sb = get_supabase()
    # If first profile, make it active
    existing = sb.table("kseb_profiles").select("id").eq("user_id", user_id).execute()
    is_first = len(existing.data) == 0

    res = (
        sb.table("kseb_profiles")
        .insert({
            "user_id":         user_id,
            "consumer_number": req.consumer_number,
            "nickname":        req.nickname,
            "mobile_number":   req.mobile_number,
            "section_code":    req.section_code,
            "is_active":       is_first,
        })
        .execute()
    )
    return {"profile": res.data[0] if res.data else None}


@router.put("/{profile_id}")
def update_profile(
    profile_id: str,
    req: UpdateProfileRequest,
    user_id: str = Depends(get_user_id),
):
    sb = get_supabase()
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    res = (
        sb.table("kseb_profiles")
        .update(updates)
        .eq("id", profile_id)
        .eq("user_id", user_id)
        .execute()
    )
    return {"profile": res.data[0] if res.data else None}


@router.delete("/{profile_id}")
def delete_profile(profile_id: str, user_id: str = Depends(get_user_id)):
    sb = get_supabase()
    sb.table("kseb_profiles").delete().eq("id", profile_id).eq("user_id", user_id).execute()
    return {"message": "Profile deleted"}


@router.post("/{profile_id}/activate")
def activate_profile(profile_id: str, user_id: str = Depends(get_user_id)):
    sb = get_supabase()
    # Deactivate all
    sb.table("kseb_profiles").update({"is_active": False}).eq("user_id", user_id).execute()
    # Activate selected
    sb.table("kseb_profiles").update({"is_active": True}).eq("id", profile_id).eq("user_id", user_id).execute()
    return {"message": "Profile activated"}


# ── Bill History ──────────────────────────────────────────────────────────────

@router.get("/{profile_id}/bills")
def get_bills(profile_id: str, user_id: str = Depends(get_user_id)):
    sb = get_supabase()
    # Verify ownership
    prof = (
        sb.table("kseb_profiles")
        .select("id")
        .eq("id", profile_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not prof.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    res = (
        sb.table("bill_history")
        .select("*")
        .eq("profile_id", profile_id)
        .order("bill_month", desc=False)
        .limit(24)
        .execute()
    )
    return {"bills": res.data}


@router.post("/{profile_id}/bills")
def add_bill(profile_id: str, req: AddBillRequest, user_id: str = Depends(get_user_id)):
    sb = get_supabase()
    # Verify ownership
    prof = (
        sb.table("kseb_profiles")
        .select("id")
        .eq("id", profile_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not prof.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    res = (
        sb.table("bill_history")
        .insert({
            "profile_id":       profile_id,
            "bill_month":       req.bill_month,
            "units_consumed":   req.units_consumed,
            "energy_charge":    req.energy_charge,
            "fixed_charge":     req.fixed_charge,
            "meter_rent":       req.meter_rent,
            "electricity_duty": req.electricity_duty,
            "fuel_surcharge":   req.fuel_surcharge,
            "total_amount":     req.total_amount,
            "billing_period":   req.billing_period,
        })
        .execute()
    )
    return {"bill": res.data[0] if res.data else None}


@router.get("/{profile_id}/sync")
def sync_bills(profile_id: str, user_id: str = Depends(get_user_id)):
    """
    Manual sync trigger — fetches latest bill data from KSEB portal.
    In production this would call the KSEB web scraper service.
    Returns a placeholder response indicating sync was triggered.
    """
    sb = get_supabase()
    prof = (
        sb.table("kseb_profiles")
        .select("consumer_number, mobile_number")
        .eq("id", profile_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    if not prof.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    return {
        "message": "Sync triggered",
        "consumer_number": prof.data.get("consumer_number"),
        "note": "Connect the KSEB scraper service to populate bill data automatically.",
    }
