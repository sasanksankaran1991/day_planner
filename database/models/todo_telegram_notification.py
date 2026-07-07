from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UniqueConstraint

from database.base_model import BaseModel


class TodoTelegramNotification(BaseModel):

    __tablename__ = "todo_telegram_notifications"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "plan_date",
            "occurrence_id",
            "notification_type",
            name="uq_todo_telegram_notification",
        ),
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    plan_date = Column(
        Date,
        nullable=False,
    )

    occurrence_id = Column(
        Integer,
        ForeignKey("todo_occurrences.id"),
        nullable=False,
    )

    notification_type = Column(
        String(50),
        nullable=False,
        default="TASK_REMINDER",
    )
