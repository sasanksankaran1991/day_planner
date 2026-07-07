import re

from telegram import Update
from telegram.ext import ContextTypes

from services.telegram_service import TelegramService

_BLOCK_REPLY_PATTERN = re.compile(
    r"^\s*#?(\d+)\s+(yes|no|undo)\s*$",
    re.IGNORECASE,
)


async def block_reply_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_chat is None:
        return

    text = update.message.text or ""
    match = _BLOCK_REPLY_PATTERN.match(text)

    if not match:
        return

    block_number = int(match.group(1))
    action = match.group(2).lower()
    chat_id = str(update.effective_chat.id)

    try:
        if action == "yes":
            confirmation = TelegramService.mark_block_done_by_number(
                chat_id=chat_id,
                block_number=block_number,
            )
        elif action == "no":
            confirmation = TelegramService.mark_block_skipped_by_number(
                chat_id=chat_id,
                block_number=block_number,
            )
        else:
            confirmation = TelegramService.mark_block_pending_by_number(
                chat_id=chat_id,
                block_number=block_number,
            )

        await update.message.reply_text(confirmation)

    except ValueError as error:
        await update.message.reply_text(str(error))
