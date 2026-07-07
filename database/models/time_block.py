from sqlalchemy import Column
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Time

from sqlalchemy.orm import relationship

from database.base_model import BaseModel
from utils.enums import BlockStatus


class TimeBlock(BaseModel):

    __tablename__ = "time_blocks"

    day_plan_id = Column(
        Integer,
        ForeignKey("day_plans.id"),
        nullable=False,
    )

    start_time = Column(
        Time,
        nullable=False,
    )

    end_time = Column(
        Time,
        nullable=False,
    )

    title = Column(
        String(255),
        nullable=False,
    )

    status = Column(
        Enum(BlockStatus),
        nullable=False,
        default=BlockStatus.PENDING,
    )

    sort_order = Column(
        Integer,
        nullable=False,
        default=0,
    )

    tag_id = Column(
        Integer,
        ForeignKey("planner_tags.id"),
        nullable=True,
    )

    day_plan = relationship(
        "DayPlan",
        back_populates="blocks",
    )

    tag = relationship(
        "PlannerTag",
    )

    def __repr__(self):
        return (
            f"<TimeBlock("
            f"id={self.id}, "
            f"{self.start_time}-{self.end_time}, "
            f"title={self.title}"
            f")>"
        )
