import asyncio
import logging
from typing import Optional

from telegram import Bot

from config.settings import TODO_TELEGRAM_BOT_TOKEN
from services.todo_telegram_service import NOTIFICATION_TASK_END
from services.todo_telegram_service import NOTIFICATION_TASK_REMINDER
from services.todo_telegram_service import TodoTelegramService

logger = logging.getLogger(__name__)


async def execute_morning_notifications(*, bot: Optional[Bot] = None) -> int:
    if not TODO_TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TODO_TELEGRAM_BOT_TOKEN is not configured.")

    telegram_bot = bot or Bot(token=TODO_TELEGRAM_BOT_TOKEN)
    due_notifications = TodoTelegramService.get_due_morning_notifications()
    sent_count = 0

    for user, plan_date, items, now, notification_type in due_notifications:
        try:
            image_file, caption, reply_markup = TodoTelegramService.build_morning_message(
                user=user,
                plan_date=plan_date,
                items=items,
                now=now,
                notification_type=notification_type,
            )

            await telegram_bot.send_photo(
                chat_id=user.todo_telegram_chat_id,
                photo=image_file,
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )

            TodoTelegramService.record_notification(
                user_id=user.id,
                plan_date=plan_date,
                occurrence_id=items[0]["occurrence_id"],
                notification_type=notification_type,
            )
            sent_count += 1

        except Exception:
            logger.exception(
                "Failed to send todo morning notification for user %s date %s type %s",
                user.id,
                plan_date,
                notification_type,
            )

    return sent_count


async def execute_task_reminders(*, bot: Optional[Bot] = None) -> int:
    if not TODO_TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TODO_TELEGRAM_BOT_TOKEN is not configured.")

    telegram_bot = bot or Bot(token=TODO_TELEGRAM_BOT_TOKEN)
    due_notifications = TodoTelegramService.get_due_task_reminders()
    sent_count = 0

    for (
        user,
        plan_date,
        items,
        focus_item,
        task_number,
        now,
        notification_type,
    ) in due_notifications:
        try:
            image_file, caption, reply_markup = TodoTelegramService.build_task_alert_message(
                user=user,
                plan_date=plan_date,
                items=items,
                focus_item=focus_item,
                task_number=task_number,
                now=now,
                notification_type=notification_type,
            )

            await telegram_bot.send_photo(
                chat_id=user.todo_telegram_chat_id,
                photo=image_file,
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )

            TodoTelegramService.record_notification(
                user_id=user.id,
                plan_date=plan_date,
                occurrence_id=focus_item["occurrence_id"],
                notification_type=NOTIFICATION_TASK_REMINDER,
            )
            sent_count += 1

        except Exception:
            logger.exception(
                "Failed to send todo reminder for user %s occurrence %s",
                user.id,
                focus_item["occurrence_id"],
            )

    return sent_count


async def execute_task_end_notifications(*, bot: Optional[Bot] = None) -> int:
    if not TODO_TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TODO_TELEGRAM_BOT_TOKEN is not configured.")

    telegram_bot = bot or Bot(token=TODO_TELEGRAM_BOT_TOKEN)
    due_notifications = TodoTelegramService.get_due_task_end_notifications()
    sent_count = 0

    for (
        user,
        plan_date,
        items,
        focus_item,
        task_number,
        now,
        notification_type,
    ) in due_notifications:
        try:
            image_file, caption, reply_markup = TodoTelegramService.build_task_alert_message(
                user=user,
                plan_date=plan_date,
                items=items,
                focus_item=focus_item,
                task_number=task_number,
                now=now,
                notification_type=notification_type,
            )

            await telegram_bot.send_photo(
                chat_id=user.todo_telegram_chat_id,
                photo=image_file,
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )

            TodoTelegramService.record_notification(
                user_id=user.id,
                plan_date=plan_date,
                occurrence_id=focus_item["occurrence_id"],
                notification_type=NOTIFICATION_TASK_END,
            )
            sent_count += 1

        except Exception:
            logger.exception(
                "Failed to send todo end notification for user %s occurrence %s",
                user.id,
                focus_item["occurrence_id"],
            )

    return sent_count


def execute_morning_notifications_sync() -> dict:
    sent = asyncio.run(execute_morning_notifications())
    return {"job": "todo_morning", "sent": sent}


def execute_task_reminders_sync() -> dict:
    sent = asyncio.run(execute_task_reminders())
    return {"job": "todo_reminders", "sent": sent}


def execute_task_end_notifications_sync() -> dict:
    sent = asyncio.run(execute_task_end_notifications())
    return {"job": "todo_task_end", "sent": sent}
