from typing import Dict
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


def _resolve_tag_id_from_session(
    *,
    key: str,
    tags: List[PlannerTag],
) -> Optional[int]:
    selected = st.session_state.get(key)

    if selected is None:
        return None

    if isinstance(selected, PlannerTag):
        return selected.id

    if isinstance(selected, int):
        return selected

    if isinstance(selected, str):
        if selected == "No tag":
            return None

        for tag in tags:
            if tag.name == selected:
                return tag.id

    return None


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

    tag_by_name: Dict[str, PlannerTag] = {tag.name: tag for tag in tags}
    option_names = [tag.name for tag in tags]

    if not required:
        option_names = ["No tag", *option_names]

    default_name: Optional[str] = None

    if current_tag_id is not None:
        for tag in tags:
            if tag.id == current_tag_id:
                default_name = tag.name
                break
    elif not required:
        default_name = "No tag"
    elif option_names:
        default_name = option_names[0]

    st.markdown(
        " ".join(tag_pill_html(tag=tag) for tag in tags),
        unsafe_allow_html=True,
    )

    label = "Tag" if required else "Tag (optional)"
    selected_name = st.pills(
        label,
        options=option_names,
        default=default_name,
        selection_mode="single",
        key=key,
    )

    if not selected_name or selected_name == "No tag":
        return None

    return tag_by_name[selected_name].id


def resolve_tag_id_from_session(
    *,
    key: str,
    tags: List[PlannerTag],
    required: bool,
) -> Optional[int]:
    tag_id = _resolve_tag_id_from_session(key=key, tags=tags)

    if tag_id is not None:
        return tag_id

    if required:
        raise ValueError("Please select a tag.")

    return None
