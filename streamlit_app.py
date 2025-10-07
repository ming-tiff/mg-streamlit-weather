import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests
import io

# -----------------------------------
# Page Configuration
# -----------------------------------
st.set_page_config(page_title="Malaysia Regional Weather Dashboard", layout="wide")

# -----------------------------------
# Main Title
# -----------------------------------
st.title("🌤️ Malaysia Regional Weather Dashboard")
st.markdown("""
This dashboard displays **temperature**, **wind**, and **precipitation** data 
across selected regions in Malaysia. You can compare multiple regions, 
analyze daily trends, and visualize wind directions using a wind rose chart.
""")

st.markdown("---")

# -----------------------------------
# Sidebar Controls
# -----------------------------------
st.sidebar.header("⚙️ Dashboard Controls")

# --- Location list ---
locations = {
    "Kuala Lumpur": (3.139, 101.6869),
    "Selangor": (3.0738, 101.5183),
    "Kelantan": (6.1254, 102.2386),
    "Terengganu": (5.3302, 103.1408),
    "Perlis": (6.443, 100.204),
    "Kedah": (6.1248, 100.3675),
    "Perak": (4.5921, 101.0901),
    "Johor": (1.4927, 103.7414),
    "Sabah": (5.9788, 116.0753),
    "Sarawak": (1.553, 110.359)
}

selected_location = st.sidebar.selectbox("Select Region", list(locations.keys()), index=3)

# --- Date range control ---
current_year = datetime.now().year
years = st.sidebar.slider("Select Year Range", 2014, current_year, (2020, current_year))
default_start = datetime(years[0], 1, 1)
default_end = datetime(years[1], 12, 31)

start_date = st.sidebar.date_input("Start Date", default_start)
end_date = st.sidebar.date_input("End Date", default_end)

st.sidebar.markdown("---")

# -----------------------------------
# Weather API Function
# -----------------------------------
def get_weather_data(lat, lon, start_date, end_date):
    url = (
        f"https://archive-api.open-meteo.com/v1/era5?"
        f"latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}"
        f"&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
        f"precipitation_sum,wind_speed_10m_max,wind_speed_10m_mean,wind_direction_10m_dominant"
        f"&timezone=auto"
    )
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data["daily"])
    df["date"] = pd.to_datetime(df["time"])
    df["temp_mean_calc"] = (df["temperature_2m_max"] + df["temperature_2m_min"]) / 2
    return df

# -----------------------------------
# Fetch Data
# -----------------------------------
lat, lon = locations[selected_location]
df = get_weather_data(lat, lon, start_date, end_date)

# -----------------------------------
# Download Button
# -----------------------------------
csv_buffer = io.StringIO()
df.to_csv(csv_buffer, index=False)
st.sidebar.download_button(
    label="📥 Download Weather Data (CSV)",
    data=csv_buffer.getvalue(),
    file_name=f"{selected_location.lower()}_weather_data.csv",
    mime="text/csv"
)

# -----------------------------------
# Charts Section
# -----------------------------------
st.subheader(f"📊 Daily Weather Trends — {selected_location}")

col1, col2, col3 = st.columns(3)

# 🌡️ Temperature Chart
with col1:
    st.markdown("### 🌡️ Temperature (°C)")
    temp_df = pd.melt(
        df,
        id_vars="date",
        value_vars=["temperature_2m_min", "temp_mean_calc", "temperature_2m_max"],
        var_name="Type",
        value_name="Temperature (°C)"
    )
    temp_df["Type"] = temp_df["Type"].replace({
        "temperature_2m_min": "Min",
        "temp_mean_calc": "Mean",
        "temperature_2m_max": "Max"
    })
    fig_temp = px.line(
        temp_df,
        x="date",
        y="Temperature (°C)",
        color="Type",
        color_discrete_sequence=["#ffb3b3", "#ff6666", "#cc0000"],
        title="Daily Temperature — Min / Mean / Max"
    )
    st.plotly_chart(fig_temp, use_container_width=True)

# 🌬️ Wind Speed Chart
with col2:
    st.markdown("### 🌬️ Wind Speed (m/s)")
    wind_df = pd.melt(
        df,
        id_vars="date",
        value_vars=["wind_speed_10m_mean", "wind_speed_10m_max"],
        var_name="Type",
        value_name="Wind Speed (m/s)"
    )
    wind_df["Type"] = wind_df["Type"].replace({
        "wind_speed_10m_mean": "Mean",
        "wind_speed_10m_max": "Max"
    })
    fig_wind = px.line(
        wind_df,
        x="date",
        y="Wind Speed (m/s)",
        color="Type",
        color_discrete_sequence=["#6baed6", "#2171b5"],
        title="Daily Wind Speed — Mean / Max"
    )
    st.plotly_chart(fig_wind, use_container_width=True)

# 🌧️ Precipitation Chart
with col3:
    st.markdown("### 🌧️ Precipitation (mm)")
    fig_prep = px.line(
        df,
        x="date",
        y="precipitation_sum",
        labels={"precipitation_sum": "Precipitation (mm)", "date": "Date"},
        title="Daily Precipitation Sum",
        color_discrete_sequence=["#6a51a3"]
    )
    st.plotly_chart(fig_prep, use_container_width=True)

st.markdown("---")

# -----------------------------------
# 🌀 Wind Rose Chart
# -----------------------------------
st.subheader(f"🌀 Wind Direction Rose — {selected_location}")

fig_rose = go.Figure()

fig_rose.add_trace(go.Barpolar(
    r=df["wind_speed_10m_mean"],
    theta=df["wind_direction_10m_dominant"],
    name="Wind Intensity",
    marker=dict(
        color=df["wind_speed_10m_mean"],
        colorscale="YlOrRd",  # Yellow → Red
        line=dict(color="white", width=1)
    ),
    opacity=0.85
))

fig_rose.update_layout(
    title=f"Wind Rose — {selected_location}",
    polar=dict(
        radialaxis=dict(showticklabels=True, ticks=''),
        angularaxis=dict(direction="clockwise")
    ),
    showlegend=True,
    legend=dict(title="Intensity (m/s)", orientation="h", x=0.3, y=-0.2),
    margin=dict(l=20, r=20, t=50, b=20)
)

st.plotly_chart(fig_rose, use_container_width=True)

st.markdown("✅ **Tip:** The wind rose uses a yellow→red scale where darker red indicates higher wind intensity.")
