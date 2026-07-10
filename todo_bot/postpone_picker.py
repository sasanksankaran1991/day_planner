from __future__ import annotations

import calendar
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from utils.time_slots import format_time_label
from utils.time_slots import generate_time_slots

POSTPONE_SESSION_KEY = "todo_postpone_session"


def get_postpone_session(context) -> Optional[dict]:
    return context.user_data.get(POSTPONE_SESSION_KEY)


def set_postpone_session(
    context,
    *,
    task_number: int,
    plan_date: Optional[date],
    task_title: str,
    calendar_month: date,
) -> None:
    context.user_data[POSTPONE_SESSION_KEY] = {
        "task_number": task_number,
        "plan_date": plan_date.isoformat() if plan_date else None,
        "task_title": task_title,
        "calendar_month": calendar_month.replace(day=1).isoformat(),
        "selected_date": None,
    }


def clear_postpone_session(context) -> None:
    context.user_data.pop(POSTPONE_SESSION_KEY, None)


def plan_date_from_session(session: dict) -> Optional[date]:
    raw = session.get("plan_date")

    if not raw:
        return None

    return date.fromisoformat(raw)


def calendar_month_from_session(session: dict) -> date:
    raw = session.get("calendar_month")

    if raw:
        return date.fromisoformat(raw)

    return date.today().replace(day=1)


def postpone_callback_data(*, action: str, value: str = "") -> str:
    if value:
        return f"{action}:{value}"

    return action


def encode_pick_date(picked: date) -> str:
    return picked.strftime("%Y%m%d")


def decode_pick_date(value: str) -> date:
    return datetime.strptime(value, "%Y%m%d").date()


def encode_year_month(month_date: date) -> str:
    return month_date.strftime("%Y%m")


def decode_year_month(value: str) -> date:
    return datetime.strptime(f"{value}01", "%Y%m%d").date()


def parse_postpone_picker_callback(*, data: str) -> Tuple[str, List[str]]:
    parts = data.split(":")
    return parts[0], parts[1:]


def build_postpone_options_keyboard(
    *,
    task_number: int,
    plan_date: date,
    today: date,
    action_callback_data,
) -> InlineKeyboardMarkup:
    def cb(action: str) -> str:
        return action_callback_data(
            action=action,
            task_number=task_number,
            plan_date=plan_date,
            today=today,
        )

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("+30 minutes", callback_data=cb("tp30")),
                InlineKeyboardButton("+1 hour", callback_data=cb("tp60")),
            ],
            [
                InlineKeyboardButton(
                    "Tomorrow (same time)",
                    callback_data=cb("tptm"),
                ),
            ],
            [
                InlineKeyboardButton("Custom…", callback_data=cb("tpcu")),
            ],
        ]
    )


def build_date_picker_keyboard(
    *,
    month_date: date,
    today: date,
) -> InlineKeyboardMarkup:
    year = month_date.year
    month = month_date.month
    month_label = month_date.strftime("%B %Y")

    prev_month = (month_date.replace(day=1) - timedelta(days=1)).replace(day=1)
    next_month = (month_date.replace(day=28) + timedelta(days=4)).replace(day=1)

    rows: List[List[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton("Today", callback_data=postpone_callback_data(action="tpdt")),
            InlineKeyboardButton(
                "Tomorrow",
                callback_data=postpone_callback_data(action="tpdn"),
            ),
        ],
        [
            InlineKeyboardButton(
                "◀",
                callback_data=postpone_callback_data(
                    action="tpdm",
                    value=encode_year_month(prev_month),
                ),
            ),
            InlineKeyboardButton(month_label, callback_data=postpone_callback_data(action="tpnoop")),
            InlineKeyboardButton(
                "▶",
                callback_data=postpone_callback_data(
                    action="tpdm",
                    value=encode_year_month(next_month),
                ),
            ),
        ],
    ]

    weekday_row = [
        InlineKeyboardButton(label, callback_data=postpone_callback_data(action="tpnoop"))
        for label in ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
    ]
    rows.append(weekday_row)

    month_weeks = calendar.monthcalendar(year, month)

    for week in month_weeks:
        week_row = []

        for day_number in week:
            if day_number == 0:
                week_row.append(
                    InlineKeyboardButton(
                        " ",
                        callback_data=postpone_callback_data(action="tpnoop"),
                    )
                )
                continue

            picked = date(year, month, day_number)
            label = str(day_number)

            if picked == today:
                label = f"•{day_number}"

            week_row.append(
                InlineKeyboardButton(
                    label,
                    callback_data=postpone_callback_data(
                        action="tpdy",
                        value=encode_pick_date(picked),
                    ),
                )
            )

        rows.append(week_row)

    rows.append(
        [
            InlineKeyboardButton(
                "Cancel",
                callback_data=postpone_callback_data(action="tpx"),
            ),
        ]
    )

    return InlineKeyboardMarkup(rows)


def build_time_picker_keyboard(*, picked_date: date) -> InlineKeyboardMarkup:
    slots = generate_time_slots(interval_minutes=30, start_hour=5, end_hour=24)
    rows: List[List[InlineKeyboardButton]] = []
    current_row: List[InlineKeyboardButton] = []

    for slot in slots:
        current_row.append(
            InlineKeyboardButton(
                format_time_label(slot),
                callback_data=postpone_callback_data(
                    action="tpt",
                    value=slot.strftime("%H%M"),
                ),
            )
        )

        if len(current_row) == 4:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    rows.append(
        [
            InlineKeyboardButton(
                "◀ Change date",
                callback_data=postpone_callback_data(action="tptb"),
            ),
            InlineKeyboardButton(
                "Cancel",
                callback_data=postpone_callback_data(action="tpx"),
            ),
        ]
    )

    return InlineKeyboardMarkup(rows)


def build_date_prompt(*, task_number: int, task_title: str) -> str:
    return (
        f"📅 <b>Custom postpone — task {task_number}</b>\n"
        f"{task_title}\n\n"
        "Pick a date below, or type e.g. <code>10-07-2026</code>"
    )


def build_time_prompt(*, picked_date: date) -> str:
    return (
        f"🕐 <b>Select time for {picked_date.strftime('%A, %d %b %Y')}</b>\n\n"
        "Tap a time below, or type e.g. <code>09:30</code>"
    )


def parse_typed_date(*, text: str, today: date) -> date:
    cleaned = text.strip().lower()

    if cleaned == "today":
        return today

    if cleaned == "tomorrow":
        return today + timedelta(days=1)

    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    raise ValueError(
        "Could not read that date. Use <code>DD-MM-YYYY</code>, "
        "<code>today</code>, or <code>tomorrow</code>."
    )


def parse_typed_time(*, text: str) -> time:
    cleaned = text.strip()

    for fmt in ("%H:%M", "%H.%M"):
        try:
            return datetime.strptime(cleaned, fmt).time().replace(second=0, microsecond=0)
        except ValueError:
            continue

    raise ValueError("Could not read that time. Use <code>HH:MM</code> (24-hour).")


def parse_typed_datetime(*, text: str, today: date) -> Tuple[date, time]:
    cleaned = text.strip()

    for fmt in ("%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M"):
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.date(), parsed.time().replace(second=0, microsecond=0)
        except ValueError:
            continue

    raise ValueError(
        "Use <code>DD-MM-YYYY HH:MM</code> e.g. <code>10-07-2026 09:30</code>."
    )
