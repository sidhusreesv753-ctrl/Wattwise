"""
Auth & Profile API routes
POST /api/auth/signup
POST /api/auth/login
POST /api/auth/logout
POST /api/auth/reset-password
GET  /api/auth/profile
PUT  /api/auth/profile
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional

from app.services.supabase_client import get_supabase

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_token(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return authorization.split(" ", 1)[1]


# ── Schemas ───────────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class ResetPasswordRequest(BaseModel):
    email: str

class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/signup")
def signup(req: SignupRequest):
    sb = get_supabase()
    options = {}
    if req.full_name:
        options["data"] = {"full_name": req.full_name}
    try:
        res = sb.auth.sign_up({"email": req.email, "password": req.password, "options": options})
        if res.user is None:
            raise HTTPException(status_code=400, detail="Signup failed")
        return {
            "user_id":      res.user.id,
            "email":        res.user.email,
            "access_token": res.session.access_token if res.session else None,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login")
def login(req: LoginRequest):
    sb = get_supabase()
    try:
        res = sb.auth.sign_in_with_password({"email": req.email, "password": req.password})
        if res.user is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {
            "user_id":       res.user.id,
            "email":         res.user.email,
            "access_token":  res.session.access_token,
            "refresh_token": res.session.refresh_token,
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
def logout(token: str = Depends(get_token)):
    sb = get_supabase()
    try:
        sb.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest):
    sb = get_supabase()
    try:
        sb.auth.reset_password_email(req.email)
        return {"message": "Password reset email sent"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/profile")
def get_profile(token: str = Depends(get_token)):
    sb = get_supabase()
    try:
        user = sb.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        profile = (
            sb.table("profiles")
            .select("display_name, avatar_url")
            .eq("user_id", user.user.id)
            .maybe_single()
            .execute()
        )
        return {
            "user_id":      user.user.id,
            "email":        user.user.email,
            "display_name": profile.data.get("display_name") if profile.data else None,
            "avatar_url":   profile.data.get("avatar_url")   if profile.data else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/profile")
def update_profile(req: UpdateProfileRequest, token: str = Depends(get_token)):
    sb = get_supabase()
    try:
        user = sb.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        sb.table("profiles").update(updates).eq("user_id", user.user.id).execute()
        return {"message": "Profile updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
