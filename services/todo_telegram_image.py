from __future__ import annotations

from datetime import date
from datetime import time
from io import BytesIO
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from utils.enums import OccurrenceStatus
from utils.time_slots import add_minutes_to_time
from utils.time_slots import format_time_label

SUMMARY_UPDATE_WINDOW_DAYS = 7
TASK_DURATION_MINUTES = 30
REMINDER_MINUTES_BEFORE = 15

ROW_HEIGHT = 68
PADDING = 24
WIDTH = 900
HEADER_HEIGHT = 110
FOOTER_HEIGHT = 64

STATE_COLORS = {
    "done": (165, 214, 167),
    "overdue": (255, 205, 210),
    "skipped": (255, 205, 210),
    "upcoming": (187, 222, 251),
    "current": (255, 224, 130),
    "postponed": (255, 243, 224),
}

STATE_BORDER_COLORS = {
    "done": (46, 125, 50),
    "overdue": (229, 57, 53),
    "skipped": (198, 40, 40),
    "upcoming": (30, 136, 229),
    "current": (255, 160, 0),
    "postponed": (251, 140, 0),
}

STATE_TEXT_COLORS = {
    "done": (27, 94, 32),
    "overdue": (62, 39, 35),
    "skipped": (62, 39, 35),
    "upcoming": (13, 71, 161),
    "current": (62, 39, 35),
    "postponed": (230, 81, 0),
}

STATUS_LABELS = {
    "done": "Done",
    "overdue": "Pending",
    "skipped": "Skipped",
    "upcoming": "Upcoming",
    "current": "Now",
    "postponed": "Postponed",
}

NO_TAG_FILL = (233, 236, 239)
NO_TAG_TEXT = (73, 80, 87)

ACTIONABLE_STATES = {"overdue", "current", "postponed"}


def html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def format_task_time_range(*, task_time: time) -> str:
    end_time = add_minutes_to_time(task_time, TASK_DURATION_MINUTES)
    return (
        f"{format_time_label(task_time)} – {format_time_label(end_time)} "
        f"({TASK_DURATION_MINUTES}m)"
    )


def action_callback_data(
    *,
    action: str,
    task_number: int,
    plan_date: date,
    today: date,
) -> str:
    if plan_date == today:
        return f"{action}:{task_number}"

    return f"{action}:{plan_date.isoformat()}:{task_number}"


def is_task_actionable(*, item: dict) -> bool:
    if item["status"] in (OccurrenceStatus.DONE, OccurrenceStatus.SKIPPED):
        return False

    return item["visual_state"] in ACTIONABLE_STATES


def _parse_hex_color(value: str, *, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
    cleaned = (value or "").strip().lstrip("#")

    if len(cleaned) != 6:
        return fallback

    try:
        return (
            int(cleaned[0:2], 16),
            int(cleaned[2:4], 16),
            int(cleaned[4:6], 16),
        )
    except ValueError:
        return fallback


def _text_color_for_background(rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    red, green, blue = rgb
    luminance = (0.299 * red) + (0.587 * green) + (0.114 * blue)
    return (33, 37, 41) if luminance > 160 else (255, 255, 255)


def _load_font(*, size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []

    if bold:
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/Library/Fonts/Arial Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            ]
        )
    else:
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
        )

    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue

    return ImageFont.load_default()


def _text_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _truncate_to_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font,
    max_width: int,
) -> str:
    if max_width <= 0 or not text:
        return ""

    if _text_width(draw, text, font) <= max_width:
        return text

    ellipsis = "…"
    trimmed = text

    while len(trimmed) > 1:
        trimmed = trimmed[:-1]
        candidate = f"{trimmed.rstrip()}{ellipsis}"

        if _text_width(draw, candidate, font) <= max_width:
            return candidate

    return ellipsis


def _draw_tag_pill(
    draw: ImageDraw.ImageDraw,
    *,
    left: int,
    top: int,
    tag_name: Optional[str],
    tag_color: Optional[str],
    font,
) -> int:
    label = tag_name or "No tag"
    fill = (
        _parse_hex_color(tag_color, fallback=(30, 136, 229))
        if tag_name and tag_color
        else NO_TAG_FILL
    )
    text_color = _text_color_for_background(fill) if tag_name else NO_TAG_TEXT
    horizontal_padding = 12
    vertical_padding = 5
    text_width = _text_width(draw, label, font)
    pill_width = text_width + (horizontal_padding * 2)
    pill_height = 28

    draw.rounded_rectangle(
        (left, top, left + pill_width, top + pill_height),
        radius=12,
        fill=fill,
    )
    draw.text(
        (left + horizontal_padding, top + vertical_padding - 1),
        label,
        fill=text_color,
        font=font,
    )

    return pill_width


class TelegramTodoImageBuilder:

    @staticmethod
    def build(
        *,
        items: List[dict],
        plan_date: date,
        today: date,
        now: time,
    ) -> bytes:
        done_count = sum(
            1 for item in items if item["status"] == OccurrenceStatus.DONE
        )
        total = len(items)
        percent = round((done_count / total) * 100) if total else 0

        height = HEADER_HEIGHT + (len(items) * ROW_HEIGHT) + FOOTER_HEIGHT
        image = Image.new("RGB", (WIDTH, height), (248, 249, 250))
        draw = ImageDraw.Draw(image)

        title_font = _load_font(size=34, bold=True)
        meta_font = _load_font(size=24)
        code_font = _load_font(size=24, bold=True)
        label_font = _load_font(size=20, bold=True)
        row_font = _load_font(size=24)
        tag_font = _load_font(size=18, bold=True)
        footer_font = _load_font(size=20)

        draw.text(
            (PADDING, 22),
            plan_date.strftime("%A, %d %b %Y"),
            fill=(33, 37, 41),
            font=title_font,
        )
        draw.text(
            (PADDING, 68),
            f"Achievement: {percent}%  ({done_count}/{total})",
            fill=(73, 80, 87),
            font=meta_font,
        )

        y = HEADER_HEIGHT

        for index, item in enumerate(items):
            state = item["visual_state"]
            bg_color = STATE_COLORS.get(state, STATE_COLORS["upcoming"])
            border_color = STATE_BORDER_COLORS.get(state, STATE_BORDER_COLORS["upcoming"])
            text_color = STATE_TEXT_COLORS.get(state, STATE_TEXT_COLORS["upcoming"])
            row_top = y
            row_bottom = y + ROW_HEIGHT - 8

            draw.rounded_rectangle(
                (PADDING, row_top, WIDTH - PADDING, row_bottom),
                radius=12,
                fill=bg_color,
                outline=border_color,
                width=2,
            )

            code_label = str(index + 1)
            row_text_top = row_top + 18
            code_left = PADDING + 14
            draw.text((code_left, row_text_top), code_label, fill=text_color, font=code_font)

            tag_left = code_left + 36
            tag_top = row_top + 16
            tag_width = _draw_tag_pill(
                draw,
                left=tag_left,
                top=tag_top,
                tag_name=item.get("tag_name"),
                tag_color=item.get("tag_color"),
                font=tag_font,
            )

            time_label = format_task_time_range(task_time=item["display_time"])
            time_left = tag_left + tag_width + 12
            draw.text((time_left, row_text_top), time_label, fill=text_color, font=label_font)

            status_label = STATUS_LABELS.get(state, "Task")
            status_width = _text_width(draw, status_label, label_font)
            status_left = WIDTH - PADDING - status_width - 8
            time_width = _text_width(draw, time_label, label_font)
            desc_left = time_left + time_width + 10
            max_desc_width = status_left - desc_left - 8
            description = item["title"].strip() or "Untitled task"
            desc_text = _truncate_to_width(
                draw,
                f"· {description}",
                row_font,
                max_desc_width,
            )

            if desc_text:
                draw.text(
                    (desc_left, row_text_top),
                    desc_text,
                    fill=text_color,
                    font=row_font,
                )

            draw.text(
                (status_left, row_text_top),
                status_label,
                fill=text_color,
                font=label_font,
            )

            y += ROW_HEIGHT

        legend_y = y + 10
        legend_items = [
            ("Done", STATE_COLORS["done"]),
            ("Pending", STATE_COLORS["overdue"]),
            ("Skipped", STATE_COLORS["skipped"]),
            ("Upcoming", STATE_COLORS["upcoming"]),
            ("Now", STATE_COLORS["current"]),
        ]
        legend_x = PADDING

        for label, color in legend_items:
            draw.rounded_rectangle(
                (legend_x, legend_y, legend_x + 16, legend_y + 16),
                radius=4,
                fill=color,
            )
            draw.text((legend_x + 24, legend_y - 2), label, fill=(73, 80, 87), font=footer_font)
            legend_x += 160

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    @staticmethod
    def build_action_keyboard(
        *,
        items: List[dict],
        plan_date: date,
        today: date,
    ) -> Optional[InlineKeyboardMarkup]:
        keyboard_rows = []

        for index, item in enumerate(items):
            if not is_task_actionable(item=item):
                continue

            task_number = index + 1
            keyboard_rows.append(
                [
                    InlineKeyboardButton(
                        f"✓ {task_number} Done",
                        callback_data=action_callback_data(
                            action="td",
                            task_number=task_number,
                            plan_date=plan_date,
                            today=today,
                        ),
                    ),
                    InlineKeyboardButton(
                        f"⏭ {task_number} Skip",
                        callback_data=action_callback_data(
                            action="ts",
                            task_number=task_number,
                            plan_date=plan_date,
                            today=today,
                        ),
                    ),
                    InlineKeyboardButton(
                        f"⏰ {task_number} Postpone",
                        callback_data=action_callback_data(
                            action="tp",
                            task_number=task_number,
                            plan_date=plan_date,
                            today=today,
                        ),
                    ),
                ]
            )

        if not keyboard_rows:
            return None

        return InlineKeyboardMarkup(keyboard_rows)

    @staticmethod
    def build_day_summary_caption(*, items: List[dict], plan_date: date) -> str:
        done_count = sum(
            1 for item in items if item["status"] == OccurrenceStatus.DONE
        )
        skipped_count = sum(
            1 for item in items if item["status"] == OccurrenceStatus.SKIPPED
        )
        pending_count = sum(1 for item in items if is_task_actionable(item=item))
        total = len(items)
        percent = round((done_count / total) * 100) if total else 0

        lines = [
            f"<b>Yesterday's tasks · {plan_date.strftime('%A, %d %b %Y')}</b>",
            (
                f"Done: {done_count} · Skipped: {skipped_count} · "
                f"Open: {pending_count}"
            ),
            f"Achievement: {percent}% ({done_count}/{total})",
        ]

        if pending_count > 0:
            lines.extend(
                [
                    "",
                    "Tap Done / Skip / Postpone below for any open tasks.",
                    (
                        f"Buttons stay active for {SUMMARY_UPDATE_WINDOW_DAYS} days "
                        "after the task date."
                    ),
                ]
            )

        return "\n".join(lines)

    @staticmethod
    def build_today_list_caption(*, items: List[dict], plan_date: date) -> str:
        lines = [
            f"<b>Today's tasks · {plan_date.strftime('%A, %d %b %Y')}</b>",
            f"{len(items)} task{'s' if len(items) != 1 else ''} scheduled.",
            "",
            "You'll get reminders 15 minutes before each task and when it ends.",
        ]

        return "\n".join(lines)

    @staticmethod
    def build_task_reminder_caption(*, item: dict, task_number: int) -> str:
        time_label = format_task_time_range(task_time=item["display_time"])
        tag_name = item.get("tag_name") or "No tag"

        lines = [
            f"<b>Task {task_number} starts in {REMINDER_MINUTES_BEFORE} minutes</b>",
            f"<b>Time:</b> {time_label}",
            f"<b>Tag:</b> {html_escape(tag_name)}",
            f"<b>Task:</b> {html_escape(item['title'])}",
            "",
            (
                f'<code>{task_number} yes</code> done · '
                f'<code>{task_number} no</code> skip · '
                f'Postpone → <b>Custom</b> for calendar'
            ),
            "Or tap the Done / Skip / Postpone buttons below.",
        ]

        return "\n".join(lines)

    @staticmethod
    def build_task_end_caption(*, item: dict, task_number: int) -> str:
        time_label = format_task_time_range(task_time=item["display_time"])
        tag_name = item.get("tag_name") or "No tag"

        lines = [
            f"<b>Task {task_number} time is up</b>",
            f"<b>Time:</b> {time_label}",
            f"<b>Tag:</b> {html_escape(tag_name)}",
            f"<b>Task:</b> {html_escape(item['title'])}",
            "",
            (
                f'<code>{task_number} yes</code> done · '
                f'<code>{task_number} no</code> skip · '
                f'Postpone → <b>Custom</b> for calendar'
            ),
            "Or tap the Done / Skip / Postpone buttons below.",
        ]

        return "\n".join(lines)

    @staticmethod
    def build_postpone_options_keyboard(
        *,
        task_number: int,
        plan_date: date,
        today: date,
    ) -> InlineKeyboardMarkup:
        from todo_bot.postpone_picker import (
            build_postpone_options_keyboard as build_custom_postpone_keyboard,
        )

        return build_custom_postpone_keyboard(
            task_number=task_number,
            plan_date=plan_date,
            today=today,
            action_callback_data=action_callback_data,
        )

    @staticmethod
    def build_single_task_keyboard(
        *,
        item: dict,
        task_number: int,
        plan_date: date,
        today: date,
    ) -> Optional[InlineKeyboardMarkup]:
        if not is_task_actionable(item=item):
            return None

        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"✓ {task_number} Done",
                        callback_data=action_callback_data(
                            action="td",
                            task_number=task_number,
                            plan_date=plan_date,
                            today=today,
                        ),
                    ),
                    InlineKeyboardButton(
                        f"⏭ {task_number} Skip",
                        callback_data=action_callback_data(
                            action="ts",
                            task_number=task_number,
                            plan_date=plan_date,
                            today=today,
                        ),
                    ),
                    InlineKeyboardButton(
                        f"⏰ {task_number} Postpone",
                        callback_data=action_callback_data(
                            action="tp",
                            task_number=task_number,
                            plan_date=plan_date,
                            today=today,
                        ),
                    ),
                ]
            ]
        )


def build_day_summary_notification(
    *,
    items: List[dict],
    plan_date: date,
    today: date,
    now: time,
) -> Tuple[bytes, str, Optional[InlineKeyboardMarkup]]:
    image_bytes = TelegramTodoImageBuilder.build(
        items=items,
        plan_date=plan_date,
        today=today,
        now=now,
    )
    caption = TelegramTodoImageBuilder.build_day_summary_caption(
        items=items,
        plan_date=plan_date,
    )
    reply_markup = TelegramTodoImageBuilder.build_action_keyboard(
        items=items,
        plan_date=plan_date,
        today=today,
    )
    return image_bytes, caption, reply_markup


def build_today_list_notification(
    *,
    items: List[dict],
    plan_date: date,
    today: date,
    now: time,
) -> Tuple[bytes, str, Optional[InlineKeyboardMarkup]]:
    image_bytes = TelegramTodoImageBuilder.build(
        items=items,
        plan_date=plan_date,
        today=today,
        now=now,
    )
    caption = TelegramTodoImageBuilder.build_today_list_caption(
        items=items,
        plan_date=plan_date,
    )
    return image_bytes, caption, None


def build_task_reminder_notification(
    *,
    items: List[dict],
    focus_item: dict,
    task_number: int,
    plan_date: date,
    today: date,
    now: time,
) -> Tuple[bytes, str, Optional[InlineKeyboardMarkup]]:
    image_bytes = TelegramTodoImageBuilder.build(
        items=items,
        plan_date=plan_date,
        today=today,
        now=now,
    )
    caption = TelegramTodoImageBuilder.build_task_reminder_caption(
        item=focus_item,
        task_number=task_number,
    )
    reply_markup = TelegramTodoImageBuilder.build_single_task_keyboard(
        item=focus_item,
        task_number=task_number,
        plan_date=plan_date,
        today=today,
    )
    return image_bytes, caption, reply_markup


def build_task_end_notification(
    *,
    items: List[dict],
    focus_item: dict,
    task_number: int,
    plan_date: date,
    today: date,
    now: time,
) -> Tuple[bytes, str, Optional[InlineKeyboardMarkup]]:
    image_bytes = TelegramTodoImageBuilder.build(
        items=items,
        plan_date=plan_date,
        today=today,
        now=now,
    )
    caption = TelegramTodoImageBuilder.build_task_end_caption(
        item=focus_item,
        task_number=task_number,
    )
    reply_markup = TelegramTodoImageBuilder.build_single_task_keyboard(
        item=focus_item,
        task_number=task_number,
        plan_date=plan_date,
        today=today,
    )
    return image_bytes, caption, reply_markup
