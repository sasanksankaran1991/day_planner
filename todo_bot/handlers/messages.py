import re
from datetime import date
from datetime import datetime

import pytz
from telegram import Update
from telegram.ext import ContextTypes

from services.todo_telegram_service import TodoTelegramService
from todo_bot.postpone_picker import build_time_picker_keyboard
from todo_bot.postpone_picker import build_time_prompt
from todo_bot.postpone_picker import clear_postpone_session
from todo_bot.postpone_picker import get_postpone_session
from todo_bot.postpone_picker import parse_typed_date
from todo_bot.postpone_picker import parse_typed_datetime
from todo_bot.postpone_picker import parse_typed_time
from todo_bot.postpone_picker import plan_date_from_session

_TASK_REPLY_PATTERN = re.compile(
    r"^\s*#?(\d+)\s+(yes|no)\s*$",
    re.IGNORECASE,
)

_POSTPONE_REPLY_PATTERN = re.compile(
    r"^\s*#?(\d+)\s+("
    r"later\s+\d{1,2}:\d{2}|"
    r"postpone\s+\d{2}-\d{2}-\d{4}\s+\d{1,2}:\d{2}|"
    r"postpone\s+tomorrow\s+\d{1,2}:\d{2}"
    r")\s*$",
    re.IGNORECASE,
)


async def _handle_active_postpone_session(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    text: str,
    chat_id: str,
    user,
) -> bool:
    session = get_postpone_session(context)

    if session is None:
        return False

    tz = pytz.timezone(user.timezone)
    today = datetime.now(tz).date()
    plan_date = plan_date_from_session(session)

    try:
        if session.get("selected_date"):
            picked_date = date.fromisoformat(session["selected_date"])
            picked_time = parse_typed_time(text=text)
        else:
            try:
                picked_date, picked_time = parse_typed_datetime(text=text, today=today)
            except ValueError:
                picked_date = parse_typed_date(text=text, today=today)
                session["selected_date"] = picked_date.isoformat()
                context.user_data["todo_postpone_session"] = session
                await update.message.reply_text(
                    build_time_prompt(picked_date=picked_date),
                    parse_mode="HTML",
                    reply_markup=build_time_picker_keyboard(picked_date=picked_date),
                )
                return True

        confirmation = TodoTelegramService.postpone_task_by_number(
            chat_id=chat_id,
            task_number=session["task_number"],
            plan_date=plan_date,
            new_date=picked_date,
            new_time=picked_time,
        )
        clear_postpone_session(context)
        await update.message.reply_text(confirmation)
        return True

    except ValueError as error:
        await update.message.reply_text(str(error), parse_mode="HTML")
        return True


async def todo_reply_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_chat is None:
        return

    text = update.message.text or ""
    chat_id = str(update.effective_chat.id)
    user = TodoTelegramService.get_user_by_chat_id(chat_id=chat_id)

    if user is not None:
        handled = await _handle_active_postpone_session(
            update,
            context,
            text=text,
            chat_id=chat_id,
            user=user,
        )

        if handled:
            return

    postpone_match = _POSTPONE_REPLY_PATTERN.match(text)

    if postpone_match:
        if user is None:
            await update.message.reply_text("Telegram account is not linked.")
            return

        try:
            task_number, new_date, new_time = TodoTelegramService.parse_postpone_reply(
                text=text,
                user=user,
            )
            confirmation = TodoTelegramService.postpone_task_by_number(
                chat_id=chat_id,
                task_number=task_number,
                new_date=new_date,
                new_time=new_time,
            )
            await update.message.reply_text(confirmation)

        except ValueError as error:
            await update.message.reply_text(str(error), parse_mode="HTML")

        return

    match = _TASK_REPLY_PATTERN.match(text)

    if not match:
        return

    task_number = int(match.group(1))
    action = match.group(2).lower()

    try:
        if action == "yes":
            confirmation = TodoTelegramService.mark_task_done_by_number(
                chat_id=chat_id,
                task_number=task_number,
            )
        else:
            confirmation = TodoTelegramService.mark_task_skipped_by_number(
                chat_id=chat_id,
                task_number=task_number,
            )

        await update.message.reply_text(confirmation)

    except ValueError as error:
        await update.message.reply_text(str(error))
