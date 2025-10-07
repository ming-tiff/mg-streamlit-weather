# Success message
display_region_name = selected_region if selected_region != "Custom Coordinates" else "Custom Location"
st.success(f"Loaded {len(full_df)} days of weather data for **{display_region_name}** ({start_date} to {end_date})")

# -----------------------------
# 📈 Compute Median Columns
# -----------------------------
full_df["temp_median"] = full_df[["temp_min", "temp_max"]].median(axis=1)
full_df["wind_median"] = full_df[["wind_min", "wind_max"]].median(axis=1)

# -----------------------------
# 📈 Plot Daily Data
# -----------------------------
st.subheader(f"📊 Daily Weather Trends — {display_region_name}")

tab1, tab2, tab3 = st.tabs(["🌧️ Precipitation", "🌬️ Wind", "🌡️ Temperature"])

with tab1:
    fig = px.line(
        full_df,
        x="date",
        y="precipitation",
        title="Daily Precipitation (mm)",
        labels={"date": "Date", "precipitation": "Precipitation (mm)"},
        color_discrete_sequence=["#1f77b4"],  # blue tone
    )
    fig.update_layout(xaxis_title="Date", yaxis_title="Precipitation (mm)")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    fig = px.line(
        full_df,
        x="date",
        y=["wind_min", "wind_median", "wind_max"],
        title="Daily Wind Speed (Min, Median & Max)",
        labels={"value": "Wind Speed (m/s)", "variable": "Wind"},
        color_discrete_sequence=["#6baed6", "#2171b5", "#08306b"],  # light → dark blue
    )
    fig.update_layout(xaxis_title="Date", yaxis_title="Wind Speed (m/s)")
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    fig = px.line(
        full_df,
        x="date",
        y=["temp_min", "temp_median", "temp_max"],
        title="Daily Temperature (Min, Median & Max)",
        labels={"value": "Temperature (°C)", "variable": "Temperature"},
        color_discrete_sequence=["#ffb3b3", "#ff6666", "#cc0000"],  # light → dark red
    )
    fig.update_layout(xaxis_title="Date", yaxis_title="Temperature (°C)")
    st.plotly_chart(fig, use_container_width=True)
