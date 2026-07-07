import asyncio
import logging
from dataclasses import dataclass
from typing import Callable

from telegram import Update
from telegram.ext import Application

from services.telegram_offset_store import read_offset
from services.telegram_offset_store import write_offset

logger = logging.getLogger(__name__)


@dataclass
class TelegramPollBatch:
    bot_name: str
    application: Application
    updates: list[Update]

    @property
    def pending(self) -> int:
        return len(self.updates)


async def fetch_telegram_updates(
    *,
    build_application: Callable[[], Application],
    bot_name: str,
) -> TelegramPollBatch | None:
    """Call Telegram API only — no DB required. Returns None if no new messages."""
    application = build_application()

    await application.initialize()
    await application.start()

    offset = read_offset(bot_name)
    updates = await application.bot.get_updates(
        offset=offset,
        timeout=0,
        allowed_updates=["message", "callback_query"],
    )

    if not updates:
        await application.stop()
        await application.shutdown()
        logger.info("Telegram poll (%s): no new updates", bot_name)
        return None

    logger.info("Telegram poll (%s): %s update(s) pending", bot_name, len(updates))
    return TelegramPollBatch(
        bot_name=bot_name,
        application=application,
        updates=updates,
    )


async def process_telegram_batch(batch: TelegramPollBatch) -> dict:
    processed = 0

    for update in batch.updates:
        await batch.application.process_update(update)
        processed += 1

    write_offset(batch.bot_name, batch.updates[-1].update_id + 1)

    await batch.application.stop()
    await batch.application.shutdown()

    return {
        "bot": batch.bot_name,
        "processed": processed,
        "next_offset": read_offset(batch.bot_name),
    }


async def run_telegram_poll_once(
    *,
    build_application: Callable[[], Application],
    bot_name: str,
) -> dict:
    batch = await fetch_telegram_updates(
        build_application=build_application,
        bot_name=bot_name,
    )

    if batch is None:
        return {
            "bot": bot_name,
            "processed": 0,
            "next_offset": read_offset(bot_name),
            "db_loaded": False,
        }

    result = await process_telegram_batch(batch)
    result["db_loaded"] = True
    return result


def fetch_telegram_updates_sync(
    *,
    build_application: Callable[[], Application],
    bot_name: str,
) -> TelegramPollBatch | None:
    return asyncio.run(
        fetch_telegram_updates(
            build_application=build_application,
            bot_name=bot_name,
        )
    )


def process_telegram_batch_sync(batch: TelegramPollBatch) -> dict:
    return asyncio.run(process_telegram_batch(batch))


def run_telegram_poll_sync(
    *,
    build_application: Callable[[], Application],
    bot_name: str,
) -> dict:
    return asyncio.run(
        run_telegram_poll_once(
            build_application=build_application,
            bot_name=bot_name,
        )
    )
