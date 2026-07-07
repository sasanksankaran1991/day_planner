from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UniqueConstraint

from database.base_model import BaseModel


class PlannerTag(BaseModel):

    __tablename__ = "planner_tags"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_planner_tag_user_name"),
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    name = Column(
        String(50),
        nullable=False,
    )

    color = Column(
        String(7),
        nullable=False,
        default="#1E88E5",
    )

    require_on_create = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    sort_order = Column(
        Integer,
        nullable=False,
        default=0,
    )

    def __repr__(self):
        return f"<PlannerTag(id={self.id}, name={self.name})>"
