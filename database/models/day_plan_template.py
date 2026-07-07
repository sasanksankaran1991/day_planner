from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text

from sqlalchemy.orm import relationship

from database.base_model import BaseModel


class DayPlanTemplate(BaseModel):

    __tablename__ = "day_plan_templates"

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    name = Column(
        String(100),
        nullable=False,
    )

    daily_note = Column(
        Text,
        nullable=True,
    )

    blocks = relationship(
        "DayPlanTemplateBlock",
        back_populates="template",
        order_by="DayPlanTemplateBlock.sort_order",
    )

    def __repr__(self):
        return f"<DayPlanTemplate(id={self.id}, name={self.name})>"
