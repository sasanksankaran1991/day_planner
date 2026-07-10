from typing import List
from typing import Optional

from database.models import PlannerTag


class PlannerTagRepository:

    @staticmethod
    def list_for_user(db, *, user_id: int) -> List[PlannerTag]:
        return (
            db.query(PlannerTag)
            .filter(
                PlannerTag.user_id == user_id,
                PlannerTag.is_active.is_(True),
            )
            .order_by(PlannerTag.sort_order, PlannerTag.name)
            .all()
        )

    @staticmethod
    def get_by_id(db, *, tag_id: int) -> Optional[PlannerTag]:
        return (
            db.query(PlannerTag)
            .filter(
                PlannerTag.id == tag_id,
                PlannerTag.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def get_by_name(db, *, user_id: int, name: str) -> Optional[PlannerTag]:
        return (
            db.query(PlannerTag)
            .filter(
                PlannerTag.user_id == user_id,
                PlannerTag.name == name,
                PlannerTag.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def get_by_name_any_status(db, *, user_id: int, name: str) -> Optional[PlannerTag]:
        return (
            db.query(PlannerTag)
            .filter(
                PlannerTag.user_id == user_id,
                PlannerTag.name == name,
            )
            .first()
        )

    @staticmethod
    def create(db, *, tag: PlannerTag) -> PlannerTag:
        db.add(tag)
        db.flush()
        db.refresh(tag)
        return tag

    @staticmethod
    def update(db, *, tag: PlannerTag) -> PlannerTag:
        db.flush()
        db.refresh(tag)
        return tag
