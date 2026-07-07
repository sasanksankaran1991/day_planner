import streamlit as st

from services.user_service import UserService


def render_settings_sidebar():
    user = st.session_state["user"]

    with st.sidebar:
        st.header("Settings")

        timezones = [
            "Asia/Kolkata",
            "Asia/Dubai",
            "Asia/Singapore",
            "Europe/London",
            "America/New_York",
            "UTC",
        ]

        selected_tz = st.selectbox(
            "Timezone",
            options=timezones,
            index=timezones.index(user["timezone"])
            if user["timezone"] in timezones
            else 0,
        )

        if selected_tz != user["timezone"]:
            updated = UserService.update_timezone(
                user_id=user["id"],
                timezone=selected_tz,
            )
            st.session_state["user"]["timezone"] = updated.timezone
            st.success(f"Timezone updated to {selected_tz}")
