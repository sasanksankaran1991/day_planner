from datetime import datetime
from datetime import timedelta

import pytz
import streamlit as st

from services.day_plan_service import DayPlanService


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


def render_planner_dashboard_tab(*, user_id: int, timezone: str) -> None:
    _inject_dashboard_styles()

    tz = pytz.timezone(timezone)
    today = datetime.now(tz).date()

    st.subheader("Dashboard")
    st.caption(f"Stats as of {today.strftime('%A, %d %B %Y')}")

    today_percent = DayPlanService.get_achievement_percent(
        user_id=user_id,
        plan_date=today,
    )
    planning_streak = DayPlanService.get_planning_streak(
        user_id=user_id,
        as_of_date=today,
    )
    completion_streak = DayPlanService.get_completion_streak(
        user_id=user_id,
        as_of_date=today,
    )

    week_start = today - timedelta(days=6)
    week_summaries = DayPlanService.get_daily_summaries(
        user_id=user_id,
        start_date=week_start,
        end_date=today,
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

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        _render_stat_card(
            label="Today's achievement",
            value=f"{today_percent}%" if today_percent is not None else "—",
            caption="Blocks completed today"
            if today_percent is not None
            else "No blocks planned yet",
        )

    with col2:
        _render_stat_card(
            label="7-day average",
            value=f"{week_avg}%" if week_avg is not None else "—",
            caption="Average completion this week",
        )

    with col3:
        _render_stat_card(
            label="Planning streak",
            value=str(planning_streak),
            caption="Consecutive days with a plan",
        )

    with col4:
        _render_stat_card(
            label="Perfect-day streak",
            value=str(completion_streak),
            caption="Consecutive 100% days",
        )

    if today_percent is not None:
        st.progress(today_percent / 100)

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
            st.markdown(f"**{label}** — no plan")
            continue

        percent = summary["percent"]
        st.markdown(
            f"**{label}** — {summary['done_count']}/{summary['total']} blocks "
            f"({percent}%)"
        )
        st.progress(percent / 100)
