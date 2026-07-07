import calendar
from datetime import date
from datetime import timedelta
from typing import List
from typing import Optional

from utils.enums import RecurrenceType


def generate_occurrence_dates(
    *,
    recurrence_type: RecurrenceType,
    first_date: date,
    end_date: Optional[date],
    custom_days: Optional[List[int]] = None,
    horizon_days: int = 90,
) -> List[date]:
    if recurrence_type == RecurrenceType.ONE_TIME:
        return [first_date]

    if end_date is None:
        end_date = first_date + timedelta(days=horizon_days)

    dates: List[date] = []
    current = first_date

    while current <= end_date:
        if _matches_recurrence(
            current=current,
            first_date=first_date,
            recurrence_type=recurrence_type,
            custom_days=custom_days,
        ):
            dates.append(current)

        current += timedelta(days=1)

    return dates


def _matches_recurrence(
    *,
    current: date,
    first_date: date,
    recurrence_type: RecurrenceType,
    custom_days: Optional[List[int]],
) -> bool:
    if recurrence_type == RecurrenceType.DAILY:
        return True

    if recurrence_type == RecurrenceType.WEEKLY:
        return current.weekday() == first_date.weekday()

    if recurrence_type == RecurrenceType.WEEKDAYS:
        return current.weekday() < 5

    if recurrence_type == RecurrenceType.MONTHLY:
        return _monthly_day_matches(current=current, anchor_date=first_date)

    if recurrence_type == RecurrenceType.CUSTOM:
        return current.weekday() in (custom_days or [])

    return False


def _monthly_day_matches(*, current: date, anchor_date: date) -> bool:
    target_day = anchor_date.day
    last_day = calendar.monthrange(current.year, current.month)[1]
    return current.day == min(target_day, last_day)


RECURRENCE_SHORT_LABELS = {
    RecurrenceType.ONE_TIME: "",
    RecurrenceType.DAILY: "Daily",
    RecurrenceType.WEEKLY: "Weekly",
    RecurrenceType.WEEKDAYS: "Weekdays",
    RecurrenceType.MONTHLY: "Monthly",
    RecurrenceType.CUSTOM: "Custom",
}

WEEKDAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def format_recurrence_label(
    *,
    recurrence_type: RecurrenceType,
    custom_days: Optional[str] = None,
) -> str:
    if recurrence_type == RecurrenceType.ONE_TIME:
        return ""

    if recurrence_type == RecurrenceType.CUSTOM and custom_days:
        day_indexes = [
            int(day.strip())
            for day in custom_days.split(",")
            if day.strip().isdigit()
        ]
        labels = [WEEKDAY_SHORT[index] for index in day_indexes if 0 <= index < 7]

        if labels:
            return ", ".join(labels)

    return RECURRENCE_SHORT_LABELS.get(recurrence_type, "")
