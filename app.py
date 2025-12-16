import streamlit as st
import asyncio
import pandas as pd
from datetime import datetime

# =========================
# IMPORT AGENT CLASSES
# =========================
from agents.data_analysis_agent import DataAnalysisAgent
from agents.diagnosis_agent import DiagnosisAgent
from agents.master_agent import get_master_agent

# Chat + RCA
from langchain_ollama import ChatOllama
from utils.rca_engine import load_all_datasets, build_rca_signal
from services.speech_to_text import transcribe
from services.text_to_speech import speak

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Agentic Automotive AI",
    page_icon="🚗",
    layout="wide"
)

# =========================
# INIT AGENTS (SINGLETON STYLE)
# =========================
@st.cache_resource
def init_agents():
    return {
        "data": DataAnalysisAgent(),
        "diagnosis": DiagnosisAgent(),
        "master": get_master_agent()
    }

agents = init_agents()

# =========================
# SIDEBAR NAVIGATION
# =========================
st.sidebar.title("🧭 Navigation")

page = st.sidebar.radio(
    "Go to",
    [
        "🏠 Agent Dashboard",
        "💬 Normal Chat",
        "🧠 Deep RCA",
        "📅 Schedule Service",
    ],
)

lang = st.sidebar.selectbox("Language", ["English", "Hindi"])

# =========================
# LLM
# =========================
llm = ChatOllama(
    model="llama3.1:8b",
    base_url="http://localhost:11434",
    temperature=0.35
)

# =========================
# DATASETS (ONLY FOR RCA)
# =========================
@st.cache_data
def get_datasets():
    return load_all_datasets("data")

datasets = get_datasets()

# ======================================================
# 🏠 HOME — AGENT DASHBOARD
# ======================================================
if page == "🏠 Agent Dashboard":

    st.title("🤖 Agentic Automotive AI – Live Agent Dashboard")

    # -------- MASTER AGENT --------
    st.subheader("🧠 Master Agent Status")
    master_data = agents["master"].get_dashboard_data()
    st.json(master_data)

    # -------- DATA ANALYSIS AGENT --------
    st.subheader("📊 Data Analysis Agent (Sample Run)")

    sample_telematics = {
        "vehicle_id": "DEMO_VEHICLE",
        "telematics_data": {
            "engine_temp": 112,
            "oil_pressure": 28,
            "brake_pad_wear": 82,
            "tire_pressure": 31,
            "battery_voltage": 12.4,
            "rpm": 2900,
            "fuel_level": 55
        }
    }

    analysis_result = asyncio.run(
        agents["data"].analyze_telematics(sample_telematics)
    )

    st.metric("Health Score", analysis_result["health_score"])
    st.metric("Anomalies Detected", analysis_result["anomalies_detected"])
    st.json(analysis_result["service_forecast"])

    # -------- DIAGNOSIS AGENT --------
    st.subheader("🔧 Diagnosis Agent Output")

    diagnosis_input = {
        "vehicle_id": "DEMO_VEHICLE",
        "analysis_data": {
            "anomalies": analysis_result["anomalies"]
        }
    }

    diagnosis_result = asyncio.run(
        agents["diagnosis"].diagnose_failures(diagnosis_input)
    )

    st.metric("Priority", diagnosis_result["priority"])
    st.metric("Confidence", diagnosis_result["confidence_score"])
    st.dataframe(pd.DataFrame(diagnosis_result["predicted_failures"]))

    st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ======================================================
# 💬 NORMAL CHAT
# ======================================================
elif page == "💬 Normal Chat":

    st.title("💬 Automotive Assistant (Quick Help)")

    mic = st.audio_input("🎤 Speak")
    text = st.text_area("Describe your issue")

    if mic:
        text = transcribe(mic.getvalue())

    if st.button("Ask"):
        prompt = f"""
You are an experienced automotive assistant.

User problem:
{text}

Give quick, practical advice.
No deep RCA. No datasets.

Respond ONLY in {lang}.
"""
        response = llm.invoke(prompt).content
        st.write(response)
        st.audio(speak(response, lang), format="audio/mp3")

# ======================================================
# 🧠 DEEP RCA
# ======================================================
elif page == "🧠 Deep RCA":

    st.title("🧠 Deep Root Cause Analysis")

    with st.expander("🚗 Optional Vehicle Details"):
        brand = st.text_input("Brand")
        model = st.text_input("Model")
        year = st.text_input("Year")

    mic = st.audio_input("🎤 Speak")
    text = st.text_area("Describe the problem")

    if mic:
        text = transcribe(mic.getvalue())

    if st.button("Run RCA"):
        signal = build_rca_signal(text, datasets)

        prompt = f"""
You are a senior automotive service engineer.

User complaint:
{text}

Vehicle:
Brand: {brand or "Not specified"}
Model: {model or "Not specified"}
Year: {year or "Not specified"}

Internal hint:
{signal}

Explain:
1. What the problem indicates
2. Possible causes
3. How to fix now
4. When it becomes serious
5. How to prevent

Do NOT mention datasets.
Respond ONLY in {lang}.
"""
        response = llm.invoke(prompt).content
        st.write(response)
        st.audio(speak(response, lang), format="audio/mp3")

# ======================================================
# 📅 SCHEDULE SERVICE
# ======================================================
elif page == "📅 Schedule Service":
    st.switch_page("pages/Schedule_Service.py")
