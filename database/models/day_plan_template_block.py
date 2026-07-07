from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Time

from sqlalchemy.orm import relationship

from database.base_model import BaseModel


class DayPlanTemplateBlock(BaseModel):

    __tablename__ = "day_plan_template_blocks"

    template_id = Column(
        Integer,
        ForeignKey("day_plan_templates.id"),
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

    sort_order = Column(
        Integer,
        nullable=False,
        default=0,
    )

    template = relationship(
        "DayPlanTemplate",
        back_populates="blocks",
    )

    def __repr__(self):
        return (
            f"<DayPlanTemplateBlock("
            f"id={self.id}, "
            f"{self.start_time}-{self.end_time}, "
            f"title={self.title}"
            f")>"
        )
