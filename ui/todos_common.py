from datetime import date
from datetime import time
from datetime import timedelta
from typing import Optional

import streamlit as st

from services.todo_service import TodoService
from services.user_service import UserService
from ui.tag_helpers import render_tag_selector
from ui.tag_helpers import resolve_tag_id_from_session
from utils.enums import OccurrenceStatus
from utils.enums import RecurrenceType
from utils.recurrence import generate_occurrence_dates
from utils.time_slots import format_time_label
from utils.time_slots import generate_time_slots
from utils.time_slots import next_available_slot

TIME_SLOTS = generate_time_slots()
TIME_LABELS = [format_time_label(slot) for slot in TIME_SLOTS]

RECURRENCE_LABELS = {
    RecurrenceType.ONE_TIME: "One time",
    RecurrenceType.DAILY: "Daily",
    RecurrenceType.WEEKLY: "Weekly",
    RecurrenceType.WEEKDAYS: "Weekdays (Mon–Fri)",
    RecurrenceType.MONTHLY: "Monthly",
    RecurrenceType.CUSTOM: "Custom days",
}

WEEKDAY_OPTIONS = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}

TASK_STYLES = {
    "current": {"text": "#3E2723", "badge": "Now"},
    "overdue": {"text": "#3E2723", "badge": "Pending"},
    "skipped": {"text": "#3E2723", "badge": "Skipped"},
    "done": {"text": "#1B5E20", "badge": "Done"},
    "upcoming": {"text": "#0D47A1", "badge": "Upcoming"},
    "postponed": {"text": "#E65100", "badge": "Postponed"},
}


def inject_todo_styles() -> None:
    st.markdown(
        """
        <style>
        .todo-legend {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem 1rem;
            margin: 0 0 0.9rem;
        }
        .todo-legend-item {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            font-size: 0.85rem;
            color: #424242;
        }
        .todo-legend-dot {
            width: 11px;
            height: 11px;
            border-radius: 999px;
            display: inline-block;
        }
        .plan-date-nav-marker,
        .plan-date-nav-wrap-marker,
        .plan-date-nav-section-start,
        .plan-date-nav-extra {
            display: none !important;
        }
        [data-testid="stHorizontalBlock"]:has(.plan-date-nav-wrap-marker) {
            background: rgba(127, 127, 127, 0.12) !important;
            border: 1px solid rgba(127, 127, 127, 0.22) !important;
            border-radius: 14px !important;
            padding: 0.45rem 0.55rem !important;
            margin-bottom: 0.5rem !important;
            width: 100% !important;
            max-width: 100% !important;
            align-items: center !important;
        }
        [data-testid="stHorizontalBlock"]:has(.plan-date-nav-wrap-marker) [data-testid="stMarkdown"] p {
            margin: 0 !important;
            text-align: center;
            line-height: 1.2;
        }
        .plan-date-nav-label {
            font-size: 1.02rem;
            font-weight: 700;
            margin: 0;
            color: inherit;
        }
        .plan-date-nav-today {
            display: inline-block;
            margin-left: 0.45rem;
            padding: 0.1rem 0.45rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            background: rgba(30, 136, 229, 0.18);
            color: #64B5F6;
            vertical-align: middle;
        }
        [data-testid="stHorizontalBlock"]:has(.plan-date-nav-wrap-marker) [data-testid="stButton"] {
            width: 100%;
        }
        [data-testid="stHorizontalBlock"]:has(.plan-date-nav-wrap-marker) [data-testid="stButton"] > button {
            min-height: 2.1rem !important;
            width: 100% !important;
            padding: 0.15rem 0.35rem !important;
            border-radius: 8px !important;
            border: none !important;
            background: transparent !important;
            color: inherit !important;
            font-size: 1.15rem !important;
            font-weight: 700 !important;
            box-shadow: none !important;
        }
        [data-testid="stHorizontalBlock"]:has(.plan-date-nav-wrap-marker) [data-testid="stButton"] > button:hover {
            background: rgba(127, 127, 127, 0.18) !important;
        }
        [data-testid="stElementContainer"]:has(.plan-date-nav-extra) [data-testid="stDateInput"] {
            margin-top: 0 !important;
            margin-bottom: 0.35rem !important;
        }
        [data-testid="stElementContainer"]:has(.plan-date-nav-extra) [data-testid="stDateInput"] > div {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        [data-testid="stElementContainer"]:has(.plan-date-nav-jump) [data-testid="stButton"] > button {
            min-height: 1.6rem !important;
            font-size: 0.82rem !important;
            font-weight: 600 !important;
            opacity: 0.85;
        }
        .todo-ribbon-marker {
            display: none !important;
        }
        [data-testid="stHorizontalBlock"]:has(.todo-ribbon-marker) {
            background: var(--ribbon-bg, #ECEFF1) !important;
            border: 1px solid var(--ribbon-border, #B0BEC5) !important;
            border-radius: 10px;
            padding: 4px 10px !important;
            margin-bottom: 0.45rem !important;
            align-items: center !important;
            gap: 0.2rem !important;
        }
        [data-testid="stHorizontalBlock"]:has(.todo-ribbon-current) {
            background: #FFE082 !important;
            border-color: #FFA000 !important;
        }
        [data-testid="stHorizontalBlock"]:has(.todo-ribbon-overdue) {
            background: #FFCDD2 !important;
            border-color: #E53935 !important;
        }
        [data-testid="stHorizontalBlock"]:has(.todo-ribbon-skipped) {
            background: #FFCDD2 !important;
            border-color: #C62828 !important;
        }
        [data-testid="stHorizontalBlock"]:has(.todo-ribbon-done) {
            background: #A5D6A7 !important;
            border-color: #2E7D32 !important;
        }
        [data-testid="stHorizontalBlock"]:has(.todo-ribbon-upcoming) {
            background: #BBDEFB !important;
            border-color: #1E88E5 !important;
        }
        [data-testid="stHorizontalBlock"]:has(.todo-ribbon-postponed) {
            background: #FFF3E0 !important;
            border-color: #FB8C00 !important;
        }
        [data-testid="stHorizontalBlock"]:has(.todo-ribbon-marker) > [data-testid="column"] {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        [data-testid="stHorizontalBlock"]:has(.todo-ribbon-marker) > [data-testid="column"]:first-child {
            justify-content: flex-start !important;
        }
        [data-testid="stHorizontalBlock"]:has(.todo-ribbon-marker) > [data-testid="column"]:last-child {
            justify-content: flex-end !important;
        }
        [data-testid="stHorizontalBlock"]:has(.todo-ribbon-marker) [data-testid="stButton"] > button {
            min-height: 28px !important;
            max-height: 28px !important;
            min-width: 28px !important;
            max-width: 28px !important;
            width: 28px !important;
            height: 28px !important;
            padding: 0 !important;
            font-size: 0.88rem !important;
            border-radius: 6px !important;
            background: rgba(255, 255, 255, 0.6) !important;
            border: 1px solid rgba(0, 0, 0, 0.08) !important;
        }
        .todo-ribbon-title {
            font-weight: 600;
            font-size: 0.95rem;
            line-height: 1.35;
        }
        .todo-recurrence-pill {
            display: inline-block;
            font-size: 0.72rem;
            font-weight: 700;
            color: #455A64;
            background: rgba(255, 255, 255, 0.55);
            border: 1px solid rgba(0, 0, 0, 0.08);
            border-radius: 999px;
            padding: 0.1rem 0.45rem;
            margin-left: 0.35rem;
            vertical-align: middle;
        }
        .add-task-tail {
            display: none;
        }
        [data-testid="stVerticalBlock"]:has(.add-task-tail) [data-testid="stButton"] > button {
            border: 2px dashed #90CAF9 !important;
            background: linear-gradient(180deg, #F8FBFF 0%, #E8F4FD 100%) !important;
            color: #1565C0 !important;
            min-height: 54px;
            border-radius: 10px;
            font-weight: 700;
            font-size: 1rem;
            letter-spacing: 0.02em;
        }
        [data-testid="stVerticalBlock"]:has(.add-task-tail) [data-testid="stButton"] > button:hover {
            border-color: #1E88E5 !important;
            background: linear-gradient(180deg, #E3F2FD 0%, #BBDEFB 100%) !important;
            box-shadow: 0 3px 10px rgba(30, 136, 229, 0.18);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_time(value: time) -> str:
    return value.strftime("%H:%M")


def render_todo_date_navigator(*, today: date) -> date:
    if "todo_plan_date" not in st.session_state:
        st.session_state["todo_plan_date"] = today

    plan_date = st.session_state["todo_plan_date"]
    date_label = plan_date.strftime("%A, %d %b %Y")
    today_badge = (
        '<span class="plan-date-nav-today">Today</span>' if plan_date == today else ""
    )

    st.markdown('<div class="plan-date-nav-section-start"></div>', unsafe_allow_html=True)

    prev_col, date_col, cal_col, next_col = st.columns(
        [0.45, 8, 0.45, 0.45],
        gap="small",
        vertical_alignment="center",
    )

    with prev_col:
        st.markdown('<div class="plan-date-nav-wrap-marker"></div>', unsafe_allow_html=True)
        if st.button("‹", key="todo_date_prev", help="Previous day", use_container_width=True):
            st.session_state["todo_plan_date"] = plan_date - timedelta(days=1)
            st.session_state.pop("show_todo_date_picker", None)
            st.rerun()

    with date_col:
        st.markdown(
            f'<p class="plan-date-nav-label">{date_label}{today_badge}</p>',
            unsafe_allow_html=True,
        )

    with cal_col:
        if st.button("📅", key="todo_date_calendar", help="Pick a date", use_container_width=True):
            st.session_state["show_todo_date_picker"] = not st.session_state.get(
                "show_todo_date_picker",
                False,
            )
            st.rerun()

    with next_col:
        if st.button("›", key="todo_date_next", help="Next day", use_container_width=True):
            st.session_state["todo_plan_date"] = plan_date + timedelta(days=1)
            st.session_state.pop("show_todo_date_picker", None)
            st.rerun()

    if st.session_state.get("show_todo_date_picker"):
        st.markdown('<div class="plan-date-nav-extra"></div>', unsafe_allow_html=True)
        picked = st.date_input(
            "Choose date",
            value=plan_date,
            key="todo_date_picker_widget",
            label_visibility="collapsed",
        )

        if picked != plan_date:
            st.session_state["todo_plan_date"] = picked
            st.session_state.pop("show_todo_date_picker", None)
            st.rerun()

    if plan_date != today:
        st.markdown('<div class="plan-date-nav-jump"></div>', unsafe_allow_html=True)
        if st.button("Jump to today", key="todo_date_today", use_container_width=True):
            st.session_state["todo_plan_date"] = today
            st.session_state.pop("show_todo_date_picker", None)
            st.rerun()

    return st.session_state["todo_plan_date"]


def render_legend() -> None:
    items = [
        ("Done", "#A5D6A7"),
        ("Pending", "#FFCDD2"),
        ("Skipped", "#FFCDD2"),
        ("Postponed", "#FFF3E0"),
        ("Upcoming", "#BBDEFB"),
        ("Now", "#FFE082"),
    ]
    legend_html = '<div class="todo-legend">'

    for label, color in items:
        legend_html += (
            f'<span class="todo-legend-item">'
            f'<span class="todo-legend-dot" style="background:{color};"></span>'
            f"{label}</span>"
        )

    legend_html += "</div>"
    st.markdown(legend_html, unsafe_allow_html=True)


def render_postpone_form(*, occurrence_id: int, user_id: int, current_date: date) -> None:
    with st.form(f"postpone_{occurrence_id}"):
        col1, col2 = st.columns(2)

        with col1:
            new_date = st.date_input(
                "New date",
                value=current_date,
                key=f"postpone_date_{occurrence_id}",
            )

        with col2:
            new_time = st.time_input(
                "New time",
                value=time(9, 0),
                key=f"postpone_time_{occurrence_id}",
            )

        if st.form_submit_button("Confirm postpone", use_container_width=True):
            TodoService.postpone_occurrence(
                occurrence_id=occurrence_id,
                user_id=user_id,
                new_date=new_date,
                new_time=new_time,
            )
            st.session_state.pop(f"show_postpone_{occurrence_id}", None)
            st.rerun()


def render_task_ribbon(*, item: dict, user_id: int, view_date: date) -> None:
    occurrence_id = item["occurrence_id"]
    todo_id = item["todo_id"]
    state = item["visual_state"]
    style = TASK_STYLES[state]
    status = item["status"]
    is_resolved = status in (OccurrenceStatus.DONE, OccurrenceStatus.SKIPPED)
    is_actionable = status in (
        OccurrenceStatus.PENDING,
        OccurrenceStatus.POSTPONED,
    )

    tag_html = ""

    if item.get("tag_name") and item.get("tag_color"):
        tag_html = (
            f'<span class="planner-tag-pill" style="background:'
            f'{item["tag_color"]};">{item["tag_name"]}</span> '
        )

    recurrence_html = ""

    if item.get("recurrence_label"):
        recurrence_html = (
            f'<span class="todo-recurrence-pill">{item["recurrence_label"]}</span>'
        )

    meta = ""

    if not item["is_owner"]:
        meta = f' <span style="font-size:0.8rem;color:#616161;">· {item["owner_name"]}</span>'

    text_col, done_col, skip_col, postpone_col, delete_col, badge_col = st.columns(
        [4.8, 0.36, 0.36, 0.36, 0.36, 1.0],
        gap="small",
        vertical_alignment="center",
    )

    with text_col:
        st.markdown(
            f"""
            <div class="todo-ribbon-marker todo-ribbon-{state}"></div>
            <span class="todo-ribbon-title" style="color:{style['text']};">
                {tag_html}{format_time(item['display_time'])} · {item['title']}
                {recurrence_html}{meta}
            </span>
            """,
            unsafe_allow_html=True,
        )

        if item["description"]:
            st.caption(item["description"])

    with done_col:
        if is_resolved:
            if st.button("↩", key=f"todo_undo_{occurrence_id}", help="Reset to pending"):
                TodoService.mark_pending(occurrence_id=occurrence_id, user_id=user_id)
                st.rerun()
        elif is_actionable and st.button(
            "👍",
            key=f"todo_done_{occurrence_id}",
            help="Mark done",
        ):
            TodoService.mark_done(occurrence_id=occurrence_id, user_id=user_id)
            st.rerun()

    with skip_col:
        if is_actionable and st.button(
            "👎",
            key=f"todo_skip_{occurrence_id}",
            help="Mark skipped",
        ):
            TodoService.mark_skipped(occurrence_id=occurrence_id, user_id=user_id)
            st.rerun()

    with postpone_col:
        if is_actionable and st.button(
            "⏰",
            key=f"todo_postpone_{occurrence_id}",
            help="Postpone",
        ):
            st.session_state[f"show_postpone_{occurrence_id}"] = True

    with delete_col:
        if item["is_owner"] and st.button(
            "✕",
            key=f"todo_delete_{todo_id}",
            help="Delete task series",
        ):
            TodoService.delete_todo(todo_id=todo_id, user_id=user_id)
            st.rerun()

    with badge_col:
        st.markdown(
            f'<span style="font-weight:700;font-size:0.82rem;color:{style["text"]};">'
            f'{style["badge"]}</span>',
            unsafe_allow_html=True,
        )

    if st.session_state.get(f"show_postpone_{occurrence_id}"):
        render_postpone_form(
            occurrence_id=occurrence_id,
            user_id=user_id,
            current_date=view_date,
        )


def clear_quick_add_fields() -> None:
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("quick_add_"):
            st.session_state.pop(key, None)


def preview_occurrence_count(
    *,
    recurrence_type: RecurrenceType,
    scheduled_date: date,
    recurrence_end_date: Optional[date],
    custom_days: Optional[str],
) -> int:
    return len(
        generate_occurrence_dates(
            recurrence_type=recurrence_type,
            first_date=scheduled_date,
            end_date=recurrence_end_date,
            custom_days=TodoService._parse_custom_days(custom_days),
        )
    )


def resolve_quick_add_tag_id(*, tags: list, tags_required: bool) -> Optional[int]:
    if not tags:
        return None

    return resolve_tag_id_from_session(
        key="quick_add_tag",
        tags=tags,
        required=tags_required,
    )


def collect_quick_add_input(
    *,
    today: date,
    plan_date: date,
    tags: list,
    tags_required: bool,
) -> dict:
    title = (st.session_state.get("quick_add_title") or "").strip()

    if not title:
        raise ValueError("Title is required.")

    scheduled_time = st.session_state.get("quick_add_time")

    if scheduled_time is None:
        raise ValueError("Time is required.")

    show_advanced = st.session_state.get("quick_add_show_advanced", False)

    if not show_advanced:
        return {
            "title": title,
            "description": None,
            "scheduled_date": plan_date,
            "scheduled_time": scheduled_time,
            "recurrence_type": RecurrenceType.ONE_TIME,
            "recurrence_end_date": None,
            "custom_days": None,
            "assignee_ids": None,
            "tag_id": resolve_quick_add_tag_id(tags=tags, tags_required=tags_required),
        }

    scheduled_date = st.session_state.get("quick_add_date", today)
    recurrence_type = st.session_state.get(
        "quick_add_recurrence",
        RecurrenceType.ONE_TIME,
    )
    description = (st.session_state.get("quick_add_description") or "").strip() or None

    recurrence_end_date = None

    if recurrence_type != RecurrenceType.ONE_TIME:
        recurrence_end_date = st.session_state.get(
            "quick_add_recurrence_end",
            scheduled_date,
        )

        if recurrence_end_date is None:
            raise ValueError("Recurring tasks require a repeat-until date.")

        if recurrence_end_date < scheduled_date:
            raise ValueError("Repeat-until date cannot be before the start date.")

    custom_days = None

    if recurrence_type == RecurrenceType.CUSTOM:
        selected_days = st.session_state.get("quick_add_custom_days", [])

        if not selected_days:
            raise ValueError("Select at least one day for custom repeat.")

        custom_days = ",".join(
            str(WEEKDAY_OPTIONS[day]) for day in selected_days
        )

    if recurrence_type != RecurrenceType.ONE_TIME:
        occurrence_count = preview_occurrence_count(
            recurrence_type=recurrence_type,
            scheduled_date=scheduled_date,
            recurrence_end_date=recurrence_end_date,
            custom_days=custom_days,
        )

        if occurrence_count <= 1 and recurrence_end_date > scheduled_date:
            raise ValueError(
                "Only 1 day would be created. Set 'Starts on' to the first day of "
                f"the series (e.g. {today.strftime('%d %b %Y')}), not the end date."
            )

        if (
            occurrence_count <= 1
            and recurrence_type == RecurrenceType.WEEKDAYS
            and scheduled_date == recurrence_end_date
        ):
            raise ValueError(
                "'Starts on' and 'Repeat until' are the same. For weekdays, set "
                f"'Starts on' to today ({today.strftime('%d %b %Y')}) or the first "
                "weekday you want."
            )

    assignee_ids = None
    assignees = st.session_state.get("quick_add_assignees")

    if assignees:
        assignee_ids = [user.id for user in assignees]

    return {
        "title": title,
        "description": description,
        "scheduled_date": scheduled_date,
        "scheduled_time": scheduled_time,
        "recurrence_type": recurrence_type,
        "recurrence_end_date": recurrence_end_date,
        "custom_days": custom_days,
        "assignee_ids": assignee_ids,
        "tag_id": resolve_quick_add_tag_id(tags=tags, tags_required=tags_required),
    }


def render_add_task_form(
    *,
    user_id: int,
    plan_date: date,
    today: date,
    now: time,
    tags: list,
    tags_required: bool,
) -> None:
    default_time = next_available_slot(now=now, slots=TIME_SLOTS)

    st.caption(f"Adding task for **{plan_date.strftime('%A, %d %b %Y')}**")

    st.text_input("Task title", key="quick_add_title")
    st.time_input(
        "Time",
        value=default_time,
        key="quick_add_time",
    )

    if tags:
        render_tag_selector(
            tags=tags,
            required=tags_required,
            key="quick_add_tag",
        )

    show_advanced = st.checkbox(
        "Advanced options",
        key="quick_add_show_advanced",
    )

    if show_advanced:
        st.text_area(
            "Description (optional)",
            key="quick_add_description",
        )

        if "quick_add_date" not in st.session_state:
            st.session_state["quick_add_date"] = plan_date

        st.date_input("Starts on", key="quick_add_date")
        st.selectbox(
            "Repeat",
            options=list(RECURRENCE_LABELS.keys()),
            format_func=lambda value: RECURRENCE_LABELS[value],
            key="quick_add_recurrence",
        )

        recurrence_type = st.session_state.get(
            "quick_add_recurrence",
            RecurrenceType.ONE_TIME,
        )

        if recurrence_type != RecurrenceType.ONE_TIME:
            start_date = st.session_state.get("quick_add_date", today)

            if "quick_add_recurrence_end" not in st.session_state:
                st.session_state["quick_add_recurrence_end"] = start_date

            st.date_input(
                "Repeat until",
                min_value=start_date,
                key="quick_add_recurrence_end",
            )

            if recurrence_type == RecurrenceType.MONTHLY:
                anchor = st.session_state.get("quick_add_date", plan_date)
                st.caption(
                    f"Repeats on day {anchor.day} of each month "
                    f"(or the last day in shorter months)."
                )

        if recurrence_type == RecurrenceType.CUSTOM:
            st.multiselect(
                "Repeat on",
                options=list(WEEKDAY_OPTIONS.keys()),
                key="quick_add_custom_days",
            )

        users = UserService.list_users()
        other_users = [user for user in users if user.id != user_id]

        if other_users:
            st.multiselect(
                "Assign users (optional)",
                options=other_users,
                format_func=lambda user: user.display_name,
                key="quick_add_assignees",
            )

    if st.button("Create task", key="quick_add_submit", use_container_width=True):
        try:
            payload = collect_quick_add_input(
                today=today,
                plan_date=plan_date,
                tags=tags,
                tags_required=tags_required,
            )

            TodoService.create_todo(
                owner_id=user_id,
                **payload,
            )
            clear_quick_add_fields()
            scheduled_date = payload["scheduled_date"]

            if payload["recurrence_type"] == RecurrenceType.ONE_TIME:
                if scheduled_date == plan_date:
                    message = "Task created."
                else:
                    message = (
                        "Task created for "
                        f"{scheduled_date.strftime('%A, %d %b %Y')}."
                    )
            else:
                occurrence_count = preview_occurrence_count(
                    recurrence_type=payload["recurrence_type"],
                    scheduled_date=scheduled_date,
                    recurrence_end_date=payload["recurrence_end_date"],
                    custom_days=payload["custom_days"],
                )
                message = (
                    f"Recurring task created · {occurrence_count} days "
                    f"from {scheduled_date.strftime('%d %b')} to "
                    f"{payload['recurrence_end_date'].strftime('%d %b %Y')}."
                )

            st.session_state["quick_add_flash"] = ("success", message)
            st.rerun()

        except ValueError as error:
            st.error(str(error))

        except Exception as error:
            st.error(f"Could not create task: {error}")


@st.dialog("Add task")
def add_task_dialog(
    *,
    user_id: int,
    plan_date: date,
    today: date,
    now: time,
    tags: list,
    tags_required: bool,
) -> None:
    render_add_task_form(
        user_id=user_id,
        plan_date=plan_date,
        today=today,
        now=now,
        tags=tags,
        tags_required=tags_required,
    )


def render_add_task_footer(
    *,
    user_id: int,
    plan_date: date,
    today: date,
    now: time,
    tags: list,
    tags_required: bool,
    has_tasks: bool,
) -> None:
    if has_tasks:
        hint = "Add another task for this day"
    else:
        hint = "Add your first task for this day"

    st.caption(hint)
    st.markdown('<div class="add-task-tail"></div>', unsafe_allow_html=True)

    if st.button(
        "＋  Add task",
        key="open_add_task_dialog",
        use_container_width=True,
        type="secondary",
    ):
        add_task_dialog(
            user_id=user_id,
            plan_date=plan_date,
            today=today,
            now=now,
            tags=tags,
            tags_required=tags_required,
        )


def render_edit_series_form(
    *,
    todo: dict,
    user_id: int,
    effective_from: date,
) -> None:
    todo_id = todo["todo_id"]

    with st.form(f"todo_edit_form_{todo_id}"):
        title = st.text_input("Title", value=todo["title"])
        description = st.text_area(
            "Description",
            value=todo["description"] or "",
        )
        scheduled_time = st.time_input(
            "Time",
            value=todo["default_time"],
        )
        recurrence_type = st.selectbox(
            "Repeat",
            options=list(RECURRENCE_LABELS.keys()),
            index=list(RECURRENCE_LABELS.keys()).index(todo["recurrence_type"]),
            format_func=lambda value: RECURRENCE_LABELS[value],
        )

        recurrence_end_date = todo["recurrence_end_date"]
        custom_days = todo["custom_days"]

        if recurrence_type != RecurrenceType.ONE_TIME:
            recurrence_end_date = st.date_input(
                "Repeat until",
                value=recurrence_end_date or effective_from,
                min_value=effective_from,
            )

            if recurrence_type == RecurrenceType.MONTHLY:
                st.caption(
                    f"Repeats on day {todo['first_date'].day} of each month "
                    f"(or the last day in shorter months)."
                )

        if recurrence_type == RecurrenceType.CUSTOM:
            selected = []

            if custom_days:
                reverse_map = {index: name for name, index in WEEKDAY_OPTIONS.items()}

                for day_index in custom_days.split(","):
                    if day_index.strip().isdigit():
                        name = reverse_map.get(int(day_index.strip()))

                        if name:
                            selected.append(name)

            selected_days = st.multiselect(
                "Repeat on",
                options=list(WEEKDAY_OPTIONS.keys()),
                default=selected,
            )
            custom_days = ",".join(
                str(WEEKDAY_OPTIONS[day]) for day in selected_days
            )

        if st.form_submit_button("Save changes", use_container_width=True):
            if not title.strip():
                st.error("Title is required.")
                return

            try:
                TodoService.update_todo(
                    todo_id=todo_id,
                    title=title.strip(),
                    description=description.strip() or None,
                    scheduled_time=scheduled_time,
                    recurrence_type=recurrence_type,
                    recurrence_end_date=recurrence_end_date,
                    custom_days=custom_days,
                    from_date=effective_from,
                )
                st.session_state.pop(f"show_edit_todo_{todo_id}", None)
                st.success("Task updated for future dates.")
                st.rerun()

            except ValueError as error:
                st.error(str(error))

    if st.button("Cancel edit", key=f"cancel_edit_{todo_id}", use_container_width=True):
        st.session_state.pop(f"show_edit_todo_{todo_id}", None)
        st.rerun()
