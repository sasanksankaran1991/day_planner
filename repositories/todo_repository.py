from datetime import date
from typing import List
from typing import Optional

from sqlalchemy.orm import joinedload

from database.models import Todo
from database.models import TodoAssignment
from database.models import TodoOccurrence
from database.models import TodoUserStatus
from utils.enums import OccurrenceStatus
from utils.enums import RecurrenceType


class TodoRepository:

    @staticmethod
    def create_todo(db, *, todo: Todo) -> Todo:
        db.add(todo)
        db.flush()
        db.refresh(todo)
        return todo

    @staticmethod
    def get_todo_by_id(db, *, todo_id: int) -> Optional[Todo]:
        return (
            db.query(Todo)
            .options(joinedload(Todo.tag))
            .filter(
                Todo.id == todo_id,
                Todo.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def create_occurrence(db, *, occurrence: TodoOccurrence) -> TodoOccurrence:
        db.add(occurrence)
        db.flush()
        db.refresh(occurrence)
        return occurrence

    @staticmethod
    def get_occurrence_by_id(db, *, occurrence_id: int) -> Optional[TodoOccurrence]:
        return (
            db.query(TodoOccurrence)
            .filter(
                TodoOccurrence.id == occurrence_id,
                TodoOccurrence.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def get_occurrences_for_todo(db, *, todo_id: int) -> List[TodoOccurrence]:
        return (
            db.query(TodoOccurrence)
            .filter(
                TodoOccurrence.todo_id == todo_id,
                TodoOccurrence.is_active.is_(True),
            )
            .order_by(TodoOccurrence.occurrence_date)
            .all()
        )

    @staticmethod
    def get_future_occurrences(
        db,
        *,
        todo_id: int,
        from_date: date,
    ) -> List[TodoOccurrence]:
        return (
            db.query(TodoOccurrence)
            .filter(
                TodoOccurrence.todo_id == todo_id,
                TodoOccurrence.occurrence_date >= from_date,
                TodoOccurrence.is_exception.is_(False),
                TodoOccurrence.is_active.is_(True),
            )
            .order_by(TodoOccurrence.occurrence_date)
            .all()
        )

    @staticmethod
    def get_occurrences_on_date(
        db,
        *,
        on_date: date,
        user_ids: List[int],
    ) -> List[TodoOccurrence]:
        return (
            db.query(TodoOccurrence)
            .options(
                joinedload(TodoOccurrence.todo).joinedload(Todo.tag),
                joinedload(TodoOccurrence.todo).joinedload(Todo.owner),
            )
            .join(Todo)
            .filter(
                TodoOccurrence.occurrence_date == on_date,
                TodoOccurrence.is_active.is_(True),
                Todo.is_active.is_(True),
            )
            .order_by(TodoOccurrence.occurrence_time)
            .all()
        )

    @staticmethod
    def get_postponed_occurrences_for_user(
        db,
        *,
        user_id: int,
        postponed_date: date,
    ) -> List[TodoOccurrence]:
        return (
            db.query(TodoOccurrence)
            .join(TodoUserStatus)
            .options(
                joinedload(TodoOccurrence.todo).joinedload(Todo.tag),
                joinedload(TodoOccurrence.todo).joinedload(Todo.owner),
            )
            .join(Todo)
            .filter(
                TodoUserStatus.user_id == user_id,
                TodoUserStatus.postponed_date == postponed_date,
                TodoUserStatus.status == OccurrenceStatus.POSTPONED,
                TodoUserStatus.is_active.is_(True),
                TodoOccurrence.is_active.is_(True),
                Todo.is_active.is_(True),
            )
            .order_by(TodoUserStatus.postponed_time)
            .all()
        )

    @staticmethod
    def create_assignment(db, *, assignment: TodoAssignment) -> TodoAssignment:
        db.add(assignment)
        db.flush()
        db.refresh(assignment)
        return assignment

    @staticmethod
    def get_assignment(
        db,
        *,
        todo_id: int,
        assignee_id: int,
    ) -> Optional[TodoAssignment]:
        return (
            db.query(TodoAssignment)
            .filter(
                TodoAssignment.todo_id == todo_id,
                TodoAssignment.assignee_id == assignee_id,
                TodoAssignment.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def get_assignments_for_user(db, *, user_id: int) -> List[TodoAssignment]:
        return (
            db.query(TodoAssignment)
            .filter(
                TodoAssignment.assignee_id == user_id,
                TodoAssignment.is_active.is_(True),
            )
            .all()
        )

    @staticmethod
    def create_user_status(db, *, status: TodoUserStatus) -> TodoUserStatus:
        db.add(status)
        db.flush()
        db.refresh(status)
        return status

    @staticmethod
    def get_user_status(
        db,
        *,
        occurrence_id: int,
        user_id: int,
    ) -> Optional[TodoUserStatus]:
        return (
            db.query(TodoUserStatus)
            .filter(
                TodoUserStatus.occurrence_id == occurrence_id,
                TodoUserStatus.user_id == user_id,
                TodoUserStatus.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def update_user_status(db, *, status: TodoUserStatus) -> TodoUserStatus:
        db.flush()
        db.refresh(status)
        return status

    @staticmethod
    def soft_delete_occurrences(db, *, occurrences: List[TodoOccurrence]) -> None:
        for occurrence in occurrences:
            occurrence.is_active = False

    @staticmethod
    def list_recurring_todos_for_owner(db, *, owner_id: int) -> List[Todo]:
        return (
            db.query(Todo)
            .options(joinedload(Todo.tag))
            .filter(
                Todo.owner_id == owner_id,
                Todo.is_active.is_(True),
                Todo.recurrence_type != RecurrenceType.ONE_TIME,
            )
            .order_by(Todo.first_date.desc(), Todo.id.desc())
            .all()
        )

    @staticmethod
    def count_active_occurrences(db, *, todo_id: int) -> int:
        return (
            db.query(TodoOccurrence)
            .filter(
                TodoOccurrence.todo_id == todo_id,
                TodoOccurrence.is_active.is_(True),
            )
            .count()
        )

    @staticmethod
    def soft_delete_todo(db, *, todo: Todo) -> None:
        todo.is_active = False

        for occurrence in todo.occurrences:
            if occurrence.is_active:
                occurrence.is_active = False
