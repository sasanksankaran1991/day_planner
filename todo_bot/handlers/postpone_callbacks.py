from datetime import date
from datetime import datetime
from datetime import timedelta

import pytz
from telegram import Update
from telegram.ext import ContextTypes

from services.todo_telegram_service import TodoTelegramService
from services.todo_telegram_image import html_escape
from todo_bot.postpone_picker import build_date_picker_keyboard
from todo_bot.postpone_picker import build_date_prompt
from todo_bot.postpone_picker import build_time_picker_keyboard
from todo_bot.postpone_picker import build_time_prompt
from todo_bot.postpone_picker import calendar_month_from_session
from todo_bot.postpone_picker import decode_pick_date
from todo_bot.postpone_picker import decode_year_month
from todo_bot.postpone_picker import clear_postpone_session
from todo_bot.postpone_picker import get_postpone_session
from todo_bot.postpone_picker import parse_postpone_picker_callback
from todo_bot.postpone_picker import plan_date_from_session
from todo_bot.postpone_picker import set_postpone_session


async def _show_date_picker(
    *,
    query,
    context: ContextTypes.DEFAULT_TYPE,
    session: dict,
    today: date,
) -> None:
    month_date = calendar_month_from_session(session)
    session["calendar_month"] = month_date.isoformat()
    context.user_data["todo_postpone_session"] = session

    await query.message.reply_text(
        build_date_prompt(
            task_number=session["task_number"],
            task_title=html_escape(session["task_title"]),
        ),
        parse_mode="HTML",
        reply_markup=build_date_picker_keyboard(
            month_date=month_date,
            today=today,
        ),
    )


async def _show_time_picker(
    *,
    query,
    session: dict,
    picked_date: date,
) -> None:
    await query.message.reply_text(
        build_time_prompt(picked_date=picked_date),
        parse_mode="HTML",
        reply_markup=build_time_picker_keyboard(picked_date=picked_date),
    )


async def _complete_postpone(
    *,
    query,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: str,
    session: dict,
    picked_date: date,
    picked_time,
) -> None:
    plan_date = plan_date_from_session(session)

    confirmation = TodoTelegramService.postpone_task_by_number(
        chat_id=chat_id,
        task_number=session["task_number"],
        plan_date=plan_date,
        new_date=picked_date,
        new_time=picked_time,
    )
    clear_postpone_session(context)
    await query.message.reply_text(confirmation)


async def handle_postpone_picker_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    query = update.callback_query

    if query is None or query.data is None or update.effective_chat is None:
        return False

    action, values = parse_postpone_picker_callback(data=query.data)
    picker_actions = {
        "tpnoop",
        "tpx",
        "tpcu",
        "tpdm",
        "tpdt",
        "tpdn",
        "tpdy",
        "tptb",
        "tpt",
    }

    if action not in picker_actions:
        return False

    chat_id = str(update.effective_chat.id)

    if action == "tpnoop":
        await query.answer()
        return True

    if action == "tpx":
        await query.answer("Cancelled")
        clear_postpone_session(context)
        await query.message.reply_text("Postpone cancelled.")
        return True

    session = get_postpone_session(context)

    if action == "tpcu":
        await query.answer()

        try:
            _parsed_action, parsed_plan_date, task_number = (
                TodoTelegramService.parse_action_callback(data=query.data)
            )
        except ValueError as error:
            await query.answer(str(error), show_alert=True)
            return True

        user = TodoTelegramService.get_user_by_chat_id(chat_id=chat_id)

        if user is None:
            await query.answer("Account not linked.", show_alert=True)
            return True

        _items, item, _number, today, _target_date, _now = (
            TodoTelegramService.get_task_action_context(
                user=user,
                task_number=task_number,
                plan_date=parsed_plan_date,
            )
        )

        set_postpone_session(
            context,
            task_number=task_number,
            plan_date=parsed_plan_date,
            task_title=item["title"],
            calendar_month=today,
        )

        await _show_date_picker(
            query=query,
            context=context,
            session=get_postpone_session(context),
            today=today,
        )
        return True

    if session is None:
        await query.answer("Session expired. Tap Postpone again.", show_alert=True)
        return True

    user = TodoTelegramService.get_user_by_chat_id(chat_id=chat_id)

    if user is None:
        await query.answer("Account not linked.", show_alert=True)
        clear_postpone_session(context)
        return True

    tz = pytz.timezone(user.timezone)
    today = datetime.now(tz).date()

    if action == "tpdm" and values:
        await query.answer()
        session["calendar_month"] = decode_year_month(values[0]).isoformat()
        context.user_data["todo_postpone_session"] = session
        await query.message.edit_reply_markup(
            reply_markup=build_date_picker_keyboard(
                month_date=calendar_month_from_session(session),
                today=today,
            ),
        )
        return True

    if action == "tpdt":
        await query.answer()
        session["selected_date"] = today.isoformat()
        context.user_data["todo_postpone_session"] = session
        await _show_time_picker(query=query, session=session, picked_date=today)
        return True

    if action == "tpdn":
        await query.answer()
        picked = today + timedelta(days=1)
        session["selected_date"] = picked.isoformat()
        context.user_data["todo_postpone_session"] = session
        await _show_time_picker(query=query, session=session, picked_date=picked)
        return True

    if action == "tpdy" and values:
        await query.answer()
        picked = decode_pick_date(values[0])
        session["selected_date"] = picked.isoformat()
        context.user_data["todo_postpone_session"] = session
        await _show_time_picker(query=query, session=session, picked_date=picked)
        return True

    if action == "tptb":
        await query.answer()
        session.pop("selected_date", None)
        context.user_data["todo_postpone_session"] = session
        await _show_date_picker(
            query=query,
            context=context,
            session=session,
            today=today,
        )
        return True

    if action == "tpt" and values:
        await query.answer()
        picked_time = datetime.strptime(values[0], "%H%M").time()
        selected_raw = session.get("selected_date")

        if not selected_raw:
            await query.answer("Pick a date first.", show_alert=True)
            return True

        await _complete_postpone(
            query=query,
            context=context,
            chat_id=chat_id,
            session=session,
            picked_date=date.fromisoformat(selected_raw),
            picked_time=picked_time,
        )
        return True

    return False
