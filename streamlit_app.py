import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd
from math import ceil

def plot_wind_rose(df_dict):
    """
    df_dict: dict of {location_name: dataframe} 
    Each dataframe should have columns: ['winddirection', 'windspeed']
    """

    num_points = len(df_dict)
    if num_points == 0:
        st.warning("No location selected for wind rose plot.")
        return

    # Determine grid size (up to 2 columns per row)
    cols = 2 if num_points > 1 else 1
    rows = ceil(num_points / cols)

    # Create subplots layout
    fig = make_subplots(
        rows=rows, cols=cols,
        specs=[[{'type': 'polar'} for _ in range(cols)] for _ in range(rows)],
        subplot_titles=list(df_dict.keys())
    )

    # Set consistent rose plot size and add traces
    row, col = 1, 1
    for i, (loc, df) in enumerate(df_dict.items()):
        rose = px.bar_polar(
            df,
            r="windspeed",
            theta="winddirection",
            color="windspeed",
            color_continuous_scale="Turbo",
            title=f"{loc}",
            range_color=[df['windspeed'].min(), df['windspeed'].max()]
        )

        for trace in rose.data:
            fig.add_trace(trace, row=row, col=col)

        # Move to next grid position
        col += 1
        if col > cols:
            col = 1
            row += 1

    # Update layout for uniform sizing and legend
    fig.update_layout(
        height=500 * rows,
        width=700 if cols == 1 else 1200,
        coloraxis_colorbar=dict(title="Wind Speed (m/s)"),
        showlegend=True,
        legend_title_text="Location",
        title_x=0.5,
        margin=dict(l=30, r=30, t=60, b=30)
    )

    st.plotly_chart(fig, use_container_width=True)


# Example usage inside your Streamlit app:
# (replace with your actual data collection loop)
if "selected_points" in st.session_state:
    df_dict = {}
    for point in st.session_state["selected_points"]:
        df = get_wind_data_for_point(point)  # <- your function
        df_dict[point["name"]] = df
    plot_wind_rose(df_dict)
