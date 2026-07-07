import logging

from telegram.ext import ContextTypes

from jobs.todo import execute_morning_notifications
from jobs.todo import execute_task_end_notifications
from jobs.todo import execute_task_reminders

logger = logging.getLogger(__name__)


async def check_morning_notifications(context: ContextTypes.DEFAULT_TYPE) -> None:
    await execute_morning_notifications(bot=context.bot)


async def check_task_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    await execute_task_reminders(bot=context.bot)


async def check_task_end_notifications(context: ContextTypes.DEFAULT_TYPE) -> None:
    await execute_task_end_notifications(bot=context.bot)
