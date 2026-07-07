import streamlit as st

from config.settings import DEFAULT_TIMEZONE
from services.user_service import UserService
from utils.enums import UserRole


def render_admin_tab():
    st.subheader("User management")

    with st.form("create_user_form"):
        username = st.text_input("Username")
        display_name = st.text_input("Display name")
        password = st.text_input("Temporary password", type="password")
        role = st.selectbox("Role", options=[UserRole.USER, UserRole.ADMIN])

        if st.form_submit_button("Create user", use_container_width=True):
            if not username.strip() or not display_name.strip() or not password:
                st.error("All fields are required.")
            else:
                try:
                    UserService.create_user(
                        username=username.strip(),
                        password=password,
                        display_name=display_name.strip(),
                        role=role,
                        timezone=DEFAULT_TIMEZONE,
                    )
                    st.success(f"User '{username}' created.")
                    st.rerun()

                except ValueError as error:
                    st.error(str(error))

    st.divider()
    st.markdown("**Existing users**")

    users = UserService.list_users()

    for user in users:
        st.write(
            f"- **{user.display_name}** (@{user.username}) — "
            f"{user.role.value} — {user.timezone}"
        )
