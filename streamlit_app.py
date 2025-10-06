# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import requests
import altair as alt
from datetime import datetime

st.set_page_config(
    page_title="Terengganu Weather Dashboard",
    page_icon="🌦️",
    layout="wide",
)

"""
# 🌤️ Terengganu Weather Dashboard

Explore daily temperature, rainfall, and wind for Terengganu, Malaysia.
"""

# --- Get weather data from Open-Meteo API ---
@st.cache_data
def get_weather_data():
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        "latitude=5.33&longitude=103.14&"
        "daily=temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max&"
        "timezone=Asia/Kuala_Lumpur&start_date=2024-01-01&end_date=2024-12-31"
    )
    r = requests.get(url)
    data = r.json()

    df = pd.DataFrame({
        "date": pd.to_datetime(data["daily"]["time"]),
        "temp_max": data["daily"]["temperature_2m_max"],
        "temp_min": data["daily"]["temperature_2m_min"],
        "precipitation": data["daily"]["precipitation_sum"],
        "wind": data["daily"]["wind_speed_10m_max"],
    })
    return df

df = get_weather_data()

# --- Summary statistics ---
st.subheader("2024 Summary")

col1, col2, col3 = st.columns(3)
col1.metric("Max Temperature", f"{df['temp_max'].max():.1f} °C")
col2.metric("Min Temperature", f"{df['temp_min'].min():.1f} °C")
col3.metric("Total Rainfall", f"{df['precipitation'].sum():.1f} mm")

col1, col2 = st.columns(2)
col1.metric("Highest Wind Speed", f"{df['wind'].max():.1f} m/s")
col2.metric("Average Wind Speed", f"{df['wind'].mean():.1f} m/s")

st.markdown("---")

# --- Charts ---
st.subheader("Temperature Trends")

temp_chart = (
    alt.Chart(df)
    .mark_area(opacity=0.5)
    .encode(
        x="date:T",
        y=alt.Y("temp_max:Q", title="Temperature (°C)"),
        y2="temp_min:Q",
        tooltip=["date:T", "temp_max", "temp_min"],
    )
    .properties(height=300)
)
st.altair_chart(temp_chart, use_container_width=True)

st.subheader("Rainfall and Wind Overview")

rain_chart = (
    alt.Chart(df)
    .mark_bar()
    .encode(
        x="date:T",
        y=alt.Y("precipitation:Q", title="Rainfall (mm)"),
        tooltip=["date:T", "precipitation"],
    )
    .properties(height=200)
)

wind_chart = (
    alt.Chart(df)
    .mark_line(color="orange")
    .encode(
        x="date:T",
        y=alt.Y("wind:Q", title="Wind Speed (m/s)"),
        tooltip=["date:T", "wind"],
    )
    .properties(height=200)
)

st.altair_chart(rain_chart, use_container_width=True)
st.altair_chart(wind_chart, use_container_width=True)

st.subheader("Raw Data")
st.dataframe(df)
