"""
WattWise Python Backend
FastAPI conversion of the Lovable/React project.

Run with:
    uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os

from app.routers import energy, auth, profiles, chat

app = FastAPI(
    title="WattWise API",
    description="Kerala KSEB Energy Tracker — Python/FastAPI backend",
    version="1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(energy.router)
app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(chat.router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "app": "WattWise API", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}
