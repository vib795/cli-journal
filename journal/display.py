from __future__ import annotations

import getpass
from datetime import datetime
from typing import Iterator

import frontmatter
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from journal import __version__
from journal.config import Config

console = Console()

# Color palette
ACCENT   = "#E08050"          # Claude Code-style orange
C_INFO   = "bold #5B8DB8"
C_SUCCESS = "bold green"
C_WARNING = "bold #D4A017"
C_ERROR  = "bold red"
C_META   = "dim cyan"
C_AI_LABEL = "bold #5B8DB8"
C_BORDER = ACCENT
C_DIM    = "dim white"

# Pixel-art robot (orange, similar to Claude Code mascot)
_ROBOT = [
    "   ┌───────┐   ",
    "   │  ■  ■  │   ",
    "   ├───────┤   ",
    "   │  ▄▄▄  │   ",
    "   └──┘ └──┘   ",
]


def print_banner(
    config: Config,
    entry_count: int,
    recent_posts: list[frontmatter.Post] | None = None,
) -> None:
    recent_posts = recent_posts or []
    username = getpass.getuser().capitalize()
    today = datetime.now().strftime("%A, %B %-d, %Y")

    # ── Left column: greeting, robot, stats ─────────────
    left = Text()
    left.append("\n")
    left.append(f"  Welcome back, {username}!\n\n", style="bold white")
    for line in _ROBOT:
        left.append(line + "\n", style=ACCENT)
    left.append("\n")
    left.append(f"  {config.model}", style="dim white")
    left.append("  ·  ", style="dim")
    noun = "entry" if entry_count == 1 else "entries"
    left.append(f"{entry_count} {noun}\n", style="dim white")
    left.append(f"  {today}\n", style="dim white")
    if config.no_ai:
        left.append("\n  AI disabled (no API key)\n", style=f"bold {C_WARNING[5:]}")
    else:
        left.append(f"\n  AI enabled\n", style="dim #90B870")

    # ── Right column: tips + recent entries ─────────────
    right = Text()
    right.append("\n")
    right.append("  Quick start\n", style=f"bold {ACCENT}")
    right.append("  /new", style="bold white")
    right.append("   — write a new entry\n", style="dim white")
    right.append("  /list", style="bold white")
    right.append("  — browse past entries\n", style="dim white")
    right.append("  /chat", style="bold white")
    right.append("  — ask Claude about your journal\n", style="dim white")
    right.append("  /help", style="bold white")
    right.append("  — see all commands\n\n", style="dim white")

    right.append("  Recent entries\n", style=f"bold {ACCENT}")
    if recent_posts:
        for post in recent_posts[:3]:
            date = str(post.get("date", ""))[:10]
            raw = post.content.replace("\n", " ").strip()
            preview = raw[:38] + ("…" if len(raw) > 38 else "")
            right.append("  › ", style=ACCENT)
            right.append(f"{date}  ", style="dim white")
            right.append(f"{preview}\n", style="dim white")
    else:
        right.append("  No entries yet — start writing!\n", style="dim white")

    # ── Two-column grid ──────────────────────────────────
    layout = Table.grid(expand=True)
    layout.add_column(ratio=1)
    layout.add_column(width=1)
    layout.add_column(ratio=1)
    layout.add_row(left, Text("│", style="dim"), right)

    console.print(
        Panel(
            layout,
            title=f"[{ACCENT}]journal[/{ACCENT}] [dim]v{__version__}[/dim]",
            title_align="left",
            box=box.ROUNDED,
            border_style=ACCENT,
            padding=(0, 1),
        )
    )
    console.print(
        f"  [dim]✦  Start typing to save a quick entry, or use [bold]/help[/bold] to see all commands.[/dim]"
    )
    console.print()


def print_entry(post: frontmatter.Post, show_body: bool = True) -> None:
    entry_id = post.get("id", "unknown")
    date = post.get("date", "")
    tags = post.get("tags") or []
    mood = post.get("mood", "")
    word_count = post.get("word_count", 0)

    meta_parts = [f"[{C_META}]{date}[/{C_META}]"]
    if mood:
        meta_parts.append(f"[{C_META}]mood: {mood}[/{C_META}]")
    if tags:
        tag_str = "  ".join(f"#{t}" for t in tags)
        meta_parts.append(f"[{C_META}]{tag_str}[/{C_META}]")
    meta_parts.append(f"[dim]{word_count}w[/dim]")
    meta_line = "  [dim]·[/dim]  ".join(meta_parts)

    if show_body and post.content:
        body_render: object = Markdown(post.content)
    else:
        body_render = f"[{C_DIM}](empty)[/{C_DIM}]"

    console.print(
        Panel(
            body_render,  # type: ignore[arg-type]
            title=f"[{C_META}]{entry_id}[/{C_META}]",
            subtitle=meta_line,
            box=box.ROUNDED,
            border_style=C_BORDER,
            padding=(0, 1),
        )
    )


def print_entry_list(posts: list[frontmatter.Post]) -> None:
    if not posts:
        print_info("No entries found.")
        return

    table = Table(box=box.SIMPLE, show_header=True, header_style=C_INFO, expand=False)
    table.add_column("ID", style=C_META, no_wrap=True)
    table.add_column("Date", style="dim white", no_wrap=True)
    table.add_column("Mood", style="dim white")
    table.add_column("Tags", style="dim white")
    table.add_column("Words", style="dim white", justify="right")
    table.add_column("Preview", style="dim white")

    for post in posts:
        entry_id = post.get("id", "?")
        date = str(post.get("date", ""))[:16]
        mood = post.get("mood", "") or ""
        tags = "  ".join(f"#{t}" for t in (post.get("tags") or []))
        words = str(post.get("word_count", 0))
        preview = post.content.replace("\n", " ")[:60].strip()
        if len(post.content) > 60:
            preview += "…"
        table.add_row(entry_id, date, mood, tags, words, preview)

    console.print(table)


def print_help_table() -> None:
    table = Table(
        box=box.SIMPLE,
        show_header=True,
        header_style=C_INFO,
        title="[bold]Available Commands[/bold]",
        title_style=C_INFO,
        expand=False,
    )
    table.add_column("Command", style="bold white", no_wrap=True)
    table.add_column("Args", style=C_META)
    table.add_column("Description", style="dim white")

    rows = [
        ("/new", "", "Create a new entry (opens $EDITOR or inline input)"),
        ("/edit", "<id>", "Edit an existing entry in $EDITOR"),
        ("/list", "[--date DATE] [--tag TAG]", "List entries (optionally filtered)"),
        ("/search", "<query>", "Full-text search across all entries"),
        ("/delete", "<id>", "Delete an entry (asks for confirmation)"),
        ("/tag", "<id> <tag> [tag...]", "Add tags to an entry"),
        ("/chat", "<question>", "Ask Claude about your journal"),
        ("/reflect", "[week|month]", "Generate an AI reflection/summary"),
        ("/mood", "[id]", "Auto-tag mood on an entry (defaults to latest)"),
        ("/help", "", "Show this help"),
        ("/exit", "", "Quit journal"),
        ("(free text)", "", "Save a quick inline journal entry"),
    ]

    for cmd, args, desc in rows:
        table.add_row(cmd, args, desc)

    console.print()
    console.print(table)
    console.print()


def print_success(msg: str) -> None:
    console.print(f"[{C_SUCCESS}]✓[/{C_SUCCESS}] {msg}")


def print_error(msg: str) -> None:
    console.print(f"[{C_ERROR}]✗ {msg}[/{C_ERROR}]")


def print_info(msg: str) -> None:
    console.print(f"[{C_INFO}]{msg}[/{C_INFO}]")


def print_warning(msg: str) -> None:
    console.print(f"[{C_WARNING}]⚠ {msg}[/{C_WARNING}]")


def stream_ai_response(stream_iterator: Iterator[str]) -> str:
    """Print streaming tokens directly (no Live — avoids conflict with prompt_toolkit)."""
    console.print()
    console.print(f"[{C_AI_LABEL}]assistant[/{C_AI_LABEL}] ", end="")
    full_text: list[str] = []
    for chunk in stream_iterator:
        console.print(chunk, end="", highlight=False, markup=False)
        full_text.append(chunk)
    console.print()
    console.print()
    return "".join(full_text)
