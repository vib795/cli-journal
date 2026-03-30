from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from datetime import datetime, timedelta

import frontmatter
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML

from journal import ai, display, storage
from journal.ai import AINotConfiguredError
from journal.config import Config
from journal.display import console
from journal.storage import EntryNotFoundError


def cmd_new(config: Config, session: PromptSession, inline_text: str | None = None) -> None:
    if inline_text:
        body = inline_text.strip()
    else:
        body = _open_in_editor(config) or _prompt_inline()
        if not body:
            display.print_info("Entry cancelled.")
            return

    post = storage.create_entry(config, body)
    display.print_success(f"Entry saved: {post['id']}")
    display.print_entry(post, show_body=False)


def cmd_edit(config: Config, session: PromptSession, entry_id: str) -> None:
    try:
        post = storage.read_entry(config, entry_id)
    except EntryNotFoundError as e:
        display.print_error(str(e))
        return

    new_body = _open_in_editor(config, initial_content=post.content) or _prompt_inline()
    if not new_body:
        display.print_info("Edit cancelled.")
        return

    storage.update_entry(config, post["id"], body=new_body)
    display.print_success(f"Entry updated: {post['id']}")


def cmd_list(config: Config, args: list[str]) -> None:
    date_filter, tag_filter = _parse_list_args(args)
    posts = storage.list_entries(config, date_filter=date_filter, tag_filter=tag_filter)
    display.print_entry_list(posts)


def cmd_search(config: Config, query: str) -> None:
    if not query.strip():
        display.print_error("Usage: /search <query>")
        return
    posts = storage.search_entries(config, query)
    if posts:
        display.print_info(f"Found {len(posts)} {'entry' if len(posts) == 1 else 'entries'} matching '{query}':")
    display.print_entry_list(posts)


def cmd_delete(config: Config, session: PromptSession, entry_id: str) -> None:
    try:
        post = storage.read_entry(config, entry_id)
    except EntryNotFoundError as e:
        display.print_error(str(e))
        return

    display.print_entry(post, show_body=False)
    try:
        confirm = session.prompt(
            HTML("<ansired><b>Delete this entry? [y/N] </b></ansired>")
        )
    except (KeyboardInterrupt, EOFError):
        display.print_info("Delete cancelled.")
        return

    if confirm.strip().lower() == "y":
        storage.delete_entry(config, post["id"])
        display.print_success(f"Entry {post['id']} deleted.")
    else:
        display.print_info("Delete cancelled.")


def cmd_tag(config: Config, entry_id: str, new_tags: list[str]) -> None:
    if not new_tags:
        display.print_error("Usage: /tag <id> <tag> [tag...]")
        return
    try:
        post = storage.read_entry(config, entry_id)
    except EntryNotFoundError as e:
        display.print_error(str(e))
        return

    existing = list(post.get("tags") or [])
    merged = list(dict.fromkeys(existing + [t.lower() for t in new_tags]))
    storage.update_entry(config, post["id"], metadata_updates={"tags": merged})
    display.print_success(f"Tags updated: {', '.join(merged)}")


def cmd_chat(config: Config, question: str) -> None:
    if not question.strip():
        display.print_error("Usage: /chat <question>")
        return
    try:
        posts = storage.list_entries(config, limit=config.context_entries)
        stream_gen = ai.stream_chat(config, question, posts)
        with console.status(
            "[bold #5B8DB8]Thinking…[/bold #5B8DB8]", spinner="dots"
        ):
            first_chunk = next(stream_gen, None)
        if first_chunk is None:
            display.print_error("No response from AI.")
            return

        def _prepend(first: str, rest):
            yield first
            yield from rest

        display.stream_ai_response(_prepend(first_chunk, stream_gen))
    except AINotConfiguredError as e:
        display.print_warning(str(e))


def cmd_reflect(config: Config, args: list[str]) -> None:
    period = args[0].lower() if args else "week"
    if period not in ("week", "month"):
        display.print_error("Usage: /reflect [week|month]")
        return

    days = 7 if period == "week" else 30
    since = datetime.now() - timedelta(days=days)
    try:
        posts = storage.list_entries(config, since=since)
        if not posts:
            display.print_info(f"No entries in the past {period} to reflect on.")
            return
        display.print_info(
            f"Reflecting on {len(posts)} {'entry' if len(posts) == 1 else 'entries'} "
            f"from the past {period}…"
        )
        stream_gen = ai.stream_reflection(config, period, posts)
        with console.status(
            "[bold #5B8DB8]Reflecting…[/bold #5B8DB8]", spinner="dots"
        ):
            first_chunk = next(stream_gen, None)
        if first_chunk is None:
            display.print_error("No response from AI.")
            return

        def _prepend(first: str, rest):
            yield first
            yield from rest

        display.stream_ai_response(_prepend(first_chunk, stream_gen))
    except AINotConfiguredError as e:
        display.print_warning(str(e))


def cmd_mood(config: Config, args: list[str]) -> None:
    entry_id = args[0] if args else None
    try:
        if entry_id:
            post = storage.read_entry(config, entry_id)
        else:
            post = storage.get_latest_entry(config)
            if not post:
                display.print_info("No entries found.")
                return
        if not post.content.strip():
            display.print_error("Entry has no content to analyze.")
            return
        with console.status(
            "[bold #5B8DB8]Analyzing mood…[/bold #5B8DB8]", spinner="dots"
        ):
            mood = ai.classify_mood(config, post.content)
        storage.update_entry(config, post["id"], metadata_updates={"mood": mood})
        display.print_success(f"Mood tagged as: [bold]{mood}[/bold]")
    except EntryNotFoundError as e:
        display.print_error(str(e))
    except AINotConfiguredError as e:
        display.print_warning(str(e))


def cmd_quick_entry(config: Config, text: str) -> None:
    body = text.strip()
    if not body:
        return
    post = storage.create_entry(config, body)
    display.print_success(f"Quick entry saved: {post['id']}")


# ── helpers ──────────────────────────────────────────────────────────────────

def _open_in_editor(config: Config, initial_content: str = "") -> str | None:
    editor = config.editor or os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if not editor:
        return None
    with tempfile.NamedTemporaryFile(
        suffix=".md", mode="w", delete=False, prefix="journal_", encoding="utf-8"
    ) as f:
        if initial_content:
            f.write(initial_content)
        tmppath = f.name
    try:
        result = subprocess.run(
            f"{editor} {shlex.quote(tmppath)}", shell=True
        )
        if result.returncode != 0:
            return None
        with open(tmppath, encoding="utf-8") as f:
            content = f.read().strip()
        return content or None
    finally:
        try:
            os.unlink(tmppath)
        except OSError:
            pass


def _prompt_inline() -> str | None:
    # Use a fresh PromptSession — reusing the main REPL session with multiline=True
    # permanently mutates session.multiline, breaking Enter for all future prompts.
    from prompt_toolkit import PromptSession as _PS
    display.print_info("Enter your entry below. Press [Esc] then [Enter] to finish, or Ctrl+C to cancel.")
    try:
        text = _PS().prompt(
            HTML("<ansibrightgreen><b>  </b></ansibrightgreen>"),
            multiline=True,
        )
        return text.strip() or None
    except (KeyboardInterrupt, EOFError):
        return None


def _parse_list_args(args: list[str]) -> tuple[str | None, str | None]:
    date_filter = tag_filter = None
    it = iter(args)
    for tok in it:
        if tok == "--date":
            date_filter = next(it, None)
        elif tok == "--tag":
            tag_filter = next(it, None)
    return date_filter, tag_filter
