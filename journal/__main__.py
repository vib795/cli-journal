import sys
from pathlib import Path

import click

from journal import __version__
from journal.config import load_config
from journal.display import print_error


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "-v", "--version", prog_name="journal")
@click.option(
    "--journal-dir",
    default=None,
    envvar="JOURNAL_DIR",
    help="Override the journal directory (default: ~/.journal).",
    type=click.Path(),
)
@click.option(
    "--no-ai",
    is_flag=True,
    default=False,
    help="Disable AI features even if ANTHROPIC_API_KEY is set.",
)
def main(journal_dir: str | None, no_ai: bool) -> None:
    """An interactive CLI journaling tool."""
    journal_path = Path(journal_dir).expanduser() if journal_dir else None

    try:
        config = load_config(journal_dir=journal_path, no_ai=no_ai)
    except Exception as e:
        print_error(f"Failed to load config: {e}")
        sys.exit(1)

    # Import here to avoid circular imports at module level
    from journal.repl import run_repl

    run_repl(config)


if __name__ == "__main__":
    main()
