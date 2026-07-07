from datetime import date
from typing import List
from typing import Optional
from typing import Tuple

from sqlalchemy.orm import joinedload

from database.models import DayPlan
from database.models import TimeBlock
from utils.enums import BlockStatus


class DayPlanRepository:

    @staticmethod
    def get_by_user_and_date(
        db,
        *,
        user_id: int,
        plan_date: date,
    ) -> Optional[DayPlan]:
        return (
            db.query(DayPlan)
            .filter(
                DayPlan.user_id == user_id,
                DayPlan.plan_date == plan_date,
                DayPlan.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def create(db, *, day_plan: DayPlan) -> DayPlan:
        db.add(day_plan)
        db.flush()
        db.refresh(day_plan)
        return day_plan

    @staticmethod
    def update(db, *, day_plan: DayPlan) -> DayPlan:
        db.flush()
        db.refresh(day_plan)
        return day_plan

    @staticmethod
    def create_block(db, *, block: TimeBlock) -> TimeBlock:
        db.add(block)
        db.flush()
        db.refresh(block)
        return block

    @staticmethod
    def get_block_by_id(db, *, block_id: int) -> Optional[TimeBlock]:
        return (
            db.query(TimeBlock)
            .filter(
                TimeBlock.id == block_id,
                TimeBlock.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def get_blocks_for_plan(db, *, day_plan_id: int) -> List[TimeBlock]:
        return (
            db.query(TimeBlock)
            .options(joinedload(TimeBlock.tag))
            .filter(
                TimeBlock.day_plan_id == day_plan_id,
                TimeBlock.is_active.is_(True),
            )
            .order_by(TimeBlock.sort_order, TimeBlock.start_time)
            .all()
        )

    @staticmethod
    def update_block(db, *, block: TimeBlock) -> TimeBlock:
        db.flush()
        db.refresh(block)
        return block

    @staticmethod
    def list_plans_in_range(
        db,
        *,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> List[DayPlan]:
        return (
            db.query(DayPlan)
            .filter(
                DayPlan.user_id == user_id,
                DayPlan.plan_date >= start_date,
                DayPlan.plan_date <= end_date,
                DayPlan.is_active.is_(True),
            )
            .order_by(DayPlan.plan_date)
            .all()
        )

    @staticmethod
    def get_block_counts_for_plan(
        db,
        *,
        day_plan_id: int,
    ) -> Tuple[int, int]:
        blocks = (
            db.query(TimeBlock)
            .filter(
                TimeBlock.day_plan_id == day_plan_id,
                TimeBlock.is_active.is_(True),
            )
            .all()
        )

        total = len(blocks)
        done_count = sum(
            1 for block in blocks if block.status == BlockStatus.DONE
        )

        return done_count, total
