import streamlit as st
import google.generativeai as genai
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
    # Use the secret name we set up in the Streamlit Dashboard
    api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        return "⚠️ Gemini API key not set. Please add `GEMINI_API_KEY` to your Streamlit Secrets."

    try:
        # Configure the Google AI library
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=SYSTEM_PROMPT
        )

        # Convert the history format to Gemini's format
        # Gemini uses 'parts' instead of 'content'
        gemini_history = []
        for msg in messages[:-1]:  # All messages except the last one
            role = "model" if msg["role"] == "assistant" else "user"
            gemini_history.append({"role": role, "parts": [msg["content"]]})
        
        # Start chat session
        chat = model.start_chat(history=gemini_history)
        
        # Send the latest user message (the last item in the list)
        last_message = messages[-1]["content"]
        response = chat.send_message(last_message)
        
        return response.text

    except Exception as e:
        return f"❌ Gemini Error: {str(e)}"

def show():
    # Find the block at the bottom of show() and update it to this:
    if not st.secrets.get("GEMINI_API_KEY"):
        st.info("💡 **No Gemini key detected.** Add `GEMINI_API_KEY` to your Streamlit Secrets to activate AI responses.", icon="ℹ️")

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
