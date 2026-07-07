import logging

from telegram.ext import ContextTypes

from jobs.planner import execute_block_starts
from jobs.planner import execute_day_summaries

logger = logging.getLogger(__name__)


async def check_block_starts(context: ContextTypes.DEFAULT_TYPE) -> None:
    await execute_block_starts(bot=context.bot)


async def check_day_summaries(context: ContextTypes.DEFAULT_TYPE) -> None:
    await execute_day_summaries(bot=context.bot)
