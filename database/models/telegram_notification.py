from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UniqueConstraint

from database.base_model import BaseModel


class TelegramNotification(BaseModel):

    __tablename__ = "telegram_notifications"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "plan_date",
            "block_id",
            "notification_type",
            name="uq_telegram_block_notification",
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

    block_id = Column(
        Integer,
        ForeignKey("time_blocks.id"),
        nullable=False,
    )

    notification_type = Column(
        String(50),
        nullable=False,
        default="BLOCK_START",
    )

    def __repr__(self):
        return (
            f"<TelegramNotification(user_id={self.user_id}, "
            f"block_id={self.block_id}, type={self.notification_type})>"
        )
