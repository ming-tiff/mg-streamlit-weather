import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import date

# ----------------------------------------------------------
# APP SETUP
# ----------------------------------------------------------
st.set_page_config(page_title="Malaysia Climate Dashboard", page_icon="🌦️", layout="wide")
st.title("🌦️ Malaysia Climate & Weather Dashboard")

# ----------------------------------------------------------
# REGIONS / STATES WITH COORDINATES
# ----------------------------------------------------------
regions = {
    "Kuala Lumpur": (3.1390, 101.6869),
    "Selangor": (3.0733, 101.5185),
    "Kelantan": (6.1254, 102.2381),
    "Terengganu": (5.3302, 103.1408),
    "Perlis": (6.4447, 100.2048),
    "Kedah": (6.1200, 100.3600),
    "Perak": (4.5975, 101.0901),
    "Johor": (1.4854, 103.7618),
    "Sabah": (5.9788, 116.0753),
    "Sarawak": (1.5533, 110.3592),
}

# ----------------------------------------------------------
# SIDEBAR INPUTS
# ----------------------------------------------------------
st.sidebar.header("Settings")
region_name = st.sidebar.selectbox("Select Region / State", list(regions.keys()))
LAT, LON = regions[region_name]

start_year = st.sidebar.number_input("Start Year", min_value=1980, max_value=date.today().year - 1, value=2014)
end_year = st.sidebar.number_input("End Year", min_value=start_year, max_value=date.today().year, value=2015)

st.sidebar.markdown("Source: [Open-Meteo ERA5 Reanalysis](https://open-meteo.com/)")
st.sidebar.info(f"📍 {region_name} (Lat: {LAT:.3f}, Lon: {LON:.3f})")

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
    df["date"] = pd.to_datetime(df["time"])
    df.rename(columns={
        "temperature_2m_max": "temp_max",
        "temperature_2m_min": "temp_min",
        "precipitation_sum": "precipitation",
        "windspeed_10m_max": "wind"
    }, inplace=True)
    df = df[["date", "temp_max", "temp_min", "precipitation", "wind"]]
    return df

# ----------------------------------------------------------
# LOAD DATA
# ----------------------------------------------------------
try:
    full_df = get_weather_data(LAT, LON, start_year, end_year)
    st.success(f"✅ Data loaded for {region_name} ({start_year}–{end_year}, {len(full_df)} days)")

    # ----------------------------------------------------------
    # METRIC SUMMARY (YEAR-TO-YEAR)
    # ----------------------------------------------------------
    if end_year > start_year:
        df_current = full_df[full_df["date"].dt.year == end_year]
        df_previous = full_df[full_df["date"].dt.year == end_year - 1]

        max_temp_current = df_current["temp_max"].max()
        max_temp_prev = df_previous["temp_max"].max()

        min_temp_current = df_current["temp_min"].min()
        min_temp_prev = df_previous["temp_min"].min()

        max_wind_current = df_current["wind"].max()
        max_wind_prev = df_previous["wind"].max()

        min_wind_current = df_current["wind"].min()
        min_wind_prev = df_previous["wind"].min()

        max_prec_current = df_current["precipitation"].max()
        max_prec_prev = df_previous["precipitation"].max()

        min_prec_current = df_current["precipitation"].min()
        min_prec_prev = df_previous["precipitation"].min()

        st.subheader(f"📊 {end_year} vs {end_year-1} Summary — {region_name}")

        cols = st.columns(2)
        with cols[0]:
            st.metric("Max Temperature", f"{max_temp_current:.1f} °C", delta=f"{max_temp_current - max_temp_prev:.1f} °C")
        with cols[1]:
            st.metric("Min Temperature", f"{min_temp_current:.1f} °C", delta=f"{min_temp_current - min_temp_prev:.1f} °C")

        cols = st.columns(2)
        with cols[0]:
            st.metric("Max Precipitation", f"{max_prec_current:.1f} mm", delta=f"{max_prec_current - max_prec_prev:.1f} mm")
        with cols[1]:
            st.metric("Min Precipitation", f"{min_prec_current:.1f} mm", delta=f"{min_prec_current - min_prec_prev:.1f} mm")

        cols = st.columns(2)
        with cols[0]:
            st.metric("Max Wind", f"{max_wind_current:.1f} m/s", delta=f"{max_wind_current - max_wind_prev:.1f} m/s")
        with cols[1]:
            st.metric("Min Wind", f"{min_wind_current:.1f} m/s", delta=f"{min_wind_current - min_wind_prev:.1f} m/s")

    else:
        st.warning("⚠️ To view the summary, please select at least two consecutive years (e.g., 2014–2015).")

    # ----------------------------------------------------------
    # ANNUAL SUMMARY
    # ----------------------------------------------------------
    full_df["year"] = full_df["date"].dt.year
    annual_df = full_df.groupby("year").agg({
        "precipitation": ["min", "mean", "max"],
        "wind": ["mean", "max"],
        "temp_max": "mean",
        "temp_min": "mean"
    })
    annual_df.columns = ["Min Rainfall", "Mean Rainfall", "Max Rainfall", "Mean Wind", "Max Wind", "Mean Max Temp", "Mean Min Temp"]
    annual_df.reset_index(inplace=True)

    # ----------------------------------------------------------
    # PLOTS
    # ----------------------------------------------------------
    st.subheader(f"📈 Annual Trends for {region_name}")

    # Annual rainfall
    fig_rain = px.line(
        annual_df, x="year", y=["Min Rainfall", "Mean Rainfall", "Max Rainfall"],
        markers=True, title="🌧️ Annual Rainfall Trends (mm)"
    )
    st.plotly_chart(fig_rain, use_container_width=True)

    # Annual wind (mean and max)
    fig_wind = px.line(
        annual_df, x="year", y=["Mean Wind", "Max Wind"],
        markers=True, title="💨 Annual Wind Speed Trends (m/s)"
    )
    st.plotly_chart(fig_wind, use_container_width=True)

    # Daily wind (within selected range)
    st.subheader("💨 Daily Wind Speed (m/s)")
    fig_wind_daily = px.line(full_df, x="date", y="wind", title=f"Daily Wind Speed ({start_year}–{end_year})")
    st.plotly_chart(fig_wind_daily, use_container_width=True)

    # ----------------------------------------------------------
    # DATA DOWNLOAD
    # ----------------------------------------------------------
    st.subheader("📂 Download Data")
    st.download_button(
        label="📥 Download Daily Data (CSV)",
        data=full_df.to_csv(index=False).encode("utf-8"),
        file_name=f"{region_name.lower().replace(' ', '_')}_daily_{start_year}_{end_year}.csv",
        mime="text/csv"
    )

    st.download_button(
        label="📥 Download Annual Summary (CSV)",
        data=annual_df.to_csv(index=False).encode("utf-8"),
        file_name=f"{region_name.lower().replace(' ', '_')}_annual_summary_{start_year}_{end_year}.csv",
        mime="text/csv"
    )

except Exception as e:
    st.error(f"❌ Failed to load weather data: {e}")
