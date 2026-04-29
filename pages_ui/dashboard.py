import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from app.services.kseb_tariff import calculate_kseb_bill, TELESCOPIC_LIMIT
from app.services.energy_service import (
    compute_daily_kwh, compute_appliance_breakdown,
    generate_stochastic_profile, get_smart_recommendations,
)

def show():
    profile = st.session_state.profile

    # ── Header ────────────────────────────────────────────────────────────────
import datetime
import pytz

# Define the India timezone
ist = pytz.timezone('Asia/Kolkata')
now = datetime.datetime.now(ist)
hour = now.hour

# Determine the greeting based on India time
if hour < 12:
    greeting = "Good morning"
elif 12 <= hour < 17:
    greeting = "Good afternoon"
else:
    greeting = "Good evening"

st.title(f"{greeting} ⚡")    

    # ── Compute values ────────────────────────────────────────────────────────
    daily_kwh   = compute_daily_kwh(profile.appliances)
    monthly_kwh = profile.scanned_monthly_kwh or round(daily_kwh * 30)
    bill        = calculate_kseb_bill(monthly_kwh, profile.phase)
    today_cost  = round(daily_kwh * bill.effective_rate)
    hourly      = generate_stochastic_profile(daily_kwh, bill.effective_rate)
    peak_hour   = max(hourly, key=lambda h: h.kwh)
    breakdown   = compute_appliance_breakdown(profile.appliances, daily_kwh)

    # ── Phase selector ────────────────────────────────────────────────────────
    col_phase, col_kwh = st.columns([1, 2])
    with col_phase:
        phase = st.selectbox("Connection Phase", ["1-phase", "3-phase"],
                             index=0 if profile.phase == "1-phase" else 1)
        if phase != profile.phase:
            profile.phase = phase
            st.rerun()
    with col_kwh:
        scanned = st.number_input(
            "Override monthly units (kWh) — leave 0 to use appliance estimate",
            min_value=0, max_value=2000,
            value=int(profile.scanned_monthly_kwh or 0),
        )
        if scanned != (profile.scanned_monthly_kwh or 0):
            profile.scanned_monthly_kwh = float(scanned) if scanned > 0 else None
            st.rerun()

    # ── Metric cards ──────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        (c1, "Daily Usage",   f"{daily_kwh} kWh",             "Appliance estimate"),
        (c2, "Today's Cost",  f"₹{today_cost}",               "Estimated"),
        (c3, "Monthly Bill",  f"₹{bill.total:,}",             f"{monthly_kwh} kWh · {bill.billing_type}"),
        (c4, "Peak Hour",     peak_hour.hour,                  f"{peak_hour.kwh} kWh"),
    ]
    for col, label, val, sub in cards:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="label">{label}</div>
                <div class="value">{val}</div>
                <div class="sub">{sub}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Slab cliff warning ────────────────────────────────────────────────────
    if bill.near_slab_cliff:
        if bill.billing_type == "non-telescopic":
            st.markdown(f"""
            <div class="warn-banner">
            🚨 <strong>Non-Telescopic Rates Active!</strong><br>
            At {monthly_kwh} units you're above the {TELESCOPIC_LIMIT}-unit limit.
            Dropping {monthly_kwh - TELESCOPIC_LIMIT} units could save
            <strong>₹{bill.cliff_savings}/month</strong>.
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="info-banner">
            ⚠️ <strong>Near Slab Cliff</strong> — You're at {monthly_kwh} units,
            just {TELESCOPIC_LIMIT - monthly_kwh} units from the Non-Telescopic cliff.
            </div>""", unsafe_allow_html=True)

    # ── Slab progress bar ─────────────────────────────────────────────────────
    st.markdown(f"**Slab progress** — {monthly_kwh} / {TELESCOPIC_LIMIT} telescopic limit")
    pct = min(monthly_kwh / TELESCOPIC_LIMIT, 1.0)
    bar_color = "#ef4444" if monthly_kwh > TELESCOPIC_LIMIT else ("#eab308" if pct > 0.85 else "#38bdf8")
    st.markdown(f"""
    <div style="background:#1e2d4a;border-radius:8px;height:12px;overflow:hidden;margin-bottom:6px">
      <div style="width:{min(pct*100,100):.1f}%;height:100%;background:{bar_color};border-radius:8px;transition:width 0.5s"></div>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:0.72rem;color:#475569">
      <span>0</span><span>250 units (cliff)</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts ────────────────────────────────────────────────────────────────
    col_chart, col_donut = st.columns([2, 1])

    with col_chart:
        st.markdown("**Hourly Usage Profile**")
        hours  = [h.hour for h in hourly]
        kwhs   = [h.kwh  for h in hourly]
        colors = ["#ef4444" if h.peak_status == "Peak"
                  else "#64748b" if h.peak_status == "Off-Peak"
                  else "#38bdf8" for h in hourly]
        fig = go.Figure(go.Bar(
            x=hours, y=kwhs, marker_color=colors,
            hovertemplate="%{x}<br>%{y:.2f} kWh<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#94a3b8", margin=dict(l=0,r=0,t=10,b=0),
            height=220, showlegend=False,
            xaxis=dict(showgrid=False, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#1e2d4a", tickfont=dict(size=9)),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_donut:
        st.markdown("**Appliance Share**")
        labels = [a["name"] for a in breakdown if a["kwh"] > 0]
        values = [a["kwh"]  for a in breakdown if a["kwh"] > 0]
        fig2 = go.Figure(go.Pie(
            labels=labels, values=values, hole=0.55,
            textinfo="percent", textfont_size=10,
            marker_colors=["#38bdf8","#22c55e","#f97316","#a855f7","#eab308","#06b6d4","#64748b"],
        ))
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", font_color="#94a3b8",
            margin=dict(l=0,r=0,t=10,b=0), height=220,
            legend=dict(font=dict(size=9), bgcolor="rgba(0,0,0,0)"),
            showlegend=True,
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # ── Recommendations ───────────────────────────────────────────────────────
    st.markdown("**AI Recommendations**")
    recs = get_smart_recommendations(monthly_kwh)
    for r in recs[:3]:
        dot_cls = "rec-dot-high" if r["impact"] == "high" else "rec-dot-medium"
        slab_tag = '<span class="slab-saver-tag">Slab Saver</span>' if r["slab_saver"] else ""
        st.markdown(f"""
        <div class="rec-row">
          <div class="{dot_cls}"></div>
          <div style="flex:1">
            <div class="rec-title">{r['title']} {slab_tag}</div>
            <div class="rec-save">Save ₹{r['savings']}/month</div>
          </div>
          <span style="font-size:0.72rem;color:#38bdf8;font-weight:600;text-transform:uppercase">{r['impact']}</span>
        </div>
        """, unsafe_allow_html=True)
