import asyncio
import logging
from typing import Callable

from telegram.ext import Application

from services.telegram_offset_store import read_offset
from services.telegram_offset_store import write_offset

logger = logging.getLogger(__name__)


async def run_telegram_poll_once(
    *,
    build_application: Callable[[], Application],
    bot_name: str,
) -> dict:
    application = build_application()

    await application.initialize()
    await application.start()

    offset = read_offset(bot_name)
    updates = await application.bot.get_updates(
        offset=offset,
        timeout=0,
        allowed_updates=["message", "callback_query"],
    )

    processed = 0

    for update in updates:
        await application.process_update(update)
        processed += 1

    if updates:
        write_offset(bot_name, updates[-1].update_id + 1)

    await application.stop()
    await application.shutdown()

    return {
        "bot": bot_name,
        "processed": processed,
        "next_offset": read_offset(bot_name),
    }


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
