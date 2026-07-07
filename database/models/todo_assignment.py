from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import UniqueConstraint

from sqlalchemy.orm import relationship

from database.base_model import BaseModel
from utils.enums import AssignmentStatus


class TodoAssignment(BaseModel):

    __tablename__ = "todo_assignments"

    __table_args__ = (
        UniqueConstraint(
            "todo_id",
            "assignee_id",
            name="uq_todo_assignee",
        ),
    )

    todo_id = Column(
        Integer,
        ForeignKey("todos.id"),
        nullable=False,
    )

    assignee_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    assigned_by_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    status = Column(
        Enum(AssignmentStatus),
        nullable=False,
        default=AssignmentStatus.PENDING,
    )

    todo = relationship(
        "Todo",
        back_populates="assignments",
    )

    assignee = relationship(
        "User",
        foreign_keys=[assignee_id],
    )

    assigned_by = relationship(
        "User",
        foreign_keys=[assigned_by_id],
    )

    def __repr__(self):
        return (
            f"<TodoAssignment("
            f"todo_id={self.todo_id}, "
            f"assignee_id={self.assignee_id}, "
            f"status={self.status}"
            f")>"
        )
