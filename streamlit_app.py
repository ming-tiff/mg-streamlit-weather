import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- App Title ---
st.set_page_config(page_title="Terengganu Weather Dashboard", page_icon="🌤️", layout="wide")
st.title("🌤️ Terengganu Live Weather Dashboard")

# --- Coordinates for Terengganu (near Kuala Terengganu) ---
LAT, LON = 5.3302, 103.1408

# --- Sidebar ---
st.sidebar.header("Weather Settings")
forecast_days = st.sidebar.slider("Forecast Days", 1, 7, 3)
st.sidebar.markdown("Data Source: [Open-Meteo API](https://open-meteo.com/)")

# --- Fetch Data ---
@st.cache_data(ttl=3600)
def get_weather_data(lat, lon, days):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&timezone=Asia/Kuala_Lumpur"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        f"&forecast_days={days}"
    )
    response = requests.get(url)
    data = response.json()
    return data

try:
    data = get_weather_data(LAT, LON, forecast_days)
    df = pd.DataFrame({
        "Date": data["daily"]["time"],
        "Max Temp (°C)": data["daily"]["temperature_2m_max"],
        "Min Temp (°C)": data["daily"]["temperature_2m_min"],
        "Precipitation (mm)": data["daily"]["precipitation_sum"]
    })

    # --- Current Weather Display ---
    today = df.iloc[0]
    st.metric("📅 Today", today["Date"])
    st.metric("🌡️ Max Temp (°C)", today["Max Temp (°C)"])
    st.metric("🌧️ Precipitation (mm)", today["Precipitation (mm)"])

    # --- Charts ---
    st.subheader("📈 7-Day Temperature & Rainfall Forecast")
    fig = px.line(df, x="Date", y=["Max Temp (°C)", "Min Temp (°C)"], markers=True)
    st.plotly_chart(fig, use_container_width=True)

    fig2 = px.bar(df, x="Date", y="Precipitation (mm)", color="Precipitation (mm)",
                  title="Daily Rainfall Forecast (mm)")
    st.plotly_chart(fig2, use_container_width=True)

    # --- Table ---
    st.subheader("📋 Weather Data Table")
    st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"Failed to load weather data: {e}")
