import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import tomli_w

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib  # type: ignore[no-redef]
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

DEFAULT_JOURNAL_DIR = Path("~/.journal").expanduser()
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_CONTEXT_ENTRIES = 20


@dataclass
class Config:
    journal_dir: Path
    entries_dir: Path
    api_key: str | None
    editor: str
    model: str
    context_entries: int
    no_ai: bool


def load_config(journal_dir: Path | None = None, no_ai: bool = False) -> Config:
    base_dir = (journal_dir or DEFAULT_JOURNAL_DIR).expanduser().resolve()
    config_path = base_dir / "config.toml"

    data: dict = {}
    if config_path.exists():
        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to parse {config_path}: {e}") from e

    raw_key = (
        data.get("api_key")
        or data.get("ANTHROPIC_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or ""
    )
    api_key = raw_key.strip() or None

    editor = (
        data.get("editor")
        or os.environ.get("VISUAL")
        or os.environ.get("EDITOR")
        or ""
    )

    model = data.get("model", DEFAULT_MODEL)
    context_entries = int(data.get("context_entries", DEFAULT_CONTEXT_ENTRIES))

    config = Config(
        journal_dir=base_dir,
        entries_dir=base_dir / "entries",
        api_key=api_key,
        editor=editor,
        model=model,
        context_entries=context_entries,
        no_ai=no_ai or not bool(api_key),
    )

    _ensure_dirs(config)
    return config


def save_config(config: Config) -> None:
    config_path = config.journal_dir / "config.toml"
    data = {
        "model": config.model,
        "context_entries": config.context_entries,
        "editor": config.editor,
    }
    if config.api_key:
        data["api_key"] = config.api_key
    with open(config_path, "wb") as f:
        tomli_w.dump(data, f)


def _ensure_dirs(config: Config) -> None:
    try:
        config.journal_dir.mkdir(parents=True, exist_ok=True)
        config.entries_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        raise RuntimeError(
            f"Cannot create journal directory at {config.journal_dir}: {e}"
        ) from e
