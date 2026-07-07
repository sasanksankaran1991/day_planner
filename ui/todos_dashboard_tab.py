from datetime import datetime
from datetime import timedelta

import pytz
import streamlit as st

from services.todo_service import TodoService


def _inject_dashboard_styles() -> None:
    st.markdown(
        """
        <style>
        .stat-card {
            background: #FAFAFA;
            border: 1px solid #E0E0E0;
            border-radius: 12px;
            padding: 1rem 1.1rem;
            margin-bottom: 0.5rem;
        }
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            line-height: 1.1;
            margin: 0;
        }
        .stat-label {
            color: #616161;
            font-size: 0.9rem;
            margin-bottom: 0.2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_stat_card(*, label: str, value: str, caption: str = "") -> None:
    caption_html = (
        f'<div style="color:#757575;font-size:0.9rem;">{caption}</div>'
        if caption
        else ""
    )

    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-label">{label}</div>
            <p class="stat-value">{value}</p>
            {caption_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_pending_assignments(user_id: int) -> None:
    assignments = TodoService.get_pending_assignments(user_id=user_id)

    if not assignments:
        return

    st.markdown("### Pending invitations")

    for assignment in assignments:
        with st.container(border=True):
            st.write(
                f"**{assignment['title']}** — invited by "
                f"{assignment['assigned_by']}"
            )

            accept_col, reject_col = st.columns(2)

            with accept_col:
                if st.button(
                    "Accept",
                    key=f"accept_{assignment['id']}",
                    use_container_width=True,
                ):
                    TodoService.respond_to_assignment(
                        todo_id=assignment["todo_id"],
                        assignee_id=user_id,
                        accept=True,
                    )
                    st.rerun()

            with reject_col:
                if st.button(
                    "Reject",
                    key=f"reject_{assignment['id']}",
                    use_container_width=True,
                ):
                    TodoService.respond_to_assignment(
                        todo_id=assignment["todo_id"],
                        assignee_id=user_id,
                        accept=False,
                    )
                    st.rerun()

    st.divider()


def render_todos_dashboard_tab(*, user_id: int, timezone: str) -> None:
    _inject_dashboard_styles()

    tz = pytz.timezone(timezone)
    today = datetime.now(tz).date()
    now = datetime.now(tz).time().replace(second=0, microsecond=0)

    st.subheader("Dashboard")
    st.caption(f"Stats as of {today.strftime('%A, %d %B %Y')}")

    today_stats = TodoService.get_day_stats(
        user_id=user_id,
        on_date=today,
        today=today,
        now=now,
    )

    week_start = today - timedelta(days=6)
    week_summaries = TodoService.get_daily_summaries(
        user_id=user_id,
        start_date=week_start,
        end_date=today,
        today=today,
        now=now,
    )

    week_percents = [
        summary["percent"]
        for summary in week_summaries
        if summary["percent"] is not None
    ]
    week_avg = (
        round(sum(week_percents) / len(week_percents))
        if week_percents
        else None
    )

    days_with_tasks = sum(1 for summary in week_summaries if summary["total"] > 0)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        _render_stat_card(
            label="Today's achievement",
            value=(
                f"{today_stats['percent']}%"
                if today_stats["percent"] is not None
                else "—"
            ),
            caption="Tasks completed today"
            if today_stats["percent"] is not None
            else "No tasks planned yet",
        )

    with col2:
        _render_stat_card(
            label="7-day average",
            value=f"{week_avg}%" if week_avg is not None else "—",
            caption="Average completion this week",
        )

    with col3:
        _render_stat_card(
            label="Overdue today",
            value=str(today_stats["overdue_count"]),
            caption="Tasks still pending past their time",
        )

    with col4:
        _render_stat_card(
            label="Active days",
            value=str(days_with_tasks),
            caption="Days with tasks in the last 7 days",
        )

    if today_stats["percent"] is not None:
        st.progress(today_stats["percent"] / 100)

    st.divider()
    st.markdown("### Last 7 days")

    summary_by_date = {
        summary["plan_date"]: summary for summary in week_summaries
    }

    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        summary = summary_by_date.get(day)

        label = day.strftime("%a, %d %b")
        if day == today:
            label += " (today)"

        if summary is None or summary["total"] == 0:
            st.markdown(f"**{label}** — no tasks")
            continue

        percent = summary["percent"]
        st.markdown(
            f"**{label}** — {summary['done_count']}/{summary['total']} tasks "
            f"({percent}%)"
        )
        st.progress(percent / 100)

    st.divider()
    _render_pending_assignments(user_id)
