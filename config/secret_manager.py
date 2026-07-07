import logging
import os
from functools import lru_cache
from typing import Dict
from typing import Tuple

logger = logging.getLogger(__name__)

# (env var for secret id override, default secret id in GSM)
SECRET_DEFINITIONS: Dict[str, Tuple[str, str]] = {
    "TELEGRAM_BOT_TOKEN": (
        "SECRET_ID_TELEGRAM_BOT_TOKEN",
        "day-planner-telegram-bot-token",
    ),
    "TELEGRAM_BOT_USERNAME": (
        "SECRET_ID_TELEGRAM_BOT_USERNAME",
        "day-planner-telegram-bot-username",
    ),
    "TODO_TELEGRAM_BOT_TOKEN": (
        "SECRET_ID_TODO_TELEGRAM_BOT_TOKEN",
        "day-planner-todo-telegram-bot-token",
    ),
    "TODO_TELEGRAM_BOT_USERNAME": (
        "SECRET_ID_TODO_TELEGRAM_BOT_USERNAME",
        "day-planner-todo-telegram-bot-username",
    ),
    "SCHEDULER_SECRET": (
        "SECRET_ID_SCHEDULER_SECRET",
        "day-planner-scheduler-secret",
    ),
}


def _use_secret_manager() -> bool:
    explicit = os.getenv("USE_SECRET_MANAGER", "").strip().lower()

    if explicit in ("0", "false", "no", "off"):
        return False

    if explicit in ("1", "true", "yes", "on"):
        return True

    # Local Mac/Windows: use .env even if gcloud is installed.
    # GCP: Cloud Run sets K_SERVICE (service) or CLOUD_RUN_JOB (jobs).
    return bool(os.getenv("K_SERVICE") or os.getenv("CLOUD_RUN_JOB"))


def _resolve_project_id() -> str:
    return (
        os.getenv("GCP_PROJECT_ID", "").strip()
        or os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
        or os.getenv("GCLOUD_PROJECT", "").strip()
    )


@lru_cache(maxsize=1)
def _secret_manager_client():
    from google.cloud import secretmanager

    return secretmanager.SecretManagerServiceClient()


@lru_cache(maxsize=None)
def _fetch_secret_from_gcp(*, secret_id: str) -> str:
    project_id = _resolve_project_id()

    if not project_id:
        raise RuntimeError(
            "GCP_PROJECT_ID (or GOOGLE_CLOUD_PROJECT) is required when "
            "USE_SECRET_MANAGER=true."
        )

    client = _secret_manager_client()
    resource_name = (
        f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    )
    response = client.access_secret_version(request={"name": resource_name})
    value = response.payload.data.decode("UTF-8").strip()

    if not value:
        raise ValueError(f"Secret '{secret_id}' is empty.")

    return value


def get_secret(env_key: str, *, default: str = "") -> str:
    env_value = os.getenv(env_key, default).strip()
    definition = SECRET_DEFINITIONS.get(env_key)

    if definition is None:
        return env_value

    secret_id_env, default_secret_id = definition
    secret_id = os.getenv(secret_id_env, default_secret_id).strip()

    if not _use_secret_manager():
        return env_value

    try:
        return _fetch_secret_from_gcp(secret_id=secret_id)
    except Exception as error:
        allow_env_fallback = os.getenv("SECRET_ENV_OVERRIDE", "").lower() == "true"

        if allow_env_fallback and env_value:
            logger.warning(
                "Secret Manager lookup failed for %s (%s); using env value.",
                env_key,
                error,
            )
            return env_value

        raise RuntimeError(
            f"Failed to load '{env_key}' from Secret Manager "
            f"(secret id: {secret_id})."
        ) from error


def secret_manager_status() -> str:
    if _use_secret_manager():
        return f"enabled (project={_resolve_project_id() or 'unknown'})"

    return "disabled (using .env)"
