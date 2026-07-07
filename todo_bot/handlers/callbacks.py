from telegram import Update
from telegram.ext import ContextTypes

from services.todo_telegram_service import TodoTelegramService


async def todo_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    if query is None or query.data is None or update.effective_chat is None:
        return

    await query.answer()

    if not (query.data.startswith("td:") or query.data.startswith("ts:")):
        return

    chat_id = str(update.effective_chat.id)

    try:
        action, plan_date, task_number = TodoTelegramService.parse_action_callback(
            data=query.data,
        )

        if action == "td":
            confirmation = TodoTelegramService.mark_task_done_by_number(
                chat_id=chat_id,
                task_number=task_number,
                plan_date=plan_date,
            )
        else:
            confirmation = TodoTelegramService.mark_task_skipped_by_number(
                chat_id=chat_id,
                task_number=task_number,
                plan_date=plan_date,
            )

        await query.message.reply_text(confirmation)

    except ValueError as error:
        await query.answer(str(error), show_alert=True)
