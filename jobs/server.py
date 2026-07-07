import logging

from flask import Flask
from flask import jsonify

from database.init_db import initialize_database
from database.migrate import migrate_database
from jobs.auth import require_scheduler_auth
from jobs.planner import execute_block_starts_sync
from jobs.planner import execute_day_summaries_sync
from jobs.todo import execute_morning_notifications_sync
from jobs.todo import execute_task_end_notifications_sync
from jobs.todo import execute_task_reminders_sync
from services.user_service import UserService

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    bootstrap_database()
    app = Flask(__name__)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/jobs/planner/block-starts")
    @require_scheduler_auth
    def planner_block_starts():
        result = execute_block_starts_sync()
        return jsonify({"ok": True, **result})

    @app.post("/jobs/planner/day-summaries")
    @require_scheduler_auth
    def planner_day_summaries():
        result = execute_day_summaries_sync()
        return jsonify({"ok": True, **result})

    @app.post("/jobs/todo/morning")
    @require_scheduler_auth
    def todo_morning():
        result = execute_morning_notifications_sync()
        return jsonify({"ok": True, **result})

    @app.post("/jobs/todo/reminders")
    @require_scheduler_auth
    def todo_reminders():
        result = execute_task_reminders_sync()
        return jsonify({"ok": True, **result})

    @app.post("/jobs/todo/task-end")
    @require_scheduler_auth
    def todo_task_end():
        result = execute_task_end_notifications_sync()
        return jsonify({"ok": True, **result})

    @app.post("/jobs/tick")
    @require_scheduler_auth
    def tick_all():
        """Run every notification job (useful for local 5s polling)."""
        results = [
            execute_block_starts_sync(),
            execute_day_summaries_sync(),
            execute_morning_notifications_sync(),
            execute_task_reminders_sync(),
            execute_task_end_notifications_sync(),
        ]
        return jsonify({"ok": True, "results": results})

    return app


def bootstrap_database() -> None:
    migrate_database()
    initialize_database()
    UserService.ensure_admin_exists()


app = create_app()


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    from config.settings import PORT

    logger.info("Jobs server listening on port %s", PORT)
    app.run(host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
