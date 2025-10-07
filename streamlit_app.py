import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import io
from plotly.subplots import make_subplots
import plotly.graph_objects as go
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
# Region Selection
# --------------------------------------------
region_option = st.sidebar.selectbox(
    "Select Region Type",
    ["Predefined Regions", "Custom (points or shapefile)"]
)

coords = []
selected_regions = []

if region_option == "Custom (points or shapefile)":
    st.sidebar.subheader("🗺️ Custom Input Options")

    option = st.sidebar.radio("Choose Input Type", ["Manual Coordinates", "Upload Shapefile (.zip)"])

    if option == "Manual Coordinates":
        n_points = st.sidebar.number_input("Number of Points", min_value=1, max_value=10, value=2)
        for i in range(n_points):
            lat = st.sidebar.number_input(f"Latitude #{i+1}", key=f"lat_{i}", format="%.6f")
            lon = st.sidebar.number_input(f"Longitude #{i+1}", key=f"lon_{i}", format="%.6f")
            coords.append((lat, lon))
        selected_regions = [f"Point #{i+1}" for i in range(len(coords))]

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
                    selected_regions = [f"ShapePoint #{i+1}" for i in range(len(coords))]
                    st.sidebar.success(f"✅ Loaded {len(coords)} points from shapefile.")
                else:
                    st.sidebar.error("❌ No .shp file found inside ZIP!")

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

    selected_regions = st.sidebar.multiselect(
        "Select Regions", options=list(region_coords.keys()), default=["Selangor", "Kuala Lumpur"]
    )
    coords = [region_coords[r] for r in selected_regions]

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
for i, region in enumerate(selected_regions):
    lat, lon = coords[i]
    df = get_weather_data(lat, lon, start_date, end_date, region)
    if df is not None:
        all_data.append(df)

if not all_data:
    st.warning("⚠️ No data loaded. Please select at least one region or upload a shapefile.")
    st.stop()

full_df = pd.concat(all_data)

# --------------------------------------------
# Aggregate data by frequency for download
# --------------------------------------------
def aggregate_data(df, freq):
    df = df.copy()
    df.set_index("date", inplace=True)
    resample_map = {"Daily": "D", "Weekly": "W", "Monthly": "M", "Yearly": "Y"}
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
download_df = pd.concat([aggregate_data(full_df[full_df["region"] == r], download_freq) for r in selected_regions])
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
# 🌡️ Temperature plot
# --------------------------------------------
with col1:
    st.markdown("🌡️ **Temperature (°C)**")
    fig_temp = px.line(
        full_df,
        x="date",
        y=["temperature_2m_min", "temperature_2m_mean", "temperature_2m_max"],
        labels={"value": "Temperature (°C)", "date": "Date"},
    )
    fig_temp.update_layout(
        legend_title_text="Type",
        legend=dict(orientation="h", y=-0.25, x=0),
        margin=dict(l=0, r=0, t=40, b=0)
    )
    st.plotly_chart(fig_temp, use_container_width=True)

# --------------------------------------------
# 💨 Wind Speed + Multi Wind Rose
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
        legend_title_text="Type",
        legend=dict(orientation="h", y=-0.25, x=0)
    )
    st.plotly_chart(fig_wind, use_container_width=True)

    # 🌀 Multi Wind Rose Plot
    st.markdown("🌀 **Wind Rose — Direction & Intensity (m/s)**")

    if len(selected_regions) > 1:
        # Create subplot grid (max 3 per row)
        rows = int(np.ceil(len(selected_regions) / 3))
        cols = min(len(selected_regions), 3)

        fig_multi = make_subplots(rows=rows, cols=cols,
                                  specs=[[{'type': 'polar'}]*cols]*rows,
                                  subplot_titles=selected_regions)

        for idx, region in enumerate(selected_regions):
            df_wind = full_df[full_df["region"] == region].dropna(subset=["wind_direction_10m_dominant", "wind_speed_10m_mean"])
            if df_wind.empty:
                continue
            r, c = divmod(idx, cols)
            fig_multi.add_trace(
                go.Barpolar(
                    r=df_wind["wind_speed_10m_mean"],
                    theta=df_wind["wind_direction_10m_dominant"],
                    marker=dict(color=df_wind["wind_speed_10m_mean"],
                                colorscale=["yellow", "orange", "red"],
                                cmin=0, cmax=df_wind["wind_speed_10m_mean"].max()),
                    name=region
                ),
                row=r+1, col=c+1
            )

        fig_multi.update_layout(
            showlegend=False,
            coloraxis_colorbar=dict(title="Intensity (m/s)"),
            polar=dict(
                angularaxis=dict(direction="clockwise", rotation=90),
                radialaxis=dict(showticklabels=True, ticks="outside")
            ),
            height=400 * rows,
            margin=dict(t=100)
        )
        st.plotly_chart(fig_multi, use_container_width=True)

    else:
        # Single Wind Rose
        df_wind = full_df.dropna(subset=["wind_direction_10m_dominant", "wind_speed_10m_mean"])
        fig_rose = px.bar_polar(
            df_wind,
            r="wind_speed_10m_mean",
            theta="wind_direction_10m_dominant",
            color="wind_speed_10m_mean",
            color_continuous_scale=["yellow", "orange", "red"],
            labels={"wind_speed_10m_mean": "Wind Speed (m/s)", "wind_direction_10m_dominant": "Direction (°)"}
        )
        fig_rose.update_layout(
            polar=dict(
                radialaxis=dict(showticklabels=True, ticks="outside"),
                angularaxis=dict(direction="clockwise", rotation=90)
            ),
            coloraxis_colorbar=dict(title="Intensity (m/s)")
        )
        st.plotly_chart(fig_rose, use_container_width=True)

# --------------------------------------------
# 🌧️ Precipitation plot
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
