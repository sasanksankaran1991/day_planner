from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Time
from sqlalchemy import UniqueConstraint

from sqlalchemy.orm import relationship

from database.base_model import BaseModel


class TodoOccurrence(BaseModel):

    __tablename__ = "todo_occurrences"

    __table_args__ = (
        UniqueConstraint(
            "todo_id",
            "occurrence_date",
            name="uq_todo_occurrence_date",
        ),
    )

    todo_id = Column(
        Integer,
        ForeignKey("todos.id"),
        nullable=False,
    )

    occurrence_date = Column(
        Date,
        nullable=False,
    )

    occurrence_time = Column(
        Time,
        nullable=False,
    )

    is_exception = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    original_date = Column(
        Date,
        nullable=True,
    )

    original_time = Column(
        Time,
        nullable=True,
    )

    todo = relationship(
        "Todo",
        back_populates="occurrences",
    )

    user_statuses = relationship(
        "TodoUserStatus",
        back_populates="occurrence",
    )

    def __repr__(self):
        return (
            f"<TodoOccurrence("
            f"id={self.id}, "
            f"date={self.occurrence_date}, "
            f"time={self.occurrence_time}"
            f")>"
        )
