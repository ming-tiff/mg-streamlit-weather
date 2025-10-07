import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(page_title="Malaysia Regional Weather Dashboard", layout="wide")

# -----------------------------
# Main Title
# -----------------------------
st.title("🌤️ Malaysia Regional Weather Dashboard")
st.markdown("""
This dashboard displays **temperature**, **wind**, and **precipitation** patterns 
across regions in Malaysia. You can select specific locations and date ranges from the sidebar.
""")

st.markdown("---")

# -----------------------------
# Sidebar: Location & Date Range
# -----------------------------
st.sidebar.header("⚙️ Dashboard Controls")

# --- Location selection ---
locations = {
    "Kuala Lumpur": (3.139, 101.6869),
    "Selangor": (3.0738, 101.5183),
    "Kelantan": (6.1254, 102.2386),
    "Terengganu": (5.3302, 103.1408),
    "Perlis": (6.443, 100.204),
    "Kedah": (6.1248, 100.3675),
    "Perak": (4.5921, 101.0901),
    "Johor": (1.4927, 103.7414),
    "Sabah": (5.9788, 116.0753),
    "Sarawak": (1.553, 110.359)
}

selected_locations = st.sidebar.multiselect(
    "Select Region(s)",
    options=list(locations.keys()),
    default=["Kuala Lumpur"]
)

# --- Year and Date Range (combined) ---
current_year = datetime.now().year
years = st.sidebar.slider("Select Year Range", 2014, current_year, (2014, current_year))
default_start = datetime(years[0], 1, 1)
default_end = datetime(years[1], 12, 31)

start_date = st.sidebar.date_input("Start Date", default_start)
end_date = st.sidebar.date_input("End Date", default_end)

st.sidebar.markdown("---")

# -----------------------------
# Fetch weather data
# -----------------------------
def get_weather_data(lat, lon, start_date, end_date):
    url = (
        f"https://archive-api.open-meteo.com/v1/era5?"
        f"latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"
        f"&timezone=auto"
    )
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data["daily"])
    df["date"] = pd.to_datetime(df["time"])
    df["temp_mean"] = (df["temperature_2m_max"] + df["temperature_2m_min"]) / 2
    return df

# -----------------------------
# Combine data for multiple regions
# -----------------------------
all_data = []

for loc in selected_locations:
    lat, lon = locations[loc]
    df = get_weather_data(lat, lon, start_date, end_date)
    df["region"] = loc
    all_data.append(df)

full_df = pd.concat(all_data, ignore_index=True)

# -----------------------------
# Download button
# -----------------------------
csv_buffer = io.StringIO()
full_df.to_csv(csv_buffer, index=False)
st.sidebar.download_button(
    label="📥 Download Weather Data (CSV)",
    data=csv_buffer.getvalue(),
    file_name="malaysia_weather_data.csv",
    mime="text/csv"
)

st.sidebar.markdown("---")

# -----------------------------
# Charts layout
# -----------------------------
st.subheader("📊 Weather Data Visualization")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🌡️ Temperature (°C)")
    fig_temp = px.line(
        full_df,
        x="date",
        y="temp_mean",
        color="region",
        title="Daily Mean Temperature"
    )
    st.plotly_chart(fig_temp, use_container_width=True)

with col2:
    st.markdown("### 🌬️ Wind Speed (m/s)")
    fig_wind = px.line(
        full_df,
        x="date",
        y="wind_speed_10m_max",
        color="region",
        title="Daily Maximum Wind Speed"
    )
    st.plotly_chart(fig_wind, use_container_width=True)

with col3:
    st.markdown("### 🌧️ Precipitation (mm)")
    fig_prep = px.line(
        full_df,
        x="date",
        y="precipitation_sum",
        color="region",
        title="Daily Precipitation Sum"
    )
    st.plotly_chart(fig_prep, use_container_width=True)

st.markdown("---")
st.markdown("✅ **Tip:** You can select multiple regions and export the combined dataset using the sidebar.")

