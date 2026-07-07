from telegram import Update
from telegram.ext import ContextTypes

from services.telegram_service import TelegramService
from bot.help_text import build_planner_help_text


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    await update.message.reply_text(
        build_planner_help_text(),
        parse_mode="HTML",
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_chat is None:
        return

    if context.args:
        link_code = TelegramService.parse_link_payload(payload=context.args[0])

        if link_code is not None:
            try:
                display_name = TelegramService.link_telegram_account(
                    link_code=link_code,
                    chat_id=str(update.effective_chat.id),
                )
                await update.message.reply_text(
                    f"Linked to {display_name}. You'll receive day updates when blocks start."
                )

            except ValueError as error:
                await update.message.reply_text(str(error))

            return

    await update.message.reply_text(
        "Day Planner bot\n\n"
        "1. Open Day Planner → Settings\n"
        "2. Click Connect Telegram\n"
        "3. Tap Start in this chat\n\n"
        "When a block starts, you'll get a colored day image with "
        "code, time, description, and tag for every block.\n\n"
        "Send /help for full command list.\n\n"
        "Reply with block number + action: "
        "<code>2 yes</code> done, <code>2 no</code> skip, <code>2 undo</code> reset.",
        parse_mode="HTML",
    )


async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_chat is None:
        return

    if not context.args:
        await update.message.reply_text("Usage: /link <6-digit-code>")
        return

    link_code = context.args[0].strip()

    try:
        display_name = TelegramService.link_telegram_account(
            link_code=link_code,
            chat_id=str(update.effective_chat.id),
        )
        await update.message.reply_text(
            f"Linked to {display_name}. You'll receive day updates when blocks start."
        )

    except ValueError as error:
        await update.message.reply_text(str(error))


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_chat is None:
        return

    user = TelegramService.get_user_by_chat_id(
        chat_id=str(update.effective_chat.id),
    )

    if user is None:
        await update.message.reply_text(
            "Link your account first from Day Planner → Settings → Connect Telegram."
        )
        return

    from datetime import datetime

    import pytz

    from services.day_plan_service import DayPlanService
    from utils.enums import BlockStatus

    tz = pytz.timezone(user.timezone)
    today = datetime.now(tz).date()
    now = datetime.now(tz).time()
    blocks = DayPlanService.get_blocks(user_id=user.id, plan_date=today)

    if not blocks:
        await update.message.reply_text("No blocks planned for today.")
        return

    current_block = None

    for block in blocks:
        if block.start_time <= now < block.end_time and block.status != BlockStatus.DONE:
            current_block = block
            break

    if current_block is None:
        for block in blocks:
            if block.status != BlockStatus.DONE:
                current_block = block
                break

    if current_block is None:
        current_block = blocks[-1]

    image_file, caption, reply_markup = TelegramService.build_block_start_message(
        user=user,
        plan_date=today,
        blocks=blocks,
        current_block=current_block,
        now=now,
    )

    await update.message.reply_photo(
        photo=image_file,
        caption=caption,
        parse_mode="HTML",
        reply_markup=reply_markup,
    )
