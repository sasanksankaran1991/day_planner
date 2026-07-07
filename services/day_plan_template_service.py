from datetime import date
from typing import List

from database.models import DayPlanTemplate
from database.models import DayPlanTemplateBlock
from database.models import TimeBlock
from database.session import get_db
from repositories.day_plan_repository import DayPlanRepository
from repositories.day_plan_template_repository import DayPlanTemplateRepository
from services.day_plan_service import DayPlanService
from utils.enums import BlockStatus


class DayPlanTemplateService:

    @staticmethod
    def list_templates(*, user_id: int) -> List[DayPlanTemplate]:
        with get_db() as db:
            return DayPlanTemplateRepository.list_for_user(db=db, user_id=user_id)

    @staticmethod
    def save_from_day(
        *,
        user_id: int,
        plan_date: date,
        name: str,
    ) -> DayPlanTemplate:
        blocks = DayPlanService.get_blocks(user_id=user_id, plan_date=plan_date)

        if not blocks:
            raise ValueError("This day has no blocks to save as a template.")

        day_plan = DayPlanService.get_day_plan(user_id=user_id, plan_date=plan_date)

        with get_db() as db:
            template = DayPlanTemplate(
                user_id=user_id,
                name=name.strip(),
                daily_note=day_plan.daily_note if day_plan else None,
            )
            template = DayPlanTemplateRepository.create(db=db, template=template)

            for index, block in enumerate(blocks):
                template_block = DayPlanTemplateBlock(
                    template_id=template.id,
                    start_time=block.start_time,
                    end_time=block.end_time,
                    title=block.title,
                    sort_order=index,
                )
                DayPlanTemplateRepository.create_block(db=db, block=template_block)

            return template

    @staticmethod
    def apply_to_date(
        *,
        user_id: int,
        template_id: int,
        plan_date: date,
        overwrite: bool = False,
    ):
        with get_db() as db:
            template = DayPlanTemplateRepository.get_by_id(
                db=db,
                template_id=template_id,
            )

            if template is None or template.user_id != user_id:
                raise ValueError("Template not found.")

            template_blocks = DayPlanTemplateRepository.get_blocks_for_template(
                db=db,
                template_id=template_id,
            )

            if not template_blocks:
                raise ValueError("Template has no blocks.")

        existing_blocks = DayPlanService.get_blocks(
            user_id=user_id,
            plan_date=plan_date,
        )

        if existing_blocks and not overwrite:
            raise ValueError(
                "This day already has blocks. Enable overwrite to replace them."
            )

        with get_db() as db:
            if existing_blocks:
                day_plan = DayPlanRepository.get_by_user_and_date(
                    db=db,
                    user_id=user_id,
                    plan_date=plan_date,
                )

                for block in DayPlanRepository.get_blocks_for_plan(
                    db=db,
                    day_plan_id=day_plan.id,
                ):
                    block.is_active = False

            day_plan = DayPlanService._ensure_day_plan(
                db=db,
                user_id=user_id,
                plan_date=plan_date,
                daily_note=template.daily_note,
            )

            for index, template_block in enumerate(template_blocks):
                block = TimeBlock(
                    day_plan_id=day_plan.id,
                    start_time=template_block.start_time,
                    end_time=template_block.end_time,
                    title=template_block.title,
                    sort_order=index,
                    status=BlockStatus.PENDING,
                )
                DayPlanRepository.create_block(db=db, block=block)

            return day_plan

    @staticmethod
    def delete_template(*, user_id: int, template_id: int) -> None:
        with get_db() as db:
            template = DayPlanTemplateRepository.get_by_id(
                db=db,
                template_id=template_id,
            )

            if template is None or template.user_id != user_id:
                raise ValueError("Template not found.")

            template.is_active = False

            for block in DayPlanTemplateRepository.get_blocks_for_template(
                db=db,
                template_id=template_id,
            ):
                block.is_active = False

    @staticmethod
    def get_template_block_count(*, template_id: int) -> int:
        with get_db() as db:
            return len(
                DayPlanTemplateRepository.get_blocks_for_template(
                    db=db,
                    template_id=template_id,
                )
            )
