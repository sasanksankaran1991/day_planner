from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import String

from database.base_model import BaseModel
from utils.enums import UserRole


class User(BaseModel):

    __tablename__ = "users"

    username = Column(
        String(50),
        unique=True,
        nullable=False,
    )

    password_hash = Column(
        String(255),
        nullable=False,
    )

    display_name = Column(
        String(100),
        nullable=False,
    )

    role = Column(
        Enum(UserRole),
        nullable=False,
        default=UserRole.USER,
    )

    timezone = Column(
        String(50),
        nullable=False,
        default="Asia/Kolkata",
    )

    telegram_chat_id = Column(
        String(50),
        nullable=True,
    )

    telegram_link_code = Column(
        String(20),
        nullable=True,
    )

    telegram_link_expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    todo_telegram_chat_id = Column(
        String(50),
        nullable=True,
    )

    todo_telegram_link_code = Column(
        String(20),
        nullable=True,
    )

    todo_telegram_link_expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"
