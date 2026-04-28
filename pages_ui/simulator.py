import streamlit as st
import plotly.graph_objects as go
from app.services.kseb_tariff import calculate_kseb_bill
from app.services.energy_service import compute_daily_kwh

SOLAR_COSTS = {
    1: {"total_cost": 65000,  "subsidy": 30000, "net_cost": 35000},
    2: {"total_cost": 120000, "subsidy": 60000, "net_cost": 60000},
    3: {"total_cost": 180000, "subsidy": 78000, "net_cost": 102000},
    5: {"total_cost": 300000, "subsidy": 78000, "net_cost": 222000},
}
SOLAR_GEN_PER_KW = 4   # kWh/kW/day Kerala average
CO2_PER_UNIT     = 0.82

def show():
    profile = st.session_state.profile

    st.markdown('<div class="section-title">🎛️ Bill Simulator</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Compare scenarios and explore solar ROI</div>', unsafe_allow_html=True)

    daily_kwh   = compute_daily_kwh(profile.appliances)
    monthly_kwh = profile.scanned_monthly_kwh or round(daily_kwh * 30)

    # ── Controls ──────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Baseline**")
        base_units = st.number_input("Current monthly kWh", min_value=0, max_value=1500,
                                     value=int(monthly_kwh), step=5)
        base_phase = st.selectbox("Phase", ["1-phase", "3-phase"], key="base_phase")

    with col2:
        st.markdown("**New Scenario**")
        new_units  = st.slider("Simulated monthly kWh", min_value=0, max_value=1500,
                               value=max(0, int(monthly_kwh) - 30), step=5)

    # ── Solar ─────────────────────────────────────────────────────────────────
    st.markdown("**☀️ Solar Panel Option**")
    sc1, sc2 = st.columns([2, 1])
    solar_kw = sc1.slider("Solar capacity (kW)", min_value=0, max_value=10, value=0, step=1)
    virt_bat = sc2.toggle("Virtual Battery (+15% yield)", value=False)

    # ── Calculations ──────────────────────────────────────────────────────────
    base_bill = calculate_kseb_bill(base_units, base_phase)
    new_bill  = calculate_kseb_bill(new_units, base_phase)

    solar_monthly = solar_kw * SOLAR_GEN_PER_KW * 30
    battery_bonus = solar_monthly * 0.15 if virt_bat else 0
    solar_offset  = min(new_units, solar_monthly + battery_bonus)
    net_units     = max(0, new_units - solar_offset)
    solar_bill    = calculate_kseb_bill(net_units, base_phase) if solar_kw > 0 else None

    savings_behaviour = base_bill.total - new_bill.total
    savings_solar     = base_bill.total - (solar_bill.total if solar_bill else new_bill.total)
    co2_saved         = round((base_units - new_units) * CO2_PER_UNIT, 1)

    # ── Results ───────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)

    def delta_color(val):
        return "#22c55e" if val > 0 else "#ef4444"

    c1.markdown(f"""
    <div class="metric-card">
        <div class="label">Baseline Bill</div>
        <div class="value">₹{base_bill.total:,}</div>
        <div class="sub">{base_units} kWh · {base_bill.billing_type}</div>
    </div>""", unsafe_allow_html=True)

    c2.markdown(f"""
    <div class="metric-card">
        <div class="label">New Bill</div>
        <div class="value">₹{new_bill.total:,}</div>
        <div class="sub">{new_units} kWh · {new_bill.billing_type}</div>
    </div>""", unsafe_allow_html=True)

    c3.markdown(f"""
    <div class="metric-card">
        <div class="label">Behaviour Savings</div>
        <div class="value" style="color:{delta_color(savings_behaviour)}">
          {'₹' + str(abs(savings_behaviour)) if savings_behaviour >= 0 else '-₹' + str(abs(savings_behaviour))}
        </div>
        <div class="sub">{'saved' if savings_behaviour >= 0 else 'extra'} per month</div>
    </div>""", unsafe_allow_html=True)

    c4.markdown(f"""
    <div class="metric-card">
        <div class="label">CO₂ Saved</div>
        <div class="value" style="color:#22c55e">{co2_saved} kg</div>
        <div class="sub">per month</div>
    </div>""", unsafe_allow_html=True)

    # ── Bill comparison chart ─────────────────────────────────────────────────
    st.markdown("<br>**Bill Comparison**")
    categories = ["Baseline", "Behaviour Change"]
    totals     = [base_bill.total, new_bill.total]
    colors     = ["#38bdf8", "#22c55e" if savings_behaviour >= 0 else "#ef4444"]
    if solar_kw > 0 and solar_bill:
        categories.append(f"Solar {solar_kw}kW")
        totals.append(solar_bill.total)
        colors.append("#a855f7")

    fig = go.Figure(go.Bar(
        x=categories, y=totals, marker_color=colors,
        text=[f"₹{t:,}" for t in totals],
        textposition="outside",
        textfont=dict(color="#94a3b8", size=11),
        hovertemplate="%{x}<br>₹%{y:,}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#94a3b8", margin=dict(l=0,r=0,t=30,b=0),
        height=280, showlegend=False,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#1e2d4a", tickprefix="₹"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Solar ROI ─────────────────────────────────────────────────────────────
    if solar_kw > 0:
        sizes    = sorted(SOLAR_COSTS.keys())
        closest  = min(sizes, key=lambda s: abs(s - solar_kw))
        sc       = SOLAR_COSTS[closest]
        monthly_save = base_bill.total - (solar_bill.total if solar_bill else new_bill.total)
        payback  = round(sc["net_cost"] / monthly_save) if monthly_save > 0 else "∞"
        payback_years = f"{payback // 12}y {payback % 12}m" if isinstance(payback, int) else payback

        st.markdown(f"""
        <div class="info-banner">
          <strong>☀️ Solar {closest}kW ROI (PM Surya Ghar subsidy applied)</strong><br>
          Total cost: ₹{sc['total_cost']:,} &nbsp;|&nbsp;
          Govt subsidy: ₹{sc['subsidy']:,} &nbsp;|&nbsp;
          <strong>Net cost: ₹{sc['net_cost']:,}</strong><br>
          Monthly generation: ~{round(solar_monthly)} kWh &nbsp;|&nbsp;
          Monthly savings: ₹{round(monthly_save):,} &nbsp;|&nbsp;
          <strong>Payback: {payback_years}</strong>
        </div>
        """, unsafe_allow_html=True)

        # Break-even chart
        months   = list(range(0, min(int(payback * 1.5) + 1 if isinstance(payback, int) else 121, 121)))
        cost_no  = [-base_bill.total * m for m in months]
        cost_sol = [-sc["net_cost"] - (new_bill.total if solar_bill else base_bill.total - monthly_save) * m
                     + monthly_save * m for m in months]

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=months, y=cost_no, mode="lines",
                                  line=dict(color="#64748b", width=1.5),
                                  name="No solar", hovertemplate="Month %{x}<br>₹%{y:,}<extra></extra>"))
        fig2.add_trace(go.Scatter(x=months, y=cost_sol, mode="lines",
                                  line=dict(color="#a855f7", width=2),
                                  name=f"Solar {closest}kW", hovertemplate="Month %{x}<br>₹%{y:,}<extra></extra>"))
        if isinstance(payback, int):
            fig2.add_shape(type="line", x0=payback, x1=payback, y0=min(cost_no), y1=0,
                           line=dict(color="#22c55e", width=1.5, dash="dash"))
            fig2.add_annotation(x=payback, y=0, text=f"Break-even\n{payback_years}",
                                 font=dict(color="#22c55e", size=9), showarrow=False)
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#94a3b8", margin=dict(l=0,r=0,t=10,b=0),
            height=220, legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9)),
            xaxis=dict(title="Months", showgrid=False, tickfont=dict(size=9)),
            yaxis=dict(title="Cumulative ₹", showgrid=True, gridcolor="#1e2d4a", tickfont=dict(size=9)),
        )
        st.markdown("**Break-even Analysis**")
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
