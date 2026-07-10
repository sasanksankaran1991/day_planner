from telegram import Update
from telegram.ext import ContextTypes

from services.todo_telegram_service import TodoTelegramService
from todo_bot.handlers.postpone_callbacks import handle_postpone_picker_callback


async def todo_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    if query is None or query.data is None or update.effective_chat is None:
        return

    if not query.data.startswith("t"):
        return

    if await handle_postpone_picker_callback(update, context):
        return

    chat_id = str(update.effective_chat.id)

    try:
        action, plan_date, task_number = TodoTelegramService.parse_action_callback(
            data=query.data,
        )

        if action == "tp":
            await query.answer()
            message, reply_markup = TodoTelegramService.build_postpone_prompt(
                chat_id=chat_id,
                task_number=task_number,
                plan_date=plan_date,
            )
            await query.message.reply_text(
                message,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
            return

        await query.answer()

        if action == "td":
            confirmation = TodoTelegramService.mark_task_done_by_number(
                chat_id=chat_id,
                task_number=task_number,
                plan_date=plan_date,
            )
        elif action == "ts":
            confirmation = TodoTelegramService.mark_task_skipped_by_number(
                chat_id=chat_id,
                task_number=task_number,
                plan_date=plan_date,
            )
        elif action in ("tp30", "tp60", "tptm"):
            confirmation = TodoTelegramService.postpone_task_preset(
                chat_id=chat_id,
                task_number=task_number,
                plan_date=plan_date,
                preset=action,
            )
        else:
            raise ValueError("Invalid action.")

        await query.message.reply_text(confirmation)

    except ValueError as error:
        await query.answer(str(error), show_alert=True)
