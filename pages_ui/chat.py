import streamlit as st
import os, json, requests

SYSTEM_PROMPT = """You are WattWise AI, an expert energy coach specializing in Kerala's 
electricity system (KSEB). Help users reduce their electricity bills, understand KSEB 
tariff slabs, optimize appliance usage, and evaluate solar options.

Key KSEB knowledge:
- Telescopic billing (≤250 units/month): progressive slab rates ₹3.35–₹8.50/unit
- Non-Telescopic billing (>250 units/month): flat rate on ALL units ₹6.40–₹9.20/unit  
- The 250-unit cliff is critical — crossing it dramatically increases the bill
- Fixed charge: ₹110 (1-phase), ₹220 (3-phase). Electricity duty: 10%. FAC: ₹0.15/unit
- PM Surya Ghar subsidy available for rooftop solar

Always give practical, actionable advice. Use Indian Rupee ₹ symbol. Be concise."""

QUICK_REPLIES = [
    "Why is my bill high this month?",
    "How can I reduce electricity cost?",
    "Best time to run washing machine?",
    "Should I install solar panels?",
    "What is the 250-unit cliff?",
]

def get_ai_response(messages: list[dict]) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return "⚠️ OpenAI API key not set. Add `OPENAI_API_KEY=sk-...` to your `.env` file to enable AI chat."

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "max_tokens": 600,
        "temperature": 0.7,
    }
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload, timeout=30,
        )
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Error: {e}"

def show():
    st.markdown('<div class="section-title">💬 AI Energy Coach</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Get personalised KSEB energy advice powered by AI</div>', unsafe_allow_html=True)

    # ── Chat history ──────────────────────────────────────────────────────────
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_messages:
            if msg["role"] == "assistant":
                st.markdown(f'<div class="bubble-ai">🤖 {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="bubble-user">{msg["content"]}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Quick reply buttons ───────────────────────────────────────────────────
    st.markdown("**Quick questions:**")
    quick_cols = st.columns(len(QUICK_REPLIES))
    for i, (col, q) in enumerate(zip(quick_cols, QUICK_REPLIES)):
        if col.button(q, key=f"quick_{i}"):
            _send(q)
            st.rerun()

    # ── Input ─────────────────────────────────────────────────────────────────
    with st.form("chat_form", clear_on_submit=True):
        col_input, col_send = st.columns([5, 1])
        user_input = col_input.text_input("Ask about your energy usage...",
                                          placeholder="e.g. How much does my AC cost per month?",
                                          label_visibility="collapsed")
        submitted = col_send.form_submit_button("Send ➤")
        if submitted and user_input.strip():
            _send(user_input.strip())
            st.rerun()

    # ── Clear button ──────────────────────────────────────────────────────────
    if st.button("🗑️ Clear chat"):
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "Hi! I'm your WattWise AI Energy Coach ⚡ Ask me anything about your KSEB bill, appliances, or savings tips!"}
        ]
        st.rerun()

    if not os.environ.get("OPENAI_API_KEY"):
        st.info("💡 **No OpenAI key detected.** Add `OPENAI_API_KEY=sk-...` to your `.env` file to activate AI responses.", icon="ℹ️")


def _send(text: str):
    st.session_state.chat_messages.append({"role": "user", "content": text})
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.chat_messages
    ]
    with st.spinner("WattWise is thinking..."):
        reply = get_ai_response(history)
    st.session_state.chat_messages.append({"role": "assistant", "content": reply})
