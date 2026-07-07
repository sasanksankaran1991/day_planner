import sqlite3

from config.settings import DB_PATH


def _get_columns(connection, table_name: str) -> list:
    return [
        row[1]
        for row in connection.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    ]


def _migrate_remove_plan_scope(connection) -> None:
    columns = _get_columns(connection, "day_plans")

    if "plan_scope" not in columns:
        return

    connection.execute("PRAGMA foreign_keys=OFF")

    connection.execute(
        """
        CREATE TABLE day_plans_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_date DATE NOT NULL,
            daily_note TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            UNIQUE (user_id, plan_date),
            FOREIGN KEY(user_id) REFERENCES users (id)
        )
        """
    )

    connection.execute(
        """
        INSERT INTO day_plans_new (
            id, user_id, plan_date, daily_note, created_at, is_active
        )
        SELECT id, user_id, plan_date, daily_note, created_at, is_active
        FROM day_plans
        """
    )

    connection.execute("DROP TABLE day_plans")
    connection.execute("ALTER TABLE day_plans_new RENAME TO day_plans")
    connection.commit()
    connection.execute("PRAGMA foreign_keys=ON")


def _migrate_telegram_fields(connection) -> None:
    columns = _get_columns(connection, "users")

    if "telegram_link_code" not in columns:
        connection.execute(
            "ALTER TABLE users ADD COLUMN telegram_link_code VARCHAR(20)"
        )

    if "telegram_link_expires_at" not in columns:
        connection.execute(
            "ALTER TABLE users ADD COLUMN telegram_link_expires_at DATETIME"
        )

    tables = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]

    if "telegram_notifications" not in tables:
        connection.execute(
            """
            CREATE TABLE telegram_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_date DATE NOT NULL,
                block_id INTEGER NOT NULL,
                notification_type VARCHAR(50) NOT NULL DEFAULT 'BLOCK_START',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                UNIQUE (user_id, plan_date, block_id, notification_type),
                FOREIGN KEY(user_id) REFERENCES users (id),
                FOREIGN KEY(block_id) REFERENCES time_blocks (id)
            )
            """
        )

    connection.commit()


def _migrate_planner_tags(connection) -> None:
    tables = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]

    if "planner_tags" not in tables:
        connection.execute(
            """
            CREATE TABLE planner_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name VARCHAR(50) NOT NULL,
                color VARCHAR(7) NOT NULL DEFAULT '#1E88E5',
                require_on_create BOOLEAN NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                UNIQUE (user_id, name),
                FOREIGN KEY(user_id) REFERENCES users (id)
            )
            """
        )

    if "tag_id" not in _get_columns(connection, "time_blocks"):
        connection.execute(
            "ALTER TABLE time_blocks ADD COLUMN tag_id INTEGER "
            "REFERENCES planner_tags (id)"
        )

    if "tag_id" not in _get_columns(connection, "todos"):
        connection.execute(
            "ALTER TABLE todos ADD COLUMN tag_id INTEGER "
            "REFERENCES planner_tags (id)"
        )

    connection.commit()


def _migrate_todo_telegram(connection) -> None:
    columns = _get_columns(connection, "users")

    if "todo_telegram_chat_id" not in columns:
        connection.execute(
            "ALTER TABLE users ADD COLUMN todo_telegram_chat_id VARCHAR(50)"
        )

    if "todo_telegram_link_code" not in columns:
        connection.execute(
            "ALTER TABLE users ADD COLUMN todo_telegram_link_code VARCHAR(20)"
        )

    if "todo_telegram_link_expires_at" not in columns:
        connection.execute(
            "ALTER TABLE users ADD COLUMN todo_telegram_link_expires_at DATETIME"
        )

    tables = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]

    if "todo_telegram_notifications" not in tables:
        connection.execute(
            """
            CREATE TABLE todo_telegram_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_date DATE NOT NULL,
                occurrence_id INTEGER NOT NULL,
                notification_type VARCHAR(50) NOT NULL DEFAULT 'TASK_REMINDER',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                UNIQUE (user_id, plan_date, occurrence_id, notification_type),
                FOREIGN KEY(user_id) REFERENCES users (id),
                FOREIGN KEY(occurrence_id) REFERENCES todo_occurrences (id)
            )
            """
        )

    connection.commit()


def migrate_database() -> None:
    if not DB_PATH.exists():
        return

    connection = sqlite3.connect(DB_PATH)

    try:
        _migrate_remove_plan_scope(connection)
        _migrate_telegram_fields(connection)
        _migrate_planner_tags(connection)
        _migrate_todo_telegram(connection)
    finally:
        connection.close()
