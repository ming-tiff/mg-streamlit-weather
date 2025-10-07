import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io
from plotly.subplots import make_subplots
from plotly import graph_objects as go
import numpy as np
import geopandas as gpd
import tempfile, zipfile, os

# --------------------------------------------
# Page Setup
# --------------------------------------------
st.set_page_config(page_title="🌤️ Malaysia Regional Weather Dashboard", layout="wide")
st.title("🌤️ Malaysia Regional Weather Dashboard")

st.markdown("""
This dashboard shows **daily, weekly, monthly, and yearly** summaries of 
**temperature (°C)**, **wind speed (m/s)**, **wind direction**, and **precipitation (mm)** 
for multiple regions in Malaysia using the **Open-Meteo API**.
""")

# --------------------------------------------
# Sidebar — Controls
# --------------------------------------------
st.sidebar.header("⚙️ Configuration")
st.sidebar.markdown("---")

# --------------------------------------------
# Region selection
# --------------------------------------------
region_option = st.sidebar.selectbox(
    "Select Region or Custom Input",
    ["Selangor", "Kuala Lumpur", "Kelantan", "Terengganu", "Perlis", "Kedah", "Perak", "Johor", "Sabah", "Sarawak", "Custom (points or shapefile or CSV)"]
)

coords = []

# --------------------------------------------
# Handle custom coordinate or shapefile/csv
# --------------------------------------------
if region_option == "Custom (points or shapefile or CSV)":
    st.sidebar.subheader("🗺️ Custom Input Options")

    option = st.sidebar.radio("Choose Input Type", ["Manual Coordinates", "Upload Shapefile (.zip)", "Upload CSV (lat/lon)"])

    if option == "Manual Coordinates":
        n_points = st.sidebar.number_input("Number of Points", min_value=1, max_value=10, value=2)
        for i in range(n_points):
            lat = st.sidebar.number_input(f"Latitude #{i+1}", key=f"lat_{i}", format="%.6f")
            lon = st.sidebar.number_input(f"Longitude #{i+1}", key=f"lon_{i}", format="%.6f")
            coords.append((lat, lon))

    elif option == "Upload Shapefile (.zip)":
        uploaded_file = st.sidebar.file_uploader("Upload Shapefile (.zip)", type=["zip"])
        if uploaded_file is not None:
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
                    for geom in gdf["centroid"]:
                        coords.append((geom.y, geom.x))
                    st.sidebar.success(f"✅ Loaded {len(coords)} centroid points from shapefile.")
                else:
                    st.sidebar.error("❌ No .shp file found inside ZIP!")

    elif option == "Upload CSV (lat/lon)":
        csv_file = st.sidebar.file_uploader("Upload CSV File", type=["csv"], help="CSV must contain only 'latitude' and 'longitude' columns.")
        if csv_file is not None:
            df_csv = pd.read_csv(csv_file)
            if all(col in df_csv.columns for col in ["latitude", "longitude"]):
                coords = list(zip(df_csv["latitude"], df_csv["longitude"]))
                st.sidebar.success(f"✅ Loaded {len(coords)} points from CSV.")
            else:
                st.sidebar.error("❌ CSV must have columns named 'latitude' and 'longitude' only.")
else:
    region_coords = {
        "Selangor": (3.0738, 101.5183),
        "Kuala Lumpur": (3.139, 101.6869),
        "Kelantan": (6.1254, 102.2381),
        "Terengganu": (5.3302, 103.1408),
        "Perlis": (6.4444, 100.2048),
        "Kedah": (6.1184, 100.3685),
        "Perak": (4.5921, 101.0901),
        "Johor": (1.4927, 103.7414),
        "Sabah": (5.9788, 116.0753),
        "Sarawak": (1.553, 110.359),
    }
    coords = [region_coords[region_option]]

# --------------------------------------------
# 🗺️ Mini Map Preview in Sidebar
# --------------------------------------------
if coords:
    st.sidebar.markdown("### 🗺️ Location Preview")

    df_map = pd.DataFrame(coords, columns=["Latitude", "Longitude"])
    df_map["Region"] = [f"Point {i+1}" for i in range(len(df_map))]

    fig_map = px.scatter_mapbox(
        df_map,
        lat="Latitude",
        lon="Longitude",
        hover_name="Region",
        zoom=5,
        height=300,
        color_discrete_sequence=["#FF0000"],  # 🔴 Red marker
    )

    fig_map.update_layout(
        mapbox_style="open-street-map",
        dragmode="pan",  # Allow map movement
        margin=dict(l=0, r=0, t=0, b=0),
    )

    st.sidebar.plotly_chart(fig_map, use_container_width=True)
else:
    st.sidebar.info("No coordinates available yet. Add or upload points to preview them on the map.")

# --------------------------------------------
# Year range selector
# --------------------------------------------
current_year = datetime.now().year
years = st.sidebar.slider("Select Year Range", 2014, current_year, (2020, current_year))
start_date = f"{years[0]}-01-01"
end_date = f"{years[1]}-12-31"

# Download frequency
download_freq = st.sidebar.selectbox("Download Data Frequency", ["Daily", "Weekly", "Monthly", "Yearly"])

# --------------------------------------------
# Function — Fetch Open-Meteo API Data
# --------------------------------------------
@st.cache_data(show_spinner=False)
def get_weather_data(lat, lon, start_date, end_date, region_name):
    url = (
        "https://archive-api.open-meteo.com/v1/era5?"
        f"latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&"
        "daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
        "precipitation_sum,wind_speed_10m_max,wind_speed_10m_mean,wind_direction_10m_dominant"
        "&timezone=Asia/Kuala_Lumpur"
    )
    r = requests.get(url)
    if r.status_code != 200:
        st.error(f"Failed to load weather data for {region_name}")
        return None

    data = r.json()
    df = pd.DataFrame(data["daily"])
    df["region"] = region_name
    df["date"] = pd.to_datetime(df["time"])
    return df

# --------------------------------------------
# Load data for all regions
# --------------------------------------------
all_data = []
for i, (lat, lon) in enumerate(coords):
    df = get_weather_data(lat, lon, start_date, end_date, f"Point {i+1}")
    if df is not None:
        all_data.append(df)

if not all_data:
    st.stop()

full_df = pd.concat(all_data)

# --------------------------------------------
# Aggregate data by frequency for download
# --------------------------------------------
def aggregate_data(df, freq):
    df = df.copy()
    df.set_index("date", inplace=True)
    resample_map = {
        "Daily": "D",
        "Weekly": "W",
        "Monthly": "M",
        "Yearly": "Y"
    }
    freq_code = resample_map.get(freq, "D")

    agg_df = df.resample(freq_code).agg({
        "temperature_2m_min": "min",
        "temperature_2m_mean": "mean",
        "temperature_2m_max": "max",
        "precipitation_sum": "sum",
        "wind_speed_10m_max": "max",
        "wind_speed_10m_mean": "mean",
        "wind_direction_10m_dominant": "mean"
    }).reset_index()
    agg_df["region"] = df["region"].iloc[0]
    return agg_df

# --------------------------------------------
# Download button
# --------------------------------------------
download_df = pd.concat([aggregate_data(full_df[full_df["region"] == r], download_freq) for r in full_df["region"].unique()])
csv_buffer = io.StringIO()
download_df.to_csv(csv_buffer, index=False)
st.sidebar.download_button(
    label=f"📥 Download {download_freq} Data (CSV)",
    data=csv_buffer.getvalue(),
    file_name=f"weather_data_{download_freq.lower()}.csv",
    mime="text/csv"
)

# --------------------------------------------
# Layout — 3 columns for plots
# --------------------------------------------
st.subheader("📊 Weather Trends")
col1, col2, col3 = st.columns(3)

# --------------------------------------------
# Temperature plot
# --------------------------------------------
with col1:
    st.markdown("🌡️ **Temperature (°C)**")
    fig_temp = px.line(
        full_df,
        x="date",
        y=["temperature_2m_min", "temperature_2m_mean", "temperature_2m_max"],
        labels={"value": "Temperature (°C)", "date": "Date"},
    )
    fig_temp.update_traces(line=dict(width=1.5))
    fig_temp.update_layout(
        showlegend=True,
        legend_title_text="Type",
        legend=dict(orientation="h", y=-0.25, x=0),
        margin=dict(l=0, r=0, t=40, b=0)
    )
    st.plotly_chart(fig_temp, use_container_width=True)

# --------------------------------------------
# Wind plot + Wind rose
# --------------------------------------------
with col2:
    st.markdown("💨 **Wind Speed (m/s)**")
    fig_wind = px.line(
        full_df,
        x="date",
        y=["wind_speed_10m_mean", "wind_speed_10m_max"],
        labels={"value": "Wind Speed (m/s)", "date": "Date"},
    )
    fig_wind.update_layout(
        showlegend=True,
        legend_title_text="Type",
        legend=dict(orientation="h", y=-0.25, x=0)
    )
    st.plotly_chart(fig_wind, use_container_width=True)

    # Wind Rose
    st.markdown("🌀 **Wind Rose — Direction & Intensity (m/s)**")
    rose_dict = {region: full_df[full_df["region"] == region] for region in full_df["region"].unique()}
    num_plots = len(rose_dict)
    cols = 2 if num_plots > 1 else 1
    rows = int(np.ceil(num_plots / cols))

    fig_rose = make_subplots(rows=rows, cols=cols, specs=[[{'type': 'polar'} for _ in range(cols)] for _ in range(rows)],
                             subplot_titles=list(rose_dict.keys()))

    row, col_num = 1, 1
    for region, df_region in rose_dict.items():
        df_wind = df_region.dropna(subset=["wind_direction_10m_dominant", "wind_speed_10m_mean"])
        fig_part = px.bar_polar(
            df_wind,
            r="wind_speed_10m_mean",
            theta="wind_direction_10m_dominant",
            color="wind_speed_10m_mean",
            color_continuous_scale=["yellow", "orange", "red"],
            labels={"wind_speed_10m_mean": "Wind Speed (m/s)", "wind_direction_10m_dominant": "Direction (°)"}
        )
        for trace in fig_part.data:
            fig_rose.add_trace(trace, row=row, col=col_num)
        col_num += 1
        if col_num > cols:
            col_num = 1
            row += 1

    fig_rose.update_layout(
        height=400 * rows,
        coloraxis_colorbar=dict(title="Intensity (m/s)"),
        showlegend=False,
        title_x=0.5
    )
    st.plotly_chart(fig_rose, use_container_width=True)

# --------------------------------------------
# Precipitation plot
# --------------------------------------------
with col3:
    st.markdown("🌧️ **Precipitation (mm)**")
    fig_prep = px.line(
        full_df,
        x="date",
        y="precipitation_sum",
        labels={"precipitation_sum": "Precipitation (mm)", "date": "Date"}
    )
    fig_prep.update_traces(line_color="#1f77b4", line_width=1.5)
    st.plotly_chart(fig_prep, use_container_width=True)
