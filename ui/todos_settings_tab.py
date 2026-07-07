from datetime import datetime
from datetime import timedelta

import pytz
import streamlit as st

from services.todo_service import TodoService
from services.todo_telegram_service import TodoTelegramService
from services.user_service import UserService
from ui.todos_common import format_time
from ui.todos_common import render_edit_series_form


@st.fragment(run_every=timedelta(seconds=3))
def _poll_todo_telegram_connection(*, user_id: int) -> None:
    if TodoTelegramService.is_telegram_linked(user_id=user_id):
        st.session_state.pop("todo_telegram_connect_url", None)
        st.success("Todo Telegram connected successfully.")
        st.rerun()


def _render_todo_telegram_section(*, user_id: int) -> None:
    st.markdown("### Todo Telegram")

    db_user = UserService.get_by_id(user_id=user_id)

    if db_user and db_user.todo_telegram_chat_id:
        st.success(
            "Todo Telegram is connected. You'll get a 5 AM summary, today's tasks, "
            "and reminders 15 minutes before each task and when it ends."
        )

        if st.button("Disconnect Todo Telegram", key="disconnect_todo_telegram"):
            UserService.clear_todo_telegram_link(user_id=user_id)
            st.session_state.pop("todo_telegram_connect_url", None)
            st.success("Todo Telegram disconnected.")
            st.rerun()

        return

    if not TodoTelegramService.is_bot_configured():
        st.warning(
            "Todo Telegram bot is not configured yet. Set "
            "`TODO_TELEGRAM_BOT_TOKEN` in `.env` or Secret Manager and run "
            "`python scripts/run_todo_bot.py`."
        )
        return

    st.caption(
        "Connect the Todos bot for morning summaries and task reminders with "
        "Done / Skip buttons."
    )

    connect_url = st.session_state.get("todo_telegram_connect_url")

    if connect_url is None:
        if st.button("Connect Todo Telegram", key="start_todo_telegram_connect"):
            try:
                connect_url = TodoTelegramService.start_connect_flow(user_id=user_id)
                st.session_state["todo_telegram_connect_url"] = connect_url
                st.components.v1.html(
                    f'<script>window.open("{connect_url}", "_blank");</script>',
                    height=0,
                )
                st.rerun()
            except ValueError as error:
                st.error(str(error))
        return

    st.info("Telegram opened — tap **Start** in the Todos bot to finish linking.")
    st.link_button(
        "Re-open Todo Telegram",
        connect_url,
        use_container_width=True,
    )

    if st.button("Cancel", key="cancel_todo_telegram_connect"):
        st.session_state.pop("todo_telegram_connect_url", None)
        st.rerun()

    _poll_todo_telegram_connection(user_id=user_id)


def render_todos_settings_tab(*, user_id: int, timezone: str) -> None:
    tz = pytz.timezone(timezone)
    today = datetime.now(tz).date()

    _render_todo_telegram_section(user_id=user_id)

    st.divider()
    st.subheader("Recurring tasks")
    st.caption(
        "Edit a series here — changes apply from today forward. "
        "Past completed or skipped tasks are not changed."
    )

    recurring_todos = TodoService.list_recurring_todos(owner_id=user_id)

    if not recurring_todos:
        st.info("No recurring tasks yet. Create one from the Todos tab with Advanced options.")
        return

    for todo in recurring_todos:
        tag_html = ""

        if todo.get("tag_name") and todo.get("tag_color"):
            tag_html = f" · {todo['tag_name']}"

        end_label = (
            todo["recurrence_end_date"].strftime("%d %b %Y")
            if todo["recurrence_end_date"]
            else "—"
        )

        with st.container(border=True):
            st.markdown(
                f"**{todo['title']}**{tag_html}"
            )
            st.caption(
                f"{format_time(todo['default_time'])} · "
                f"{todo['recurrence_label']} · "
                f"from {todo['first_date'].strftime('%d %b %Y')} "
                f"to {end_label} · "
                f"{todo['occurrence_count']} scheduled days"
            )

            if todo["description"]:
                st.write(todo["description"])

            edit_col, delete_col = st.columns(2)

            with edit_col:
                if st.button(
                    "Edit series",
                    key=f"settings_edit_{todo['todo_id']}",
                    use_container_width=True,
                ):
                    st.session_state[f"show_edit_todo_{todo['todo_id']}"] = True
                    st.rerun()

            with delete_col:
                if st.button(
                    "Delete series",
                    key=f"settings_delete_{todo['todo_id']}",
                    use_container_width=True,
                ):
                    TodoService.delete_todo(todo_id=todo["todo_id"], user_id=user_id)
                    st.success("Recurring task deleted.")
                    st.rerun()

        if st.session_state.get(f"show_edit_todo_{todo['todo_id']}"):
            with st.container(border=True):
                st.markdown("**Edit task series**")
                st.caption(
                    f"Changes apply from {today.strftime('%A, %d %b %Y')} forward."
                )
                edit_todo = TodoService.get_todo_for_edit(
                    todo_id=todo["todo_id"],
                    owner_id=user_id,
                )
                render_edit_series_form(
                    todo=edit_todo,
                    user_id=user_id,
                    effective_from=today,
                )
