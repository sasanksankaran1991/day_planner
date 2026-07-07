from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint

from sqlalchemy.orm import relationship

from database.base_model import BaseModel


class DayPlan(BaseModel):

    __tablename__ = "day_plans"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "plan_date",
            name="uq_user_plan_date",
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

    daily_note = Column(
        Text,
        nullable=True,
    )

    user = relationship(
        "User",
    )

    blocks = relationship(
        "TimeBlock",
        back_populates="day_plan",
        order_by="TimeBlock.sort_order",
    )

    def __repr__(self):
        return f"<DayPlan(id={self.id}, date={self.plan_date})>"
