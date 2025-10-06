import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from io import StringIO
from datetime import date

# --- App setup ---
st.set_page_config(page_title="Terengganu Climate Dashboard", page_icon="🌦️", layout="wide")
st.title("🌦️ Terengganu Climate & Weather Dashboard")

# --- Coordinates for Terengganu ---
LAT, LON = 5.3302, 103.1408

# --- Sidebar inputs ---
st.sidebar.header("Settings")
start_year = st.sidebar.number_input("Start Year", min_value=1980, max_value=date.today().year-1, value=2015)
end_year = st.sidebar.number_input("End Year", min_value=start_year, max_value=date.today().year, value=2024)
st.sidebar.markdown("Source: [Open-Meteo ERA5 Reanalysis](https://open-meteo.com/)")

# --- Fetch function ---
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

# --- Get data ---
try:
    df = get_weather_data(LAT, LON, start_year, end_year)
    st.success(f"Data loaded for {start_year}–{end_year} ({len(df)} days)")

    # --- Compute Annual Summary ---
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

    # --- Plot 1: Annual Rainfall ---
    st.subheader("🌧️ Annual Rainfall (Daily Statistics)")
    fig_rain = px.line(
        annual, x="Year", y=["Min Rainfall", "Mean Rainfall", "Max Rainfall"],
        markers=True, title="Annual Min, Mean & Max Daily Rainfall (mm)"
    )
    st.plotly_chart(fig_rain, use_container_width=True)

    # --- Plot 2: Temperature Trends ---
    st.subheader("🌡️ Annual Mean Temperature Trends")
    fig_temp = px.line(
        annual, x="Year", y=["Mean Max Temp", "Mean Min Temp"],
        markers=True, title="Annual Average Temperature (°C)"
    )
    st.plotly_chart(fig_temp, use_container_width=True)

    # --- Plot 3: Wind Trends ---
    st.subheader("💨 Annual Mean Wind Speed")
    fig_wind = px.bar(
        annual, x="Year", y="Mean Wind", title="Mean Annual Wind Speed (m/s)"
    )
    st.plotly_chart(fig_wind, use_container_width=True)

    # --- Data tables ---
    st.subheader("📋 Raw Daily Data")
    st.dataframe(df, use_container_width=True)

    st.subheader("📘 Annual Summary Data")
    st.dataframe(annual, use_container_width=True)

    # --- Download CSV ---
    st.download_button(
        label="📥 Download Daily Data (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"terengganu_weather_{start_year}_{end_year}.csv",
        mime="text/csv"
    )

    st.download_button(
        label="📥 Download Annual Summary (CSV)",
        data=annual.to_csv(index=False).encode("utf-8"),
        file_name=f"terengganu_annual_summary_{start_year}_{end_year}.csv",
        mime="text/csv"
    )

except Exception as e:
    st.error(f"❌ Failed to load weather data: {e}")
