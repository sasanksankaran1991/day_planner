from datetime import date
from datetime import time
from datetime import timedelta
import re
from typing import List
from typing import Optional
from typing import Tuple

from utils.enums import RecurrenceType

_DATE_TIME_PATTERN = re.compile(
    r"^(\d{1,2})-(\d{1,2})-(\d{4})\s+(\d{1,2}):(\d{2})$"
)
_RELATIVE_TIME_PATTERN = re.compile(
    r"^(today|tomorrow)\s+(\d{1,2}):(\d{2})$",
    re.IGNORECASE,
)
_DATE_ONLY_PATTERN = re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{4})$")

WEEKDAY_ALIASES = {
    "mon": 0,
    "monday": 0,
    "tue": 1,
    "tuesday": 1,
    "wed": 2,
    "wednesday": 2,
    "thu": 3,
    "thursday": 3,
    "fri": 4,
    "friday": 4,
    "sat": 5,
    "saturday": 5,
    "sun": 6,
    "sunday": 6,
}

REPEAT_CHOICES = [
    ("One time", RecurrenceType.ONE_TIME),
    ("Daily", RecurrenceType.DAILY),
    ("Weekly", RecurrenceType.WEEKLY),
    ("Weekdays (Mon–Fri)", RecurrenceType.WEEKDAYS),
    ("Monthly", RecurrenceType.MONTHLY),
    ("Custom days", RecurrenceType.CUSTOM),
]


def format_help_text() -> str:
    return (
        "<b>Create a task</b>\n\n"
        "I'll ask for a few details step by step.\n"
        "Send /cancel anytime to stop.\n\n"
        "<b>Formats</b>\n"
        "• Date & time: <code>DD-MM-YYYY HH:MM</code>\n"
        "  e.g. <code>07-07-2026 09:30</code>\n"
        "• Or: <code>today 09:30</code> / <code>tomorrow 14:00</code>\n"
        "• Repeat until: <code>DD-MM-YYYY</code>\n"
        "• Custom days: <code>mon,wed,fri</code> or <code>0,2,4</code> "
        "(0=Mon … 6=Sun)\n\n"
        "<b>Step 1 — Title</b>\n"
        "What is the task title?"
    )


def _build_time(hour: int, minute: int) -> time:
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("Invalid time. Use HH:MM between 00:00 and 23:59.")

    return time(hour, minute)


def parse_scheduled_datetime(*, text: str, today: date) -> Tuple[date, time]:
    cleaned = text.strip()

    relative_match = _RELATIVE_TIME_PATTERN.match(cleaned)

    if relative_match:
        day_word = relative_match.group(1).lower()
        hour = int(relative_match.group(2))
        minute = int(relative_match.group(3))
        scheduled_date = today

        if day_word == "tomorrow":
            scheduled_date = today + timedelta(days=1)

        return scheduled_date, _build_time(hour, minute)

    absolute_match = _DATE_TIME_PATTERN.match(cleaned)

    if absolute_match:
        day = int(absolute_match.group(1))
        month = int(absolute_match.group(2))
        year = int(absolute_match.group(3))
        hour = int(absolute_match.group(4))
        minute = int(absolute_match.group(5))

        try:
            scheduled_date = date(year, month, day)
        except ValueError as error:
            raise ValueError("Invalid date. Use DD-MM-YYYY HH:MM.") from error

        return scheduled_date, _build_time(hour, minute)

    raise ValueError(
        "Could not read date/time. Use DD-MM-YYYY HH:MM "
        "(e.g. 07-07-2026 09:30) or today 09:30 / tomorrow 14:00."
    )


def parse_repeat_until(*, text: str) -> date:
    cleaned = text.strip()
    match = _DATE_ONLY_PATTERN.match(cleaned)

    if not match:
        raise ValueError("Use DD-MM-YYYY for repeat-until (e.g. 31-07-2026).")

    day = int(match.group(1))
    month = int(match.group(2))
    year = int(match.group(3))

    try:
        return date(year, month, day)
    except ValueError as error:
        raise ValueError("Invalid date. Use DD-MM-YYYY.") from error


def parse_repeat_choice(*, text: str) -> RecurrenceType:
    cleaned = text.strip().lower()

    if cleaned.isdigit():
        index = int(cleaned)

        if 1 <= index <= len(REPEAT_CHOICES):
            return REPEAT_CHOICES[index - 1][1]

    aliases = {
        "one": RecurrenceType.ONE_TIME,
        "one time": RecurrenceType.ONE_TIME,
        "once": RecurrenceType.ONE_TIME,
        "daily": RecurrenceType.DAILY,
        "weekly": RecurrenceType.WEEKLY,
        "weekdays": RecurrenceType.WEEKDAYS,
        "weekday": RecurrenceType.WEEKDAYS,
        "monthly": RecurrenceType.MONTHLY,
        "custom": RecurrenceType.CUSTOM,
    }

    if cleaned in aliases:
        return aliases[cleaned]

    raise ValueError(
        f"Reply with a number 1–{len(REPEAT_CHOICES)} or a repeat type name."
    )


def parse_custom_days(*, text: str) -> str:
    parts = [part.strip().lower() for part in text.split(",") if part.strip()]

    if not parts:
        raise ValueError(
            "List at least one day: mon,wed,fri or 0,2,4 (0=Mon … 6=Sun)."
        )

    day_indexes = []

    for part in parts:
        if part.isdigit():
            index = int(part)

            if index < 0 or index > 6:
                raise ValueError("Day numbers must be 0–6 (0=Mon … 6=Sun).")

            day_indexes.append(index)
            continue

        if part in WEEKDAY_ALIASES:
            day_indexes.append(WEEKDAY_ALIASES[part])
            continue

        raise ValueError(
            f"Unknown day '{part}'. Use mon,tue,… or 0–6."
        )

    unique_indexes = sorted(set(day_indexes))
    return ",".join(str(index) for index in unique_indexes)


def format_repeat_menu() -> str:
    lines = ["<b>Repeat</b>", "How often should this task repeat?", ""]

    for index, (label, _type) in enumerate(REPEAT_CHOICES, start=1):
        lines.append(f"{index}. {label}")

    lines.append("")
    lines.append("Reply with the number (e.g. <code>1</code> for one time).")

    return "\n".join(lines)


def format_tag_menu(*, tags: list, tags_required: bool) -> str:
    lines = ["<b>Tag</b>", "Pick a tag for this task:", ""]

    for index, tag in enumerate(tags, start=1):
        lines.append(f"{index}. {tag.name}")

    if not tags_required:
        lines.append("")
        lines.append(
            f"{len(tags) + 1}. No tag"
        )

    lines.append("")
    lines.append("Reply with the number.")

    return "\n".join(lines)


def parse_tag_choice(
    *,
    text: str,
    tags: list,
    tags_required: bool,
) -> Optional[int]:
    cleaned = text.strip()

    if not cleaned.isdigit():
        raise ValueError("Reply with the tag number from the list.")

    choice = int(cleaned)

    if not tags_required and choice == len(tags) + 1:
        return None

    if choice < 1 or choice > len(tags):
        raise ValueError(f"Reply with a number between 1 and {len(tags)}.")

    return tags[choice - 1].id
