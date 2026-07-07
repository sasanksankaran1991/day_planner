import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.init_db import initialize_database
from database.migrate import migrate_database
from services.user_service import UserService


def main():
    migrate_database()
    initialize_database()
    UserService.ensure_admin_exists()
    print("Database initialized. Default admin user is ready.")


if __name__ == "__main__":
    main()
