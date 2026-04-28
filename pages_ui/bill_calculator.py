import streamlit as st
import plotly.graph_objects as go
from app.services.kseb_tariff import (
    calculate_kseb_bill, TELESCOPIC_SLABS, NON_TELESCOPIC_SLABS, TELESCOPIC_LIMIT
)

def show():
    st.markdown('<div class="section-title">📊 Bill Calculator</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Calculate your exact KSEB bill for any usage</div>', unsafe_allow_html=True)

    # ── Inputs ────────────────────────────────────────────────────────────────
    col1, col2 = st.columns([2, 1])
    with col1:
        units = st.slider("Monthly units (kWh)", min_value=0, max_value=800,
                          value=200, step=5)
    with col2:
        phase = st.selectbox("Phase", ["1-phase", "3-phase"])

    bill = calculate_kseb_bill(units, phase)

    # ── Warning ───────────────────────────────────────────────────────────────
    if bill.near_slab_cliff:
        if bill.billing_type == "non-telescopic":
            st.markdown(f"""
            <div class="warn-banner">
            🚨 <strong>Non-Telescopic Active!</strong> You're {units - TELESCOPIC_LIMIT} units above the cliff.
            Dropping to 250 units saves <strong>₹{bill.cliff_savings}</strong> this month.
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="info-banner">
            ⚠️ Only <strong>{TELESCOPIC_LIMIT - units} units</strong> away from the Non-Telescopic cliff!
            </div>""", unsafe_allow_html=True)

    # ── Bill summary ──────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    pill = ('<span class="pill-telescopic">Telescopic</span>'
            if bill.billing_type == "telescopic"
            else '<span class="pill-nontelescopic">Non-Telescopic</span>')
    st.markdown(f"**Estimated Bill** &nbsp; {pill}", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"""
    <div class="metric-card">
        <div class="label">Total Bill</div>
        <div class="value">₹{bill.total:,}</div>
        <div class="sub">{units} kWh · {phase}</div>
    </div>""", unsafe_allow_html=True)
    c2.markdown(f"""
    <div class="metric-card">
        <div class="label">Effective Rate</div>
        <div class="value">₹{bill.effective_rate}</div>
        <div class="sub">per unit</div>
    </div>""", unsafe_allow_html=True)
    c3.markdown(f"""
    <div class="metric-card">
        <div class="label">Energy Charge</div>
        <div class="value">₹{bill.energy_charge:,}</div>
        <div class="sub">excl. fixed & duty</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Bill breakdown ────────────────────────────────────────────────────────
    col_break, col_chart = st.columns([1, 1])

    with col_break:
        st.markdown("**Bill Breakdown**")
        items = [
            ("Fixed Charge",      bill.fixed_charge),
            ("Energy Charge",     bill.energy_charge),
            ("Electricity Duty",  bill.electricity_duty),
            ("Fuel Surcharge",    bill.fuel_surcharge),
            ("Meter Rent",        bill.meter_rent),
        ]
        for label, amount in items:
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;padding:8px 0;
                        border-bottom:1px solid #1e2d4a;font-size:0.88rem">
              <span style="color:#94a3b8">{label}</span>
              <span style="color:#e2e8f0;font-weight:600">₹{amount:,}</span>
            </div>""", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;padding:10px 0;font-size:1rem">
          <span style="color:#38bdf8;font-weight:700">Total</span>
          <span style="color:#38bdf8;font-weight:700">₹{bill.total:,}</span>
        </div>""", unsafe_allow_html=True)

    with col_chart:
        st.markdown("**Slab Breakdown**")
        slab_labels = [s.slab for s in bill.slab_breakdown]
        slab_costs  = [s.cost for s in bill.slab_breakdown]
        fig = go.Figure(go.Bar(
            x=slab_labels, y=slab_costs,
            marker_color="#38bdf8",
            text=[f"₹{c}" for c in slab_costs],
            textposition="outside",
            textfont=dict(color="#94a3b8", size=10),
            hovertemplate="%{x}<br>₹%{y}<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#94a3b8", margin=dict(l=0,r=0,t=10,b=0),
            height=250, showlegend=False,
            xaxis=dict(showgrid=False, tickfont=dict(size=9)),
            yaxis=dict(showgrid=True, gridcolor="#1e2d4a", tickfont=dict(size=9)),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Rate curve ────────────────────────────────────────────────────────────
    st.markdown("**Effective Rate Curve** — how your rate changes with usage")
    x_vals = list(range(10, 601, 5))
    y_vals = [calculate_kseb_bill(u, phase).effective_rate for u in x_vals]
    cliff_x = [TELESCOPIC_LIMIT, TELESCOPIC_LIMIT]
    cliff_y = [min(y_vals), max(y_vals)]

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=x_vals, y=y_vals, mode="lines",
        line=dict(color="#38bdf8", width=2),
        fill="tozeroy", fillcolor="rgba(56,189,248,0.08)",
        name="Effective rate",
        hovertemplate="%{x} kWh → ₹%{y}/unit<extra></extra>",
    ))
    fig3.add_shape(type="line", x0=TELESCOPIC_LIMIT, x1=TELESCOPIC_LIMIT,
                   y0=0, y1=max(y_vals),
                   line=dict(color="#ef4444", width=1.5, dash="dash"))
    fig3.add_annotation(x=TELESCOPIC_LIMIT, y=max(y_vals)*0.95,
                        text="250 unit cliff", showarrow=False,
                        font=dict(color="#ef4444", size=10))
    # Mark current usage
    cur_rate = calculate_kseb_bill(units, phase).effective_rate
    fig3.add_trace(go.Scatter(
        x=[units], y=[cur_rate], mode="markers",
        marker=dict(color="#f97316", size=10),
        name=f"You ({units} kWh)",
        hovertemplate=f"{units} kWh → ₹{cur_rate}/unit<extra></extra>",
    ))
    fig3.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#94a3b8", margin=dict(l=0,r=10,t=10,b=0),
        height=240, legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9)),
        xaxis=dict(title="Monthly kWh", showgrid=False, tickfont=dict(size=9)),
        yaxis=dict(title="₹/unit", showgrid=True, gridcolor="#1e2d4a", tickfont=dict(size=9)),
    )
    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

    # ── Tariff reference ──────────────────────────────────────────────────────
    with st.expander("📋 KSEB Tariff Reference FY 2025-26"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Telescopic Slabs (≤ 250 units)**")
            for s in TELESCOPIC_SLABS:
                st.markdown(f"• {s['from']}–{s['to']} units → ₹{s['rate']}/unit")
        with c2:
            st.markdown("**Non-Telescopic Flat Rates (> 250 units)**")
            for s in NON_TELESCOPIC_SLABS:
                to = "∞" if s["to"] == float("inf") else s["to"]
                st.markdown(f"• {s['from']}–{to} units → ₹{s['rate']}/unit (on ALL units)")
