# Terengganu Climate Dashboard — Combined Version
# Features:
# - District selector (single or multi-select)
# - Pulls multi-year daily ERA5 data (Open-Meteo archive)
# - Daily variables: max/min temperature, precipitation, max wind, relative humidity, surface pressure, cloud cover
# - Annual aggregation (min/mean/max daily rainfall, mean temps, mean wind, mean humidity/pressure/cloud)
# - Multi-district comparison charts
# - Interactive map (folium) with district markers and popups (falls back to st.map if folium not available)
# - CSV download for raw daily data and aggregated annual summaries
#
# Requirements (put in requirements.txt):
# streamlit
# requests
# pandas
# plotly
# folium
# streamlit-folium
# (optional) pydeck

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import date
from typing import Tuple

# Optional folium for map visualization
USE_FOLIUM = True
try:
    import folium
    from streamlit_folium import st_folium
except Exception:
    USE_FOLIUM = False

# --- App config ---
st.set_page_config(page_title="Terengganu Climate Dashboard (Combined)", page_icon="🌦️", layout="wide")
st.title("🌦️ Terengganu Climate & Weather Dashboard — Combined")

# --- Districts and coordinates ---
# Coordinates are approximate centroid values for each district
DISTRICTS = {
    "Kuala Terengganu": (5.3302, 103.1408),
    "Besut": (5.8333, 102.5000),
    "Setiu": (5.6500, 102.7500),
    "Marang": (5.2050, 103.2050),
    "Dungun": (4.7600, 103.4000),
    "Kemaman": (4.2333, 103.4500),
    "Hulu Terengganu": (5.0500, 102.9500)
}

# --- Sidebar controls ---
st.sidebar.header("Settings")
mode = st.sidebar.radio("Mode", ["Single District", "Compare Multiple Districts"], index=0)

if mode == "Single District":
    district = st.sidebar.selectbox("Select district", list(DISTRICTS.keys()))
    selected_districts = [district]
else:
    selected_districts = st.sidebar.multiselect("Select districts (multiple)", list(DISTRICTS.keys()), default=["Kuala Terengganu", "Kemaman"]) 

start_year = st.sidebar.number_input("Start Year", min_value=1980, max_value=date.today().year - 1, value=2015)
end_year = st.sidebar.number_input("End Year", min_value=start_year, max_value=date.today().year, value=2024)

st.sidebar.markdown("Data source: Open-Meteo ERA5 archive (https://archive-api.open-meteo.com)")

# --- Helper: Build API URL and fetch data ---
@st.cache_data(show_spinner=False)
def get_weather_data(lat: float, lon: float, start: int, end: int) -> pd.DataFrame:
    """Fetch daily ERA5 variables from Open-Meteo archive and return a cleaned DataFrame."""
    # daily variables we will request
    daily_vars = [
        "temperature_2m_max",
        "temperature_2m_min",
        "precipitation_sum",
        "windspeed_10m_max",
        "relativehumidity_2m_mean",
        "surface_pressure_mean",
        "cloudcover_mean"
    ]
    daily_query = ",".join(daily_vars)

    url = (
        "https://archive-api.open-meteo.com/v1/era5?"
        f"latitude={lat}&longitude={lon}&start_date={start}-01-01&end_date={end}-12-31"
        f"&daily={daily_query}&timezone=Asia/Kuala_Lumpur"
    )

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    js = resp.json()

    if "daily" not in js or "time" not in js["daily"]:
        raise ValueError("No 'daily' data returned from API for this location / period")

    df = pd.DataFrame(js["daily"])
    # convert time column
    df["time"] = pd.to_datetime(df["time"])  # YYYY-MM-DD

    # rename columns if present
    rename_map = {
        "time": "Date",
        "temperature_2m_max": "Max Temp (°C)",
        "temperature_2m_min": "Min Temp (°C)",
        "precipitation_sum": "Rainfall (mm)",
        "windspeed_10m_max": "Max Wind (m/s)",
        "relativehumidity_2m_mean": "Rel Humidity (%)",
        "surface_pressure_mean": "Surface Pressure (hPa)",
        "cloudcover_mean": "Cloud Cover (%)"
    }
    available_cols = [c for c in df.columns if c in rename_map]
    df = df.rename(columns=rename_map)

    # keep only renamed columns + Date
    keep_cols = [rename_map.get(c, c) for c in df.columns if c in rename_map.values()]
    keep_cols = ["Date"] + [c for c in df.columns if c != "time" and c != "Date"]  # simpler: keep Date + everything else

    # ensure types
    numeric_cols = [c for c in df.columns if c != "time" and c != "Date"]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')

    return df

# --- Helper: compute annual summary ---
def compute_annual_summary(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Year"] = df["Date"].dt.year
    agg = df.groupby("Year").agg({
        "Rainfall (mm)": ["min", "mean", "max"],
        "Max Temp (°C)": "mean",
        "Min Temp (°C)": "mean",
        "Max Wind (m/s)": "mean",
        "Rel Humidity (%)": "mean",
        "Surface Pressure (hPa)": "mean",
        "Cloud Cover (%)": "mean"
    })
    # flatten columns
    agg.columns = [
        "Min Rainfall",
        "Mean Rainfall",
        "Max Rainfall",
        "Mean Max Temp",
        "Mean Min Temp",
        "Mean Wind",
        "Mean Rel Humidity",
        "Mean Surface Pressure",
        "Mean Cloud Cover"
    ]
    agg = agg.reset_index()
    return agg

# --- Main UI ---
st.markdown(f"**Selected years:** {start_year} — {end_year}")

if not selected_districts:
    st.error("Please select at least one district.")
    st.stop()

# We'll store raw and annual dfs for each district
raw_data_store = {}
annual_store = {}

progress = st.sidebar.empty()
for i, d in enumerate(selected_districts, start=1):
    lat, lon = DISTRICTS[d]
    progress.text(f"Loading {d} ({i}/{len(selected_districts)})...")
    try:
        df_raw = get_weather_data(lat, lon, start_year, end_year)
        raw_data_store[d] = df_raw
        annual_store[d] = compute_annual_summary(df_raw)
    except Exception as e:
        st.error(f"Failed to fetch data for {d}: {e}")
        # continue to others

progress.empty()

# --- Map ---
st.subheader("🗺️ District Map")
if USE_FOLIUM:
    # Create folium map centered on average of selected points
    avg_lat = sum(DISTRICTS[d][0] for d in selected_districts) / len(selected_districts)
    avg_lon = sum(DISTRICTS[d][1] for d in selected_districts) / len(selected_districts)
    fmap = folium.Map(location=[avg_lat, avg_lon], zoom_start=8)
    for dname, (lat, lon) in DISTRICTS.items():
        popup_html = f"<b>{dname}</b><br>Lat: {lat:.4f}<br>Lon: {lon:.4f}"
        folium.Marker([lat, lon], popup=popup_html, tooltip=dname).add_to(fmap)
    # show map and capture last click (if any)
    map_out = st_folium(fmap, width=700, height=400)
else:
    # fallback - simple st.map (less interactive)
    coords = pd.DataFrame([{"lat": v[0], "lon": v[1], "district": k} for k, v in DISTRICTS.items()])
    st.map(coords.rename(columns={"lat": "latitude", "lon": "longitude"}))

# --- Comparison Charts ---
st.subheader("📊 Annual Comparisons")

# Combine annual data for multi-district plots
annual_combined = []
for d, adf in annual_store.items():
    if adf is None or adf.empty:
        continue
    tmp = adf.copy()
    tmp["District"] = d
    annual_combined.append(tmp)

if len(annual_combined) == 0:
    st.error("No annual data available for selected districts.")
    st.stop()

annual_df_all = pd.concat(annual_combined, ignore_index=True)

# 1) Mean rainfall comparison
fig_mean_rain = px.line(
    annual_df_all,
    x="Year",
    y="Mean Rainfall",
    color="District",
    markers=True,
    title="Mean Annual Daily Rainfall — Comparison"
)
st.plotly_chart(fig_mean_rain, use_container_width=True)

# 2) Min/Max Rainfall (faceted by district if multiple)
if len(selected_districts) <= 3:
    # show min/mean/max per district lines
    fig_minmax = px.line(
        annual_df_all,
        x="Year",
        y=["Min Rainfall", "Max Rainfall"],
        color="District",
        title="Annual Min & Max Daily Rainfall (per district)"
    )
    st.plotly_chart(fig_minmax, use_container_width=True)
else:
    # when many districts, show small-multiples
    st.write("Showing Min & Max Rainfall per district (small multiples)")
    for d in selected_districts:
        if d in annual_store and not annual_store[d].empty:
            fig = px.line(annual_store[d], x="Year", y=["Min Rainfall", "Max Rainfall"], markers=True, title=f"{d} — Min & Max Rainfall")
            st.plotly_chart(fig, use_container_width=True)

# 3) Temperature comparison
fig_temp = px.line(annual_df_all, x="Year", y=["Mean Max Temp", "Mean Min Temp"], color="District", title="Annual Mean Temperatures — Comparison")
st.plotly_chart(fig_temp, use_container_width=True)

# 4) Wind comparison
fig_wind = px.bar(annual_df_all, x="Year", y="Mean Wind", color="District", barmode='group', title="Mean Annual Wind Speed — Comparison")
st.plotly_chart(fig_wind, use_container_width=True)

# 5) Humidity / Pressure / Cloud comparisons (if available)
cols_extra = [c for c in ["Mean Rel Humidity", "Mean Surface Pressure", "Mean Cloud Cover"] if c in annual_df_all.columns]
if cols_extra:
    for col in cols_extra:
        fig = px.line(annual_df_all, x="Year", y=col, color="District", markers=True, title=f"{col} — Comparison")
        st.plotly_chart(fig, use_container_width=True)

# --- Raw data and downloads ---
st.subheader("📥 Raw Data & Downloads")

# show raw daily tables collapsed
with st.expander("View raw daily data for each district"):
    for d, rdf in raw_data_store.items():
        st.write(f"### {d}")
        st.dataframe(rdf, use_container_width=True)

# prepare combined CSV downloads
# Combine daily with district column
all_daily = []
for d, rdf in raw_data_store.items():
    tmp = rdf.copy()
    tmp["District"] = d
    all_daily.append(tmp)

if all_daily:
    daily_all_df = pd.concat(all_daily, ignore_index=True)
    csv_daily = daily_all_df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download combined daily CSV", data=csv_daily, file_name=f"terengganu_daily_{start_year}_{end_year}.csv", mime="text/csv")

# Combined annual
all_annual = []
for d, adf in annual_store.items():
    if adf is None or adf.empty:
        continue
    tmp = adf.copy()
    tmp["District"] = d
    all_annual.append(tmp)

if all_annual:
    annual_all_df = pd.concat(all_annual, ignore_index=True)
    csv_annual = annual_all_df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download combined annual CSV", data=csv_annual, file_name=f"terengganu_annual_summary_{start_year}_{end_year}.csv", mime="text/csv")

st.sidebar.success("Ready — adjust settings and re-run")

# --- Footer / quick tips ---
st.caption("Notes: Data pulled from Open-Meteo ERA5 reanalysis (archive API). ERA5 is a reanalysis product that blends models and observations; it's excellent for climate studies but may differ from station observations. If a variable is missing for a location, the app will show NaNs for those columns.")
