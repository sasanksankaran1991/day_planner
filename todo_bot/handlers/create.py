from datetime import datetime

import pytz
from telegram import Update
from telegram.ext import CommandHandler
from telegram.ext import ContextTypes
from telegram.ext import ConversationHandler
from telegram.ext import MessageHandler
from telegram.ext import filters

from services.planner_tag_service import PlannerTagService
from services.todo_service import TodoService
from services.todo_telegram_service import TodoTelegramService
from todo_bot.create_parsing import format_help_text
from todo_bot.create_parsing import format_repeat_menu
from todo_bot.create_parsing import format_tag_menu
from todo_bot.create_parsing import parse_custom_days
from todo_bot.create_parsing import parse_repeat_choice
from todo_bot.create_parsing import parse_repeat_until
from todo_bot.create_parsing import parse_scheduled_datetime
from todo_bot.create_parsing import parse_tag_choice
from utils.enums import RecurrenceType
from utils.recurrence import format_recurrence_label
from utils.recurrence import generate_occurrence_dates

(
    CREATE_TITLE,
    CREATE_DATETIME,
    CREATE_TAG,
    CREATE_REPEAT,
    CREATE_REPEAT_UNTIL,
    CREATE_CUSTOM_DAYS,
) = range(6)

CREATE_SESSION_KEY = "todo_create_session"


def _get_session(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.user_data.setdefault(CREATE_SESSION_KEY, {})


def _clear_session(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop(CREATE_SESSION_KEY, None)


def _require_linked_user(update: Update):
    if update.effective_chat is None:
        return None

    return TodoTelegramService.get_user_by_chat_id(
        chat_id=str(update.effective_chat.id),
    )


async def create_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    user = _require_linked_user(update)

    if user is None:
        await update.message.reply_text(
            "Link your account first from Day Planner → Todos → Settings."
        )
        return ConversationHandler.END

    _clear_session(context)
    _get_session(context)["user_id"] = user.id

    await update.message.reply_text(
        format_help_text(),
        parse_mode="HTML",
    )
    return CREATE_TITLE


async def create_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    title = (update.message.text or "").strip()

    if not title:
        await update.message.reply_text("Title cannot be empty. What is the task title?")
        return CREATE_TITLE

    session = _get_session(context)
    session["title"] = title

    await update.message.reply_text(
        "<b>Step 2 — Date & time</b>\n"
        "When is this task?\n\n"
        "Format: <code>DD-MM-YYYY HH:MM</code>\n"
        "Examples:\n"
        "• <code>07-07-2026 09:30</code>\n"
        "• <code>today 09:30</code>\n"
        "• <code>tomorrow 14:00</code>",
        parse_mode="HTML",
    )
    return CREATE_DATETIME


async def create_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    user = _require_linked_user(update)

    if user is None:
        await update.message.reply_text("Account link lost. Start again with /create.")
        _clear_session(context)
        return ConversationHandler.END

    tz = pytz.timezone(user.timezone)
    today = datetime.now(tz).date()
    session = _get_session(context)

    try:
        scheduled_date, scheduled_time = parse_scheduled_datetime(
            text=update.message.text or "",
            today=today,
        )
    except ValueError as error:
        await update.message.reply_text(str(error))
        return CREATE_DATETIME

    session["scheduled_date"] = scheduled_date.isoformat()
    session["scheduled_time"] = scheduled_time.strftime("%H:%M")

    tags = PlannerTagService.list_tags(user_id=user.id)
    tags_required = PlannerTagService.tags_required_on_create(user_id=user.id)
    session["tags_required"] = tags_required

    if not tags:
        if tags_required:
            await update.message.reply_text(
                "Tags are required but you have none. "
                "Add tags in Day Planner → Settings first."
            )
            _clear_session(context)
            return ConversationHandler.END

        session["tag_id"] = None
        await update.message.reply_text(
            format_repeat_menu(),
            parse_mode="HTML",
        )
        return CREATE_REPEAT

    await update.message.reply_text(
        format_tag_menu(tags=tags, tags_required=tags_required),
        parse_mode="HTML",
    )
    return CREATE_TAG


async def create_tag(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    user = _require_linked_user(update)

    if user is None:
        await update.message.reply_text("Account link lost. Start again with /create.")
        _clear_session(context)
        return ConversationHandler.END

    session = _get_session(context)
    tags = PlannerTagService.list_tags(user_id=user.id)
    tags_required = session.get("tags_required", False)

    try:
        tag_id = parse_tag_choice(
            text=update.message.text or "",
            tags=tags,
            tags_required=tags_required,
        )
    except ValueError as error:
        await update.message.reply_text(str(error))
        return CREATE_TAG

    session["tag_id"] = tag_id

    await update.message.reply_text(
        format_repeat_menu(),
        parse_mode="HTML",
    )
    return CREATE_REPEAT


async def create_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    session = _get_session(context)

    try:
        recurrence_type = parse_repeat_choice(text=update.message.text or "")
    except ValueError as error:
        await update.message.reply_text(str(error))
        return CREATE_REPEAT

    session["recurrence_type"] = recurrence_type.value

    if recurrence_type == RecurrenceType.ONE_TIME:
        return await _finalize_create(update, context)

    session["recurrence_type_enum"] = recurrence_type

    await update.message.reply_text(
        "<b>Repeat until</b>\n"
        "Last date for this repeating task?\n\n"
        "Format: <code>DD-MM-YYYY</code>\n"
        "Example: <code>31-07-2026</code>",
        parse_mode="HTML",
    )
    return CREATE_REPEAT_UNTIL


async def create_repeat_until(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    session = _get_session(context)
    scheduled_date = datetime.fromisoformat(session["scheduled_date"]).date()

    try:
        recurrence_end_date = parse_repeat_until(text=update.message.text or "")
    except ValueError as error:
        await update.message.reply_text(str(error))
        return CREATE_REPEAT_UNTIL

    if recurrence_end_date < scheduled_date:
        await update.message.reply_text(
            "Repeat-until cannot be before the start date. Try again."
        )
        return CREATE_REPEAT_UNTIL

    session["recurrence_end_date"] = recurrence_end_date.isoformat()
    recurrence_type = RecurrenceType(session["recurrence_type"])

    if recurrence_type == RecurrenceType.CUSTOM:
        await update.message.reply_text(
            "<b>Custom repeat days</b>\n"
            "Which days should it repeat on?\n\n"
            "Examples:\n"
            "• <code>mon,wed,fri</code>\n"
            "• <code>0,2,4</code> (0=Mon … 6=Sun)",
            parse_mode="HTML",
        )
        return CREATE_CUSTOM_DAYS

    return await _finalize_create(update, context)


async def create_custom_days(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is None:
        return ConversationHandler.END

    session = _get_session(context)

    try:
        custom_days = parse_custom_days(text=update.message.text or "")
    except ValueError as error:
        await update.message.reply_text(str(error))
        return CREATE_CUSTOM_DAYS

    session["custom_days"] = custom_days
    return await _finalize_create(update, context)


async def _finalize_create(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> int:
    if update.message is None:
        return ConversationHandler.END

    user = _require_linked_user(update)

    if user is None:
        await update.message.reply_text("Account link lost. Start again with /create.")
        _clear_session(context)
        return ConversationHandler.END

    session = _get_session(context)
    scheduled_date = datetime.fromisoformat(session["scheduled_date"]).date()
    hour, minute = session["scheduled_time"].split(":")
    scheduled_time = datetime.strptime(
        f"{hour}:{minute}",
        "%H:%M",
    ).time()
    recurrence_type = RecurrenceType(session["recurrence_type"])
    recurrence_end_date = None
    custom_days = session.get("custom_days")

    if recurrence_type != RecurrenceType.ONE_TIME:
        recurrence_end_date = datetime.fromisoformat(
            session["recurrence_end_date"]
        ).date()

    try:
        TodoService.create_todo(
            owner_id=user.id,
            title=session["title"],
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            recurrence_type=recurrence_type,
            recurrence_end_date=recurrence_end_date,
            custom_days=custom_days,
            tag_id=session.get("tag_id"),
        )
    except ValueError as error:
        await update.message.reply_text(f"Could not create task: {error}")
        _clear_session(context)
        return ConversationHandler.END

    tag_label = "No tag"
    tag_id = session.get("tag_id")

    if tag_id is not None:
        tags = PlannerTagService.list_tags(user_id=user.id)
        tag_by_id = {tag.id: tag.name for tag in tags}
        tag_label = tag_by_id.get(tag_id, "Tag")

    recurrence_label = format_recurrence_label(
        recurrence_type=recurrence_type,
        custom_days=custom_days,
    )

    if recurrence_type == RecurrenceType.ONE_TIME:
        ack = (
            f"✅ Task created\n\n"
            f"<b>{session['title']}</b>\n"
            f"📅 {scheduled_date.strftime('%A, %d %b %Y')}\n"
            f"🕐 {scheduled_time.strftime('%H:%M')}\n"
            f"🏷 {tag_label}"
        )
    else:
        occurrence_count = len(
            generate_occurrence_dates(
                recurrence_type=recurrence_type,
                first_date=scheduled_date,
                end_date=recurrence_end_date,
                custom_days=TodoService._parse_custom_days(custom_days),
            )
        )
        ack = (
            f"✅ Recurring task created\n\n"
            f"<b>{session['title']}</b>\n"
            f"📅 Starts {scheduled_date.strftime('%d %b %Y')} "
            f"→ until {recurrence_end_date.strftime('%d %b %Y')}\n"
            f"🕐 {scheduled_time.strftime('%H:%M')}\n"
            f"🔁 {recurrence_label or recurrence_type.value}\n"
            f"🏷 {tag_label}\n"
            f"📋 {occurrence_count} days scheduled"
        )

    await update.message.reply_text(ack, parse_mode="HTML")
    _clear_session(context)
    return ConversationHandler.END


async def create_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message is not None:
        await update.message.reply_text("Task creation cancelled.")

    _clear_session(context)
    return ConversationHandler.END


def build_create_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("create", create_start)],
        states={
            CREATE_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_title),
            ],
            CREATE_DATETIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_datetime),
            ],
            CREATE_TAG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_tag),
            ],
            CREATE_REPEAT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_repeat),
            ],
            CREATE_REPEAT_UNTIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_repeat_until),
            ],
            CREATE_CUSTOM_DAYS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, create_custom_days),
            ],
        },
        fallbacks=[CommandHandler("cancel", create_cancel)],
        name="todo_create_conversation",
        persistent=False,
    )
