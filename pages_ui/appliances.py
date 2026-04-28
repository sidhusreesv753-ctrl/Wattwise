import streamlit as st
from app.services.kseb_tariff import calculate_kseb_bill
from app.services.energy_service import compute_daily_kwh, compute_appliance_breakdown, get_efficiency_insights
from app.models.schemas import ApplianceInput, AGE_OPTIONS, AGE_DEGRADATION
import uuid

AGE_LABELS = {o["value"]: o["label"] for o in AGE_OPTIONS}

def show():
    profile = st.session_state.profile

    st.markdown('<div class="section-title">🔌 Appliance Insights</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Manage energy star ratings & view consumption breakdown</div>', unsafe_allow_html=True)

    daily_kwh   = compute_daily_kwh(profile.appliances)
    monthly_kwh = profile.scanned_monthly_kwh or round(daily_kwh * 30)
    bill        = calculate_kseb_bill(monthly_kwh, profile.phase)
    breakdown   = compute_appliance_breakdown(profile.appliances, daily_kwh)

    # ── Slab banner ───────────────────────────────────────────────────────────
    bill_pill = '<span class="pill-telescopic">Telescopic ≤250</span>' if bill.billing_type == "telescopic" else '<span class="pill-nontelescopic">Non-Telescopic >250</span>'
    st.markdown(f"""
    <div class="info-banner">
      {bill_pill} &nbsp; {monthly_kwh} units/mo · Effective rate: ₹{bill.effective_rate}/unit
      {'<br><span style="color:#ef4444;font-size:0.8rem">⚠️ Dropping ' + str(monthly_kwh-250) + ' units saves ₹' + str(bill.cliff_savings) + '/mo!</span>' if bill.near_slab_cliff and bill.billing_type == "non-telescopic" else ''}
    </div>
    """, unsafe_allow_html=True)

    # ── Efficiency alerts ─────────────────────────────────────────────────────
    insights = get_efficiency_insights(breakdown)
    if insights:
        st.markdown("### ⚠️ Efficiency Alerts")
        for ins in insights:
            st.markdown(f"""
            <div class="warn-banner">
              <strong>{ins['icon']} {ins['name']}</strong> — {ins['message']}<br>
              <span style="color:#94a3b8;font-size:0.8rem">→ {ins['recommendation']}</span>
              <span style="float:right;color:#eab308;font-size:0.78rem;font-weight:700">+{ins['savings_percent']}% waste</span>
            </div>""", unsafe_allow_html=True)

    # ── Add appliance ─────────────────────────────────────────────────────────
    with st.expander("➕ Add New Appliance"):
        cols = st.columns(4)
        new_name  = cols[0].text_input("Name", placeholder="e.g. TV")
        new_icon  = cols[1].text_input("Icon", value="🔌")
        new_watts = cols[2].number_input("Wattage (kW)", min_value=0.01, max_value=20.0, value=0.1, step=0.05)
        new_hours = cols[3].number_input("Hours/day", min_value=0.1, max_value=24.0, value=4.0, step=0.5)
        if st.button("Add Appliance") and new_name:
            profile.appliances.append(ApplianceInput(
                id=str(uuid.uuid4())[:8],
                name=new_name, icon=new_icon,
                hours_per_day=new_hours, wattage=new_watts,
                color="hsl(200,80%,55%)", star_rating=3, age="3-5",
            ))
            st.success(f"Added {new_name}!")
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Appliance cards ───────────────────────────────────────────────────────
    cols_per_row = 2
    appliances = profile.appliances
    for i in range(0, len(appliances), cols_per_row):
        row_apps = appliances[i:i+cols_per_row]
        cols = st.columns(cols_per_row)
        for col, app in zip(cols, row_apps):
            bd = next((b for b in breakdown if b["id"] == app.id), None)
            kwh = bd["kwh"] if bd else 0
            pct = bd["percentage"] if bd else 0
            daily_cost = round(kwh * bill.effective_rate, 2)
            monthly_cost = round(daily_cost * 30)
            deg = AGE_DEGRADATION.get(app.age, 1.0)
            age_loss = f"+{round((deg-1)*100)}% age loss" if deg > 1 else ""

            with col:
                with st.container():
                    st.markdown(f"""
                    <div class="appliance-card">
                      <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
                        <span style="font-size:1.8rem">{app.icon}</span>
                        <div>
                          <div style="font-weight:600;color:#e2e8f0">{app.name}</div>
                          <div style="font-size:0.72rem;color:#64748b">{kwh} kWh/day {f'<span style="color:#eab308">({age_loss})</span>' if age_loss else ''}</div>
                        </div>
                      </div>
                      <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                        <span style="font-size:0.78rem;color:#64748b">Share</span>
                        <span style="font-size:0.78rem;font-weight:600;color:#38bdf8">{pct}%</span>
                      </div>
                      <div style="background:#1e2d4a;border-radius:4px;height:6px;margin-bottom:10px">
                        <div style="width:{pct}%;height:100%;background:#38bdf8;border-radius:4px"></div>
                      </div>
                      <div style="display:flex;justify-content:space-between;font-size:0.75rem;color:#475569">
                        <span>≈ ₹{daily_cost}/day</span><span>≈ ₹{monthly_cost}/mo</span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Controls below card
                    c1, c2, c3 = st.columns([1, 1, 1])
                    new_hours = c1.number_input("Hrs/day", min_value=0.1, max_value=24.0,
                                                value=float(app.hours_per_day), step=0.5,
                                                key=f"hrs_{app.id}", label_visibility="collapsed")
                    new_star = c2.selectbox("Stars", [1,2,3,4,5],
                                            index=app.star_rating-1,
                                            key=f"star_{app.id}", label_visibility="collapsed",
                                            format_func=lambda x: "⭐"*x)
                    new_age = c3.selectbox("Age", [o["value"] for o in AGE_OPTIONS],
                                           index=[o["value"] for o in AGE_OPTIONS].index(app.age),
                                           key=f"age_{app.id}", label_visibility="collapsed",
                                           format_func=lambda v: AGE_LABELS[v])
                    if (new_hours != app.hours_per_day or new_star != app.star_rating or new_age != app.age):
                        app.hours_per_day = new_hours
                        app.star_rating   = new_star
                        app.age           = new_age
                        st.rerun()

                    if st.button("🗑️ Remove", key=f"del_{app.id}"):
                        profile.appliances = [a for a in profile.appliances if a.id != app.id]
                        st.rerun()
