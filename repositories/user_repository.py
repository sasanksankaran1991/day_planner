from typing import List
from typing import Optional

from database.models import User


class UserRepository:

    @staticmethod
    def create(db, *, user: User) -> User:
        db.add(user)
        db.flush()
        db.refresh(user)
        return user

    @staticmethod
    def get_by_id(db, *, user_id: int) -> Optional[User]:
        return (
            db.query(User)
            .filter(
                User.id == user_id,
                User.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def get_by_username(db, *, username: str) -> Optional[User]:
        return (
            db.query(User)
            .filter(
                User.username == username,
                User.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def get_by_username_any(db, *, username: str) -> Optional[User]:
        return (
            db.query(User)
            .filter(User.username == username)
            .first()
        )

    @staticmethod
    def list_all(db) -> List[User]:
        return (
            db.query(User)
            .filter(User.is_active.is_(True))
            .order_by(User.username)
            .all()
        )

    @staticmethod
    def update(db, *, user: User) -> User:
        db.flush()
        db.refresh(user)
        return user

    @staticmethod
    def get_by_telegram_chat_id(db, *, chat_id: str) -> Optional[User]:
        return (
            db.query(User)
            .filter(
                User.telegram_chat_id == chat_id,
                User.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def get_by_link_code(db, *, link_code: str) -> Optional[User]:
        return (
            db.query(User)
            .filter(
                User.telegram_link_code == link_code,
                User.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def list_with_telegram(db) -> List[User]:
        return (
            db.query(User)
            .filter(
                User.telegram_chat_id.isnot(None),
                User.telegram_chat_id != "",
                User.is_active.is_(True),
            )
            .all()
        )

    @staticmethod
    def get_by_todo_telegram_chat_id(db, *, chat_id: str) -> Optional[User]:
        return (
            db.query(User)
            .filter(
                User.todo_telegram_chat_id == chat_id,
                User.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def get_by_todo_link_code(db, *, link_code: str) -> Optional[User]:
        return (
            db.query(User)
            .filter(
                User.todo_telegram_link_code == link_code,
                User.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def list_with_todo_telegram(db) -> List[User]:
        return (
            db.query(User)
            .filter(
                User.todo_telegram_chat_id.isnot(None),
                User.todo_telegram_chat_id != "",
                User.is_active.is_(True),
            )
            .all()
        )
