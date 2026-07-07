from datetime import datetime

import pytz
import streamlit as st

from services.planner_tag_service import PlannerTagService
from services.todo_service import TodoService
from ui.todos_common import inject_todo_styles
from ui.todos_common import render_add_task_footer
from ui.todos_common import render_legend
from ui.todos_common import render_task_ribbon
from ui.todos_common import render_todo_date_navigator


def render_todos_planner_tab(*, user_id: int, timezone: str) -> None:
    inject_todo_styles()

    tz = pytz.timezone(timezone)
    now = datetime.now(tz).time().replace(second=0, microsecond=0)
    today = datetime.now(tz).date()

    flash = st.session_state.pop("quick_add_flash", None)

    if flash is not None:
        kind, message = flash

        if kind == "error":
            st.error(message)
        else:
            st.success(message)

    view_date = render_todo_date_navigator(today=today)

    items = TodoService.get_dashboard_occurrences(
        user_id=user_id,
        on_date=view_date,
        today=today,
        now=now,
    )

    tags = PlannerTagService.list_tags(user_id=user_id)
    tags_required = PlannerTagService.tags_required_on_create(user_id=user_id)

    if items:
        render_legend()

        for item in items:
            render_task_ribbon(item=item, user_id=user_id, view_date=view_date)
    else:
        st.info("No tasks for this date.")

    render_add_task_footer(
        user_id=user_id,
        plan_date=view_date,
        today=today,
        now=now,
        tags=tags,
        tags_required=tags_required,
        has_tasks=bool(items),
    )
