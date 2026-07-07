from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import Time

from sqlalchemy.orm import relationship

from database.base_model import BaseModel
from utils.enums import RecurrenceType


class Todo(BaseModel):

    __tablename__ = "todos"

    owner_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    title = Column(
        String(255),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    recurrence_type = Column(
        Enum(RecurrenceType),
        nullable=False,
        default=RecurrenceType.ONE_TIME,
    )

    recurrence_end_date = Column(
        Date,
        nullable=True,
    )

    custom_days = Column(
        String(50),
        nullable=True,
    )

    default_time = Column(
        Time,
        nullable=False,
    )

    first_date = Column(
        Date,
        nullable=False,
    )

    tag_id = Column(
        Integer,
        ForeignKey("planner_tags.id"),
        nullable=True,
    )

    owner = relationship(
        "User",
        foreign_keys=[owner_id],
    )

    occurrences = relationship(
        "TodoOccurrence",
        back_populates="todo",
    )

    assignments = relationship(
        "TodoAssignment",
        back_populates="todo",
    )

    tag = relationship(
        "PlannerTag",
    )

    def __repr__(self):
        return f"<Todo(id={self.id}, title={self.title})>"
