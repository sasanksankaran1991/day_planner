import logging
import time

import httpx

from config.settings import JOBS_SERVICE_URL
from config.settings import SCHEDULER_POLL_SECONDS
from config.settings import SCHEDULER_SECRET

logger = logging.getLogger(__name__)


def run_forever() -> None:
    if not SCHEDULER_SECRET:
        raise RuntimeError(
            "SCHEDULER_SECRET is required for the local scheduler runner."
        )

    headers = {"X-Scheduler-Secret": SCHEDULER_SECRET}
    tick_url = f"{JOBS_SERVICE_URL.rstrip('/')}/jobs/tick"

    logger.info(
        "Local scheduler calling %s every %s seconds",
        tick_url,
        SCHEDULER_POLL_SECONDS,
    )

    while True:
        try:
            response = httpx.post(tick_url, headers=headers, timeout=120)
            response.raise_for_status()
            logger.debug("Tick response: %s", response.json())

        except Exception:
            logger.exception("Scheduler tick failed")

        time.sleep(SCHEDULER_POLL_SECONDS)


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    run_forever()


if __name__ == "__main__":
    main()
