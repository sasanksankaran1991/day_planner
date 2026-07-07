import re

from telegram import Update
from telegram.ext import ContextTypes

from services.todo_telegram_service import TodoTelegramService

_TASK_REPLY_PATTERN = re.compile(
    r"^\s*#?(\d+)\s+(yes|no)\s*$",
    re.IGNORECASE,
)


async def todo_reply_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_chat is None:
        return

    text = update.message.text or ""
    match = _TASK_REPLY_PATTERN.match(text)

    if not match:
        return

    task_number = int(match.group(1))
    action = match.group(2).lower()
    chat_id = str(update.effective_chat.id)

    try:
        if action == "yes":
            confirmation = TodoTelegramService.mark_task_done_by_number(
                chat_id=chat_id,
                task_number=task_number,
            )
        else:
            confirmation = TodoTelegramService.mark_task_skipped_by_number(
                chat_id=chat_id,
                task_number=task_number,
            )

        await update.message.reply_text(confirmation)

    except ValueError as error:
        await update.message.reply_text(str(error))
