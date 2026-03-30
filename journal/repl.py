from __future__ import annotations

import re
import shlex

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory, InMemoryHistory

from journal import commands, display, storage
from journal.ai import AINotConfiguredError
from journal.config import Config
from journal.storage import EntryNotFoundError

COMMAND_NAMES = [
    "/new",
    "/edit",
    "/list",
    "/search",
    "/delete",
    "/tag",
    "/chat",
    "/reflect",
    "/mood",
    "/help",
    "/exit",
    "/quit",
]


def _build_session(config: Config) -> PromptSession:
    history_path = config.journal_dir / ".repl_history"
    try:
        history = FileHistory(str(history_path))
    except Exception:
        history = InMemoryHistory()

    completer = WordCompleter(
        COMMAND_NAMES,
        pattern=re.compile(r"^(/\w*)"),
        sentence=True,
    )

    return PromptSession(
        history=history,
        completer=completer,
        complete_while_typing=True,
    )


def _get_prompt() -> HTML:
    return HTML("<ansibrightgreen><b>&gt; </b></ansibrightgreen>")


def parse_and_dispatch(config: Config, session: PromptSession, raw: str) -> bool:
    """Dispatch a raw input line. Returns False to exit the REPL."""
    text = raw.strip()
    if not text:
        return True

    if text in ("/exit", "/quit", "/q"):
        return False

    if text.startswith("/"):
        try:
            parts = shlex.split(text)
        except ValueError as e:
            display.print_error(f"Parse error: {e}")
            return True

        cmd = parts[0].lower()
        args = parts[1:]

        try:
            _dispatch(config, session, cmd, args)
        except EntryNotFoundError as e:
            display.print_error(str(e))
        except AINotConfiguredError as e:
            display.print_warning(str(e))
        except Exception as e:
            display.print_error(f"Unexpected error: {e}")
    else:
        # Free text → quick entry
        try:
            commands.cmd_quick_entry(config, text)
        except Exception as e:
            display.print_error(f"Unexpected error: {e}")

    return True


def _dispatch(config: Config, session: PromptSession, cmd: str, args: list[str]) -> None:
    if cmd == "/new":
        commands.cmd_new(config, session)
    elif cmd == "/edit":
        if not args:
            display.print_error("Usage: /edit <id>")
            return
        commands.cmd_edit(config, session, args[0])
    elif cmd == "/list":
        commands.cmd_list(config, args)
    elif cmd == "/search":
        commands.cmd_search(config, " ".join(args))
    elif cmd == "/delete":
        if not args:
            display.print_error("Usage: /delete <id>")
            return
        commands.cmd_delete(config, session, args[0])
    elif cmd == "/tag":
        if len(args) < 2:
            display.print_error("Usage: /tag <id> <tag> [tag...]")
            return
        commands.cmd_tag(config, args[0], args[1:])
    elif cmd == "/chat":
        commands.cmd_chat(config, " ".join(args))
    elif cmd == "/reflect":
        commands.cmd_reflect(config, args)
    elif cmd == "/mood":
        commands.cmd_mood(config, args)
    elif cmd == "/help":
        display.print_help_table()
    else:
        display.print_error(f"Unknown command: {cmd}  (type /help for a list)")


def run_repl(config: Config) -> None:
    entry_count = storage.count_entries(config)
    recent_posts = storage.list_entries(config, limit=3)
    display.print_banner(config, entry_count, recent_posts)
    session = _build_session(config)

    while True:
        try:
            raw = session.prompt(_get_prompt())
        except KeyboardInterrupt:
            # Ctrl+C clears the line, keeps the REPL running
            continue
        except EOFError:
            # Ctrl+D exits
            display.print_info("\nGoodbye.")
            break

        should_continue = parse_and_dispatch(config, session, raw)
        if not should_continue:
            display.print_info("Goodbye.")
            break
