import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import requests

st.set_page_config(page_title="Malaysia Regional Weather Dashboard", layout="wide")

st.title("🌤️ Malaysia Regional Weather Dashboard")
st.markdown("""
This dashboard shows **daily and annual summaries** of temperature, wind, and precipitation 
for multiple regions in Malaysia using data from the **Open-Meteo API**.
""")

# -----------------------------
# 📍 Select Region
# -----------------------------
region_coords = {
    "Terengganu": {"lat": 5.329, "lon": 103.136},
    "Kelantan": {"lat": 6.125, "lon": 102.238},
    "Selangor": {"lat": 3.073, "lon": 101.518},
    "Kuala Lumpur": {"lat": 3.139, "lon": 101.686},
    "Perlis": {"lat": 6.443, "lon": 100.204},
    "Kedah": {"lat": 6.120, "lon": 100.368},
    "Perak": {"lat": 4.597, "lon": 101.090},
    "Johor": {"lat": 1.492, "lon": 103.741},
    "Sabah": {"lat": 5.978, "lon": 116.075},
    "Sarawak": {"lat": 1.553, "lon": 110.359},
    "Custom Coordinates": None,  # 🆕 added option
}

# User selects a region
selected_region = st.selectbox("Select a Region:", list(region_coords.keys()))

# Handle custom coordinate input
if selected_region == "Custom Coordinates":
    st.markdown("### 🌍 Enter Custom Coordinates")
    custom_lat = st.number_input("Latitude", value=3.0, format="%.6f")
    custom_lon = st.number_input("Longitude", value=101.0, format="%.6f")
    lat, lon = custom_lat, custom_lon
else:
    lat, lon = region_coords[selected_region]["lat"], region_coords[selected_region]["lon"]

st.write(f"**Selected Location:** {selected_region} ({lat:.4f}, {lon:.4f})")
#-----------------------

# -----------------------------
# 📆 Select Date Range
# -----------------------------
years = st.slider("Select Year Range:", 2014, datetime.now().year, (2014, 2024))
start_date = f"{years[0]}-01-01"
end_date = f"{years[1]}-12-31"

# -----------------------------
# 🌤️ Fetch Data
# -----------------------------
@st.cache_data
def get_weather_data(lat, lon, start_date, end_date):
    url = (
        f"https://archive-api.open-meteo.com/v1/era5?"
        f"latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,wind_speed_10m_min"
        "&timezone=Asia/Kuala_Lumpur"
    )
    r = requests.get(url)
    data = r.json()
    df = pd.DataFrame({
        "date": data["daily"]["time"],
        "temp_max": data["daily"]["temperature_2m_max"],
        "temp_min": data["daily"]["temperature_2m_min"],
        "precipitation": data["daily"]["precipitation_sum"],
        "wind_max": data["daily"]["wind_speed_10m_max"],
        "wind_min": data["daily"]["wind_speed_10m_min"],
    })
    df["date"] = pd.to_datetime(df["date"])
    return df

coords = region_coords[region]
full_df = get_weather_data(coords["lat"], coords["lon"], start_date, end_date)

st.success(f"Loaded {len(full_df)} days of weather data for **{region}** ({start_date} to {end_date})")

# -----------------------------
# 📈 Plot Daily Data
# -----------------------------
st.subheader(f"📊 Daily Weather Trends ({region})")

tab1, tab2, tab3 = st.tabs(["🌧️ Precipitation", "🌬️ Wind", "🌡️ Temperature"])

with tab1:
    fig = px.line(full_df, x="date", y="precipitation", title="Daily Precipitation (mm)")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    fig = px.line(full_df, x="date", y=["wind_max", "wind_min"], 
                  labels={"value": "Wind Speed (m/s)", "date": "Date"},
                  title="Daily Wind Speed (Max & Min)")
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    fig = px.line(full_df, x="date", y=["temp_max", "temp_min"],
                  labels={"value": "Temperature (°C)", "date": "Date"},
                  title="Daily Temperature (Max & Min)")
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# 📆 Annual Summary
# -----------------------------
st.subheader(f"📅 Annual Summary Metrics — {years[1]} vs {years[1]-1}")

df_latest = full_df[full_df["date"].dt.year == years[1]]
df_prev = full_df[full_df["date"].dt.year == (years[1] - 1)]

max_temp_latest = df_latest["temp_max"].max()
max_temp_prev = df_prev["temp_max"].max()
min_temp_latest = df_latest["temp_min"].min()
min_temp_prev = df_prev["temp_min"].min()

max_wind_latest = df_latest["wind_max"].max()
max_wind_prev = df_prev["wind_max"].max()
min_wind_latest = df_latest["wind_min"].min()
min_wind_prev = df_prev["wind_min"].min()

max_prec_latest = df_latest["precipitation"].max()
max_prec_prev = df_prev["precipitation"].max()
min_prec_latest = df_latest["precipitation"].min()
min_prec_prev = df_prev["precipitation"].min()

cols = st.columns(2)
with cols[0]:
    st.metric("Max Temperature", f"{max_temp_latest:.1f}°C", delta=f"{max_temp_latest - max_temp_prev:.1f}°C")
with cols[1]:
    st.metric("Min Temperature", f"{min_temp_latest:.1f}°C", delta=f"{min_temp_latest - min_temp_prev:.1f}°C")

cols = st.columns(2)
with cols[0]:
    st.metric("Max Precipitation", f"{max_prec_latest:.1f} mm", delta=f"{max_prec_latest - max_prec_prev:.1f} mm")
with cols[1]:
    st.metric("Min Precipitation", f"{min_prec_latest:.1f} mm", delta=f"{min_prec_latest - min_prec_prev:.1f} mm")

cols = st.columns(2)
with cols[0]:
    st.metric("Max Wind", f"{max_wind_latest:.1f} m/s", delta=f"{max_wind_latest - max_wind_prev:.1f} m/s")
with cols[1]:
    st.metric("Min Wind", f"{min_wind_latest:.1f} m/s", delta=f"{min_wind_latest - min_wind_prev:.1f} m/s")

# -----------------------------
# 📥 Download Data
# -----------------------------
st.subheader("💾 Download Data")
csv = full_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download Raw Weather Data (CSV)",
    data=csv,
    file_name=f"{region.lower()}_weather_{years[0]}_{years[1]}.csv",
    mime="text/csv",
)
