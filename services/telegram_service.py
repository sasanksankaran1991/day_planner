import secrets
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from io import BytesIO
from typing import List
from typing import Optional
from typing import Tuple

import pytz

from config.settings import TELEGRAM_BOT_TOKEN
from config.settings import TELEGRAM_BOT_USERNAME
from database.models import TelegramNotification
from database.models import TimeBlock
from database.session import get_db
from repositories.telegram_notification_repository import TelegramNotificationRepository
from repositories.user_repository import UserRepository
from services.day_plan_service import DayPlanService
from services.telegram_day_plan_image import SUMMARY_UPDATE_WINDOW_DAYS
from services.telegram_day_plan_image import block_visual_state
from services.telegram_day_plan_image import build_day_plan_notification
from services.telegram_day_plan_image import build_day_summary_notification
from services.telegram_day_plan_image import format_time_range
from utils.enums import BlockStatus

LINK_CODE_TTL_MINUTES = 15
LINK_PAYLOAD_PREFIX = "link"
DAY_SUMMARY_HOUR = 5
_resolved_bot_username: Optional[str] = None


def _resolve_bot_username() -> str:
    global _resolved_bot_username

    if TELEGRAM_BOT_USERNAME:
        return TELEGRAM_BOT_USERNAME

    if _resolved_bot_username:
        return _resolved_bot_username

    if not TELEGRAM_BOT_TOKEN:
        return ""

    import httpx

    response = httpx.get(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe",
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()

    if not payload.get("ok"):
        return ""

    username = payload.get("result", {}).get("username", "")
    _resolved_bot_username = username
    return username


def _resolve_current_block(
    *,
    blocks: List[TimeBlock],
    plan_date: date,
    today: date,
    now: time,
) -> Optional[TimeBlock]:
    current_block = None

    for block in blocks:
        if (
            plan_date == today
            and block.start_time <= now < block.end_time
            and block.status != BlockStatus.DONE
        ):
            current_block = block
            break

    if current_block is None:
        for block in blocks:
            if block.status != BlockStatus.DONE:
                current_block = block
                break

    if current_block is None and blocks:
        current_block = blocks[-1]

    return current_block


def _validate_summary_update_window(*, plan_date: date, today: date) -> None:
    if plan_date > today:
        raise ValueError("Cannot update future days.")

    days_ago = (today - plan_date).days

    if days_ago > SUMMARY_UPDATE_WINDOW_DAYS:
        raise ValueError(
            f"Summary can only be updated within {SUMMARY_UPDATE_WINDOW_DAYS} days."
        )


def _get_block_action_context(
    *,
    user,
    block_number: int,
    plan_date: Optional[date] = None,
) -> Tuple[List[TimeBlock], TimeBlock, int, int, date, date, time]:
    tz = pytz.timezone(user.timezone)
    today = datetime.now(tz).date()
    now = datetime.now(tz).time()
    target_date = plan_date or today

    if plan_date is not None and plan_date != today:
        _validate_summary_update_window(plan_date=target_date, today=today)

    blocks = DayPlanService.get_blocks(user_id=user.id, plan_date=target_date)

    if not blocks:
        raise ValueError(f"No blocks planned for {target_date.strftime('%d %b %Y')}.")

    if block_number < 1 or block_number > len(blocks):
        raise ValueError(
            f"Block {block_number} does not exist. "
            f"You have {len(blocks)} blocks on that day."
        )

    block = blocks[block_number - 1]
    block_index = block_number - 1
    current_block = _resolve_current_block(
        blocks=blocks,
        plan_date=target_date,
        today=today,
        now=now,
    )
    current_index = (
        next(
            index
            for index, item in enumerate(blocks)
            if item.id == current_block.id
        )
        if current_block is not None
        else 0
    )

    return blocks, block, block_index, current_index, today, target_date, now


class TelegramService:
    @staticmethod
    def generate_link_code(*, user_id: int) -> str:
        code = f"{secrets.randbelow(900000) + 100000:06d}"
        expires_at = datetime.now(pytz.UTC) + timedelta(minutes=LINK_CODE_TTL_MINUTES)

        with get_db() as db:
            user = UserRepository.get_by_id(db=db, user_id=user_id)

            if user is None:
                raise ValueError("User not found.")

            user.telegram_link_code = code
            user.telegram_link_expires_at = expires_at
            UserRepository.update(db=db, user=user)

        return code

    @staticmethod
    def is_bot_configured() -> bool:
        return bool(TELEGRAM_BOT_TOKEN and _resolve_bot_username())

    @staticmethod
    def build_connect_url(*, link_code: str) -> str:
        bot_username = _resolve_bot_username()

        if not bot_username:
            raise ValueError(
                "Telegram bot is not configured. Set TELEGRAM_BOT_TOKEN in "
                "`.env` or Secret Manager."
            )

        payload = f"{LINK_PAYLOAD_PREFIX}{link_code}"
        return f"https://t.me/{bot_username}?start={payload}"

    @staticmethod
    def parse_link_payload(*, payload: str) -> Optional[str]:
        if not payload.startswith(LINK_PAYLOAD_PREFIX):
            return None

        link_code = payload[len(LINK_PAYLOAD_PREFIX):]

        if len(link_code) != 6 or not link_code.isdigit():
            return None

        return link_code

    @staticmethod
    def is_telegram_linked(*, user_id: int) -> bool:
        with get_db() as db:
            user = UserRepository.get_by_id(db=db, user_id=user_id)

            if user is None:
                return False

            return bool(user.telegram_chat_id)

    @staticmethod
    def start_connect_flow(*, user_id: int) -> str:
        link_code = TelegramService.generate_link_code(user_id=user_id)
        return TelegramService.build_connect_url(link_code=link_code)

    @staticmethod
    def link_telegram_account(*, link_code: str, chat_id: str) -> str:
        with get_db() as db:
            user = UserRepository.get_by_link_code(db=db, link_code=link_code)

            if user is None:
                raise ValueError("Invalid link code.")

            if user.telegram_link_expires_at is None:
                raise ValueError("Link code has expired. Generate a new one in Settings.")

            expires_at = user.telegram_link_expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=pytz.UTC)

            if datetime.now(pytz.UTC) > expires_at:
                raise ValueError("Link code has expired. Generate a new one in Settings.")

            existing = UserRepository.get_by_telegram_chat_id(db=db, chat_id=chat_id)

            if existing and existing.id != user.id:
                raise ValueError("This Telegram account is already linked to another user.")

            user.telegram_chat_id = str(chat_id)
            user.telegram_link_code = None
            user.telegram_link_expires_at = None
            UserRepository.update(db=db, user=user)

            return user.display_name

    @staticmethod
    def get_user_by_chat_id(*, chat_id: str):
        with get_db() as db:
            return UserRepository.get_by_telegram_chat_id(db=db, chat_id=str(chat_id))

    @staticmethod
    def list_linked_users():
        with get_db() as db:
            return UserRepository.list_with_telegram(db=db)

    @staticmethod
    def mark_block_done_by_number(
        *,
        chat_id: str,
        block_number: int,
        plan_date: Optional[date] = None,
    ) -> str:
        user = TelegramService.get_user_by_chat_id(chat_id=chat_id)

        if user is None:
            raise ValueError("Telegram account is not linked.")

        (
            _blocks,
            block,
            block_index,
            current_index,
            today,
            target_date,
            now,
        ) = _get_block_action_context(
            user=user,
            block_number=block_number,
            plan_date=plan_date,
        )

        state = block_visual_state(
            block=block,
            block_index=block_index,
            current_block_index=current_index,
            now=now,
            plan_date=target_date,
            today=today,
        )

        if state == "done":
            raise ValueError(f"Block {block_number} is already done.")

        if state == "upcoming":
            raise ValueError(f"Block {block_number} has not started yet.")

        DayPlanService.mark_block_done(block_id=block.id)

        time_label = format_time_range(
            start_time=block.start_time,
            end_time=block.end_time,
        )
        return (
            f"✅ Block {block_number} marked done: {block.title} ({time_label})"
        )

    @staticmethod
    def mark_block_pending_by_number(
        *,
        chat_id: str,
        block_number: int,
        plan_date: Optional[date] = None,
    ) -> str:
        user = TelegramService.get_user_by_chat_id(chat_id=chat_id)

        if user is None:
            raise ValueError("Telegram account is not linked.")

        (
            _blocks,
            block,
            block_index,
            current_index,
            today,
            target_date,
            now,
        ) = _get_block_action_context(
            user=user,
            block_number=block_number,
            plan_date=plan_date,
        )

        state = block_visual_state(
            block=block,
            block_index=block_index,
            current_block_index=current_index,
            now=now,
            plan_date=target_date,
            today=today,
        )

        if state != "done" and state != "skipped":
            raise ValueError(
                f"Block {block_number} is not done or skipped. "
                f'Use "{block_number} yes" or "{block_number} no" first.'
            )

        DayPlanService.mark_block_pending(block_id=block.id)

        time_label = format_time_range(
            start_time=block.start_time,
            end_time=block.end_time,
        )
        return (
            f"↩ Block {block_number} reset to pending: {block.title} ({time_label})"
        )

    @staticmethod
    def mark_block_skipped_by_number(
        *,
        chat_id: str,
        block_number: int,
        plan_date: Optional[date] = None,
    ) -> str:
        user = TelegramService.get_user_by_chat_id(chat_id=chat_id)

        if user is None:
            raise ValueError("Telegram account is not linked.")

        (
            _blocks,
            block,
            block_index,
            current_index,
            today,
            target_date,
            now,
        ) = _get_block_action_context(
            user=user,
            block_number=block_number,
            plan_date=plan_date,
        )

        state = block_visual_state(
            block=block,
            block_index=block_index,
            current_block_index=current_index,
            now=now,
            plan_date=target_date,
            today=today,
        )

        if state == "skipped":
            raise ValueError(f"Block {block_number} is already skipped.")

        if state == "upcoming":
            raise ValueError(f"Block {block_number} has not started yet.")

        DayPlanService.mark_block_skipped(block_id=block.id)

        time_label = format_time_range(
            start_time=block.start_time,
            end_time=block.end_time,
        )
        return (
            f"⏭ Block {block_number} marked skipped: {block.title} ({time_label})"
        )

    @staticmethod
    def get_blocks_starting_now() -> List[Tuple]:
        due_notifications = []

        for user in TelegramService.list_linked_users():
            tz = pytz.timezone(user.timezone)
            now = datetime.now(tz)
            today = now.date()
            current_time = now.time().replace(second=0, microsecond=0)

            blocks = DayPlanService.get_blocks(user_id=user.id, plan_date=today)

            for block in blocks:
                if block.status in (BlockStatus.DONE, BlockStatus.SKIPPED):
                    continue

                block_start = block.start_time.replace(second=0, microsecond=0)

                if block_start != current_time:
                    continue

                with get_db() as db:
                    already_sent = TelegramNotificationRepository.was_sent(
                        db=db,
                        user_id=user.id,
                        plan_date=today,
                        block_id=block.id,
                    )

                if already_sent:
                    continue

                due_notifications.append((user, today, blocks, block, now.time()))

        return due_notifications

    @staticmethod
    def record_block_start_notification(
        *,
        user_id: int,
        plan_date: date,
        block_id: int,
    ) -> None:
        with get_db() as db:
            TelegramNotificationRepository.record(
                db=db,
                notification=TelegramNotification(
                    user_id=user_id,
                    plan_date=plan_date,
                    block_id=block_id,
                    notification_type="BLOCK_START",
                ),
            )

    @staticmethod
    def build_block_start_message(
        *,
        user,
        plan_date: date,
        blocks: List[TimeBlock],
        current_block: TimeBlock,
        now: time,
    ) -> Tuple[BytesIO, str, Optional[object]]:
        tz = pytz.timezone(user.timezone)
        today = datetime.now(tz).date()

        image_bytes, caption, reply_markup = build_day_plan_notification(
            blocks=blocks,
            current_block=current_block,
            plan_date=plan_date,
            now=now,
            today=today,
        )

        image_file = BytesIO(image_bytes)
        image_file.name = "day_plan.png"
        return image_file, caption, reply_markup

    @staticmethod
    def parse_action_callback(*, data: str) -> Tuple[str, Optional[date], int]:
        parts = data.split(":")

        if len(parts) not in (2, 3):
            raise ValueError("Invalid action.")

        action = parts[0]

        if action not in ("bd", "bs"):
            raise ValueError("Invalid action.")

        if len(parts) == 2:
            return action, None, int(parts[1])

        return action, date.fromisoformat(parts[1]), int(parts[2])

    @staticmethod
    def get_due_day_summaries() -> List[Tuple]:
        due_summaries = []

        for user in TelegramService.list_linked_users():
            tz = pytz.timezone(user.timezone)
            now = datetime.now(tz)

            if now.hour != DAY_SUMMARY_HOUR:
                continue

            yesterday = now.date() - timedelta(days=1)
            blocks = DayPlanService.get_blocks(user_id=user.id, plan_date=yesterday)

            if not blocks:
                continue

            with get_db() as db:
                already_sent = TelegramNotificationRepository.was_day_summary_sent(
                    db=db,
                    user_id=user.id,
                    plan_date=yesterday,
                )

            if already_sent:
                continue

            due_summaries.append((user, yesterday, blocks, now.time()))

        return due_summaries

    @staticmethod
    def record_day_summary_notification(
        *,
        user_id: int,
        plan_date: date,
        block_id: int,
    ) -> None:
        with get_db() as db:
            TelegramNotificationRepository.record(
                db=db,
                notification=TelegramNotification(
                    user_id=user_id,
                    plan_date=plan_date,
                    block_id=block_id,
                    notification_type="DAY_SUMMARY",
                ),
            )

    @staticmethod
    def build_day_summary_message(
        *,
        user,
        plan_date: date,
        blocks: List[TimeBlock],
        now: time,
    ) -> Tuple[BytesIO, str, Optional[object]]:
        tz = pytz.timezone(user.timezone)
        today = datetime.now(tz).date()

        image_bytes, caption, reply_markup = build_day_summary_notification(
            blocks=blocks,
            plan_date=plan_date,
            now=now,
            today=today,
        )

        image_file = BytesIO(image_bytes)
        image_file.name = "day_summary.png"
        return image_file, caption, reply_markup
