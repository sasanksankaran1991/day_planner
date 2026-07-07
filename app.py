import streamlit as st

from config.settings import ADMIN_USERNAME
from database.init_db import initialize_database
from database.migrate import migrate_database
from services.gcs_sync import gcs_sync_enabled
from services.gcs_sync import pull_db_from_gcs
from services.user_service import UserService
from ui.account_settings_page import render_account_settings_page
from ui.admin_tab import render_admin_tab
from ui.day_planner_section import render_day_planner_section
from ui.mobile_styles import inject_mobile_styles
from ui.todos_section import render_todos_section


def _require_user():
    if "user" not in st.session_state:
        st.stop()


def todos_page():
    _require_user()
    inject_mobile_styles()
    user = st.session_state["user"]
    render_todos_section(user_id=user["id"], timezone=user["timezone"])


def day_planner_page():
    _require_user()
    inject_mobile_styles()
    user = st.session_state["user"]
    render_day_planner_section(
        user_id=user["id"],
        timezone=user["timezone"],
    )


def settings_page():
    _require_user()
    inject_mobile_styles()
    user = st.session_state["user"]
    render_account_settings_page(user_id=user["id"])


def admin_page():
    _require_user()
    inject_mobile_styles()
    st.title("Admin")
    render_admin_tab()


def render_login():
    inject_mobile_styles()

    st.title("Day Planner")
    st.caption("Plan your day — todos and hourly blocks")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if gcs_sync_enabled():
                pull_db_from_gcs(dispose_connections=True)

            try:
                UserService.ensure_admin_exists()
            except Exception as error:
                import logging

                logging.getLogger(__name__).exception("Admin sync before login failed")
                st.error(
                    f"Could not sync admin user from Secret Manager: {error}. "
                    "Try again in a moment or run: "
                    "gcloud run jobs execute dp-sync-admin --wait"
                )
                st.stop()

            user = UserService.authenticate(
                username=username.strip(),
                password=password,
            )

            if user is None:
                st.error(
                    f"Invalid username or password. "
                    f"Secret Manager admin username is '{ADMIN_USERNAME}' "
                    f"(secret: day-planner-admin-username). "
                    f"Password is in day-planner-admin-password — not the local .env file."
                )
            else:
                st.session_state["user"] = {
                    "id": user.id,
                    "username": user.username,
                    "display_name": user.display_name,
                    "role": user.role.value,
                    "timezone": user.timezone,
                }
                st.rerun()


def logout_page():
    st.session_state.pop("user", None)
    st.rerun()


def render_sidebar_user_panel():
    user = st.session_state["user"]
    st.caption(f"{user['display_name']} · {user['username']}")


def render_dashboard():
    render_sidebar_user_panel()

    pages = [
        st.Page(
            day_planner_page,
            title="Day Planner",
            icon="📅",
            url_path="day-planner",
            default=True,
        ),
        st.Page(todos_page, title="Todos", icon="✅", url_path="todos"),
        st.Page(settings_page, title="Settings", icon="👤", url_path="settings"),
    ]

    if st.session_state["user"]["role"] == "ADMIN":
        pages.append(
            st.Page(admin_page, title="Admin", icon="⚙", url_path="admin")
        )

    pages.append(
        st.Page(logout_page, title="Log out", icon="🚪", url_path="logout")
    )

    navigation = st.navigation(pages, position="sidebar", expanded=True)
    navigation.run()


def main():
    st.set_page_config(
        page_title="Day Planner",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="auto",
    )

    if gcs_sync_enabled() and "gcs_pulled_once" not in st.session_state:
        pull_db_from_gcs(dispose_connections=True)
        st.session_state["gcs_pulled_once"] = True

    migrate_database()
    initialize_database()

    try:
        UserService.ensure_admin_exists()
    except Exception as error:
        import logging

        logging.getLogger(__name__).exception(
            "Admin sync failed (login may still work if DB already has admin): %s",
            error,
        )

    if "user" not in st.session_state:
        render_login()
        return

    render_dashboard()


if __name__ == "__main__":
    main()
