from datetime import date
from typing import List
from typing import Optional

from database.models import TelegramNotification


class TelegramNotificationRepository:

    @staticmethod
    def was_sent(
        db,
        *,
        user_id: int,
        plan_date: date,
        block_id: int,
        notification_type: str = "BLOCK_START",
    ) -> bool:
        return (
            db.query(TelegramNotification)
            .filter(
                TelegramNotification.user_id == user_id,
                TelegramNotification.plan_date == plan_date,
                TelegramNotification.block_id == block_id,
                TelegramNotification.notification_type == notification_type,
                TelegramNotification.is_active.is_(True),
            )
            .first()
            is not None
        )

    @staticmethod
    def was_day_summary_sent(
        db,
        *,
        user_id: int,
        plan_date: date,
    ) -> bool:
        return (
            db.query(TelegramNotification)
            .filter(
                TelegramNotification.user_id == user_id,
                TelegramNotification.plan_date == plan_date,
                TelegramNotification.notification_type == "DAY_SUMMARY",
                TelegramNotification.is_active.is_(True),
            )
            .first()
            is not None
        )

    @staticmethod
    def record(
        db,
        *,
        notification: TelegramNotification,
    ) -> TelegramNotification:
        db.add(notification)
        db.flush()
        db.refresh(notification)
        return notification
