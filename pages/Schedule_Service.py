import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Schedule Service", layout="wide")
st.title("📅 Vehicle Service Booking")

# ---------------- LOAD DATA ----------------
df = pd.read_csv("data/datasett.csv")

# ---------------- COLUMN AUTO-DETECTION ----------------
def find_col(keys):
    for col in df.columns:
        for k in keys:
            if k in col.lower():
                return col
    return None

SERVICE_COL = find_col(["service", "repair", "job", "work"])
CENTER_COL  = find_col(["center", "workshop", "garage"])
CITY_COL    = find_col(["city", "location", "area"])
LAT_COL     = find_col(["lat"])
LON_COL     = find_col(["lon", "lng", "longitude"])

required = {
    "Service": SERVICE_COL,
    "Center": CENTER_COL,
    "City": CITY_COL
}

missing = [k for k, v in required.items() if v is None]
if missing:
    st.error(f"❌ datasett.csv missing required columns: {missing}")
    st.write("Available columns:", list(df.columns))
    st.stop()

# =========================
# 👤 CUSTOMER DETAILS
# =========================
st.subheader("👤 Customer Details")

c1, c2, c3 = st.columns(3)
with c1:
    customer_name = st.text_input("Full Name")
with c2:
    phone = st.text_input("Phone Number")
with c3:
    email = st.text_input("Email (optional)")

# =========================
# 🚗 VEHICLE DETAILS
# =========================
st.subheader("🚗 Vehicle Details")

v1, v2, v3 = st.columns(3)
with v1:
    vehicle_type = st.selectbox("Vehicle Type", ["Car", "SUV", "Bike", "EV"])
with v2:
    brand = st.text_input("Brand (e.g., Hyundai, Tata)")
with v3:
    model = st.text_input("Model (e.g., i20, Nexon)")

v4, v5 = st.columns(2)
with v4:
    fuel = st.selectbox("Fuel Type", ["Petrol", "Diesel", "EV", "Hybrid"])
with v5:
    year = st.number_input("Manufacturing Year", min_value=1995, max_value=2025, step=1)

# =========================
# 🛠 SERVICE DETAILS
# =========================
st.subheader("🛠 Service Request")

service = st.selectbox(
    "Service Category",
    sorted(df[SERVICE_COL].dropna().unique())
)

problem = st.text_area(
    "Describe the problem (optional but recommended)",
    placeholder="E.g., car overheats after 20 km, brake noise, engine vibration..."
)

city = st.text_input("Preferred City / Location")

# ---------------- FILTER SERVICE CENTERS ----------------
filtered = df[df[SERVICE_COL].astype(str).str.contains(service, case=False, na=False)]

if city:
    filtered = filtered[
        filtered[CITY_COL].astype(str).str.contains(city, case=False, na=False)
    ]

st.subheader("🏭 Available Service Centers")

if filtered.empty:
    st.warning("No service centers found for this service/location.")
    st.stop()

st.dataframe(
    filtered[[CENTER_COL, CITY_COL, SERVICE_COL]],
    use_container_width=True
)

# =========================
# 🗺 MAP VIEW
# =========================
if LAT_COL and LON_COL:
    st.subheader("📍 Service Centers Map")

    m = folium.Map(location=[12.97, 77.59], zoom_start=10)

    for _, r in filtered.iterrows():
        if pd.notna(r[LAT_COL]) and pd.notna(r[LON_COL]):
            folium.Marker(
                [r[LAT_COL], r[LON_COL]],
                popup=str(r[CENTER_COL])
            ).add_to(m)

    st_folium(m, width=700, height=400)

# =========================
# 📅 APPOINTMENT DETAILS
# =========================
st.subheader("📅 Appointment Preference")

a1, a2 = st.columns(2)
with a1:
    date = st.date_input("Preferred Date")
with a2:
    slot = st.selectbox(
        "Preferred Time Slot",
        ["09:00 – 11:00", "11:00 – 13:00", "14:00 – 16:00", "16:00 – 18:00"]
    )

# =========================
# ✅ CONFIRM BOOKING
# =========================
if st.button("✅ Confirm Service Booking"):

    if not customer_name or not phone or not brand or not model:
        st.error("❌ Please fill all mandatory fields (name, phone, brand, model).")
        st.stop()

    st.success("🎉 Service Booking Request Submitted!")

    st.markdown("### 📄 Booking Summary")
    st.markdown(f"""
**Customer:** {customer_name}  
**Phone:** {phone}  
**Vehicle:** {vehicle_type} – {brand} {model} ({fuel}, {year})  
**Service:** {service}  
**Problem:** {problem if problem else "Not specified"}  
**Location:** {city}  
**Date & Time:** {date}, {slot}  

📞 The service center will contact you to confirm availability.
""")
