import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import date

# ----------------------------------------------------------
# APP SETUP
# ----------------------------------------------------------
st.set_page_config(page_title="Terengganu Climate Dashboard", page_icon="🌦️", layout="wide")
st.title("🌦️ Terengganu Climate & Weather Dashboard")

# ----------------------------------------------------------
# TERENGGANU DISTRICTS AND COORDINATES
# ----------------------------------------------------------
districts = {
    "Kuala Terengganu": (5.3302, 103.1408),
    "Besut": (5.8333, 102.5000),
    "Setiu": (5.6500, 102.7500),
    "Marang": (5.2050, 103.2050),
    "Dungun": (4.7600, 103.4000),
    "Kemaman": (4.2333, 103.4500),
    "Hulu Terengganu": (5.0500, 102.9500)
}

# ----------------------------------------------------------
# SIDEBAR INPUTS
# ----------------------------------------------------------
st.sidebar.header("Settings")

district_name = st.sidebar.selectbox("Select District", list(districts.keys()))
LAT, LON = districts[district_name]

start_year = st.sidebar.number_input("Start Year", min_value=1980, max_value=date.today().year - 1, value=2015)
end_year = st.sidebar.number_input("End Year", min_value=start_year, max_value=date.today().year, value=2024)

st.sidebar.markdown("Source: [Open-Meteo ERA5 Reanalysis](https://open-meteo.com/)")
st.sidebar.info(f"Location: {district_name} (Lat: {LAT:.3f}, Lon: {LON:.3f})")

# ----------------------------------------------------------
# FETCH WEATHER DATA FUNCTION
# ----------------------------------------------------------
@st.cache_data(ttl=3600)
def get_weather_data(lat, lon, start, end):
    url = (
        "https://archive-api.open-meteo.com/v1/era5?"
        f"latitude={lat}&longitude={lon}&start_date={start}-01-01&end_date={end}-12-31"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max"
        "&timezone=Asia/Kuala_Lumpur"
    )
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    df = pd.DataFrame(data["daily"])
    df["time"] = pd.to_datetime(df["time"])
    df.rename(columns={
        "time": "Date",
        "temperature_2m_max": "Max Temp (°C)",
        "temperature_2m_min": "Min Temp (°C)",
        "precipitation_sum": "Rainfall (mm)",
        "windspeed_10m_max": "Max Wind (m/s)"
    }, inplace=True)
    return df

# ----------------------------------------------------------
# GET DATA
# ----------------------------------------------------------
try:
    df = get_weather_data(LAT, LON, start_year, end_year)
    st.success(f"✅ Data loaded for {district_name} ({start_year}–{end_year}, {len(df)} days)")

    # ----------------------------------------------------------
    # PROCESS DATA
    # ----------------------------------------------------------
    df["Year"] = df["Date"].dt.year
    annual = df.groupby("Year").agg({
        "Rainfall (mm)": ["min", "mean", "max"],
        "Max Temp (°C)": "mean",
        "Min Temp (°C)": "mean",
        "Max Wind (m/s)": "mean"
    })
    annual.columns = ["Min Rainfall", "Mean Rainfall", "Max Rainfall",
                      "Mean Max Temp", "Mean Min Temp", "Mean Wind"]
    annual.reset_index(inplace=True)

    # ----------------------------------------------------------
    # VISUALIZATIONS
    # ----------------------------------------------------------
    st.subheader(f"📈 Annual Climate Trends — {district_name}")

    col1, col2 = st.columns(2)

    with col1:
        fig_rain = px.line(
            annual, x="Year", y=["Min Rainfall", "Mean Rainfall", "Max Rainfall"],
            markers=True, title="🌧️ Annual Min, Mean & Max Daily Rainfall (mm)"
        )
        st.plotly_chart(fig_rain, use_container_width=True)

    with col2:
        fig_temp = px.line(
            annual, x="Year", y=["Mean Max Temp", "Mean Min Temp"],
            markers=True, title="🌡️ Annual Mean Temperature (°C)"
        )
        st.plotly_chart(fig_temp, use_container_width=True)

    fig_wind = px.bar(
        annual, x="Year", y="Mean Wind",
        title="💨 Annual Mean Wind Speed (m/s)"
    )
    st.plotly_chart(fig_wind, use_container_width=True)

    # ----------------------------------------------------------
    # DATA TABLES
    # ----------------------------------------------------------
    st.subheader("📋 Raw Daily Data")
    st.dataframe(df, use_container_width=True)

    st.subheader("📘 Annual Summary Data")
    st.dataframe(annual, use_container_width=True)

    # ----------------------------------------------------------
    # DOWNLOAD CSV BUTTONS
    # ----------------------------------------------------------
    st.download_button(
        label="📥 Download Daily Data (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{district_name.lower().replace(' ', '_')}_daily_{start_year}_{end_year}.csv",
        mime="text/csv"
    )

    st.download_button(
        label="📥 Download Annual Summary (CSV)",
        data=annual.to_csv(index=False).encode("utf-8"),
        file_name=f"{district_name.lower().replace(' ', '_')}_annual_summary_{start_year}_{end_year}.csv",
        mime="text/csv"
    )

except Exception as e:
    st.error(f"❌ Failed to load data: {e}")
