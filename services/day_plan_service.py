from datetime import date
from datetime import time
from datetime import timedelta
from typing import Dict
from typing import List
from typing import Optional

from database.models import DayPlan
from database.models import TimeBlock
from database.session import get_db
from repositories.day_plan_repository import DayPlanRepository
from services.planner_tag_service import PlannerTagService
from utils.enums import BlockStatus
from utils.time_slots import add_minutes_to_time
from utils.time_slots import time_diff_minutes


class DayPlanService:

    @staticmethod
    def get_day_plan(*, user_id: int, plan_date: date) -> Optional[DayPlan]:
        with get_db() as db:
            return DayPlanRepository.get_by_user_and_date(
                db=db,
                user_id=user_id,
                plan_date=plan_date,
            )

    @staticmethod
    def _ensure_day_plan(
        db,
        *,
        user_id: int,
        plan_date: date,
        daily_note: Optional[str] = None,
    ) -> DayPlan:
        day_plan = DayPlanRepository.get_by_user_and_date(
            db=db,
            user_id=user_id,
            plan_date=plan_date,
        )

        if day_plan:
            if daily_note is not None and day_plan.daily_note != daily_note:
                day_plan.daily_note = daily_note
            return day_plan

        day_plan = DayPlan(
            user_id=user_id,
            plan_date=plan_date,
            daily_note=daily_note,
        )

        return DayPlanRepository.create(db=db, day_plan=day_plan)

    @staticmethod
    def update_day_plan(
        *,
        user_id: int,
        plan_date: date,
        daily_note: Optional[str] = None,
    ) -> DayPlan:
        with get_db() as db:
            day_plan = DayPlanService._ensure_day_plan(
                db=db,
                user_id=user_id,
                plan_date=plan_date,
                daily_note=daily_note,
            )

            return DayPlanRepository.update(db=db, day_plan=day_plan)

    @staticmethod
    def get_blocks(*, user_id: int, plan_date: date) -> List[TimeBlock]:
        with get_db() as db:
            day_plan = DayPlanRepository.get_by_user_and_date(
                db=db,
                user_id=user_id,
                plan_date=plan_date,
            )

            if day_plan is None:
                return []

            return DayPlanRepository.get_blocks_for_plan(db=db, day_plan_id=day_plan.id)

    @staticmethod
    def add_block(
        *,
        user_id: int,
        plan_date: date,
        start_time: time,
        end_time: time,
        title: str,
        daily_note: Optional[str] = None,
        tag_id: Optional[int] = None,
    ) -> TimeBlock:
        if end_time <= start_time:
            raise ValueError("End time must be after start time.")

        PlannerTagService.validate_tag_for_user(user_id=user_id, tag_id=tag_id)

        with get_db() as db:
            day_plan = DayPlanService._ensure_day_plan(
                db=db,
                user_id=user_id,
                plan_date=plan_date,
                daily_note=daily_note,
            )

            existing_blocks = DayPlanRepository.get_blocks_for_plan(
                db=db,
                day_plan_id=day_plan.id,
            )

            if existing_blocks and start_time != existing_blocks[-1].end_time:
                raise ValueError(
                    "New block must start where the previous block ends "
                    f"({_format_time(existing_blocks[-1].end_time)})."
                )

            block = TimeBlock(
                day_plan_id=day_plan.id,
                start_time=start_time,
                end_time=end_time,
                title=title,
                sort_order=len(existing_blocks),
                tag_id=tag_id,
            )

            created = DayPlanRepository.create_block(db=db, block=block)

            updated_blocks = DayPlanRepository.get_blocks_for_plan(
                db=db,
                day_plan_id=day_plan.id,
            )
            DayPlanService._validate_blocks(updated_blocks)

            return created

    @staticmethod
    def _get_ordered_blocks(db, *, day_plan_id: int) -> List[TimeBlock]:
        return DayPlanRepository.get_blocks_for_plan(db=db, day_plan_id=day_plan_id)

    @staticmethod
    def _shift_blocks(
        blocks: List[TimeBlock],
        *,
        start_index: int,
        delta_minutes: int,
    ) -> None:
        if delta_minutes == 0:
            return

        for block in blocks[start_index:]:
            block.start_time = add_minutes_to_time(block.start_time, delta_minutes)
            block.end_time = add_minutes_to_time(block.end_time, delta_minutes)

    @staticmethod
    def _validate_blocks(blocks: List[TimeBlock]) -> None:
        for index, block in enumerate(blocks):
            if block.end_time <= block.start_time:
                raise ValueError(
                    f"Block '{block.title}' must end after it starts."
                )

            if index > 0 and block.start_time != blocks[index - 1].end_time:
                raise ValueError(
                    f"Block '{block.title}' must start where the previous block ends."
                )

    @staticmethod
    def update_block(
        *,
        block_id: int,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        title: Optional[str] = None,
        tag_id: Optional[int] = None,
    ) -> TimeBlock:
        with get_db() as db:
            block = DayPlanRepository.get_block_by_id(db=db, block_id=block_id)

            if block is None:
                raise ValueError("Block not found.")

            user_id = block.day_plan.user_id
            PlannerTagService.validate_tag_for_user(user_id=user_id, tag_id=tag_id)

            blocks = DayPlanService._get_ordered_blocks(
                db=db,
                day_plan_id=block.day_plan_id,
            )

            block_index = next(
                index for index, item in enumerate(blocks) if item.id == block_id
            )

            old_end = block.end_time

            if start_time is not None:
                if block_index != 0:
                    raise ValueError("Only the first block can change its start time.")

                if start_time >= block.end_time:
                    raise ValueError("Start time must be before end time.")

                block.start_time = start_time

            if end_time is not None:
                if end_time <= block.start_time:
                    raise ValueError("End time must be after start time.")

                block.end_time = end_time

            if title is not None:
                block.title = title.strip()

            if tag_id is not None:
                block.tag_id = tag_id

            if end_time is not None:
                delta_minutes = time_diff_minutes(block.end_time, old_end)
                DayPlanService._shift_blocks(
                    blocks,
                    start_index=block_index + 1,
                    delta_minutes=delta_minutes,
                )

            DayPlanService._validate_blocks(blocks)

            return DayPlanRepository.update_block(db=db, block=block)

    @staticmethod
    def insert_block_after(
        *,
        block_id: int,
        end_time: time,
        title: str,
        tag_id: Optional[int] = None,
    ) -> TimeBlock:
        with get_db() as db:
            block = DayPlanRepository.get_block_by_id(db=db, block_id=block_id)

            if block is None:
                raise ValueError("Block not found.")

            user_id = block.day_plan.user_id
            PlannerTagService.validate_tag_for_user(user_id=user_id, tag_id=tag_id)

            start_time = block.end_time

            if end_time <= start_time:
                raise ValueError("End time must be after start time.")

            blocks = DayPlanService._get_ordered_blocks(
                db=db,
                day_plan_id=block.day_plan_id,
            )

            block_index = next(
                index for index, item in enumerate(blocks) if item.id == block_id
            )

            delta_minutes = time_diff_minutes(end_time, start_time)

            DayPlanService._shift_blocks(
                blocks,
                start_index=block_index + 1,
                delta_minutes=delta_minutes,
            )

            new_block = TimeBlock(
                day_plan_id=block.day_plan_id,
                start_time=start_time,
                end_time=end_time,
                title=title.strip(),
                sort_order=block.sort_order + 1,
                tag_id=tag_id,
            )

            for following in blocks[block_index + 1 :]:
                following.sort_order += 1

            new_block = DayPlanRepository.create_block(db=db, block=new_block)

            updated_blocks = DayPlanService._get_ordered_blocks(
                db=db,
                day_plan_id=block.day_plan_id,
            )
            DayPlanService._validate_blocks(updated_blocks)

            return new_block

    @staticmethod
    def mark_block_done(*, block_id: int) -> TimeBlock:
        with get_db() as db:
            block = DayPlanRepository.get_block_by_id(db=db, block_id=block_id)

            if block is None:
                raise ValueError("Block not found.")

            block.status = BlockStatus.DONE
            return DayPlanRepository.update_block(db=db, block=block)

    @staticmethod
    def mark_block_skipped(*, block_id: int) -> TimeBlock:
        with get_db() as db:
            block = DayPlanRepository.get_block_by_id(db=db, block_id=block_id)

            if block is None:
                raise ValueError("Block not found.")

            block.status = BlockStatus.SKIPPED
            return DayPlanRepository.update_block(db=db, block=block)

    @staticmethod
    def mark_block_pending(*, block_id: int) -> TimeBlock:
        with get_db() as db:
            block = DayPlanRepository.get_block_by_id(db=db, block_id=block_id)

            if block is None:
                raise ValueError("Block not found.")

            block.status = BlockStatus.PENDING
            return DayPlanRepository.update_block(db=db, block=block)

    @staticmethod
    def delete_block(*, block_id: int) -> None:
        with get_db() as db:
            block = DayPlanRepository.get_block_by_id(db=db, block_id=block_id)

            if block is None:
                raise ValueError("Block not found.")

            blocks = DayPlanService._get_ordered_blocks(
                db=db,
                day_plan_id=block.day_plan_id,
            )

            block_index = next(
                index for index, item in enumerate(blocks) if item.id == block_id
            )

            deleted_duration = time_diff_minutes(block.end_time, block.start_time)

            block.is_active = False

            DayPlanService._shift_blocks(
                blocks,
                start_index=block_index + 1,
                delta_minutes=-deleted_duration,
            )

            for following in blocks[block_index + 1 :]:
                following.sort_order -= 1

            remaining_blocks = [
                item
                for item in blocks
                if item.is_active and item.id != block_id
            ]
            DayPlanService._validate_blocks(remaining_blocks)

    @staticmethod
    def get_current_block(*, user_id: int, plan_date: date, now: time) -> Optional[TimeBlock]:
        blocks = DayPlanService.get_blocks(user_id=user_id, plan_date=plan_date)

        for block in blocks:
            if block.status == BlockStatus.PENDING:
                if block.start_time <= now < block.end_time:
                    return block

        return None

    @staticmethod
    def get_achievement_percent(
        *,
        user_id: int,
        plan_date: date,
    ) -> Optional[int]:
        blocks = DayPlanService.get_blocks(user_id=user_id, plan_date=plan_date)

        if not blocks:
            return None

        done_count = sum(1 for block in blocks if block.status == BlockStatus.DONE)
        return round((done_count / len(blocks)) * 100)

    @staticmethod
    def get_daily_summaries(
        *,
        user_id: int,
        start_date: date,
        end_date: date,
    ) -> List[Dict]:
        with get_db() as db:
            plans = DayPlanRepository.list_plans_in_range(
                db=db,
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
            )

            summaries = []

            for plan in plans:
                done_count, total = DayPlanRepository.get_block_counts_for_plan(
                    db=db,
                    day_plan_id=plan.id,
                )

                percent = round((done_count / total) * 100) if total else None

                summaries.append(
                    {
                        "plan_date": plan.plan_date,
                        "done_count": done_count,
                        "total": total,
                        "percent": percent,
                    }
                )

            return summaries

    @staticmethod
    def get_planning_streak(*, user_id: int, as_of_date: date) -> int:
        streak = 0
        current_date = as_of_date

        blocks_today = DayPlanService.get_blocks(
            user_id=user_id,
            plan_date=current_date,
        )
        if not blocks_today:
            current_date -= timedelta(days=1)

        while True:
            blocks = DayPlanService.get_blocks(
                user_id=user_id,
                plan_date=current_date,
            )

            if not blocks:
                break

            streak += 1
            current_date -= timedelta(days=1)

        return streak

    @staticmethod
    def get_completion_streak(*, user_id: int, as_of_date: date) -> int:
        streak = 0
        current_date = as_of_date

        blocks_today = DayPlanService.get_blocks(
            user_id=user_id,
            plan_date=current_date,
        )
        today_complete = blocks_today and all(
            block.status == BlockStatus.DONE for block in blocks_today
        )
        if not today_complete:
            current_date -= timedelta(days=1)

        while True:
            blocks = DayPlanService.get_blocks(
                user_id=user_id,
                plan_date=current_date,
            )

            if not blocks:
                break

            if any(block.status != BlockStatus.DONE for block in blocks):
                break

            streak += 1
            current_date -= timedelta(days=1)

        return streak

    @staticmethod
    def copy_blocks_from_date(
        *,
        user_id: int,
        source_date: date,
        target_date: date,
        overwrite: bool = False,
    ) -> DayPlan:
        source_blocks = DayPlanService.get_blocks(
            user_id=user_id,
            plan_date=source_date,
        )

        if not source_blocks:
            raise ValueError("Source day has no blocks to copy.")

        target_blocks = DayPlanService.get_blocks(
            user_id=user_id,
            plan_date=target_date,
        )

        if target_blocks and not overwrite:
            raise ValueError(
                "Target day already has blocks. Enable overwrite to replace them."
            )

        source_plan = DayPlanService.get_day_plan(
            user_id=user_id,
            plan_date=source_date,
        )

        with get_db() as db:
            if target_blocks:
                target_plan = DayPlanRepository.get_by_user_and_date(
                    db=db,
                    user_id=user_id,
                    plan_date=target_date,
                )

                for block in DayPlanRepository.get_blocks_for_plan(
                    db=db,
                    day_plan_id=target_plan.id,
                ):
                    block.is_active = False

            day_plan = DayPlanService._ensure_day_plan(
                db=db,
                user_id=user_id,
                plan_date=target_date,
                daily_note=source_plan.daily_note if source_plan else None,
            )

            for index, source_block in enumerate(source_blocks):
                block = TimeBlock(
                    day_plan_id=day_plan.id,
                    start_time=source_block.start_time,
                    end_time=source_block.end_time,
                    title=source_block.title,
                    sort_order=index,
                    status=BlockStatus.PENDING,
                    tag_id=source_block.tag_id,
                )
                DayPlanRepository.create_block(db=db, block=block)

            return day_plan


def _format_time(value: time) -> str:
    return value.strftime("%H:%M")
