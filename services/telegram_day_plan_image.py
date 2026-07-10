from __future__ import annotations

from datetime import date
from datetime import time
from io import BytesIO
from typing import List
from typing import Optional
from typing import Tuple

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from database.models import PlannerTag
from database.models import TimeBlock
from utils.enums import BlockStatus
from utils.time_slots import time_diff_minutes

SUMMARY_UPDATE_WINDOW_DAYS = 7

ROW_HEIGHT = 68
PADDING = 24
WIDTH = 900
HEADER_HEIGHT = 110
FOOTER_HEIGHT = 64

# Match Streamlit block ribbon colors in ui/blocks_tab.py
STATE_COLORS = {
    "done": (165, 214, 167),
    "overdue": (255, 205, 210),
    "skipped": (255, 205, 210),
    "upcoming": (187, 222, 251),
    "now": (255, 224, 130),
}

STATE_BORDER_COLORS = {
    "done": (46, 125, 50),
    "overdue": (229, 57, 53),
    "skipped": (198, 40, 40),
    "upcoming": (30, 136, 229),
    "now": (255, 160, 0),
}

STATE_TEXT_COLORS = {
    "done": (27, 94, 32),
    "overdue": (62, 39, 35),
    "skipped": (62, 39, 35),
    "upcoming": (13, 71, 161),
    "now": (62, 39, 35),
}

STATUS_LABELS = {
    "done": "Done",
    "overdue": "Pending",
    "skipped": "Skipped",
    "upcoming": "Upcoming",
    "now": "Now",
}

NO_TAG_FILL = (233, 236, 239)
NO_TAG_TEXT = (73, 80, 87)


def _format_time(value: time) -> str:
    return value.strftime("%H:%M")


def format_block_duration(*, start_time: time, end_time: time) -> str:
    minutes = time_diff_minutes(end_time, start_time)

    if minutes < 60:
        return f"{minutes}m"

    hours, mins = divmod(minutes, 60)

    if mins == 0:
        return f"{hours}h"

    return f"{hours}h {mins}m"


def format_time_range(*, start_time: time, end_time: time) -> str:
    duration = format_block_duration(start_time=start_time, end_time=end_time)
    return (
        f"{_format_time(start_time)} – {_format_time(end_time)} ({duration})"
    )


def action_callback_data(
    *,
    action: str,
    block_number: int,
    plan_date: date,
    today: date,
) -> str:
    if plan_date == today:
        return f"{action}:{block_number}"

    return f"{action}:{plan_date.isoformat()}:{block_number}"


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
    tag: Optional[PlannerTag],
    font,
) -> int:
    label = tag.name if tag is not None else "No tag"
    fill = _parse_hex_color(tag.color, fallback=(30, 136, 229)) if tag else NO_TAG_FILL
    text_color = _text_color_for_background(fill) if tag else NO_TAG_TEXT
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


def _text_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def block_visual_state(
    *,
    block: TimeBlock,
    block_index: int,
    current_block_index: int,
    now: time,
    plan_date: date,
    today: date,
) -> str:
    if block.status == BlockStatus.DONE:
        return "done"

    if block.status == BlockStatus.SKIPPED:
        return "skipped"

    if block_index == current_block_index and plan_date == today:
        return "now"

    if plan_date < today:
        return "overdue"

    if plan_date > today:
        return "upcoming"

    if block.end_time <= now:
        return "overdue"

    if block_index < current_block_index:
        return "overdue"

    return "upcoming"


def resolve_current_block_index(
    *,
    blocks: List[TimeBlock],
    current_block: TimeBlock,
) -> int:
    return next(
        index for index, block in enumerate(blocks) if block.id == current_block.id
    )


class TelegramDayPlanImageBuilder:

    @staticmethod
    def build(
        *,
        blocks: List[TimeBlock],
        current_block: TimeBlock,
        plan_date: date,
        now: time,
        today: date,
    ) -> bytes:
        current_index = resolve_current_block_index(
            blocks=blocks,
            current_block=current_block,
        )
        done_count = sum(1 for block in blocks if block.status == BlockStatus.DONE)
        total = len(blocks)
        percent = round((done_count / total) * 100) if total else 0

        height = HEADER_HEIGHT + (len(blocks) * ROW_HEIGHT) + FOOTER_HEIGHT
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

        for index, block in enumerate(blocks):
            state = block_visual_state(
                block=block,
                block_index=index,
                current_block_index=current_index,
                now=now,
                plan_date=plan_date,
                today=today,
            )
            bg_color = STATE_COLORS[state]
            border_color = STATE_BORDER_COLORS[state]
            text_color = STATE_TEXT_COLORS[state]
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
                tag=block.tag,
                font=tag_font,
            )

            time_label = format_time_range(
                start_time=block.start_time,
                end_time=block.end_time,
            )
            time_left = tag_left + tag_width + 12
            draw.text((time_left, row_text_top), time_label, fill=text_color, font=label_font)

            status_label = STATUS_LABELS[state]
            status_width = _text_width(draw, status_label, label_font)
            status_left = WIDTH - PADDING - status_width - 8
            time_width = _text_width(draw, time_label, label_font)
            desc_left = time_left + time_width + 10
            max_desc_width = status_left - desc_left - 8
            description = block.title.strip() or "Untitled block"
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
            ("Now", STATE_COLORS["now"]),
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
    def build_caption(
        *,
        blocks: List[TimeBlock],
        current_block: TimeBlock,
        plan_date: date,
        now: time,
        today: date,
    ) -> str:
        current_index = resolve_current_block_index(
            blocks=blocks,
            current_block=current_block,
        )
        block_number = current_index + 1
        time_label = format_time_range(
            start_time=current_block.start_time,
            end_time=current_block.end_time,
        )
        tag_name = current_block.tag.name if current_block.tag is not None else "No tag"

        lines = [
            f"<b>Block {block_number} started</b>",
            f"<b>Time:</b> {time_label}",
            f"<b>Tag:</b> {html_escape(tag_name)}",
            f"<b>Description:</b> {html_escape(current_block.title)}",
            "",
            (
                f'<code>{block_number} yes</code> done · '
                f'<code>{block_number} no</code> skip · '
                f'<code>{block_number} undo</code> reset'
            ),
            "Or tap the Done / Skip buttons below.",
        ]

        return "\n".join(lines)

    @staticmethod
    def build_action_keyboard(
        *,
        blocks: List[TimeBlock],
        current_block: TimeBlock,
        plan_date: date,
        now: time,
        today: date,
    ) -> Optional[InlineKeyboardMarkup]:
        current_index = resolve_current_block_index(
            blocks=blocks,
            current_block=current_block,
        )
        keyboard_rows = []

        for index, block in enumerate(blocks):
            state = block_visual_state(
                block=block,
                block_index=index,
                current_block_index=current_index,
                now=now,
                plan_date=plan_date,
                today=today,
            )

            if state not in ("now", "overdue"):
                continue

            block_number = index + 1
            keyboard_rows.append(
                [
                    InlineKeyboardButton(
                        f"✓ {block_number} Done",
                        callback_data=action_callback_data(
                            action="bd",
                            block_number=block_number,
                            plan_date=plan_date,
                            today=today,
                        ),
                    ),
                    InlineKeyboardButton(
                        f"⏭ {block_number} Skip",
                        callback_data=action_callback_data(
                            action="bs",
                            block_number=block_number,
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
    def build_day_summary_caption(
        *,
        blocks: List[TimeBlock],
        plan_date: date,
    ) -> str:
        done_count = sum(1 for block in blocks if block.status == BlockStatus.DONE)
        skipped_count = sum(1 for block in blocks if block.status == BlockStatus.SKIPPED)
        pending_count = sum(1 for block in blocks if block.status == BlockStatus.PENDING)
        total = len(blocks)
        percent = round((done_count / total) * 100) if total else 0

        lines = [
            f"<b>Day summary · {plan_date.strftime('%A, %d %b %Y')}</b>",
            (
                f"Done: {done_count} · Skipped: {skipped_count} · "
                f"Pending: {pending_count}"
            ),
            f"Achievement: {percent}% ({done_count}/{total})",
        ]

        if pending_count > 0:
            lines.extend(
                [
                    "",
                    "Tap Done / Skip below for any pending blocks.",
                    (
                        f"Buttons stay active for {SUMMARY_UPDATE_WINDOW_DAYS} days "
                        "after the plan date."
                    ),
                ]
            )

        return "\n".join(lines)


def html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_day_plan_notification(
    *,
    blocks: List[TimeBlock],
    current_block: TimeBlock,
    plan_date: date,
    now: time,
    today: date,
) -> Tuple[bytes, str, Optional[InlineKeyboardMarkup]]:
    image_bytes = TelegramDayPlanImageBuilder.build(
        blocks=blocks,
        current_block=current_block,
        plan_date=plan_date,
        now=now,
        today=today,
    )
    caption = TelegramDayPlanImageBuilder.build_caption(
        blocks=blocks,
        current_block=current_block,
        plan_date=plan_date,
        now=now,
        today=today,
    )
    reply_markup = TelegramDayPlanImageBuilder.build_action_keyboard(
        blocks=blocks,
        current_block=current_block,
        plan_date=plan_date,
        now=now,
        today=today,
    )
    return image_bytes, caption, reply_markup


def resolve_summary_display_block(
    *,
    blocks: List[TimeBlock],
) -> TimeBlock:
    for block in blocks:
        if block.status == BlockStatus.PENDING:
            return block

    return blocks[-1]


def build_day_summary_notification(
    *,
    blocks: List[TimeBlock],
    plan_date: date,
    now: time,
    today: date,
) -> Tuple[bytes, str, Optional[InlineKeyboardMarkup]]:
    display_block = resolve_summary_display_block(blocks=blocks)
    image_bytes = TelegramDayPlanImageBuilder.build(
        blocks=blocks,
        current_block=display_block,
        plan_date=plan_date,
        now=now,
        today=today,
    )
    caption = TelegramDayPlanImageBuilder.build_day_summary_caption(
        blocks=blocks,
        plan_date=plan_date,
    )
    reply_markup = TelegramDayPlanImageBuilder.build_action_keyboard(
        blocks=blocks,
        current_block=display_block,
        plan_date=plan_date,
        now=now,
        today=today,
    )

    return image_bytes, caption, reply_markup
