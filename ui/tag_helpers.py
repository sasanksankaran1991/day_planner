from typing import List
from typing import Optional

import streamlit as st

from database.models import PlannerTag


def tag_pill_html(*, tag: PlannerTag) -> str:
    return (
        f'<span class="planner-tag-pill" style="background:{tag.color};">'
        f"{tag.name}</span>"
    )


def render_tag_pill(*, tag: Optional[PlannerTag]) -> str:
    if tag is None:
        return ""

    return tag_pill_html(tag=tag)


def render_tag_selector(
    *,
    tags: List[PlannerTag],
    required: bool,
    key: str,
    current_tag_id: Optional[int] = None,
) -> Optional[int]:
    if not tags:
        if required:
            st.warning("Add tags in Settings before creating blocks.")
        return None

    if not required:
        selected = st.selectbox(
            "Tag (optional)",
            options=[None, *tags],
            format_func=lambda tag: "No tag" if tag is None else tag.name,
            index=0,
            key=key,
        )
        return selected.id if selected else None

    options = tags
    default_index = 0

    if current_tag_id is not None:
        for index, tag in enumerate(options):
            if tag.id == current_tag_id:
                default_index = index
                break

    selected = st.selectbox(
        "Tag",
        options=options,
        format_func=lambda tag: tag.name,
        index=default_index,
        key=key,
    )

    return selected.id if selected else None
