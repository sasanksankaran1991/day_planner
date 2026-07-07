from telegram import Update
from telegram.ext import ContextTypes

from services.telegram_service import TelegramService


async def block_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    if query is None or query.data is None or update.effective_chat is None:
        return

    await query.answer()

    if not (query.data.startswith("bd:") or query.data.startswith("bs:")):
        return

    chat_id = str(update.effective_chat.id)

    try:
        action, plan_date, block_number = TelegramService.parse_action_callback(
            data=query.data,
        )

        if action == "bd":
            confirmation = TelegramService.mark_block_done_by_number(
                chat_id=chat_id,
                block_number=block_number,
                plan_date=plan_date,
            )
        else:
            confirmation = TelegramService.mark_block_skipped_by_number(
                chat_id=chat_id,
                block_number=block_number,
                plan_date=plan_date,
            )

        await query.message.reply_text(confirmation)

    except ValueError as error:
        await query.answer(str(error), show_alert=True)
