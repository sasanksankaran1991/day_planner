from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer

from sqlalchemy.sql import func

from database.base import Base


class BaseModel(Base):

    __abstract__ = True

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )
