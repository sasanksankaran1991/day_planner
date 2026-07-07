from typing import List
from typing import Optional

from config.settings import ADMIN_PASSWORD
from config.settings import ADMIN_USERNAME
from config.settings import DEFAULT_TIMEZONE
from database.models import User
from database.session import get_db
from repositories.user_repository import UserRepository
from utils.auth import hash_password
from utils.auth import verify_password
from utils.enums import UserRole


class UserService:

    @staticmethod
    def authenticate(*, username: str, password: str) -> Optional[User]:
        with get_db() as db:
            user = UserRepository.get_by_username(db=db, username=username)

            if user is None:
                return None

            if not verify_password(password, user.password_hash):
                return None

            return user

    @staticmethod
    def create_user(
        *,
        username: str,
        password: str,
        display_name: str,
        role: UserRole = UserRole.USER,
        timezone: str = DEFAULT_TIMEZONE,
    ) -> User:
        with get_db() as db:
            existing = UserRepository.get_by_username(db=db, username=username)

            if existing:
                raise ValueError(f"Username '{username}' already exists.")

            user = User(
                username=username,
                password_hash=hash_password(password),
                display_name=display_name,
                role=role,
                timezone=timezone,
            )

            return UserRepository.create(db=db, user=user)

    @staticmethod
    def list_users() -> List[User]:
        with get_db() as db:
            return UserRepository.list_all(db=db)

    @staticmethod
    def update_timezone(*, user_id: int, timezone: str) -> User:
        with get_db() as db:
            user = UserRepository.get_by_id(db=db, user_id=user_id)

            if user is None:
                raise ValueError("User not found.")

            user.timezone = timezone
            return UserRepository.update(db=db, user=user)

    @staticmethod
    def get_by_id(*, user_id: int) -> Optional[User]:
        with get_db() as db:
            return UserRepository.get_by_id(db=db, user_id=user_id)

    @staticmethod
    def clear_telegram_link(*, user_id: int) -> None:
        with get_db() as db:
            user = UserRepository.get_by_id(db=db, user_id=user_id)

            if user is None:
                raise ValueError("User not found.")

            user.telegram_chat_id = None
            user.telegram_link_code = None
            user.telegram_link_expires_at = None
            UserRepository.update(db=db, user=user)

    @staticmethod
    def clear_todo_telegram_link(*, user_id: int) -> None:
        with get_db() as db:
            user = UserRepository.get_by_id(db=db, user_id=user_id)

            if user is None:
                raise ValueError("User not found.")

            user.todo_telegram_chat_id = None
            user.todo_telegram_link_code = None
            user.todo_telegram_link_expires_at = None
            UserRepository.update(db=db, user=user)

    @staticmethod
    def change_password(
        *,
        user_id: int,
        current_password: str,
        new_password: str,
    ) -> None:
        if len(new_password) < 6:
            raise ValueError("New password must be at least 6 characters.")

        with get_db() as db:
            user = UserRepository.get_by_id(db=db, user_id=user_id)

            if user is None:
                raise ValueError("User not found.")

            if not verify_password(current_password, user.password_hash):
                raise ValueError("Current password is incorrect.")

            user.password_hash = hash_password(new_password)
            UserRepository.update(db=db, user=user)

    @staticmethod
    def ensure_admin_exists() -> None:
        """Create admin from Secret Manager, or sync password only if it changed."""
        with get_db() as db:
            admin = UserRepository.get_by_username(db=db, username=ADMIN_USERNAME)

            if admin is None:
                admin = User(
                    username=ADMIN_USERNAME,
                    password_hash=hash_password(ADMIN_PASSWORD),
                    display_name="Administrator",
                    role=UserRole.ADMIN,
                    timezone=DEFAULT_TIMEZONE,
                )
                UserRepository.create(db=db, user=admin)
                return

            if not verify_password(ADMIN_PASSWORD, admin.password_hash):
                admin.password_hash = hash_password(ADMIN_PASSWORD)
                admin.role = UserRole.ADMIN
                admin.is_active = True
                UserRepository.update(db=db, user=admin)
