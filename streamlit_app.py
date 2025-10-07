import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import geopandas as gpd
from shapely.geometry import Point

st.set_page_config(page_title="🌦️ Malaysia Regional Weather Dashboard", layout="wide")
st.sidebar.markdown("Data Source: [Open-Meteo API](https://open-meteo.com/)")

# -----------------------------
# Sidebar Configuration
# -----------------------------
st.sidebar.header("⚙️ Configuration")

region_option = st.sidebar.selectbox(
    "Select Region",
    ["Selangor", "Kuala Lumpur", "Kelantan", "Terengganu", "Perlis", "Kedah", "Perak", "Johor", "Sabah", "Sarawak", "Custom (points or shapefile)"],
)

start_date = st.sidebar.date_input("Start Date", datetime(2016, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime(2025, 1, 1))

st.sidebar.markdown("---")

# -----------------------------
# Multiple Custom Coordinates or Shapefile
# -----------------------------
coords = []

if region_option == "Custom (points or shapefile)":
    st.sidebar.subheader("🗺️ Custom Input Options")

    option = st.sidebar.radio("Choose input type", ["Manual Coordinates", "Upload Shapefile (.zip)"])

    if option == "Manual Coordinates":
        st.sidebar.markdown("Enter multiple coordinates (Lat, Lon):")
        n_points = st.sidebar.number_input("Number of points", min_value=1, max_value=10, value=2)
        for i in range(n_points):
            lat = st.sidebar.number_input(f"Latitude #{i+1}", key=f"lat_{i}")
            lon = st.sidebar.number_input(f"Longitude #{i+1}", key=f"lon_{i}")
            coords.append((lat, lon))

    elif option == "Upload Shapefile (.zip)":
        uploaded_file = st.sidebar.file_uploader("Upload shapefile (.zip)", type=["zip"])
        if uploaded_file is not None:
            import tempfile, zipfile, os
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
                    st.sidebar.success(f"Loaded {len(coords)} points from shapefile ✅")
                else:
                    st.sidebar.error("No .shp file found inside ZIP!")

else:
    # Predefined regional coordinates
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

# -----------------------------
# Function to fetch data
# -----------------------------
@st.cache_data
def get_weather_data(lat, lon, location_name):
    url = (
        f"https://archive-api.open-meteo.com/v1/era5?"
        f"latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}"
        f"&daily=temperature_2m_min,temperature_2m_max,precipitation_sum,windspeed_10m_min,windspeed_10m_max"
        f"&timezone=auto"
    )
    r = requests.get(url)
    if r.status_code != 200:
        return None
    data = r.json()
    df = pd.DataFrame({
        "date": data["daily"]["time"],
        "temp_min": data["daily"]["temperature_2m_min"],
        "temp_max": data["daily"]["temperature_2m_max"],
        "precipitation": data["daily"]["precipitation_sum"],
        "wind_min": data["daily"]["windspeed_10m_min"],
        "wind_max": data["daily"]["windspeed_10m_max"],
    })
    df["date"] = pd.to_datetime(df["date"])
    df["location"] = location_name
    df["temp_median"] = df[["temp_min", "temp_max"]].median(axis=1)
    df["wind_median"] = df[["wind_min", "wind_max"]].median(axis=1)
    return df

# -----------------------------
# Combine data from multiple points
# -----------------------------
full_df = pd.DataFrame()

for i, (lat, lon) in enumerate(coords):
    loc_name = f"Custom-{i+1}" if region_option == "Custom (points or shapefile)" else region_option
    df_part = get_weather_data(lat, lon, loc_name)
    if df_part is not None:
        full_df = pd.concat([full_df, df_part])

if full_df.empty:
    st.error("⚠️ No data loaded. Please check your coordinates or date range.")
    st.stop()

# -----------------------------
# Display Summary
# -----------------------------
st.success(f"Loaded {len(full_df)} days of weather data for {len(coords)} location(s).")

# -----------------------------
# Side-by-side plots
# -----------------------------
st.subheader("📈 Daily Weather Trends")

col1, col2, col3 = st.columns(3)

with col1:
    fig1 = px.line(
        full_df,
        x="date",
        y="precipitation",
        color="location",
        title="Precipitation (mm)",
        labels={"date": "Date", "precipitation": "mm"},
    )
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    fig2 = px.line(
        full_df,
        x="date",
        y=["wind_min", "wind_median", "wind_max"],
        color_discrete_sequence=["#6baed6", "#2171b5", "#08306b"],
        title="Wind Speed (m/s)",
        labels={"value": "Wind (m/s)", "variable": "Type"},
    )
    st.plotly_chart(fig2, use_container_width=True)

with col3:
    fig3 = px.line(
        full_df,
        x="date",
        y=["temp_min", "temp_median", "temp_max"],
        color_discrete_sequence=["#ffb3b3", "#ff6666", "#cc0000"],
        title="Temperature (°C)",
        labels={"value": "Temperature (°C)", "variable": "Type"},
    )
    st.plotly_chart(fig3, use_container_width=True)
