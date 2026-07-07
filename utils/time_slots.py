from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from typing import List


def generate_time_slots(
    *,
    interval_minutes: int = 15,
    start_hour: int = 5,
    end_hour: int = 24,
) -> List[time]:
    slots: List[time] = []
    current = datetime.combine(date.today(), time(start_hour, 0))
    end = datetime.combine(date.today(), time(end_hour - 1, 60 - interval_minutes))

    while current <= end:
        slots.append(current.time())
        current += timedelta(minutes=interval_minutes)

    return slots


def times_after(start: time, slots: List[time]) -> List[time]:
    return [slot for slot in slots if slot > start]


def format_time_label(value: time) -> str:
    return value.strftime("%H:%M")


def default_end_index(
    *,
    start: time,
    end_options: List[time],
    duration_minutes: int = 30,
) -> int:
    if not end_options:
        return 0

    target = (
        datetime.combine(date.today(), start) + timedelta(minutes=duration_minutes)
    ).time()

    for index, option in enumerate(end_options):
        if option >= target:
            return index

    return 0


def time_to_minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def minutes_to_time(minutes: int) -> time:
    if minutes < 0 or minutes >= 24 * 60:
        raise ValueError("Time must stay within the same day.")

    hours, mins = divmod(minutes, 60)
    return time(hours, mins)


def time_diff_minutes(end: time, start: time) -> int:
    return time_to_minutes(end) - time_to_minutes(start)


def add_minutes_to_time(value: time, minutes: int) -> time:
    return minutes_to_time(time_to_minutes(value) + minutes)


def index_for_time(value: time, options: List[time]) -> int:
    for index, option in enumerate(options):
        if option == value:
            return index

    for index, option in enumerate(options):
        if option > value:
            return max(0, index - 1)

    return max(0, len(options) - 1)


def next_available_slot(*, now: time, slots: List[time]) -> time:
    rounded = round_up_to_interval(now, interval_minutes=15)

    for slot in slots:
        if slot >= rounded:
            return slot

    return slots[-1] if slots else rounded


def round_up_to_interval(value: time, *, interval_minutes: int = 15) -> time:
    total_minutes = time_to_minutes(value)
    remainder = total_minutes % interval_minutes

    if remainder == 0:
        return value

    return minutes_to_time(total_minutes + (interval_minutes - remainder))
