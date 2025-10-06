import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests

st.set_page_config(page_title="Malaysia Regional Weather Dashboard", layout="wide")

st.title("🌤️ Malaysia Regional Weather Dashboard")
st.markdown("""
This dashboard shows **daily and annual summaries** of temperature, wind, and precipitation 
for multiple regions in Malaysia using data from the **Open-Meteo (ERA5) archive API**.
""")

# -----------------------------
# 📍 Select Region (with Custom)
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
    "Custom Coordinates": None,
}

selected_region = st.selectbox("Select a Region:", list(region_coords.keys()))

# If custom, let user input lat/lon
if selected_region == "Custom Coordinates":
    st.markdown("### 🌍 Enter Custom Coordinates")
    lat = st.number_input("Latitude", value=3.0, format="%.6f", step=0.000001)
    lon = st.number_input("Longitude", value=101.0, format="%.6f", step=0.000001)
else:
    coords = region_coords[selected_region]
    lat, lon = coords["lat"], coords["lon"]

st.write(f"**Selected Location:** {selected_region} ({lat:.4f}, {lon:.4f})")

# Map preview
try:
    map_df = pd.DataFrame({"lat": [lat], "lon": [lon]})
    st.map(map_df, zoom=6)
except Exception:
    # st.map can fail for invalid coords; ignore gracefully
    pass

# -----------------------------
# 📆 Select Date Range (years)
# -----------------------------
current_year = datetime.now().year
years = st.slider("Select Year Range:", 2014, current_year, (2014, current_year))
start_date = f"{years[0]}-01-01"
end_date = f"{years[1]}-12-31"

# -----------------------------
# 🌤️ Fetch Data (with caching and error handling)
# -----------------------------
@st.cache_data(show_spinner=False)
def get_weather_data(lat: float, lon: float, start_date: str = None, end_date: str = None):
    """
    Fetch ERA5 daily aggregated data from Open-Meteo archive API.
    Returns a DataFrame or raises ValueError on bad response.
    """
    url = (
        "https://archive-api.open-meteo.com/v1/era5?"
        f"latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,wind_speed_10m_min"
        "&timezone=Asia%2FKuala_Lumpur"
    )
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        raise ValueError(f"Network/API error: {e}")

    # Validate response
    if "daily" not in data or "time" not in data["daily"]:
        raise ValueError("Unexpected API response structure (missing 'daily' or 'time').")

    daily = data["daily"]
    df = pd.DataFrame({
        "date": daily.get("time", []),
        "temp_max": daily.get("temperature_2m_max", []),
        "temp_min": daily.get("temperature_2m_min", []),
        "precipitation": daily.get("precipitation_sum", []),
        "wind_max": daily.get("wind_speed_10m_max", []),
        "wind_min": daily.get("wind_speed_10m_min", []),
    })

    # Convert types
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    # coerce numeric columns
    for col in ["temp_max", "temp_min", "precipitation", "wind_max", "wind_min"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows with no valid date
    df = df.dropna(subset=["date"]).reset_index(drop=True)
    return df

# Attempt to load data
full_df = pd.DataFrame()
with st.spinner("Fetching weather data..."):
    try:
        full_df = get_weather_data(lat, lon, start_date, end_date)
    except ValueError as e:
        st.error(f"Failed to load weather data: {e}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")

if full_df.empty:
    st.warning("No data available for the selected location/date range. Try different coordinates or date range.")
    st.stop()

# Success message
display_region_name = selected_region if selected_region != "Custom Coordinates" else "Custom Location"
st.success(f"Loaded {len(full_df)} days of weather data for **{display_region_name}** ({start_date} to {end_date})")

# -----------------------------
# 📈 Plot Daily Data
# -----------------------------
st.subheader(f"📊 Daily Weather Trends — {display_region_name}")

tab1, tab2, tab3 = st.tabs(["🌧️ Precipitation", "🌬️ Wind", "🌡️ Temperature"])

with tab1:
    fig = px.line(full_df, x="date", y="precipitation", title="Daily Precipitation (mm)")
    fig.update_layout(xaxis_title="Date", yaxis_title="Precipitation (mm)")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    # melt for cleaner legend labels if desired, but keep simple as requested
    fig = px.line(full_df, x="date", y=["wind_max", "wind_min"],
                  labels={"value": "Wind Speed (m/s)", "date": "Date", "variable": "Wind"})
    fig.update_layout(title="Daily Wind Speed (Max & Min)")
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    fig = px.line(full_df, x="date", y=["temp_max", "temp_min"],
                  labels={"value": "Temperature (°C)", "date": "Date", "variable": "Temperature"})
    fig.update_layout(title="Daily Temperature (Max & Min)")
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# 📆 Annual Summary
# -----------------------------
st.subheader(f"📅 Annual Summary Metrics — {years[1]} vs {years[1]-1}")

df_latest = full_df[full_df["date"].dt.year == years[1]]
df_prev = full_df[full_df["date"].dt.year == (years[1] - 1)]

def safe_stat(series, func, default=float("nan")):
    try:
        if series.empty:
            return default
        return func(series.dropna())
    except Exception:
        return default

# Temperatures
max_temp_latest = safe_stat(df_latest["temp_max"], pd.Series.max)
max_temp_prev = safe_stat(df_prev["temp_max"], pd.Series.max)
min_temp_latest = safe_stat(df_latest["temp_min"], pd.Series.min)
min_temp_prev = safe_stat(df_prev["temp_min"], pd.Series.min)

# Wind
max_wind_latest = safe_stat(df_latest["wind_max"], pd.Series.max)
max_wind_prev = safe_stat(df_prev["wind_max"], pd.Series.max)
min_wind_latest = safe_stat(df_latest["wind_min"], pd.Series.min)
min_wind_prev = safe_stat(df_prev["wind_min"], pd.Series.min)

# Precipitation
max_prec_latest = safe_stat(df_latest["precipitation"], pd.Series.max)
max_prec_prev = safe_stat(df_prev["precipitation"], pd.Series.max)
min_prec_latest = safe_stat(df_latest["precipitation"], pd.Series.min)
min_prec_prev = safe_stat(df_prev["precipitation"], pd.Series.min)

def fmt(val, unit="", na_text="N/A"):
    return na_text if pd.isna(val) else f"{val:.1f}{unit}"

cols = st.columns(2)
with cols[0]:
    st.metric("Max Temperature", fmt(max_temp_latest, "°C"), delta=(fmt(max_temp_latest - max_temp_prev, "°C") if not pd.isna(max_temp_latest) and not pd.isna(max_temp_prev) else "N/A"))
with cols[1]:
    st.metric("Min Temperature", fmt(min_temp_latest, "°C"), delta=(fmt(min_temp_latest - min_temp_prev, "°C") if not pd.isna(min_temp_latest) and not pd.isna(min_temp_prev) else "N/A"))

cols = st.columns(2)
with cols[0]:
    st.metric("Max Precipitation", fmt(max_prec_latest, " mm"), delta=(fmt(max_prec_latest - max_prec_prev, " mm") if not pd.isna(max_prec_latest) and not pd.isna(max_prec_prev) else "N/A"))
with cols[1]:
    st.metric("Min Precipitation", fmt(min_prec_latest, " mm"), delta=(fmt(min_prec_latest - min_prec_prev, " mm") if not pd.isna(min_prec_latest) and not pd.isna(min_prec_prev) else "N/A"))

cols = st.columns(2)
with cols[0]:
    st.metric("Max Wind", fmt(max_wind_latest, " m/s"), delta=(fmt(max_wind_latest - max_wind_prev, " m/s") if not pd.isna(max_wind_latest) and not pd.isna(max_wind_prev) else "N/A"))
with cols[1]:
    st.metric("Min Wind", fmt(min_wind_latest, " m/s"), delta=(fmt(min_wind_latest - min_wind_prev, " m/s") if not pd.isna(min_wind_latest) and not pd.isna(min_wind_prev) else "N/A"))

# -----------------------------
# 📥 Download Data
# -----------------------------
st.subheader("💾 Download Data")
download_name = (selected_region if selected_region != "Custom Coordinates" else "custom_location").lower().replace(" ", "_")
csv = full_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download Raw Weather Data (CSV)",
    data=csv,
    file_name=f"{download_name}_weather_{years[0]}_{years[1]}.csv",
    mime="text/csv",
)
