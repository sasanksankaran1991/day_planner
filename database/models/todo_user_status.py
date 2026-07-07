from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Time
from sqlalchemy import UniqueConstraint

from sqlalchemy.orm import relationship

from database.base_model import BaseModel
from utils.enums import OccurrenceStatus


class TodoUserStatus(BaseModel):

    __tablename__ = "todo_user_statuses"

    __table_args__ = (
        UniqueConstraint(
            "occurrence_id",
            "user_id",
            name="uq_occurrence_user_status",
        ),
    )

    occurrence_id = Column(
        Integer,
        ForeignKey("todo_occurrences.id"),
        nullable=False,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    status = Column(
        Enum(OccurrenceStatus),
        nullable=False,
        default=OccurrenceStatus.PENDING,
    )

    postponed_date = Column(
        Date,
        nullable=True,
    )

    postponed_time = Column(
        Time,
        nullable=True,
    )

    done_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    occurrence = relationship(
        "TodoOccurrence",
        back_populates="user_statuses",
    )

    user = relationship(
        "User",
    )

    def __repr__(self):
        return (
            f"<TodoUserStatus("
            f"occurrence_id={self.occurrence_id}, "
            f"user_id={self.user_id}, "
            f"status={self.status}"
            f")>"
        )
