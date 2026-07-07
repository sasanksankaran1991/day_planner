import asyncio
import logging
from typing import Optional

from telegram import Bot

from config.settings import TELEGRAM_BOT_TOKEN
from services.telegram_service import TelegramService

logger = logging.getLogger(__name__)


async def execute_block_starts(*, bot: Optional[Bot] = None) -> int:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")

    telegram_bot = bot or Bot(token=TELEGRAM_BOT_TOKEN)
    due_notifications = TelegramService.get_blocks_starting_now()
    sent_count = 0

    for user, plan_date, blocks, current_block, now in due_notifications:
        try:
            image_file, caption, reply_markup = TelegramService.build_block_start_message(
                user=user,
                plan_date=plan_date,
                blocks=blocks,
                current_block=current_block,
                now=now,
            )

            await telegram_bot.send_photo(
                chat_id=user.telegram_chat_id,
                photo=image_file,
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )

            TelegramService.record_block_start_notification(
                user_id=user.id,
                plan_date=plan_date,
                block_id=current_block.id,
            )
            sent_count += 1

        except Exception:
            logger.exception(
                "Failed to send block start notification for user %s block %s",
                user.id,
                current_block.id,
            )

    return sent_count


async def execute_day_summaries(*, bot: Optional[Bot] = None) -> int:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")

    telegram_bot = bot or Bot(token=TELEGRAM_BOT_TOKEN)
    due_summaries = TelegramService.get_due_day_summaries()
    sent_count = 0

    for user, plan_date, blocks, now in due_summaries:
        try:
            image_file, caption, reply_markup = TelegramService.build_day_summary_message(
                user=user,
                plan_date=plan_date,
                blocks=blocks,
                now=now,
            )

            await telegram_bot.send_photo(
                chat_id=user.telegram_chat_id,
                photo=image_file,
                caption=caption,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )

            TelegramService.record_day_summary_notification(
                user_id=user.id,
                plan_date=plan_date,
                block_id=blocks[0].id,
            )
            sent_count += 1

        except Exception:
            logger.exception(
                "Failed to send day summary for user %s date %s",
                user.id,
                plan_date,
            )

    return sent_count


def execute_block_starts_sync() -> dict:
    sent = asyncio.run(execute_block_starts())
    return {"job": "planner_block_starts", "sent": sent}


def execute_day_summaries_sync() -> dict:
    sent = asyncio.run(execute_day_summaries())
    return {"job": "planner_day_summaries", "sent": sent}
