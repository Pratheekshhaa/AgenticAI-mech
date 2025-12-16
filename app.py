import streamlit as st
from langchain_ollama import ChatOllama

from utils.rca_engine import load_all_datasets, build_rca_signal
from services.speech_to_text import transcribe
from services.text_to_speech import speak

# =====================
# PAGE CONFIG
# =====================
st.set_page_config(
    page_title="Automotive AI Assistant",
    page_icon="🚗",
    layout="wide"
)

st.title("🤖 Automotive AI Assistant")

# =====================
# LOAD DATASETS (ONLY ONCE)
# =====================
@st.cache_data
def get_datasets():
    return load_all_datasets("data")

datasets = get_datasets()

# =====================
# LLM
# =====================
llm = ChatOllama(
    model="llama3.1:8b",
    base_url="http://localhost:11434",
    temperature=0.35
)

# =====================
# SIDEBAR
# =====================
st.sidebar.header("Mode")

chat_mode = st.sidebar.radio(
    "Select Assistant Mode",
    ["⚡ Normal Chat", "🧠 Deep RCA Analysis"],
    index=0
)

lang = st.sidebar.selectbox("Language", ["English", "Hindi"])

if st.sidebar.button("📅 Schedule Service"):
    st.switch_page("pages/Schedule_Service.py")

# =====================
# OPTIONAL VEHICLE DETAILS
# =====================
with st.expander("🚗 Optional Vehicle Details (improves accuracy)"):
    brand = st.text_input("Brand (optional)")
    model = st.text_input("Model (optional)")
    year = st.text_input("Year (optional)")

# =====================
# USER INPUT
# =====================
st.markdown("### Describe your vehicle problem")

mic = st.audio_input("🎤 Speak")
text = st.text_area(
    "Or type here",
    placeholder="Example: car overheats after long drive"
)

if mic:
    text = transcribe(mic.getvalue())

if not text.strip():
    st.stop()

# =====================
# SUBMIT
# =====================
if st.button("Submit"):

    # -----------------------------
    # NORMAL CHAT MODE
    # -----------------------------
    if chat_mode == "⚡ Normal Chat":

        prompt = f"""
You are an experienced automotive assistant.

User problem:
{text}

Vehicle details (if any):
Brand: {brand or "Not specified"}
Model: {model or "Not specified"}
Year: {year or "Not specified"}

Instructions:
- Give quick, practical advice
- Do NOT do deep RCA
- Do NOT mention datasets
- Focus on what the user can do now
- Keep response short and helpful

Respond ONLY in {lang}.
"""

        with st.spinner("Thinking..."):
            response = llm.invoke(prompt).content

        st.subheader("⚡ Quick Assistance")
        st.write(response)

        try:
            st.audio(speak(response, lang), format="audio/mp3")
        except:
            pass

    # -----------------------------
    # DEEP RCA MODE
    # -----------------------------
    else:
        with st.spinner("Running deep root cause analysis..."):

            signal = build_rca_signal(text, datasets)

            prompt = f"""
You are a senior automotive service engineer performing ROOT CAUSE ANALYSIS.

User complaint:
{text}

Vehicle details:
Brand: {brand or "Not specified"}
Model: {model or "Not specified"}
Year: {year or "Not specified"}

Internal reasoning hint:
{signal}

IMPORTANT RULES:
- Do NOT mention datasets, CSVs, or records
- Do NOT mention brands unless user gave them
- Assume a generic passenger vehicle if details are missing
- Explain like a mechanic talking to a customer

Provide:

1. What the problem likely indicates
2. Possible causes (ranked, practical)
3. How the user can fix or check it now
4. When the issue becomes serious or unsafe
5. How to prevent this issue in the future

Respond ONLY in {lang}.
"""

            response = llm.invoke(prompt).content

        st.subheader("🧠 Deep RCA & Prevention")
        st.write(response)

        try:
            st.audio(speak(response, lang), format="audio/mp3")
        except:
            pass
