# WattWise — Python/FastAPI Backend

Python conversion of the Lovable/React **WattWise** project — a Kerala KSEB
electricity tracker with bill calculation, appliance management, AI coaching,
and multi-profile KSEB portal sync.

---

## Project structure

```
wattt-python/
├── app/
│   ├── main.py                  ← FastAPI app entry point
│   ├── models/
│   │   └── schemas.py           ← Pydantic models (ApplianceInput, EnergyProfile, …)
│   ├── services/
│   │   ├── kseb_tariff.py       ← KSEB bill calculator (port of ksebTariff.ts)
│   │   ├── energy_service.py    ← Energy profile logic (port of useEnergyProfile.ts)
│   │   └── supabase_client.py   ← Supabase Python client
│   └── routers/
│       ├── energy.py            ← /api/energy/* — bill calc, simulator, recommendations
│       ├── auth.py              ← /api/auth/*   — signup, login, profile
│       ├── profiles.py          ← /api/profiles/* — KSEB profiles + bill history
│       └── chat.py              ← /api/chat     — streaming AI energy coach
├── requirements.txt
├── .env.example
└── README.md
```

---

## What maps to what

| Original (TypeScript / React)       | Python equivalent                          |
|-------------------------------------|--------------------------------------------|
| `src/lib/ksebTariff.ts`             | `app/services/kseb_tariff.py`              |
| `src/hooks/useEnergyProfile.ts`     | `app/services/energy_service.py`           |
| `src/contexts/AuthContext.tsx`      | `app/routers/auth.py`                      |
| `src/pages/Index.tsx`               | `GET /api/energy/summary`                  |
| `src/pages/Appliances.tsx`          | `POST /api/energy/insights`                |
| `src/pages/Simulator.tsx`           | `POST /api/energy/simulator`               |
| `src/pages/Predictions.tsx`         | `POST /api/energy/bill`                    |
| `src/pages/Chat.tsx`                | `POST /api/chat`                           |
| `src/components/dashboard/ProfileSwitcher` | `GET/POST /api/profiles`          |
| Supabase edge function `chat`       | `app/routers/chat.py` (OpenAI streaming)   |
| Supabase migrations                 | Use same SQL against your Supabase project |

---

## Setup

### 1. Clone & install

```bash
cd wattt-python
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in your SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY
```

Your `.env` values come straight from the original project's `.env` file:

```
SUPABASE_URL  = VITE_SUPABASE_URL
SUPABASE_KEY  = VITE_SUPABASE_PUBLISHABLE_KEY
OPENAI_API_KEY = (get from platform.openai.com)
```

### 3. Run

```bash
uvicorn app.main:app --reload
```

API is now live at **http://localhost:8000**
Interactive docs at **http://localhost:8000/docs**

---

## API Reference

### Energy

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/energy/summary` | Full energy summary (bill + hourly + breakdown) |
| POST | `/api/energy/bill` | Calculate KSEB bill for any kWh + phase |
| POST | `/api/energy/recommendations` | Smart saving recommendations |
| POST | `/api/energy/insights` | Appliance efficiency alerts |
| POST | `/api/energy/simulator` | Bill comparison + solar ROI calculator |
| GET  | `/api/energy/tariff` | KSEB slab reference data |

### Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/signup` | Register new user |
| POST | `/api/auth/login` | Login, returns JWT token |
| POST | `/api/auth/logout` | Logout |
| POST | `/api/auth/reset-password` | Send password reset email |
| GET  | `/api/auth/profile` | Get user profile |
| PUT  | `/api/auth/profile` | Update display name / avatar |

### KSEB Profiles

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/api/profiles` | List all KSEB profiles |
| POST   | `/api/profiles` | Create a new profile |
| PUT    | `/api/profiles/{id}` | Update profile |
| DELETE | `/api/profiles/{id}` | Delete profile |
| POST   | `/api/profiles/{id}/activate` | Set as active profile |
| GET    | `/api/profiles/{id}/bills` | Bill history (up to 24 months) |
| POST   | `/api/profiles/{id}/bills` | Add a bill record |
| GET    | `/api/profiles/{id}/sync` | Trigger KSEB portal sync |

### Chat

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Streaming SSE AI energy coach (OpenAI) |

---

## Example: Calculate a bill

```bash
curl -X POST http://localhost:8000/api/energy/bill \
  -H "Content-Type: application/json" \
  -d '{"monthly_kwh": 280, "phase": "1-phase"}'
```

```json
{
  "billing_type": "non-telescopic",
  "fixed_charge": 110,
  "energy_charge": 1792,
  "electricity_duty": 179,
  "fuel_surcharge": 42,
  "meter_rent": 20,
  "total": 2143,
  "effective_rate": 7.65,
  "near_slab_cliff": false,
  "cliff_savings": 278,
  "monthly_kwh": 280,
  "slab_breakdown": [
    {"slab": "1–280 (flat)", "units": 280, "rate": 6.40, "cost": 1792}
  ]
}
```

## Example: Energy summary

```bash
curl -X POST http://localhost:8000/api/energy/summary \
  -H "Content-Type: application/json" \
  -d '{
    "phase": "1-phase",
    "appliances": [
      {"id":"ac","name":"Air Conditioner","icon":"❄️","hours_per_day":8,
       "wattage":1.5,"color":"hsl(200,90%,55%)","star_rating":3,"age":"3-5"}
    ],
    "is_configured": true
  }'
```

---

## Database

The Supabase database schema is identical to the original project. Run the SQL
migrations in your Supabase project under **SQL Editor**:

- `supabase/migrations/20260403211811_*.sql` — creates `profiles` table
- `supabase/migrations/20260406024939_*.sql` — creates `kseb_profiles` + `bill_history`
- `supabase/migrations/20260406141542_*.sql` — additional policies

These files are in the original `wattt-main.zip` you downloaded.

---

## KSEB Tariff (FY 2025-26)

### Telescopic (≤ 250 units/month)
| Slab | Rate |
|------|------|
| 0–50 units | ₹3.35/unit |
| 51–100 units | ₹4.25/unit |
| 101–150 units | ₹5.35/unit |
| 151–200 units | ₹7.20/unit |
| 201–250 units | ₹8.50/unit |

### Non-Telescopic (> 250 units/month — flat rate on ALL units)
| Range | Rate |
|-------|------|
| 251–300 | ₹6.40/unit |
| 301–350 | ₹7.25/unit |
| 351–400 | ₹7.80/unit |
| 401–500 | ₹8.20/unit |
| 501+ | ₹9.20/unit |

> ⚠️ Crossing the 250-unit threshold applies the flat rate to **all** units, not just those above 250. Dropping back below 250 can save hundreds of rupees per month.

---

## Streamlit UI (Visual App)

This is the easiest way to run WattWise with a full visual dashboard.

### Run the Streamlit app

```bash
streamlit run streamlit_app.py
```

Opens automatically at **http://localhost:8501**

### Pages

| Page | What it does |
|------|-------------|
| 🏠 Dashboard | Live bill overview, hourly usage chart, appliance donut, AI recommendations |
| 🔌 Appliances | Edit appliances, star ratings, age — see efficiency alerts |
| 📊 Bill Calculator | Slider-based bill calculator with slab breakdown + rate curve chart |
| 🎛️ Simulator | Compare scenarios, solar ROI, break-even chart |
| 💬 AI Coach | Chat with AI energy coach (needs OpenAI key) |

### Streamlit files

```
streamlit_app.py        ← entry point (run this)
pages_ui/
  dashboard.py          ← Dashboard page
  appliances.py         ← Appliances page
  bill_calculator.py    ← Bill Calculator page
  simulator.py          ← Simulator page
  chat.py               ← AI Chat page
```
