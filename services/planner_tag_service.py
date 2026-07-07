import re
from typing import List
from typing import Optional

from database.models import PlannerTag
from database.session import get_db
from repositories.planner_tag_repository import PlannerTagRepository

DEFAULT_TAG_COLORS = [
    "#1E88E5",
    "#43A047",
    "#E53935",
    "#FB8C00",
    "#8E24AA",
    "#00ACC1",
    "#6D4C41",
    "#546E7A",
]

_HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


class PlannerTagService:

    @staticmethod
    def list_tags(*, user_id: int) -> List[PlannerTag]:
        with get_db() as db:
            return PlannerTagRepository.list_for_user(db=db, user_id=user_id)

    @staticmethod
    def tags_required_on_create(*, user_id: int) -> bool:
        tags = PlannerTagService.list_tags(user_id=user_id)
        return any(tag.require_on_create for tag in tags)

    @staticmethod
    def create_tag(*, user_id: int, name: str, color: str) -> PlannerTag:
        cleaned_name = name.strip()

        if not cleaned_name:
            raise ValueError("Tag name is required.")

        if len(cleaned_name) > 50:
            raise ValueError("Tag name must be 50 characters or fewer.")

        normalized_color = PlannerTagService._normalize_color(color)

        with get_db() as db:
            existing = PlannerTagRepository.get_by_name(
                db=db,
                user_id=user_id,
                name=cleaned_name,
            )

            if existing:
                raise ValueError(f"Tag '{cleaned_name}' already exists.")

            tags = PlannerTagRepository.list_for_user(db=db, user_id=user_id)
            default_color = DEFAULT_TAG_COLORS[len(tags) % len(DEFAULT_TAG_COLORS)]

            tag = PlannerTag(
                user_id=user_id,
                name=cleaned_name,
                color=normalized_color or default_color,
                sort_order=len(tags),
            )

            return PlannerTagRepository.create(db=db, tag=tag)

    @staticmethod
    def update_require_on_create(
        *,
        user_id: int,
        tag_id: int,
        require_on_create: bool,
    ) -> PlannerTag:
        with get_db() as db:
            tag = PlannerTagRepository.get_by_id(db=db, tag_id=tag_id)

            if tag is None or tag.user_id != user_id:
                raise ValueError("Tag not found.")

            tag.require_on_create = require_on_create
            return PlannerTagRepository.update(db=db, tag=tag)

    @staticmethod
    def delete_tag(*, user_id: int, tag_id: int) -> None:
        with get_db() as db:
            tag = PlannerTagRepository.get_by_id(db=db, tag_id=tag_id)

            if tag is None or tag.user_id != user_id:
                raise ValueError("Tag not found.")

            tag.is_active = False
            PlannerTagRepository.update(db=db, tag=tag)

    @staticmethod
    def validate_tag_for_user(*, user_id: int, tag_id: Optional[int]) -> None:
        if tag_id is None:
            if PlannerTagService.tags_required_on_create(user_id=user_id):
                raise ValueError("A tag is required for this block.")
            return

        with get_db() as db:
            tag = PlannerTagRepository.get_by_id(db=db, tag_id=tag_id)

            if tag is None or tag.user_id != user_id:
                raise ValueError("Selected tag is not valid.")

    @staticmethod
    def get_tags_map(*, user_id: int) -> dict:
        tags = PlannerTagService.list_tags(user_id=user_id)
        return {tag.id: tag for tag in tags}

    @staticmethod
    def _normalize_color(color: str) -> str:
        value = color.strip()

        if not value:
            return ""

        if not value.startswith("#"):
            value = f"#{value}"

        if not _HEX_COLOR_PATTERN.match(value):
            raise ValueError("Tag color must be a hex value like #1E88E5.")

        return value.upper()
