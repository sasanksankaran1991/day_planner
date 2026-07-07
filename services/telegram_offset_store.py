from config.settings import DATA_DIR

_OFFSET_FILES = {
    "planner": DATA_DIR / "telegram_offset_planner.txt",
    "todo": DATA_DIR / "telegram_offset_todo.txt",
}


def read_offset(bot_name: str) -> int:
    path = _OFFSET_FILES.get(bot_name)

    if path is None:
        raise ValueError(f"Unknown bot: {bot_name}")

    if not path.is_file():
        return 0

    raw = path.read_text(encoding="utf-8").strip()

    if raw.isdigit():
        return int(raw)

    return 0


def write_offset(bot_name: str, offset: int) -> None:
    path = _OFFSET_FILES.get(bot_name)

    if path is None:
        raise ValueError(f"Unknown bot: {bot_name}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(offset), encoding="utf-8")

    from services.gcs_sync import mark_db_modified

    mark_db_modified()
