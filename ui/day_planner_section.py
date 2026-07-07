import streamlit as st

from ui.blocks_tab import render_blocks_tab
from ui.planner_dashboard_tab import render_planner_dashboard_tab
from ui.planner_settings_tab import render_planner_settings_tab


def render_day_planner_section(*, user_id: int, timezone: str) -> None:
    st.title("Day Planner")

    tabs = st.tabs(["Planner", "Dashboard", "Settings"])

    with tabs[0]:
        render_blocks_tab(user_id=user_id, timezone=timezone)

    with tabs[1]:
        render_planner_dashboard_tab(user_id=user_id, timezone=timezone)

    with tabs[2]:
        render_planner_settings_tab(user_id=user_id, timezone=timezone)
