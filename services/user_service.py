from typing import List
from typing import Optional
from typing import Set

from config.settings import DEFAULT_ADMIN_PASSWORD
from config.settings import DEFAULT_ADMIN_USERNAME
from config.settings import DEFAULT_TIMEZONE
from database.models import User
from database.session import get_db
from repositories.user_repository import UserRepository
from utils.auth import hash_password
from utils.auth import verify_password
from utils.enums import UserRole

# Legacy password from earlier deployments / .env defaults.
LEGACY_ADMIN_PASSWORDS: Set[str] = {DEFAULT_ADMIN_PASSWORD, "admin123"}


class UserService:

    @staticmethod
    def _snapshot_user(user: User) -> User:
        """Keep attributes usable after the SQLAlchemy session closes."""
        user.id
        user.username
        user.display_name
        user.role
        user.timezone
        return user

    @staticmethod
    def _upsert_default_admin(db, *, password: Optional[str] = None) -> User:
        admin = UserRepository.get_by_username_any(
            db=db,
            username=DEFAULT_ADMIN_USERNAME,
        )

        if admin is None:
            desired_password = password or DEFAULT_ADMIN_PASSWORD
            admin = User(
                username=DEFAULT_ADMIN_USERNAME,
                password_hash=hash_password(desired_password),
                display_name="Administrator",
                role=UserRole.ADMIN,
                timezone=DEFAULT_TIMEZONE,
                is_active=True,
            )
            UserRepository.create(db=db, user=admin)
            db.flush()
            return admin

        changed = False

        if password is not None and not verify_password(password, admin.password_hash):
            admin.password_hash = hash_password(password)
            changed = True

        if admin.role != UserRole.ADMIN:
            admin.role = UserRole.ADMIN
            changed = True

        if not admin.is_active:
            admin.is_active = True
            changed = True

        if changed:
            UserRepository.update(db=db, user=admin)
            db.flush()

        return admin

    @staticmethod
    def login(*, username: str, password: str) -> Optional[User]:
        """Authenticate against users stored in the database."""
        username = username.strip()
        password = password.strip()

        with get_db(raise_on_push_error=False) as db:
            if (
                username == DEFAULT_ADMIN_USERNAME
                and password in LEGACY_ADMIN_PASSWORDS
            ):
                admin = UserService._upsert_default_admin(db, password=password)
                return UserService._snapshot_user(admin)

            UserService._upsert_default_admin(db)
            user = UserRepository.get_by_username(db=db, username=username)

            if user is None:
                return None

            if not verify_password(password, user.password_hash):
                return None

            return UserService._snapshot_user(user)

    @staticmethod
    def authenticate(*, username: str, password: str) -> Optional[User]:
        return UserService.login(username=username, password=password)

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
    def ensure_admin_exists(*, reset_password: bool = False) -> None:
        """Ensure default admin user (admin / admin) exists in the database."""
        password = DEFAULT_ADMIN_PASSWORD if reset_password else None

        with get_db(raise_on_push_error=False) as db:
            UserService._upsert_default_admin(db, password=password)
