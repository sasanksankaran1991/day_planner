import streamlit as st

from ui.todos_dashboard_tab import render_todos_dashboard_tab
from ui.todos_planner_tab import render_todos_planner_tab
from ui.todos_settings_tab import render_todos_settings_tab


def render_todos_section(*, user_id: int, timezone: str) -> None:
    st.title("Todos")

    tabs = st.tabs(["Todos", "Dashboard", "Settings"])

    with tabs[0]:
        render_todos_planner_tab(user_id=user_id, timezone=timezone)

    with tabs[1]:
        render_todos_dashboard_tab(user_id=user_id, timezone=timezone)

    with tabs[2]:
        render_todos_settings_tab(user_id=user_id, timezone=timezone)
