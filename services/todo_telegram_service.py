import secrets
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from io import BytesIO
from typing import List
from typing import Optional
from typing import Tuple

import pytz

from config.settings import TODO_TELEGRAM_BOT_TOKEN
from config.settings import TODO_TELEGRAM_BOT_USERNAME
from database.models import TodoTelegramNotification
from database.session import get_db
from repositories.todo_telegram_notification_repository import (
    TodoTelegramNotificationRepository,
)
from repositories.user_repository import UserRepository
from services.todo_service import TodoService
from services.todo_telegram_image import REMINDER_MINUTES_BEFORE
from services.todo_telegram_image import SUMMARY_UPDATE_WINDOW_DAYS
from services.todo_telegram_image import TASK_DURATION_MINUTES
from services.todo_telegram_image import build_day_summary_notification
from services.todo_telegram_image import build_task_end_notification
from services.todo_telegram_image import build_task_reminder_notification
from services.todo_telegram_image import build_today_list_notification
from services.todo_telegram_image import format_task_time_range
from services.todo_telegram_image import is_task_actionable
from utils.enums import OccurrenceStatus
from utils.time_slots import minutes_to_time
from utils.time_slots import time_to_minutes

LINK_CODE_TTL_MINUTES = 15
LINK_PAYLOAD_PREFIX = "todolink"
DAY_SUMMARY_HOUR = 5

NOTIFICATION_DAY_SUMMARY = "TODO_DAY_SUMMARY"
NOTIFICATION_TODAY_LIST = "TODO_TODAY_LIST"
NOTIFICATION_TASK_REMINDER = "TASK_REMINDER"
NOTIFICATION_TASK_END = "TASK_END"

_resolved_bot_username: Optional[str] = None


def _resolve_bot_username() -> str:
    global _resolved_bot_username

    if TODO_TELEGRAM_BOT_USERNAME:
        return TODO_TELEGRAM_BOT_USERNAME

    if _resolved_bot_username:
        return _resolved_bot_username

    if not TODO_TELEGRAM_BOT_TOKEN:
        return ""

    import httpx

    response = httpx.get(
        f"https://api.telegram.org/bot{TODO_TELEGRAM_BOT_TOKEN}/getMe",
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()

    if not payload.get("ok"):
        return ""

    username = payload.get("result", {}).get("username", "")
    _resolved_bot_username = username
    return username


def _validate_summary_update_window(*, plan_date: date, today: date) -> None:
    if plan_date > today:
        raise ValueError("Cannot update future days.")

    days_ago = (today - plan_date).days

    if days_ago > SUMMARY_UPDATE_WINDOW_DAYS:
        raise ValueError(
            f"Summary can only be updated within {SUMMARY_UPDATE_WINDOW_DAYS} days."
        )


def _truncate_time(value: time) -> time:
    return value.replace(second=0, microsecond=0)


def _get_task_action_context(
    *,
    user,
    task_number: int,
    plan_date: Optional[date] = None,
) -> Tuple[List[dict], dict, int, date, date, time]:
    tz = pytz.timezone(user.timezone)
    today = datetime.now(tz).date()
    now = datetime.now(tz).time().replace(second=0, microsecond=0)
    target_date = plan_date or today

    if plan_date is not None and plan_date != today:
        _validate_summary_update_window(plan_date=target_date, today=today)

    items = TodoService.get_dashboard_occurrences(
        user_id=user.id,
        on_date=target_date,
        today=today,
        now=now,
    )

    if not items:
        raise ValueError(f"No tasks planned for {target_date.strftime('%d %b %Y')}.")

    if task_number < 1 or task_number > len(items):
        raise ValueError(
            f"Task {task_number} does not exist. "
            f"You have {len(items)} tasks on that day."
        )

    item = items[task_number - 1]
    return items, item, task_number, today, target_date, now


class TodoTelegramService:

    @staticmethod
    def generate_link_code(*, user_id: int) -> str:
        code = f"{secrets.randbelow(900000) + 100000:06d}"
        expires_at = datetime.now(pytz.UTC) + timedelta(minutes=LINK_CODE_TTL_MINUTES)

        with get_db() as db:
            user = UserRepository.get_by_id(db=db, user_id=user_id)

            if user is None:
                raise ValueError("User not found.")

            user.todo_telegram_link_code = code
            user.todo_telegram_link_expires_at = expires_at
            UserRepository.update(db=db, user=user)

        return code

    @staticmethod
    def is_bot_configured() -> bool:
        return bool(TODO_TELEGRAM_BOT_TOKEN and _resolve_bot_username())

    @staticmethod
    def build_connect_url(*, link_code: str) -> str:
        bot_username = _resolve_bot_username()

        if not bot_username:
            raise ValueError(
                "Todo Telegram bot is not configured. "
                "Set TODO_TELEGRAM_BOT_TOKEN in `.env` or Secret Manager."
            )

        payload = f"{LINK_PAYLOAD_PREFIX}{link_code}"
        return f"https://t.me/{bot_username}?start={payload}"

    @staticmethod
    def parse_link_payload(*, payload: str) -> Optional[str]:
        if not payload.startswith(LINK_PAYLOAD_PREFIX):
            return None

        link_code = payload[len(LINK_PAYLOAD_PREFIX):]

        if len(link_code) != 6 or not link_code.isdigit():
            return None

        return link_code

    @staticmethod
    def is_telegram_linked(*, user_id: int) -> bool:
        with get_db() as db:
            user = UserRepository.get_by_id(db=db, user_id=user_id)

            if user is None:
                return False

            return bool(user.todo_telegram_chat_id)

    @staticmethod
    def start_connect_flow(*, user_id: int) -> str:
        link_code = TodoTelegramService.generate_link_code(user_id=user_id)
        return TodoTelegramService.build_connect_url(link_code=link_code)

    @staticmethod
    def link_telegram_account(*, link_code: str, chat_id: str) -> str:
        with get_db() as db:
            user = UserRepository.get_by_todo_link_code(db=db, link_code=link_code)

            if user is None:
                raise ValueError("Invalid link code.")

            if user.todo_telegram_link_expires_at is None:
                raise ValueError("Link code has expired. Generate a new one in Settings.")

            expires_at = user.todo_telegram_link_expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=pytz.UTC)

            if datetime.now(pytz.UTC) > expires_at:
                raise ValueError("Link code has expired. Generate a new one in Settings.")

            existing = UserRepository.get_by_todo_telegram_chat_id(
                db=db,
                chat_id=chat_id,
            )

            if existing and existing.id != user.id:
                raise ValueError("This Telegram account is already linked to another user.")

            user.todo_telegram_chat_id = str(chat_id)
            user.todo_telegram_link_code = None
            user.todo_telegram_link_expires_at = None
            UserRepository.update(db=db, user=user)

            return user.display_name

    @staticmethod
    def get_user_by_chat_id(*, chat_id: str):
        with get_db() as db:
            return UserRepository.get_by_todo_telegram_chat_id(
                db=db,
                chat_id=str(chat_id),
            )

    @staticmethod
    def list_linked_users():
        with get_db() as db:
            return UserRepository.list_with_todo_telegram(db=db)

    @staticmethod
    def parse_action_callback(*, data: str) -> Tuple[str, Optional[date], int]:
        parts = data.split(":")

        if len(parts) not in (2, 3):
            raise ValueError("Invalid action.")

        action = parts[0]

        if action not in ("td", "ts"):
            raise ValueError("Invalid action.")

        if len(parts) == 2:
            return action, None, int(parts[1])

        return action, date.fromisoformat(parts[1]), int(parts[2])

    @staticmethod
    def mark_task_done_by_number(
        *,
        chat_id: str,
        task_number: int,
        plan_date: Optional[date] = None,
    ) -> str:
        user = TodoTelegramService.get_user_by_chat_id(chat_id=chat_id)

        if user is None:
            raise ValueError("Telegram account is not linked.")

        _items, item, _number, _today, target_date, _now = _get_task_action_context(
            user=user,
            task_number=task_number,
            plan_date=plan_date,
        )

        if item["status"] == OccurrenceStatus.DONE:
            raise ValueError(f"Task {task_number} is already done.")

        if not is_task_actionable(item=item):
            raise ValueError(f"Task {task_number} is not open for updates.")

        TodoService.mark_done(
            occurrence_id=item["occurrence_id"],
            user_id=user.id,
        )

        time_label = format_task_time_range(task_time=item["display_time"])
        return f"✅ Task {task_number} marked done: {item['title']} ({time_label})"

    @staticmethod
    def mark_task_skipped_by_number(
        *,
        chat_id: str,
        task_number: int,
        plan_date: Optional[date] = None,
    ) -> str:
        user = TodoTelegramService.get_user_by_chat_id(chat_id=chat_id)

        if user is None:
            raise ValueError("Telegram account is not linked.")

        _items, item, _number, _today, target_date, _now = _get_task_action_context(
            user=user,
            task_number=task_number,
            plan_date=plan_date,
        )

        if item["status"] == OccurrenceStatus.SKIPPED:
            raise ValueError(f"Task {task_number} is already skipped.")

        if not is_task_actionable(item=item):
            raise ValueError(f"Task {task_number} is not open for updates.")

        TodoService.mark_skipped(
            occurrence_id=item["occurrence_id"],
            user_id=user.id,
        )

        time_label = format_task_time_range(task_time=item["display_time"])
        return f"⏭ Task {task_number} marked skipped: {item['title']} ({time_label})"

    @staticmethod
    def _get_user_items_for_date(*, user, plan_date: date, now: time) -> List[dict]:
        tz = pytz.timezone(user.timezone)
        today = datetime.now(tz).date()

        return TodoService.get_dashboard_occurrences(
            user_id=user.id,
            on_date=plan_date,
            today=today,
            now=now,
        )

    @staticmethod
    def get_due_morning_notifications() -> List[Tuple]:
        due = []

        for user in TodoTelegramService.list_linked_users():
            tz = pytz.timezone(user.timezone)
            now = datetime.now(tz)

            if now.hour != DAY_SUMMARY_HOUR:
                continue

            today = now.date()
            yesterday = today - timedelta(days=1)
            current_time = now.time().replace(second=0, microsecond=0)

            yesterday_items = TodoTelegramService._get_user_items_for_date(
                user=user,
                plan_date=yesterday,
                now=current_time,
            )

            if yesterday_items:
                with get_db() as db:
                    already_sent = TodoTelegramNotificationRepository.was_daily_notification_sent(
                        db=db,
                        user_id=user.id,
                        plan_date=yesterday,
                        notification_type=NOTIFICATION_DAY_SUMMARY,
                    )

                if not already_sent:
                    due.append(
                        (
                            user,
                            yesterday,
                            yesterday_items,
                            current_time,
                            NOTIFICATION_DAY_SUMMARY,
                        )
                    )

            today_items = TodoTelegramService._get_user_items_for_date(
                user=user,
                plan_date=today,
                now=current_time,
            )

            if today_items:
                with get_db() as db:
                    already_sent = TodoTelegramNotificationRepository.was_daily_notification_sent(
                        db=db,
                        user_id=user.id,
                        plan_date=today,
                        notification_type=NOTIFICATION_TODAY_LIST,
                    )

                if not already_sent:
                    due.append(
                        (
                            user,
                            today,
                            today_items,
                            current_time,
                            NOTIFICATION_TODAY_LIST,
                        )
                    )

        return due

    @staticmethod
    def get_due_task_reminders() -> List[Tuple]:
        due = []

        for user in TodoTelegramService.list_linked_users():
            tz = pytz.timezone(user.timezone)
            now = datetime.now(tz)
            today = now.date()
            current_time = _truncate_time(now.time())

            items = TodoTelegramService._get_user_items_for_date(
                user=user,
                plan_date=today,
                now=current_time,
            )

            for index, item in enumerate(items):
                if item["status"] in (OccurrenceStatus.DONE, OccurrenceStatus.SKIPPED):
                    continue

                task_time = _truncate_time(item["display_time"])
                reminder_minutes = time_to_minutes(task_time) - REMINDER_MINUTES_BEFORE

                if reminder_minutes < 0:
                    continue

                reminder_time = minutes_to_time(reminder_minutes)

                if reminder_time != current_time:
                    continue

                with get_db() as db:
                    already_sent = TodoTelegramNotificationRepository.was_sent(
                        db=db,
                        user_id=user.id,
                        plan_date=today,
                        occurrence_id=item["occurrence_id"],
                        notification_type=NOTIFICATION_TASK_REMINDER,
                    )

                if already_sent:
                    continue

                due.append(
                    (
                        user,
                        today,
                        items,
                        item,
                        index + 1,
                        current_time,
                        NOTIFICATION_TASK_REMINDER,
                    )
                )

        return due

    @staticmethod
    def get_due_task_end_notifications() -> List[Tuple]:
        due = []

        for user in TodoTelegramService.list_linked_users():
            tz = pytz.timezone(user.timezone)
            now = datetime.now(tz)
            today = now.date()
            current_time = _truncate_time(now.time())
            current_minutes = time_to_minutes(current_time)

            items = TodoTelegramService._get_user_items_for_date(
                user=user,
                plan_date=today,
                now=current_time,
            )

            for index, item in enumerate(items):
                if item["status"] in (OccurrenceStatus.DONE, OccurrenceStatus.SKIPPED):
                    continue

                task_time = _truncate_time(item["display_time"])
                end_minutes = time_to_minutes(task_time) + TASK_DURATION_MINUTES

                if end_minutes >= 24 * 60:
                    end_minutes = (24 * 60) - 1

                if current_minutes != end_minutes:
                    continue

                with get_db() as db:
                    already_sent = TodoTelegramNotificationRepository.was_sent(
                        db=db,
                        user_id=user.id,
                        plan_date=today,
                        occurrence_id=item["occurrence_id"],
                        notification_type=NOTIFICATION_TASK_END,
                    )

                if already_sent:
                    continue

                due.append(
                    (
                        user,
                        today,
                        items,
                        item,
                        index + 1,
                        current_time,
                        NOTIFICATION_TASK_END,
                    )
                )

        return due

    @staticmethod
    def record_notification(
        *,
        user_id: int,
        plan_date: date,
        occurrence_id: int,
        notification_type: str,
    ) -> None:
        with get_db() as db:
            TodoTelegramNotificationRepository.record(
                db=db,
                notification=TodoTelegramNotification(
                    user_id=user_id,
                    plan_date=plan_date,
                    occurrence_id=occurrence_id,
                    notification_type=notification_type,
                ),
            )

    @staticmethod
    def build_morning_message(
        *,
        user,
        plan_date: date,
        items: List[dict],
        now: time,
        notification_type: str,
    ) -> Tuple[BytesIO, str, Optional[object]]:
        tz = pytz.timezone(user.timezone)
        today = datetime.now(tz).date()

        if notification_type == NOTIFICATION_DAY_SUMMARY:
            image_bytes, caption, reply_markup = build_day_summary_notification(
                items=items,
                plan_date=plan_date,
                today=today,
                now=now,
            )
            filename = "todo_summary.png"
        else:
            image_bytes, caption, reply_markup = build_today_list_notification(
                items=items,
                plan_date=plan_date,
                today=today,
                now=now,
            )
            filename = "todo_today.png"

        image_file = BytesIO(image_bytes)
        image_file.name = filename
        return image_file, caption, reply_markup

    @staticmethod
    def build_task_alert_message(
        *,
        user,
        plan_date: date,
        items: List[dict],
        focus_item: dict,
        task_number: int,
        now: time,
        notification_type: str,
    ) -> Tuple[BytesIO, str, Optional[object]]:
        tz = pytz.timezone(user.timezone)
        today = datetime.now(tz).date()

        if notification_type == NOTIFICATION_TASK_REMINDER:
            image_bytes, caption, reply_markup = build_task_reminder_notification(
                items=items,
                focus_item=focus_item,
                task_number=task_number,
                plan_date=plan_date,
                today=today,
                now=now,
            )
            filename = "todo_reminder.png"
        else:
            image_bytes, caption, reply_markup = build_task_end_notification(
                items=items,
                focus_item=focus_item,
                task_number=task_number,
                plan_date=plan_date,
                today=today,
                now=now,
            )
            filename = "todo_end.png"

        image_file = BytesIO(image_bytes)
        image_file.name = filename
        return image_file, caption, reply_markup
