import streamlit as st

from utils.feedback_llm import analyze_feedback
from utils.feedback_store import save_feedback
from agents.master_agent import get_master_agent

st.set_page_config(page_title="Service Feedback", layout="centered")
st.title("🙏 Thank You for Choosing Our Service")

master_agent = get_master_agent()

# =========================
# FORM
# =========================
with st.form("feedback_form"):

    st.subheader("🚗 Service Details")
    vehicle_id = st.text_input("Vehicle / Customer ID", placeholder="e.g., KA01AB1234")

    service_type = st.selectbox(
        "Service Performed",
        [
            "General Service",
            "Brake Service",
            "Engine Repair",
            "Electrical",
            "Battery Replacement",
            "Other",
        ]
    )

    service_center = st.text_input(
        "Service Center Name",
        placeholder="e.g., Bosch Service – Indiranagar"
    )

    st.subheader("⭐ Your Experience")
    rating = st.slider("Overall Rating", 1, 5, 4)

    comments = st.text_area(
        "Tell us about your experience",
        placeholder="What went well? What could be improved?"
    )

    submitted = st.form_submit_button("Submit Feedback")

# =========================
# PROCESS
# =========================
if submitted:

    if not vehicle_id or not service_center or not comments:
        st.error("Please fill all required fields.")
        st.stop()

    # ---------- INTERNAL ANALYSIS (INVISIBLE) ----------
    feedback_struct = analyze_feedback(comments)

    # ---------- STORE ----------
    save_feedback({
        "vehicle_id": vehicle_id,
        "rating": rating,
        "sentiment": feedback_struct["sentiment"],
        "service_quality": feedback_struct["service_quality"],
        "services_done": [service_type],
        "service_cost": 0,
        "raw_comments": comments,
    })

    # ---------- UPDATE MASTER AGENT ----------
    master_agent.update_post_service_feedback(
        vehicle_id=vehicle_id,
        service_type=service_type,
        service_center=service_center,
        feedback=feedback_struct,
    )

    # =========================
    # ACKNOWLEDGEMENT PAGE
    # =========================
    st.success("✅ Feedback Submitted Successfully")

    st.markdown("""
    ### 🎉 Thank you!
    Your feedback helps us:
    - Improve service quality
    - Refine diagnostics
    - Recommend better service centers in the future

    You may now safely close this page.
    """)

    st.stop()
