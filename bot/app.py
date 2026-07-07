import logging

from telegram.ext import Application
from telegram.ext import CallbackQueryHandler
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import filters

from bot.handlers.callbacks import block_action_callback
from bot.handlers.commands import help_command
from bot.handlers.commands import link_command
from bot.handlers.commands import start_command
from bot.handlers.commands import today_command
from bot.handlers.messages import block_reply_message
from bot.scheduler import check_block_starts
from bot.scheduler import check_day_summaries
from config.settings import SCHEDULER_POLL_SECONDS
from config.settings import TELEGRAM_BOT_TOKEN
from config.settings import USE_CLOUD_SCHEDULER
from database.init_db import initialize_database
from database.migrate import migrate_database
from services.user_service import UserService

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def build_application() -> Application:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Configure it in .env "
            "(local) or Secret Manager (GCP)."
        )

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("link", link_command))
    application.add_handler(CommandHandler("today", today_command))
    application.add_handler(
        CallbackQueryHandler(block_action_callback, pattern=r"^b[ds]:")
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, block_reply_message)
    )

    if not USE_CLOUD_SCHEDULER:
        application.job_queue.run_repeating(
            check_block_starts,
            interval=SCHEDULER_POLL_SECONDS,
            first=5,
        )
        application.job_queue.run_repeating(
            check_day_summaries,
            interval=SCHEDULER_POLL_SECONDS,
            first=5,
        )
        logger.info(
            "Embedded scheduler enabled (every %s seconds). "
            "Set USE_CLOUD_SCHEDULER=true for GCP.",
            SCHEDULER_POLL_SECONDS,
        )
    else:
        logger.info(
            "Embedded scheduler disabled — use Cloud Scheduler + jobs service."
        )

    return application


def main() -> None:
    migrate_database()
    initialize_database()
    UserService.ensure_admin_exists()

    application = build_application()
    logger.info("Day Planner Telegram bot started (polling).")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
