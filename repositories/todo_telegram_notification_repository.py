from datetime import date

from database.models import TodoTelegramNotification


class TodoTelegramNotificationRepository:

    @staticmethod
    def was_sent(
        db,
        *,
        user_id: int,
        plan_date: date,
        occurrence_id: int,
        notification_type: str,
    ) -> bool:
        return (
            db.query(TodoTelegramNotification)
            .filter(
                TodoTelegramNotification.user_id == user_id,
                TodoTelegramNotification.plan_date == plan_date,
                TodoTelegramNotification.occurrence_id == occurrence_id,
                TodoTelegramNotification.notification_type == notification_type,
                TodoTelegramNotification.is_active.is_(True),
            )
            .first()
            is not None
        )

    @staticmethod
    def was_daily_notification_sent(
        db,
        *,
        user_id: int,
        plan_date: date,
        notification_type: str,
    ) -> bool:
        return (
            db.query(TodoTelegramNotification)
            .filter(
                TodoTelegramNotification.user_id == user_id,
                TodoTelegramNotification.plan_date == plan_date,
                TodoTelegramNotification.notification_type == notification_type,
                TodoTelegramNotification.is_active.is_(True),
            )
            .first()
            is not None
        )

    @staticmethod
    def record(
        db,
        *,
        notification: TodoTelegramNotification,
    ) -> TodoTelegramNotification:
        db.add(notification)
        db.flush()
        db.refresh(notification)
        return notification
