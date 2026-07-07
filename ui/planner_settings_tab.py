from datetime import datetime
from datetime import timedelta

import pytz
import streamlit as st

from services.day_plan_service import DayPlanService
from services.day_plan_template_service import DayPlanTemplateService
from services.user_service import UserService


def render_planner_settings_tab(*, user_id: int, timezone: str) -> None:
    tz = pytz.timezone(timezone)
    today = datetime.now(tz).date()

    st.subheader("Templates & Settings")

    st.markdown("### Templates")

    templates = DayPlanTemplateService.list_templates(user_id=user_id)

    if templates:
        for template in templates:
            block_count = DayPlanTemplateService.get_template_block_count(
                template_id=template.id,
            )

            with st.container(border=True):
                note = f" · {template.daily_note}" if template.daily_note else ""
                st.markdown(f"**{template.name}** — {block_count} blocks{note}")

                apply_col, delete_col = st.columns(2)

                with apply_col:
                    if st.button(
                        "Apply",
                        key=f"apply_template_{template.id}",
                        use_container_width=True,
                    ):
                        st.session_state[f"applying_template_{template.id}"] = True
                        st.rerun()

                with delete_col:
                    if st.button(
                        "Delete",
                        key=f"delete_template_{template.id}",
                        use_container_width=True,
                    ):
                        DayPlanTemplateService.delete_template(
                            user_id=user_id,
                            template_id=template.id,
                        )
                        st.success(f"Template '{template.name}' deleted.")
                        st.rerun()

            if st.session_state.get(f"applying_template_{template.id}"):
                with st.form(key=f"apply_form_{template.id}"):
                    target_date = st.date_input(
                        "Apply to date",
                        value=today,
                        key=f"apply_date_{template.id}",
                    )
                    overwrite = st.checkbox(
                        "Overwrite existing blocks",
                        key=f"apply_overwrite_{template.id}",
                    )

                    col_save, col_cancel = st.columns(2)

                    with col_save:
                        submitted = st.form_submit_button("Apply template")

                    with col_cancel:
                        cancelled = st.form_submit_button("Cancel")

                    if submitted:
                        try:
                            DayPlanTemplateService.apply_to_date(
                                user_id=user_id,
                                template_id=template.id,
                                plan_date=target_date,
                                overwrite=overwrite,
                            )
                            st.session_state.pop(
                                f"applying_template_{template.id}",
                                None,
                            )
                            st.success(
                                f"Template applied to "
                                f"{target_date.strftime('%d %b %Y')}."
                            )
                            st.rerun()

                        except ValueError as error:
                            st.error(str(error))

                    if cancelled:
                        st.session_state.pop(
                            f"applying_template_{template.id}",
                            None,
                        )
                        st.rerun()
    else:
        st.info("No templates yet. Save one from a planned day below.")

    st.divider()
    st.markdown("### Save template from a day")

    with st.form("save_template_form"):
        source_date = st.date_input("Source date", value=today)
        template_name = st.text_input("Template name", placeholder="Weekday routine")

        if st.form_submit_button("Save as template"):
            if not template_name.strip():
                st.error("Template name is required.")
            else:
                try:
                    DayPlanTemplateService.save_from_day(
                        user_id=user_id,
                        plan_date=source_date,
                        name=template_name.strip(),
                    )
                    st.success(f"Template '{template_name.strip()}' saved.")
                    st.rerun()

                except ValueError as error:
                    st.error(str(error))

    st.divider()
    st.markdown("### Quick copy")

    with st.form("copy_yesterday_form"):
        target_date = st.date_input(
            "Copy yesterday to",
            value=today,
            key="copy_target_date",
        )
        overwrite = st.checkbox("Overwrite existing blocks", key="copy_overwrite")
        yesterday = today - timedelta(days=1)

        st.caption(
            f"Copies blocks from {yesterday.strftime('%A, %d %b %Y')} "
            f"to the selected date."
        )

        if st.form_submit_button("Copy yesterday"):
            try:
                DayPlanService.copy_blocks_from_date(
                    user_id=user_id,
                    source_date=yesterday,
                    target_date=target_date,
                    overwrite=overwrite,
                )
                st.success("Yesterday's plan copied.")
                st.rerun()

            except ValueError as error:
                st.error(str(error))

    st.divider()
    st.markdown("### Settings")

    user = st.session_state["user"]

    timezones = [
        "Asia/Kolkata",
        "Asia/Dubai",
        "Asia/Singapore",
        "Europe/London",
        "America/New_York",
        "UTC",
    ]

    selected_tz = st.selectbox(
        "Timezone",
        options=timezones,
        index=timezones.index(user["timezone"])
        if user["timezone"] in timezones
        else 0,
        key="planner_timezone",
    )

    if selected_tz != user["timezone"]:
        updated = UserService.update_timezone(
            user_id=user["id"],
            timezone=selected_tz,
        )
        st.session_state["user"]["timezone"] = updated.timezone
        st.success(f"Timezone updated to {selected_tz}")
        st.rerun()
