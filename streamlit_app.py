import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import requests
from math import ceil
import io
import geopandas as gpd
import tempfile, zipfile, os, json

# --------------------------------------------
# Page Setup
# --------------------------------------------
st.set_page_config(page_title="🌤️ Malaysia Regional Weather Dashboard", layout="wide")
st.title("🌤️ Malaysia Regional Weather Dashboard")
st.sidebar.markdown("Data Source: [Open-Meteo API](https://open-meteo.com/)  \n"
                    "Forecast Data: [Windy Point Forecast API](https://api.windy.com/point-forecast/docs)")

st.markdown("""
This dashboard shows **daily, weekly, monthly, and yearly** summaries of 
**temperature (°C)**, **wind speed (m/s)**, **wind direction**, and **precipitation (mm)** 
for multiple regions in Malaysia using the **Open-Meteo ERA5 API**.

You can select from:
- 🗾 Predefined Malaysian regions  
- 📄 Upload **CSV** with latitude & longitude  
- 🗺️ Upload **Shapefile (.zip)** polygons  
- 📍 Manually enter coordinates

---
### 🌐 API Information:
- **Open-Meteo ERA5 (Historical/Archive Data):** Provides reanalysis data from 2014–present (temperature, precipitation, wind speed & direction).  
- **Windy Point Forecast (Forecast Data):** Provides forecast data (next few days) based on global models such as GFS or ICON.  
  🔸 *Used here to show upcoming weather trends for each selected region.*
---
""")

# --------------------------------------------
# Sidebar — Configuration
# --------------------------------------------
st.sidebar.header("⚙️ Configuration")

region_coords = {
    "Selangor": (3.0738, 101.5183),
    "Kuala Lumpur": (3.1390, 101.6869),
    "Kelantan": (6.1254, 102.2387),
    "Terengganu": (5.3302, 103.1408),
    "Perlis": (6.4440, 100.2048),
    "Kedah": (6.1184, 100.3685),
    "Perak": (4.5921, 101.0901),
    "Johor": (1.4854, 103.7618),
    "Sabah": (5.9788, 116.0753),
    "Sarawak": (1.5533, 110.3592),
}

region_option = st.sidebar.radio(
    "Select Input Type",
    ["Predefined Regions", "Manual Coordinates", "Upload Shapefile (.zip)", "Upload CSV (lat, lon only)"]
)

coords = {}

if region_option == "Predefined Regions":
    selected_regions = st.sidebar.multiselect(
        "Select Region(s)",
        list(region_coords.keys()),
        default=["Kuala Lumpur"]
    )
    for region in selected_regions:
        coords[region] = region_coords[region]

elif region_option == "Manual Coordinates":
    n_points = st.sidebar.number_input("Number of Points", min_value=1, max_value=10, value=1)
    for i in range(n_points):
        lat = st.sidebar.number_input(f"Latitude #{i+1}", key=f"lat_{i}", format="%.6f")
        lon = st.sidebar.number_input(f"Longitude #{i+1}", key=f"lon_{i}", format="%.6f")
        if lat != 0 and lon != 0:
            coords[f"Custom_{i+1}"] = (lat, lon)

elif region_option == "Upload Shapefile (.zip)":
    uploaded_file = st.sidebar.file_uploader("Upload Shapefile (.zip)", type=["zip"])
    if uploaded_file:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "uploaded.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmpdir)
            shp_files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".shp")]
            if shp_files:
                gdf = gpd.read_file(shp_files[0])
                gdf = gdf.to_crs(epsg=4326)
                gdf["centroid"] = gdf.geometry.centroid
                for idx, geom in enumerate(gdf["centroid"]):
                    coords[f"Shape_{idx+1}"] = (geom.y, geom.x)
                st.sidebar.success(f"✅ Loaded {len(coords)} centroid(s) from shapefile.")
            else:
                st.sidebar.error("❌ No .shp file found inside ZIP!")

elif region_option == "Upload CSV (lat, lon only)":
    st.sidebar.markdown("📄 **CSV must contain exactly two columns:** `latitude` and `longitude`.")
    csv_file = st.sidebar.file_uploader("Upload CSV file", type=["csv"])
    if csv_file is not None:
        try:
            df_csv = pd.read_csv(csv_file)
            if set(df_csv.columns.str.lower()) >= {"latitude", "longitude"}:
                for i, row in df_csv.iterrows():
                    coords[f"CSV_Point_{i+1}"] = (row["latitude"], row["longitude"])
                st.sidebar.success(f"✅ Loaded {len(coords)} point(s) from CSV file.")
            else:
                st.sidebar.error("❌ CSV must contain 'latitude' and 'longitude' columns only.")
        except Exception as e:
            st.sidebar.error(f"Error reading CSV: {e}")

# --------------------------------------------
# 🗺️ Mini Map Preview in Sidebar
# --------------------------------------------
if coords:
    st.sidebar.markdown("### 🗺️ Location Preview")
    df_map = pd.DataFrame(coords).T.reset_index()
    df_map.columns = ["Region", "Latitude", "Longitude"]

    fig_map = px.scatter_mapbox(
        df_map,
        lat="Latitude",
        lon="Longitude",
        hover_name="Region",
        zoom=4.5,
        height=300,
        color_discrete_sequence=["#0072B2"]
    )
    fig_map.update_layout(
        mapbox_style="open-street-map",
        margin=dict(l=0, r=0, t=0, b=0),
    )
    st.sidebar.plotly_chart(fig_map, use_container_width=True)

# --------------------------------------------
# Year & Frequency
# --------------------------------------------
year_now = datetime.now().year
year_range = st.sidebar.slider("Select Year Range", 2014, year_now, (2020, year_now))
start_date = f"{year_range[0]}-01-01"
end_date = f"{year_range[1]}-12-31"

plot_freq = st.sidebar.selectbox("Plot Frequency", ["Daily", "Weekly", "Monthly", "Yearly"])
download_freq = st.sidebar.selectbox("Download Data Frequency", ["Daily", "Weekly", "Monthly", "Yearly"])

# --------------------------------------------
# Fetch Weather Data (Open-Meteo)
# --------------------------------------------
@st.cache_data(show_spinner=False)
def get_weather_data(lat, lon, start_date, end_date, region):
    url = (
        "https://archive-api.open-meteo.com/v1/era5?"
        f"latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&"
        "daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
        "precipitation_sum,wind_speed_10m_max,wind_speed_10m_mean,wind_direction_10m_dominant"
        "&timezone=Asia/Kuala_Lumpur"
    )
    try:
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        df = pd.DataFrame(data["daily"])
        df["region"] = region
        df["date"] = pd.to_datetime(df["time"])
        return df
    except Exception as e:
        st.error(f"❌ Failed to load data for {region}: {e}")
        return pd.DataFrame()

data_dict = {}
for region, (lat, lon) in coords.items():
    df = get_weather_data(lat, lon, start_date, end_date, region)
    if not df.empty:
        data_dict[region] = df

if not data_dict:
    st.warning("No data available. Please select or upload a region.")
    st.stop()

# --------------------------------------------
# Aggregation
# --------------------------------------------
def aggregate_data(df, freq):
    df = df.copy()
    df.set_index("date", inplace=True)
    freq_map = {"Daily": "D", "Weekly": "W", "Monthly": "M", "Yearly": "Y"}
    rule = freq_map.get(freq, "D")

    df_agg = df.resample(rule).agg({
        "temperature_2m_min": "min",
        "temperature_2m_mean": "mean",
        "temperature_2m_max": "max",
        "precipitation_sum": "sum",
        "wind_speed_10m_mean": "mean",
        "wind_speed_10m_max": "max",
        "wind_direction_10m_dominant": "mean"
    }).reset_index()
    df_agg["region"] = df["region"].iloc[0]
    return df_agg

# --------------------------------------------
# Download Button
# --------------------------------------------
download_df = pd.concat([aggregate_data(df, download_freq) for df in data_dict.values()])
csv_buffer = io.StringIO()
download_df.to_csv(csv_buffer, index=False)
st.sidebar.download_button(
    label=f"📥 Download {download_freq} Data (CSV)",
    data=csv_buffer.getvalue(),
    file_name=f"weather_data_{download_freq.lower()}.csv",
    mime="text/csv"
)

# --------------------------------------------
# Plots — Temperature, Wind, Precipitation
# --------------------------------------------
st.subheader("📈 Weather Trends by Frequency")

agg_data_dict = {region: aggregate_data(df, plot_freq) for region, df in data_dict.items()}

for region, df in agg_data_dict.items():
    with st.expander(f"📍 {region} ({plot_freq})", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            fig_temp = px.line(df, x="date",
                y=["temperature_2m_min", "temperature_2m_mean", "temperature_2m_max"],
                labels={"value": "Temperature (°C)", "date": "Date"},
                title=f"🌡️ Temperature ({region})")
            fig_temp.update_layout(legend_title_text="Type", legend=dict(orientation="h", y=-0.3))
            st.plotly_chart(fig_temp, use_container_width=True)

        with col2:
            fig_wind = px.line(df, x="date",
                y=["wind_speed_10m_mean", "wind_speed_10m_max"],
                labels={"value": "Wind Speed (m/s)", "date": "Date"},
                title=f"💨 Wind Speed ({region})")
            fig_wind.update_layout(legend_title_text="Type", legend=dict(orientation="h", y=-0.3))
            st.plotly_chart(fig_wind, use_container_width=True)

        with col3:
            fig_prep = px.line(df, x="date", y="precipitation_sum",
                labels={"precipitation_sum": "Precipitation (mm)", "date": "Date"},
                title=f"🌧️ Precipitation ({region})")
            fig_prep.update_traces(line_color="#1f77b4")
            st.plotly_chart(fig_prep, use_container_width=True)

# --------------------------------------------
# 🌀 Wind Rose
# --------------------------------------------
st.subheader("🌀 Wind Rose — Direction & Intensity (m/s)")

def plot_wind_rose(df_dict):
    num_points = len(df_dict)
    if num_points == 0:
        st.warning("No region selected for wind rose plot.")
        return

    cols = 2 if num_points > 1 else 1
    rows = ceil(num_points / cols)

    fig = make_subplots(
        rows=rows, cols=cols,
        specs=[[{'type': 'polar'} for _ in range(cols)] for _ in range(rows)],
        subplot_titles=list(df_dict.keys())
    )

    row, col = 1, 1
    for region, df in df_dict.items():
        df = df.dropna(subset=["wind_direction_10m_dominant", "wind_speed_10m_mean"])
        rose = px.bar_polar(
            df, r="wind_speed_10m_mean", theta="wind_direction_10m_dominant",
            color="wind_speed_10m_mean", color_continuous_scale="Turbo",
            range_color=[df["wind_speed_10m_mean"].min(), df["wind_speed_10m_mean"].max()]
        )
        for trace in rose.data:
            trace.name = region
            fig.add_trace(trace, row=row, col=col)
        col += 1
        if col > cols:
            col = 1
            row += 1

    fig.update_layout(
        height=500 * rows,
        width=700 if cols == 1 else 1200,
        showlegend=True,
        legend_title_text="Region",
        coloraxis_colorbar=dict(title="Wind Speed (m/s)"),
        title_x=0.5,
        margin=dict(l=20, r=20, t=60, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

plot_wind_rose(agg_data_dict)

# ======================================================
# 🔮 NEW SECTION — Forecast Data (Windy API Integration)
# ======================================================

st.subheader("🔮 Forecast Data — Windy Point Forecast API")

@st.cache_data(show_spinner=False)
def get_windy_forecast(lat, lon, model="gfs", parameters=None):
    if parameters is None:
        parameters = ["temp", "wind", "precip"]
    url = "https://api.windy.com/api/point-forecast/v2"
    payload = {
        "lat": lat,
        "lon": lon,
        "model": model,
        "parameters": parameters,
        "levels": ["surface"],
        "key": st.secrets.get("WINDY_API_KEY", "DEMO_KEY")
    }
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload))
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.warning(f"⚠️ Windy forecast fetch failed: {e}")
        return {}

def parse_windy_to_df(windy_json, region):
    if not windy_json:
        return pd.DataFrame()
    fc = windy_json.get("forecast", {})
    if not fc:
        return pd.DataFrame()
    ts = fc.get("ts", [])
    if not ts:
        return pd.DataFrame()

    records = []
    for i, t in enumerate(ts):
        rec = {"time": pd.to_datetime(t, unit="s"), "region": region}
        for k, arr in fc.items():
            if k != "ts" and isinstance(arr, list) and i < len(arr):
                rec[k] = arr[i]
        records.append(rec)
    return pd.DataFrame(records)

forecast_dict = {}
for region, (lat, lon) in coords.items():
    windy_json = get_windy_forecast(lat, lon)
    df_fc = parse_windy_to_df(windy_json, region)
    if not df_fc.empty:
        forecast_dict[region] = df_fc

if forecast_dict:
    for region, df_fc in forecast_dict.items():
        with st.expander(f"🌤️ {region} — 7-Day Forecast", expanded=False):
            if "temp" in df_fc.columns:
                fig_fc_temp = px.line(df_fc, x="time", y="temp",
                                      labels={"temp": "Temperature (°C)", "time": "Date"},
                                      title=f"Temperature Forecast ({region})")
                st.plotly_chart(fig_fc_temp, use_container_width=True)
            if "wind" in df_fc.columns:
                fig_fc_wind = px.line(df_fc, x="time", y="wind",
                                      labels={"wind": "Wind Speed (m/s)", "time": "Date"},
                                      title=f"Wind Forecast ({region})")
                st.plotly_chart(fig_fc_wind, use_container_width=True)
            if "precip" in df_fc.columns:
                fig_fc_precip = px.bar(df_fc, x="time", y="precip",
                                       labels={"precip": "Precipitation (mm)", "time": "Date"},
                                       title=f"Precipitation Forecast ({region})")
                st.plotly_chart(fig_fc_precip, use_container_width=True)
else:
    st.info("No forecast data available (Windy API may require valid key or trial usage limit reached).")
