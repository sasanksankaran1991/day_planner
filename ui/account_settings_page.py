from datetime import timedelta

import streamlit as st

from services.telegram_service import TelegramService
from services.user_service import UserService


@st.fragment(run_every=timedelta(seconds=3))
def _poll_telegram_connection(*, user_id: int) -> None:
    if TelegramService.is_telegram_linked(user_id=user_id):
        st.session_state.pop("telegram_connect_url", None)
        st.success("Telegram connected successfully.")
        st.rerun()


def _render_password_section(*, user_id: int) -> None:
    st.markdown("### Change password")

    with st.form("change_password_form"):
        current_password = st.text_input("Current password", type="password")
        new_password = st.text_input("New password", type="password")
        confirm_password = st.text_input("Confirm new password", type="password")

        if st.form_submit_button("Update password", use_container_width=True):
            if not current_password or not new_password or not confirm_password:
                st.error("Fill in all password fields.")
            elif new_password != confirm_password:
                st.error("New passwords do not match.")
            else:
                try:
                    UserService.change_password(
                        user_id=user_id,
                        current_password=current_password,
                        new_password=new_password,
                    )
                    st.success("Password updated.")
                except ValueError as error:
                    st.error(str(error))


def _render_telegram_section(*, user_id: int) -> None:
    st.markdown("### Telegram notifications")

    db_user = UserService.get_by_id(user_id=user_id)

    if db_user and db_user.telegram_chat_id:
        st.success(
            "Telegram is connected. You'll get your full day overview when each block starts."
        )

        if st.button("Disconnect Telegram", key="account_disconnect_telegram"):
            UserService.clear_telegram_link(user_id=user_id)
            st.session_state.pop("telegram_connect_url", None)
            st.success("Telegram disconnected.")
            st.rerun()

        return

    if not TelegramService.is_bot_configured():
        st.warning(
            "Telegram bot is not configured yet. Ask your admin to set "
            "`TELEGRAM_BOT_TOKEN` in `.env` or Secret Manager and restart the app."
        )
        return

    st.caption(
        "Connect Telegram to receive your day schedule when blocks start, "
        "with Done buttons for any earlier blocks still open."
    )

    connect_url = st.session_state.get("telegram_connect_url")

    if connect_url is None:
        if st.button("Connect Telegram", key="start_telegram_connect"):
            try:
                connect_url = TelegramService.start_connect_flow(user_id=user_id)
                st.session_state["telegram_connect_url"] = connect_url
                st.components.v1.html(
                    f'<script>window.open("{connect_url}", "_blank");</script>',
                    height=0,
                )
                st.rerun()
            except ValueError as error:
                st.error(str(error))
        return

    st.info("Telegram opened — tap **Start** in the bot to finish linking.")
    st.link_button(
        "Re-open Telegram",
        connect_url,
        use_container_width=True,
    )

    if st.button("Cancel", key="cancel_telegram_connect"):
        st.session_state.pop("telegram_connect_url", None)
        st.rerun()

    _poll_telegram_connection(user_id=user_id)


def _render_tags_section(*, user_id: int) -> None:
    from services.planner_tag_service import PlannerTagService

    st.markdown("### Tags")

    st.caption(
        "Create tags with colors for planner blocks and todos. "
        "Turn on **Require** to make tag selection mandatory when creating blocks or tasks."
    )

    tags = PlannerTagService.list_tags(user_id=user_id)

    if tags:
        for tag in tags:
            tag_col, toggle_col, delete_col = st.columns([4, 2, 1])

            with tag_col:
                st.markdown(
                    f'<span class="planner-tag-pill" style="background:{tag.color};">'
                    f"{tag.name}</span>",
                    unsafe_allow_html=True,
                )

            with toggle_col:
                require = st.toggle(
                    "Require",
                    value=tag.require_on_create,
                    key=f"tag_require_{tag.id}",
                )

                if require != tag.require_on_create:
                    PlannerTagService.update_require_on_create(
                        user_id=user_id,
                        tag_id=tag.id,
                        require_on_create=require,
                    )
                    st.rerun()

            with delete_col:
                if st.button("✕", key=f"delete_tag_{tag.id}", help="Delete tag"):
                    PlannerTagService.delete_tag(user_id=user_id, tag_id=tag.id)
                    st.rerun()
    else:
        st.info("No tags yet. Add your first tag below.")

    with st.form("create_tag_form"):
        name = st.text_input("Tag name", placeholder="Work, Personal, Health...")
        color = st.color_picker("Color", value="#1E88E5")

        if st.form_submit_button("Add tag", use_container_width=True):
            try:
                PlannerTagService.create_tag(
                    user_id=user_id,
                    name=name,
                    color=color,
                )
                st.success("Tag added.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))


def render_account_settings_page(*, user_id: int) -> None:
    st.title("Settings")

    user = st.session_state["user"]
    st.caption(f"Signed in as {user['display_name']} ({user['username']})")

    _render_password_section(user_id=user_id)

    st.divider()

    _render_telegram_section(user_id=user_id)

    st.divider()

    _render_tags_section(user_id=user_id)
