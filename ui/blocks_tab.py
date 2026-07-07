from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from typing import List
from typing import Optional

import pytz
import streamlit as st

from services.day_plan_service import DayPlanService
from services.planner_tag_service import PlannerTagService
from ui.tag_helpers import render_tag_pill
from ui.tag_helpers import render_tag_selector
from utils.enums import BlockStatus
from utils.time_slots import default_end_index
from utils.time_slots import format_time_label
from utils.time_slots import generate_time_slots
from utils.time_slots import index_for_time
from utils.time_slots import next_available_slot
from utils.time_slots import times_after

TIME_SLOTS = generate_time_slots()
TIME_LABELS = [format_time_label(slot) for slot in TIME_SLOTS]

BLOCK_STYLES = {
    "current": {
        "bg": "#FFE082",
        "border": "#FFA000",
        "text": "#3E2723",
        "badge": "Now",
        "badge_color": "#E65100",
    },
    "overdue": {
        "bg": "#FFCDD2",
        "border": "#E53935",
        "text": "#3E2723",
        "badge": "Pending",
        "badge_color": "#B71C1C",
    },
    "skipped": {
        "bg": "#FFCDD2",
        "border": "#C62828",
        "text": "#3E2723",
        "badge": "Skipped",
        "badge_color": "#880E4F",
    },
    "done": {
        "bg": "#A5D6A7",
        "border": "#2E7D32",
        "text": "#1B5E20",
        "badge": "Done",
        "badge_color": "#1B5E20",
    },
    "upcoming": {
        "bg": "#BBDEFB",
        "border": "#1E88E5",
        "text": "#0D47A1",
        "badge": "Upcoming",
        "badge_color": "#1565C0",
    },
}


def _inject_block_styles() -> None:
    st.markdown(
        """
        <style>
        .achievement-card {
            background: #FAFAFA;
            border: 1px solid #E0E0E0;
            border-radius: 12px;
            padding: 1rem 1.1rem;
            margin-bottom: 1rem;
        }
        .achievement-value {
            font-size: 2rem;
            font-weight: 700;
            line-height: 1.1;
            margin: 0;
        }
        .legend-item {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            margin-right: 1rem;
            font-size: 0.85rem;
            color: #424242;
        }
        .legend-dot {
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
        /* Date bar only — never target parent page vertical blocks */
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
        @media (max-width: 768px) {
            [data-testid="stHorizontalBlock"]:has(.plan-date-nav-wrap-marker) {
                max-width: 34rem !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }
            [data-testid="stElementContainer"]:has(.plan-date-nav-extra),
            [data-testid="stElementContainer"]:has(.plan-date-nav-jump) {
                max-width: 34rem !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }
        }
        .add-block-tail {
            display: none;
        }
        [data-testid="stVerticalBlock"]:has(.add-block-tail) [data-testid="stButton"] > button {
            border: 2px dashed #90CAF9 !important;
            background: linear-gradient(180deg, #F8FBFF 0%, #E8F4FD 100%) !important;
            color: #1565C0 !important;
            min-height: 54px;
            border-radius: 10px;
            font-weight: 700;
            font-size: 1rem;
            letter-spacing: 0.02em;
            transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
        }
        [data-testid="stVerticalBlock"]:has(.add-block-tail) [data-testid="stButton"] > button:hover {
            border-color: #1E88E5 !important;
            background: linear-gradient(180deg, #E3F2FD 0%, #BBDEFB 100%) !important;
            box-shadow: 0 3px 10px rgba(30, 136, 229, 0.18);
            color: #0D47A1 !important;
        }
        .block-ribbon-marker,
        .ribbon-action-bar,
        .ribbon-btn-danger,
        .ribbon-btn-wrap,
        .ribbon-btn-done,
        .ribbon-btn-skip,
        .ribbon-btn-remove {
            display: none !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        [data-testid="stHorizontalBlock"]:has(.block-ribbon-marker) {
            background: var(--ribbon-bg, #ECEFF1) !important;
            border: 1px solid var(--ribbon-border, #B0BEC5) !important;
            border-radius: 10px;
            padding: 4px 10px !important;
            margin-bottom: 0.45rem !important;
            align-items: center !important;
            gap: 0.2rem !important;
            min-height: 0 !important;
        }
        [data-testid="stHorizontalBlock"]:has(.block-ribbon-current) {
            background: #FFE082 !important;
            border-color: #FFA000 !important;
        }
        [data-testid="stHorizontalBlock"]:has(.block-ribbon-overdue) {
            background: #FFCDD2 !important;
            border-color: #E53935 !important;
        }
        [data-testid="stHorizontalBlock"]:has(.block-ribbon-skipped) {
            background: #FFCDD2 !important;
            border-color: #C62828 !important;
        }
        [data-testid="stHorizontalBlock"]:has(.block-ribbon-done) {
            background: #A5D6A7 !important;
            border-color: #2E7D32 !important;
        }
        [data-testid="stHorizontalBlock"]:has(.block-ribbon-upcoming) {
            background: #BBDEFB !important;
            border-color: #1E88E5 !important;
        }
        [data-testid="stHorizontalBlock"]:has(.block-ribbon-marker) > [data-testid="column"] {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            min-height: 0 !important;
        }
        [data-testid="stHorizontalBlock"]:has(.block-ribbon-marker) > [data-testid="column"]:first-child {
            justify-content: flex-start !important;
        }
        [data-testid="stHorizontalBlock"]:has(.block-ribbon-marker) > [data-testid="column"]:last-child {
            justify-content: flex-end !important;
        }
        [data-testid="stHorizontalBlock"]:has(.block-ribbon-marker) [data-testid="stVerticalBlock"] {
            gap: 0 !important;
            justify-content: center !important;
            width: 100%;
        }
        [data-testid="stHorizontalBlock"]:has(.block-ribbon-marker) [data-testid="stMarkdown"] {
            margin: 0 !important;
            padding: 0 !important;
        }
        [data-testid="stHorizontalBlock"]:has(.block-ribbon-marker) [data-testid="stButton"] {
            margin: 0 !important;
            width: 100%;
            display: flex;
            justify-content: center;
        }
        [data-testid="stHorizontalBlock"]:has(.block-ribbon-marker) [data-testid="stElementContainer"] {
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
        }
        [data-testid="stHorizontalBlock"]:has(.block-ribbon-marker) [data-testid="stButton"] > button {
            min-height: 28px !important;
            max-height: 28px !important;
            min-width: 28px !important;
            max-width: 28px !important;
            width: 28px !important;
            height: 28px !important;
            padding: 0 !important;
            font-size: 0.88rem !important;
            line-height: 28px !important;
            border-radius: 6px !important;
            background: rgba(255, 255, 255, 0.6) !important;
            border: 1px solid rgba(0, 0, 0, 0.08) !important;
            color: #455A64 !important;
            box-shadow: none !important;
        }
        [data-testid="stHorizontalBlock"]:has(.block-ribbon-marker) [data-testid="stButton"] > button:hover {
            background: rgba(255, 255, 255, 0.9) !important;
            color: #263238 !important;
            transform: none !important;
        }
        [data-testid="column"]:has(.ribbon-btn-done) [data-testid="stButton"] > button {
            background: #2E7D32 !important;
            color: #fff !important;
            border-color: #2E7D32 !important;
        }
        [data-testid="column"]:has(.ribbon-btn-done) [data-testid="stButton"] > button:hover {
            background: #1B5E20 !important;
            color: #fff !important;
        }
        [data-testid="column"]:has(.ribbon-btn-remove) [data-testid="stButton"] > button:hover {
            background: rgba(229, 57, 53, 0.15) !important;
            color: #C62828 !important;
            border-color: rgba(229, 57, 53, 0.3) !important;
        }
        .block-ribbon-title {
            font-weight: 700;
            word-break: break-word;
            line-height: 1.25;
            font-size: 0.9rem;
            margin: 0;
            padding: 0;
            background: transparent !important;
        }
        [data-testid="stHorizontalBlock"]:has(.block-ribbon-marker) [data-testid="stMarkdownContainer"] {
            background: transparent !important;
        }
        [data-testid="stHorizontalBlock"]:has(.block-ribbon-marker) [data-testid="stMarkdownContainer"] p {
            margin: 0;
            background: transparent !important;
        }
        .block-ribbon-badge-pill {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.75rem;
            letter-spacing: 0.02em;
            background: rgba(255, 255, 255, 0.55);
            white-space: nowrap;
            line-height: 1.2;
            margin: 0;
        }
        @media (max-width: 768px) {
            [data-testid="stHorizontalBlock"]:has(.block-ribbon-marker) {
                flex-wrap: wrap !important;
                padding: 6px 8px !important;
            }
            [data-testid="stHorizontalBlock"]:has(.block-ribbon-marker) > [data-testid="column"]:first-child {
                flex: 1 1 100% !important;
                min-width: 100% !important;
                margin-bottom: 4px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _format_time(value: time) -> str:
    return value.strftime("%H:%M")


def _label_to_time(label: str) -> time:
    hour, minute = label.split(":")
    return datetime.strptime(f"{hour}:{minute}", "%H:%M").time()


def _get_block_state(
    *,
    block,
    now: time,
    plan_date: date,
    today: date,
) -> str:
    if block.status == BlockStatus.DONE:
        return "done"

    if block.status == BlockStatus.SKIPPED:
        return "skipped"

    if plan_date < today:
        return "overdue"

    if plan_date > today:
        return "upcoming"

    if block.start_time <= now < block.end_time:
        return "current"

    if block.end_time <= now:
        return "overdue"

    return "upcoming"


def _clear_block_ui_state(block_ids: List[int]) -> None:
    for block_id in block_ids:
        st.session_state.pop(f"edit_block_{block_id}", None)
        st.session_state.pop(f"insert_after_{block_id}", None)


def _render_plan_date_navigator(*, today: date) -> date:
    if "block_plan_date" not in st.session_state:
        st.session_state["block_plan_date"] = today

    plan_date = st.session_state["block_plan_date"]
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
        if st.button("‹", key="plan_date_prev", help="Previous day", use_container_width=True):
            st.session_state["block_plan_date"] = plan_date - timedelta(days=1)
            st.session_state.pop("show_plan_date_picker", None)
            st.rerun()

    with date_col:
        st.markdown(
            f'<p class="plan-date-nav-label">{date_label}{today_badge}</p>',
            unsafe_allow_html=True,
        )

    with cal_col:
        if st.button(
            "📅",
            key="plan_date_calendar",
            help="Pick a date",
            use_container_width=True,
        ):
            st.session_state["show_plan_date_picker"] = not st.session_state.get(
                "show_plan_date_picker",
                False,
            )
            st.rerun()

    with next_col:
        if st.button("›", key="plan_date_next", help="Next day", use_container_width=True):
            st.session_state["block_plan_date"] = plan_date + timedelta(days=1)
            st.session_state.pop("show_plan_date_picker", None)
            st.rerun()

    if st.session_state.get("show_plan_date_picker"):
        st.markdown('<div class="plan-date-nav-extra"></div>', unsafe_allow_html=True)
        picked = st.date_input(
            "Choose date",
            value=plan_date,
            key="plan_date_picker_widget",
            label_visibility="collapsed",
        )

        if picked != plan_date:
            st.session_state["block_plan_date"] = picked
            st.session_state.pop("show_plan_date_picker", None)
            st.rerun()

    if plan_date != today:
        st.markdown('<div class="plan-date-nav-jump"></div>', unsafe_allow_html=True)
        if st.button("Jump to today", key="plan_date_today", use_container_width=True):
            st.session_state["block_plan_date"] = today
            st.session_state.pop("show_plan_date_picker", None)
            st.rerun()

    return st.session_state["block_plan_date"]


def _render_block_forms(
    *,
    block,
    block_index: int,
    total_blocks: int,
    tags: list,
    tags_required: bool,
) -> None:
    if st.session_state.get(f"edit_block_{block.id}"):
        with st.container(border=True):
            st.markdown("**Edit block**")
            _render_edit_block_form(
                block,
                is_first=block_index == 0,
                tags=tags,
                tags_required=tags_required,
            )

    if st.session_state.get(f"insert_after_{block.id}"):
        with st.container(border=True):
            st.markdown("**Insert block**")
            _render_insert_block_form(
                block,
                has_following=block_index < total_blocks - 1,
                tags=tags,
                tags_required=tags_required,
            )


def _render_colored_block(
    *,
    block,
    block_index: int,
    total_blocks: int,
    now: time,
    plan_date: date,
    today: date,
    tags_map: dict,
    tags: list,
    tags_required: bool,
):
    state = _get_block_state(block=block, now=now, plan_date=plan_date, today=today)
    style = BLOCK_STYLES[state]
    is_done = block.status == BlockStatus.DONE
    is_skipped = block.status == BlockStatus.SKIPPED
    is_resolved = is_done or is_skipped
    tag = tags_map.get(block.tag_id)
    tag_html = render_tag_pill(tag=tag)

    text_col, up_col, down_col, btn2_col, btn3_col, btn4_col, badge_col = st.columns(
        [4.8, 0.36, 0.36, 0.36, 0.36, 0.36, 1.0],
        gap="small",
        vertical_alignment="center",
    )

    with text_col:
        st.markdown(
            f"""
            <div class="block-ribbon-marker block-ribbon-{state}"></div>
            <span class="block-ribbon-title" style="color:{style['text']};">
                {tag_html}{_format_time(block.start_time)} – {_format_time(block.end_time)} · {block.title}
            </span>
            """,
            unsafe_allow_html=True,
        )

    with up_col:
        if is_resolved:
            if st.button("↩", key=f"block_undo_{block.id}", help="Reset to pending"):
                DayPlanService.mark_block_pending(block_id=block.id)
                st.rerun()
        elif st.button(
            "👍",
            key=f"block_done_{block.id}",
            help="Mark done",
            type="secondary",
        ):
            DayPlanService.mark_block_done(block_id=block.id)
            st.rerun()

    with down_col:
        if not is_resolved:
            st.markdown('<div class="ribbon-btn-skip"></div>', unsafe_allow_html=True)
            if st.button(
                "👎",
                key=f"block_skip_{block.id}",
                help="Mark skipped (not done)",
                type="secondary",
            ):
                DayPlanService.mark_block_skipped(block_id=block.id)
                st.rerun()

    with btn2_col:
        if st.button("✎", key=f"block_edit_{block.id}", help="Edit"):
            st.session_state[f"edit_block_{block.id}"] = True
            st.session_state.pop(f"insert_after_{block.id}", None)
            st.rerun()

    with btn3_col:
        if st.button("＋", key=f"block_insert_{block.id}", help="Insert after"):
            st.session_state[f"insert_after_{block.id}"] = True
            st.session_state.pop(f"edit_block_{block.id}", None)
            st.rerun()

    with btn4_col:
        st.markdown('<div class="ribbon-btn-remove"></div>', unsafe_allow_html=True)
        if st.button("✕", key=f"block_remove_{block.id}", help="Remove"):
            DayPlanService.delete_block(block_id=block.id)
            st.session_state.pop(f"edit_block_{block.id}", None)
            st.session_state.pop(f"insert_after_{block.id}", None)
            st.rerun()

    with badge_col:
        st.markdown(
            f'<span class="block-ribbon-badge-pill" style="color:{style["badge_color"]};">'
            f'{style["badge"]}</span>',
            unsafe_allow_html=True,
        )

    _render_block_forms(
        block=block,
        block_index=block_index,
        total_blocks=total_blocks,
        tags=tags,
        tags_required=tags_required,
    )


def _render_block_legend() -> None:
    st.markdown(
        """
        <div class="block-legend">
            <span class="legend-item">
                <span class="legend-dot" style="background:#FFA000;"></span> Now
            </span>
            <span class="legend-item">
                <span class="legend-dot" style="background:#E53935;"></span> Pending
            </span>
            <span class="legend-item">
                <span class="legend-dot" style="background:#C62828;"></span> Skipped
            </span>
            <span class="legend-item">
                <span class="legend-dot" style="background:#2E7D32;"></span> Done
            </span>
            <span class="legend-item">
                <span class="legend-dot" style="background:#1E88E5;"></span> Upcoming
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_add_block_form(
    *,
    user_id: int,
    plan_date: date,
    blocks: list,
    today: date,
    now: time,
    tags: list,
    tags_required: bool,
):
    date_key = plan_date.isoformat()

    if blocks:
        start_time = blocks[-1].end_time
        st.caption(
            f"Start time: **{_format_time(start_time)}** "
            "(continues from the previous block)"
        )
    else:
        default_index = 0

        if plan_date == today:
            default_start = next_available_slot(now=now, slots=TIME_SLOTS)
            default_index = index_for_time(default_start, TIME_SLOTS)
            st.caption(
                f"First block starts at the next available slot: "
                f"**{format_time_label(default_start)}**"
            )
        else:
            st.caption("Select a start time for your first block of the day.")

        start_label = st.selectbox(
            "Start time",
            options=TIME_LABELS,
            index=default_index,
            key=f"block_start_{date_key}",
        )
        start_time = _label_to_time(start_label)

    end_options = times_after(start_time, TIME_SLOTS)

    if not end_options:
        st.warning("No end times available after the selected start time.")
        return

    end_labels = [format_time_label(option) for option in end_options]
    end_label = st.selectbox(
        "End time",
        options=end_labels,
        index=default_end_index(start=start_time, end_options=end_options),
        key=f"block_end_{date_key}_{_format_time(start_time)}",
    )
    end_time = _label_to_time(end_label)

    title = st.text_input("Activity", key=f"block_title_{date_key}")

    tag_id = render_tag_selector(
        tags=tags,
        required=tags_required,
        key=f"block_tag_{date_key}",
    )

    if st.button("Add block", key=f"add_block_{date_key}", use_container_width=True):
        if not title.strip():
            st.error("Activity title is required.")
            return

        if tags_required and tag_id is None:
            st.error("Please select a tag.")
            return

        try:
            DayPlanService.add_block(
                user_id=user_id,
                plan_date=plan_date,
                start_time=start_time,
                end_time=end_time,
                title=title.strip(),
                tag_id=tag_id,
            )
            st.success("Block added.")
            st.rerun()

        except ValueError as error:
            st.error(str(error))


@st.dialog("Add time block")
def _add_block_dialog(
    *,
    user_id: int,
    plan_date: date,
    blocks: list,
    today: date,
    now: time,
    tags: list,
    tags_required: bool,
):
    _render_add_block_form(
        user_id=user_id,
        plan_date=plan_date,
        blocks=blocks,
        today=today,
        now=now,
        tags=tags,
        tags_required=tags_required,
    )


def _render_add_block_footer(
    *,
    user_id: int,
    plan_date: date,
    blocks: list,
    today: date,
    now: time,
    tags: list,
    tags_required: bool,
) -> None:
    if blocks:
        hint = f"Next block starts at {_format_time(blocks[-1].end_time)}"
    else:
        hint = "Add your first block for this day"

    st.caption(hint)
    st.markdown('<div class="add-block-tail"></div>', unsafe_allow_html=True)
    if st.button(
        "＋  Add time block",
        key="open_add_block_dialog",
        use_container_width=True,
        type="secondary",
    ):
        _add_block_dialog(
            user_id=user_id,
            plan_date=plan_date,
            blocks=blocks,
            today=today,
            now=now,
            tags=tags,
            tags_required=tags_required,
        )


def _render_edit_block_form(
    block,
    *,
    is_first: bool,
    tags: list,
    tags_required: bool,
):
    start_time = block.start_time
    end_time = block.end_time

    if is_first:
        start_options = [slot for slot in TIME_SLOTS if slot < block.end_time]
        start_labels = [format_time_label(option) for option in start_options]
        start_label = st.selectbox(
            "Start time",
            options=start_labels,
            index=index_for_time(block.start_time, start_options),
            key=f"edit_start_{block.id}",
        )
        start_time = _label_to_time(start_label)
    else:
        st.caption(f"Start time: **{_format_time(block.start_time)}** (fixed)")

    end_options = times_after(start_time, TIME_SLOTS)

    if not end_options:
        st.warning("No valid end times available.")
        return

    end_labels = [format_time_label(option) for option in end_options]
    end_label = st.selectbox(
        "End time",
        options=end_labels,
        index=index_for_time(block.end_time, end_options),
        key=f"edit_end_{block.id}",
    )
    end_time = _label_to_time(end_label)

    title = st.text_input(
        "Activity",
        value=block.title,
        key=f"edit_title_{block.id}",
    )

    tag_id = render_tag_selector(
        tags=tags,
        required=tags_required,
        key=f"edit_tag_{block.id}",
        current_tag_id=block.tag_id,
    )

    col_save, col_cancel = st.columns(2)

    with col_save:
        if st.button("Save changes", key=f"save_edit_{block.id}"):
            if not title.strip():
                st.error("Activity title is required.")
                return

            if tags_required and tag_id is None:
                st.error("Please select a tag.")
                return

            try:
                DayPlanService.update_block(
                    block_id=block.id,
                    start_time=start_time if is_first else None,
                    end_time=end_time,
                    title=title.strip(),
                    tag_id=tag_id if tags_required else block.tag_id,
                )
                st.session_state.pop(f"edit_block_{block.id}", None)
                st.success("Block updated. Following blocks were adjusted.")
                st.rerun()

            except ValueError as error:
                st.error(str(error))

    with col_cancel:
        if st.button("Cancel", key=f"cancel_edit_{block.id}"):
            st.session_state.pop(f"edit_block_{block.id}", None)
            st.rerun()


def _render_insert_block_form(
    block,
    *,
    has_following: bool,
    tags: list,
    tags_required: bool,
):
    st.caption(
        f"New block starts at **{_format_time(block.end_time)}**. "
        + (
            "Later blocks will shift forward."
            if has_following
            else "This adds a new block at the end."
        )
    )

    end_options = times_after(block.end_time, TIME_SLOTS)

    if not end_options:
        st.warning("No room to insert a block here.")
        return

    end_labels = [format_time_label(option) for option in end_options]
    end_label = st.selectbox(
        "End time",
        options=end_labels,
        index=default_end_index(
            start=block.end_time,
            end_options=end_options,
            duration_minutes=15,
        ),
        key=f"insert_end_{block.id}",
    )
    end_time = _label_to_time(end_label)

    title = st.text_input("Activity", key=f"insert_title_{block.id}")

    tag_id = render_tag_selector(
        tags=tags,
        required=tags_required,
        key=f"insert_tag_{block.id}",
    )

    col_save, col_cancel = st.columns(2)

    with col_save:
        if st.button("Insert block", key=f"save_insert_{block.id}"):
            if not title.strip():
                st.error("Activity title is required.")
                return

            if tags_required and tag_id is None:
                st.error("Please select a tag.")
                return

            try:
                DayPlanService.insert_block_after(
                    block_id=block.id,
                    end_time=end_time,
                    title=title.strip(),
                    tag_id=tag_id,
                )
                st.session_state.pop(f"insert_after_{block.id}", None)
                st.success("Block inserted. Following blocks were adjusted.")
                st.rerun()

            except ValueError as error:
                st.error(str(error))

    with col_cancel:
        if st.button("Cancel", key=f"cancel_insert_{block.id}"):
            st.session_state.pop(f"insert_after_{block.id}", None)
            st.rerun()


def render_blocks_tab(user_id: int, timezone: str):
    _inject_block_styles()

    tz = pytz.timezone(timezone)
    now = datetime.now(tz).time()
    today = datetime.now(tz).date()

    plan_date = _render_plan_date_navigator(today=today)

    if st.session_state.get("blocks_active_date") != plan_date.isoformat():
        previous_ids = st.session_state.get("blocks_active_ids", [])
        _clear_block_ui_state(previous_ids)
        st.session_state["blocks_active_date"] = plan_date.isoformat()

    blocks = DayPlanService.get_blocks(user_id=user_id, plan_date=plan_date)
    st.session_state["blocks_active_ids"] = [block.id for block in blocks]

    tags = PlannerTagService.list_tags(user_id=user_id)
    tags_map = {tag.id: tag for tag in tags}
    tags_required = PlannerTagService.tags_required_on_create(user_id=user_id)

    if blocks:
        _render_block_legend()

        if plan_date == today:
            current = DayPlanService.get_current_block(
                user_id=user_id,
                plan_date=plan_date,
                now=now,
            )

            if current:
                st.caption(
                    f"Current block: **{current.title}** "
                    f"({_format_time(current.start_time)} – "
                    f"{_format_time(current.end_time)})"
                )

        for index, block in enumerate(blocks):
            _render_colored_block(
                block=block,
                block_index=index,
                total_blocks=len(blocks),
                now=now,
                plan_date=plan_date,
                today=today,
                tags_map=tags_map,
                tags=tags,
                tags_required=tags_required,
            )

    _render_add_block_footer(
        user_id=user_id,
        plan_date=plan_date,
        blocks=blocks,
        today=today,
        now=now,
        tags=tags,
        tags_required=tags_required,
    )
