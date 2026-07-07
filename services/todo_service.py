from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from typing import Dict
from typing import List
from typing import Optional

import pytz

from database.models import Todo
from database.models import TodoAssignment
from database.models import TodoOccurrence
from database.models import TodoUserStatus
from database.session import get_db
from repositories.todo_repository import TodoRepository
from repositories.user_repository import UserRepository
from services.planner_tag_service import PlannerTagService
from utils.enums import AssignmentStatus
from utils.enums import OccurrenceStatus
from utils.enums import RecurrenceType
from utils.recurrence import format_recurrence_label
from utils.recurrence import generate_occurrence_dates
from utils.time_slots import time_to_minutes

TASK_NOW_MINUTES = 30


class TodoService:

    @staticmethod
    def resolve_visual_state(
        *,
        status: OccurrenceStatus,
        display_time: time,
        view_date: date,
        today: date,
        now: time,
    ) -> str:
        if status == OccurrenceStatus.DONE:
            return "done"

        if status == OccurrenceStatus.SKIPPED:
            return "skipped"

        if status == OccurrenceStatus.POSTPONED:
            return "postponed"

        if view_date < today:
            return "overdue"

        if view_date > today:
            return "upcoming"

        display_minutes = time_to_minutes(display_time)
        now_minutes = time_to_minutes(now)
        window_end_minutes = min(
            display_minutes + TASK_NOW_MINUTES,
            (24 * 60) - 1,
        )

        if now_minutes < display_minutes:
            return "upcoming"

        if now_minutes <= window_end_minutes:
            return "current"

        return "overdue"

    @staticmethod
    def _parse_custom_days(custom_days: Optional[str]) -> Optional[List[int]]:
        if not custom_days:
            return None

        return [int(day.strip()) for day in custom_days.split(",") if day.strip()]

    @staticmethod
    def _get_participant_ids(db, *, todo: Todo) -> List[int]:
        participant_ids = [todo.owner_id]

        for assignment in todo.assignments:
            if assignment.status == AssignmentStatus.ACCEPTED:
                participant_ids.append(assignment.assignee_id)

        return list(set(participant_ids))

    @staticmethod
    def _create_statuses_for_occurrence(
        db,
        *,
        occurrence: TodoOccurrence,
        participant_ids: List[int],
    ) -> None:
        for user_id in participant_ids:
            existing = TodoRepository.get_user_status(
                db=db,
                occurrence_id=occurrence.id,
                user_id=user_id,
            )

            if existing is None:
                TodoRepository.create_user_status(
                    db=db,
                    status=TodoUserStatus(
                        occurrence_id=occurrence.id,
                        user_id=user_id,
                        status=OccurrenceStatus.PENDING,
                    ),
                )

    @staticmethod
    def create_todo(
        *,
        owner_id: int,
        title: str,
        scheduled_date: date,
        scheduled_time: time,
        recurrence_type: RecurrenceType,
        recurrence_end_date: Optional[date] = None,
        custom_days: Optional[str] = None,
        description: Optional[str] = None,
        assignee_ids: Optional[List[int]] = None,
        tag_id: Optional[int] = None,
    ) -> Todo:
        if recurrence_type != RecurrenceType.ONE_TIME and recurrence_end_date is None:
            raise ValueError("Recurring tasks require an end date.")

        PlannerTagService.validate_tag_for_user(user_id=owner_id, tag_id=tag_id)

        with get_db() as db:
            owner = UserRepository.get_by_id(db=db, user_id=owner_id)

            if owner is None:
                raise ValueError("Owner not found.")

            todo = Todo(
                owner_id=owner_id,
                title=title,
                description=description,
                recurrence_type=recurrence_type,
                recurrence_end_date=recurrence_end_date,
                custom_days=custom_days,
                default_time=scheduled_time,
                first_date=scheduled_date,
                tag_id=tag_id,
            )

            todo = TodoRepository.create_todo(db=db, todo=todo)

            occurrence_dates = generate_occurrence_dates(
                recurrence_type=recurrence_type,
                first_date=scheduled_date,
                end_date=recurrence_end_date,
                custom_days=TodoService._parse_custom_days(custom_days),
            )

            if not occurrence_dates:
                raise ValueError(
                    "No task dates match your repeat settings. "
                    "Check the start date, repeat-until date, and repeat days."
                )

            for occurrence_date in occurrence_dates:
                occurrence = TodoRepository.create_occurrence(
                    db=db,
                    occurrence=TodoOccurrence(
                        todo_id=todo.id,
                        occurrence_date=occurrence_date,
                        occurrence_time=scheduled_time,
                    ),
                )

                TodoService._create_statuses_for_occurrence(
                    db=db,
                    occurrence=occurrence,
                    participant_ids=[owner_id],
                )

            if assignee_ids:
                for assignee_id in assignee_ids:
                    if assignee_id == owner_id:
                        continue

                    assignee = UserRepository.get_by_id(db=db, user_id=assignee_id)

                    if assignee is None:
                        raise ValueError(f"Assignee {assignee_id} not found.")

                    TodoRepository.create_assignment(
                        db=db,
                        assignment=TodoAssignment(
                            todo_id=todo.id,
                            assignee_id=assignee_id,
                            assigned_by_id=owner_id,
                            status=AssignmentStatus.PENDING,
                        ),
                    )

            db.refresh(todo)
            return todo

    @staticmethod
    def update_todo(
        *,
        todo_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        scheduled_time: Optional[time] = None,
        recurrence_type: Optional[RecurrenceType] = None,
        recurrence_end_date: Optional[date] = None,
        custom_days: Optional[str] = None,
        from_date: Optional[date] = None,
    ) -> Todo:
        with get_db() as db:
            todo = TodoRepository.get_todo_by_id(db=db, todo_id=todo_id)

            if todo is None:
                raise ValueError("Todo not found.")

            effective_from = from_date or date.today()

            if title is not None:
                todo.title = title

            if description is not None:
                todo.description = description

            if recurrence_type is not None:
                todo.recurrence_type = recurrence_type

            if recurrence_end_date is not None:
                todo.recurrence_end_date = recurrence_end_date

            if custom_days is not None:
                todo.custom_days = custom_days

            if scheduled_time is not None:
                todo.default_time = scheduled_time

            future_occurrences = TodoRepository.get_future_occurrences(
                db=db,
                todo_id=todo_id,
                from_date=effective_from,
            )

            for occurrence in future_occurrences:
                if scheduled_time is not None:
                    occurrence.occurrence_time = scheduled_time

            if recurrence_type is not None or recurrence_end_date is not None:
                TodoRepository.soft_delete_occurrences(db=db, occurrences=future_occurrences)

                occurrence_dates = generate_occurrence_dates(
                    recurrence_type=todo.recurrence_type,
                    first_date=max(todo.first_date, effective_from),
                    end_date=todo.recurrence_end_date,
                    custom_days=TodoService._parse_custom_days(todo.custom_days),
                )

                participant_ids = TodoService._get_participant_ids(db=db, todo=todo)

                for occurrence_date in occurrence_dates:
                    if occurrence_date < effective_from:
                        continue

                    occurrence = TodoRepository.create_occurrence(
                        db=db,
                        occurrence=TodoOccurrence(
                            todo_id=todo.id,
                            occurrence_date=occurrence_date,
                            occurrence_time=todo.default_time,
                        ),
                    )

                    TodoService._create_statuses_for_occurrence(
                        db=db,
                        occurrence=occurrence,
                        participant_ids=participant_ids,
                    )

            db.refresh(todo)
            return todo

    @staticmethod
    def get_dashboard_occurrences(
        *,
        user_id: int,
        on_date: date,
        today: Optional[date] = None,
        now: Optional[time] = None,
    ) -> List[dict]:
        effective_today = today or date.today()
        effective_now = now or datetime.now().time().replace(second=0, microsecond=0)

        with get_db() as db:
            occurrences = TodoRepository.get_occurrences_on_date(
                db=db,
                on_date=on_date,
                user_ids=[user_id],
            )
            postponed_occurrences = TodoRepository.get_postponed_occurrences_for_user(
                db=db,
                user_id=user_id,
                postponed_date=on_date,
            )

            seen_occurrence_ids = set()
            combined_occurrences = []

            for occurrence in occurrences + postponed_occurrences:
                if occurrence.id in seen_occurrence_ids:
                    continue

                seen_occurrence_ids.add(occurrence.id)
                combined_occurrences.append(occurrence)

            results = []

            for occurrence in combined_occurrences:
                todo = occurrence.todo
                is_owner = todo.owner_id == user_id

                assignment = TodoRepository.get_assignment(
                    db=db,
                    todo_id=todo.id,
                    assignee_id=user_id,
                )

                if not is_owner:
                    if assignment is None or assignment.status != AssignmentStatus.ACCEPTED:
                        continue

                user_status = TodoRepository.get_user_status(
                    db=db,
                    occurrence_id=occurrence.id,
                    user_id=user_id,
                )

                if user_status is None:
                    continue

                display_date = user_status.postponed_date or occurrence.occurrence_date
                display_time = user_status.postponed_time or occurrence.occurrence_time

                if display_date != on_date:
                    continue

                results.append(
                    {
                        "occurrence_id": occurrence.id,
                        "todo_id": todo.id,
                        "title": todo.title,
                        "description": todo.description,
                        "status": user_status.status,
                        "display_time": display_time,
                        "is_owner": is_owner,
                        "owner_name": todo.owner.display_name,
                        "tag_id": todo.tag_id,
                        "tag_name": todo.tag.name if todo.tag else None,
                        "tag_color": todo.tag.color if todo.tag else None,
                        "recurrence_type": todo.recurrence_type,
                        "recurrence_label": format_recurrence_label(
                            recurrence_type=todo.recurrence_type,
                            custom_days=todo.custom_days,
                        ),
                        "default_time": todo.default_time,
                        "custom_days": todo.custom_days,
                        "recurrence_end_date": todo.recurrence_end_date,
                        "visual_state": TodoService.resolve_visual_state(
                            status=user_status.status,
                            display_time=display_time,
                            view_date=on_date,
                            today=effective_today,
                            now=effective_now,
                        ),
                    }
                )

            results.sort(key=lambda item: item["display_time"])
            return results

    @staticmethod
    def get_day_stats(
        *,
        user_id: int,
        on_date: date,
        today: date,
        now: time,
    ) -> Dict:
        items = TodoService.get_dashboard_occurrences(
            user_id=user_id,
            on_date=on_date,
            today=today,
            now=now,
        )
        total = len(items)
        done_count = sum(
            1 for item in items if item["status"] == OccurrenceStatus.DONE
        )
        skipped_count = sum(
            1 for item in items if item["status"] == OccurrenceStatus.SKIPPED
        )
        pending_count = sum(
            1 for item in items if item["status"] == OccurrenceStatus.PENDING
        )
        overdue_count = sum(
            1
            for item in items
            if item["visual_state"] == "overdue"
        )
        percent = round((done_count / total) * 100) if total else None

        return {
            "total": total,
            "done_count": done_count,
            "skipped_count": skipped_count,
            "pending_count": pending_count,
            "overdue_count": overdue_count,
            "percent": percent,
        }

    @staticmethod
    def get_daily_summaries(
        *,
        user_id: int,
        start_date: date,
        end_date: date,
        today: date,
        now: time,
    ) -> List[Dict]:
        summaries = []
        current = start_date

        while current <= end_date:
            stats = TodoService.get_day_stats(
                user_id=user_id,
                on_date=current,
                today=today,
                now=now,
            )
            summaries.append({"plan_date": current, **stats})
            current += timedelta(days=1)

        return summaries

    @staticmethod
    def list_recurring_todos(*, owner_id: int) -> List[Dict]:
        with get_db() as db:
            todos = TodoRepository.list_recurring_todos_for_owner(
                db=db,
                owner_id=owner_id,
            )
            results = []

            for todo in todos:
                occurrence_count = TodoRepository.count_active_occurrences(
                    db=db,
                    todo_id=todo.id,
                )
                results.append(
                    {
                        "todo_id": todo.id,
                        "title": todo.title,
                        "description": todo.description,
                        "recurrence_type": todo.recurrence_type,
                        "recurrence_label": format_recurrence_label(
                            recurrence_type=todo.recurrence_type,
                            custom_days=todo.custom_days,
                        ),
                        "recurrence_end_date": todo.recurrence_end_date,
                        "custom_days": todo.custom_days,
                        "default_time": todo.default_time,
                        "first_date": todo.first_date,
                        "occurrence_count": occurrence_count,
                        "tag_name": todo.tag.name if todo.tag else None,
                        "tag_color": todo.tag.color if todo.tag else None,
                    }
                )

            return results

    @staticmethod
    def get_todo_for_edit(*, todo_id: int, owner_id: int) -> Dict:
        with get_db() as db:
            todo = TodoRepository.get_todo_by_id(db=db, todo_id=todo_id)

            if todo is None or todo.owner_id != owner_id:
                raise ValueError("Task not found.")

            return {
                "todo_id": todo.id,
                "title": todo.title,
                "description": todo.description,
                "recurrence_type": todo.recurrence_type,
                "recurrence_end_date": todo.recurrence_end_date,
                "custom_days": todo.custom_days,
                "default_time": todo.default_time,
                "first_date": todo.first_date,
            }

    @staticmethod
    def mark_done(*, occurrence_id: int, user_id: int) -> TodoUserStatus:
        with get_db() as db:
            status = TodoRepository.get_user_status(
                db=db,
                occurrence_id=occurrence_id,
                user_id=user_id,
            )

            if status is None:
                raise ValueError("Status not found.")

            status.status = OccurrenceStatus.DONE
            status.done_at = datetime.now(pytz.UTC)

            return TodoRepository.update_user_status(db=db, status=status)

    @staticmethod
    def mark_skipped(*, occurrence_id: int, user_id: int) -> TodoUserStatus:
        with get_db() as db:
            status = TodoRepository.get_user_status(
                db=db,
                occurrence_id=occurrence_id,
                user_id=user_id,
            )

            if status is None:
                raise ValueError("Status not found.")

            status.status = OccurrenceStatus.SKIPPED
            status.done_at = None
            status.postponed_date = None
            status.postponed_time = None

            return TodoRepository.update_user_status(db=db, status=status)

    @staticmethod
    def mark_pending(*, occurrence_id: int, user_id: int) -> TodoUserStatus:
        with get_db() as db:
            status = TodoRepository.get_user_status(
                db=db,
                occurrence_id=occurrence_id,
                user_id=user_id,
            )

            if status is None:
                raise ValueError("Status not found.")

            status.status = OccurrenceStatus.PENDING
            status.done_at = None
            status.postponed_date = None
            status.postponed_time = None

            return TodoRepository.update_user_status(db=db, status=status)

    @staticmethod
    def postpone_occurrence(
        *,
        occurrence_id: int,
        user_id: int,
        new_date: Optional[date] = None,
        new_time: Optional[time] = None,
    ) -> TodoUserStatus:
        with get_db() as db:
            occurrence = TodoRepository.get_occurrence_by_id(
                db=db,
                occurrence_id=occurrence_id,
            )

            if occurrence is None:
                raise ValueError("Occurrence not found.")

            status = TodoRepository.get_user_status(
                db=db,
                occurrence_id=occurrence_id,
                user_id=user_id,
            )

            if status is None:
                raise ValueError("Status not found.")

            status.status = OccurrenceStatus.POSTPONED
            status.postponed_date = new_date or occurrence.occurrence_date
            status.postponed_time = new_time or occurrence.occurrence_time

            return TodoRepository.update_user_status(db=db, status=status)

    @staticmethod
    def respond_to_assignment(
        *,
        todo_id: int,
        assignee_id: int,
        accept: bool,
    ) -> TodoAssignment:
        with get_db() as db:
            assignment = TodoRepository.get_assignment(
                db=db,
                todo_id=todo_id,
                assignee_id=assignee_id,
            )

            if assignment is None:
                raise ValueError("Assignment not found.")

            assignment.status = (
                AssignmentStatus.ACCEPTED if accept else AssignmentStatus.REJECTED
            )

            if accept:
                todo = TodoRepository.get_todo_by_id(db=db, todo_id=todo_id)

                for occurrence in todo.occurrences:
                    if occurrence.is_active:
                        TodoService._create_statuses_for_occurrence(
                            db=db,
                            occurrence=occurrence,
                            participant_ids=[assignee_id],
                        )

            db.flush()
            db.refresh(assignment)
            return assignment

    @staticmethod
    def get_pending_assignments(*, user_id: int) -> List[dict]:
        with get_db() as db:
            assignments = TodoRepository.get_assignments_for_user(
                db=db,
                user_id=user_id,
            )

            results = []

            for assignment in assignments:
                if assignment.status != AssignmentStatus.PENDING:
                    continue

                results.append(
                    {
                        "id": assignment.id,
                        "todo_id": assignment.todo_id,
                        "title": assignment.todo.title,
                        "assigned_by": assignment.assigned_by.display_name,
                    }
                )

            return results

    @staticmethod
    def delete_todo(*, todo_id: int, user_id: int) -> None:
        with get_db() as db:
            todo = TodoRepository.get_todo_by_id(db=db, todo_id=todo_id)

            if todo is None:
                raise ValueError("Task not found.")

            if todo.owner_id != user_id:
                raise ValueError("Only the task owner can delete it.")

            TodoRepository.soft_delete_todo(db=db, todo=todo)

    @staticmethod
    def assign_user(
        *,
        todo_id: int,
        assignee_id: int,
        assigned_by_id: int,
    ) -> TodoAssignment:
        with get_db() as db:
            existing = TodoRepository.get_assignment(
                db=db,
                todo_id=todo_id,
                assignee_id=assignee_id,
            )

            if existing:
                raise ValueError("User is already assigned to this todo.")

            return TodoRepository.create_assignment(
                db=db,
                assignment=TodoAssignment(
                    todo_id=todo_id,
                    assignee_id=assignee_id,
                    assigned_by_id=assigned_by_id,
                    status=AssignmentStatus.PENDING,
                ),
            )
