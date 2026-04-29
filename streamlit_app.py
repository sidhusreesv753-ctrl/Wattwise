"""
WattWise — Streamlit UI
Kerala KSEB Energy Tracker
Run: streamlit run streamlit_app.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

st.set_page_config(
    page_title="WattWise ⚡",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}

/* Dark theme base */
.stApp {
    background: #0a0f1e;
    color: #e2e8f0;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0d1424 !important;
    border-right: 1px solid #1e2d4a;
}
[data-testid="stSidebar"] .stRadio label {
    color: #94a3b8 !important;
    font-size: 0.92rem;
    padding: 6px 0;
}
[data-testid="stSidebar"] .stRadio label:hover { color: #38bdf8 !important; }

/* Metric cards */
.metric-card {
    background: linear-gradient(135deg, #111827 0%, #1a2540 100%);
    border: 1px solid #1e3a5f;
    border-radius: 16px;
    padding: 20px 24px;
    text-align: center;
    transition: border-color 0.2s;
}
.metric-card:hover { border-color: #38bdf8; }
.metric-card .label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #64748b;
    margin-bottom: 6px;
}
.metric-card .value {
    font-size: 2rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    color: #38bdf8;
}
.metric-card .sub {
    font-size: 0.72rem;
    color: #475569;
    margin-top: 4px;
}

/* Warning / info banners */
.warn-banner {
    background: rgba(239,68,68,0.08);
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 12px;
    padding: 14px 18px;
    margin: 8px 0;
}
.info-banner {
    background: rgba(56,189,248,0.06);
    border: 1px solid rgba(56,189,248,0.25);
    border-radius: 12px;
    padding: 14px 18px;
    margin: 8px 0;
}

/* Section headers */
.section-title {
    font-size: 1.4rem;
    font-weight: 700;
    color: #e2e8f0;
    margin-bottom: 4px;
}
.section-sub {
    font-size: 0.82rem;
    color: #64748b;
    margin-bottom: 20px;
}

/* Appliance card */
.appliance-card {
    background: #111827;
    border: 1px solid #1e2d4a;
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 12px;
    transition: border-color 0.2s;
}
.appliance-card:hover { border-color: #38bdf8; }

/* Slab pill */
.pill-telescopic {
    background: rgba(56,189,248,0.12);
    color: #38bdf8;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.75rem;
    font-weight: 600;
    display: inline-block;
}
.pill-nontelescopic {
    background: rgba(239,68,68,0.12);
    color: #ef4444;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.75rem;
    font-weight: 600;
    display: inline-block;
}

/* Progress bar override */
.stProgress > div > div { background-color: #38bdf8 !important; }

/* Chat bubbles */
.bubble-user {
    background: #1d4ed8;
    color: white;
    border-radius: 18px 18px 4px 18px;
    padding: 10px 16px;
    margin: 4px 0;
    max-width: 78%;
    margin-left: auto;
    font-size: 0.9rem;
}
.bubble-ai {
    background: #1e2d4a;
    color: #e2e8f0;
    border-radius: 18px 18px 18px 4px;
    padding: 10px 16px;
    margin: 4px 0;
    max-width: 78%;
    font-size: 0.9rem;
}

/* Recommendation row */
.rec-row {
    display: flex;
    align-items: center;
    gap: 14px;
    background: #111827;
    border: 1px solid #1e2d4a;
    border-radius: 12px;
    padding: 12px 16px;
    margin-bottom: 8px;
}
.rec-dot-high  { width:8px; height:36px; border-radius:4px; background:#22c55e; flex-shrink:0; }
.rec-dot-medium{ width:8px; height:36px; border-radius:4px; background:#eab308; flex-shrink:0; }
.rec-title { font-weight:600; font-size:0.88rem; color:#e2e8f0; }
.rec-save  { font-size:0.75rem; color:#64748b; margin-top:2px; }
.slab-saver-tag {
    background: rgba(239,68,68,0.12); color:#ef4444;
    border-radius:10px; padding:2px 8px; font-size:0.7rem; font-weight:700;
}

/* Inputs */
.stNumberInput input, .stSelectbox select, .stTextInput input {
    background: #111827 !important;
    border: 1px solid #1e2d4a !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
}
.stButton button {
    background: linear-gradient(135deg, #0ea5e9, #38bdf8) !important;
    color: #0a0f1e !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 10px !important;
}
.stButton button:hover { opacity: 0.9 !important; }

/* Hide streamlit branding */
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Session state defaults ────────────────────────────────────────────────────
from app.models.schemas import DEFAULT_APPLIANCES, EnergyProfile

if "profile" not in st.session_state:
    st.session_state.profile = EnergyProfile(
        phase="1-phase",
        appliances=list(DEFAULT_APPLIANCES),
        is_configured=False,
    )
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {"role": "assistant", "content": "Hi! I'm your WattWise AI Energy Coach ⚡ Ask me anything about your KSEB bill, appliances, or savings tips!"}
    ]

# ── Sidebar navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ WattWise")
    st.markdown("<div style='color:#64748b;font-size:0.78rem;margin-bottom:20px'>Kerala Energy Tracker</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("<div style='color:#475569;font-size:0.72rem'>KSEB Tariff FY 2025-26</div>", unsafe_allow_html=True)
    st.markdown("<div style='color:#475569;font-size:0.72rem'>Telescopic ≤ 250 units</div>", unsafe_allow_html=True)
    st.markdown("<div style='color:#475569;font-size:0.72rem'>Non-Telescopic > 250 units</div>", unsafe_allow_html=True)

# ── Page routing ──────────────────────────────────────────────────────────────
if page == "🏠 Dashboard":
    from pages_ui.dashboard import show
elif page == "🔌 Appliances":
    from pages_ui.appliances import show
elif page == "📊 Bill Calculator":
    from pages_ui.bill_calculator import show
elif page == "🎛️ Simulator":
    from pages_ui.simulator import show
elif page == "💬 AI Coach":
    from pages_ui.chat import show

show()
