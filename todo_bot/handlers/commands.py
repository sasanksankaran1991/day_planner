from telegram import Update
from telegram.ext import ContextTypes

from services.todo_telegram_service import TodoTelegramService
from todo_bot.help_text import build_todo_help_text


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    await update.message.reply_text(
        build_todo_help_text(),
        parse_mode="HTML",
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_chat is None:
        return

    if context.args:
        link_code = TodoTelegramService.parse_link_payload(payload=context.args[0])

        if link_code is not None:
            try:
                display_name = TodoTelegramService.link_telegram_account(
                    link_code=link_code,
                    chat_id=str(update.effective_chat.id),
                )
                await update.message.reply_text(
                    f"Linked to {display_name}. You'll receive todo reminders "
                    "and daily task summaries."
                )

            except ValueError as error:
                await update.message.reply_text(str(error))

            return

    await update.message.reply_text(
        "Todos bot\n\n"
        "1. Open Day Planner → Todos → Settings\n"
        "2. Click Connect Todo Telegram\n"
        "3. Tap Start in this chat\n\n"
        "Every morning around 5 AM you'll get yesterday's summary and today's tasks.\n"
        "Reminders arrive 15 minutes before each task and when it ends.\n\n"
        "Send /help for full command list and formats.\n\n"
        "<b>Quick commands</b>\n"
        "/today — today's tasks\n"
        "/create — add a new task\n"
        "/cancel — stop task creation\n\n"
        "Reply with task number + action: "
        "<code>2 yes</code> done, <code>2 no</code> skip.",
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
        display_name = TodoTelegramService.link_telegram_account(
            link_code=link_code,
            chat_id=str(update.effective_chat.id),
        )
        await update.message.reply_text(
            f"Linked to {display_name}. You'll receive todo reminders "
            "and daily task summaries."
        )

    except ValueError as error:
        await update.message.reply_text(str(error))


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_chat is None:
        return

    user = TodoTelegramService.get_user_by_chat_id(
        chat_id=str(update.effective_chat.id),
    )

    if user is None:
        await update.message.reply_text(
            "Link your account first from Day Planner → Todos → Settings."
        )
        return

    from datetime import datetime

    import pytz

    from services.todo_telegram_service import NOTIFICATION_TODAY_LIST

    tz = pytz.timezone(user.timezone)
    today = datetime.now(tz).date()
    now = datetime.now(tz).time().replace(second=0, microsecond=0)
    items = TodoTelegramService._get_user_items_for_date(
        user=user,
        plan_date=today,
        now=now,
    )

    if not items:
        await update.message.reply_text("No tasks planned for today.")
        return

    image_file, caption, reply_markup = TodoTelegramService.build_morning_message(
        user=user,
        plan_date=today,
        items=items,
        now=now,
        notification_type=NOTIFICATION_TODAY_LIST,
    )

    await update.message.reply_photo(
        photo=image_file,
        caption=caption,
        parse_mode="HTML",
        reply_markup=reply_markup,
    )
