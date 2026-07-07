from functools import wraps

from flask import abort
from flask import request

from config.settings import SCHEDULER_SECRET


def require_scheduler_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not SCHEDULER_SECRET:
            abort(
                503,
                description=(
                    "SCHEDULER_SECRET is not configured on the jobs service."
                ),
            )

        provided = request.headers.get("X-Scheduler-Secret", "")

        if provided != SCHEDULER_SECRET:
            abort(401, description="Invalid scheduler credentials.")

        return view(*args, **kwargs)

    return wrapped
