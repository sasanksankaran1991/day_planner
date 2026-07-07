from typing import List
from typing import Optional

from database.models import DayPlanTemplate
from database.models import DayPlanTemplateBlock


class DayPlanTemplateRepository:

    @staticmethod
    def list_for_user(db, *, user_id: int) -> List[DayPlanTemplate]:
        return (
            db.query(DayPlanTemplate)
            .filter(
                DayPlanTemplate.user_id == user_id,
                DayPlanTemplate.is_active.is_(True),
            )
            .order_by(DayPlanTemplate.name)
            .all()
        )

    @staticmethod
    def get_by_id(db, *, template_id: int) -> Optional[DayPlanTemplate]:
        return (
            db.query(DayPlanTemplate)
            .filter(
                DayPlanTemplate.id == template_id,
                DayPlanTemplate.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def create(db, *, template: DayPlanTemplate) -> DayPlanTemplate:
        db.add(template)
        db.flush()
        db.refresh(template)
        return template

    @staticmethod
    def update(db, *, template: DayPlanTemplate) -> DayPlanTemplate:
        db.flush()
        db.refresh(template)
        return template

    @staticmethod
    def get_blocks_for_template(
        db,
        *,
        template_id: int,
    ) -> List[DayPlanTemplateBlock]:
        return (
            db.query(DayPlanTemplateBlock)
            .filter(
                DayPlanTemplateBlock.template_id == template_id,
                DayPlanTemplateBlock.is_active.is_(True),
            )
            .order_by(DayPlanTemplateBlock.sort_order, DayPlanTemplateBlock.start_time)
            .all()
        )

    @staticmethod
    def create_block(
        db,
        *,
        block: DayPlanTemplateBlock,
    ) -> DayPlanTemplateBlock:
        db.add(block)
        db.flush()
        db.refresh(block)
        return block
