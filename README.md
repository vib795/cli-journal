# journal

An interactive CLI journaling tool inspired by the look and feel of Claude Code. Write, search, and reflect on journal entries without leaving the terminal — with optional AI-powered insights via the Anthropic API.

```
╭──────────────────────────────────────────────────────────────────────────────╮
│                                                                              │
│  journal  v0.1.0                                                             │
│  42 entries  ·  Monday, March 30, 2026                                       │
│  AI enabled (claude-sonnet-4-6)                                              │
│                                                                              │
│  Type /help for commands, or start typing to create a quick entry.           │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯

>
```

---

## Features

- **Interactive REPL** — persistent session with slash commands, command history, and tab completion
- **Markdown entries** — each entry is a plain `.md` file with YAML frontmatter (portable, git-friendly)
- **Tags & metadata** — tag entries, track mood, word count, and timestamps
- **Full-text search** — search across all entry bodies and tags
- **Editor integration** — opens `$EDITOR` (vim, nano, VS Code, etc.) for writing; falls back to inline input
- **AI chat** — ask Claude questions about your journal ("what was I stressed about last month?")
- **AI reflection** — generate weekly or monthly summaries with patterns and insights
- **Mood tagging** — automatically classify the emotional tone of any entry

---

## Requirements

- Python 3.9+
- An [Anthropic API key](https://console.anthropic.com/) (optional — required only for AI features)

---

## Installation

```bash
# Clone the repo
git clone <repo-url>
cd cli-journal

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install
pip install -e .
```

Then run:

```bash
journal
```

---

## Configuration

On first launch, `journal` creates `~/.journal/` automatically. To configure it, create or edit `~/.journal/config.toml`:

```toml
# Anthropic API key (required for AI features)
# Can also be set via the ANTHROPIC_API_KEY environment variable
ANTHROPIC_API_KEY = "sk-ant-..."

# Claude model to use (default: claude-sonnet-4-6)
model = "claude-sonnet-4-6"

# Preferred editor (default: $EDITOR or $VISUAL env var)
editor = "vim"

# Number of recent entries sent as context for AI commands (default: 20)
context_entries = 20
```

All config values can also be set via environment variables:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `JOURNAL_DIR` | Override the journal directory (default: `~/.journal`) |
| `EDITOR` | Fallback editor if not set in config |
| `VISUAL` | Fallback editor (checked before `$EDITOR`) |

---

## Usage

Launch the interactive REPL:

```bash
journal
```

With options:

```bash
journal --journal-dir ~/work-journal   # use a different directory
journal --no-ai                        # disable AI features
journal --version
```

Once inside the REPL, use slash commands or just start typing:

```
> Today was a productive day. Shipped the auth refactor and finally fixed that
  annoying race condition in the test suite.
✓ Quick entry saved: 2026-03-30T09-14-22-a3f
```

---

## Commands

| Command | Args | Description |
|---|---|---|
| `/new` | | Open `$EDITOR` to write a new entry (falls back to inline input if no editor is set) |
| `/edit` | `<id>` | Reopen an existing entry in `$EDITOR` |
| `/list` | `[--date DATE] [--tag TAG]` | List entries, optionally filtered |
| `/search` | `<query>` | Full-text search across all entries |
| `/delete` | `<id>` | Delete an entry (prompts for confirmation) |
| `/tag` | `<id> <tag> [tag...]` | Add one or more tags to an entry |
| `/chat` | `<question>` | Ask Claude a question about your journal |
| `/reflect` | `[week\|month]` | Generate an AI-written reflection for the past week or month |
| `/mood` | `[id]` | Auto-classify and tag the mood of an entry (defaults to the latest entry) |
| `/help` | | Show the command reference |
| `/exit` | | Quit |
| *(free text)* | | Anything that doesn't start with `/` is saved as a quick inline entry |

### Entry IDs

Entry IDs are timestamp-based (e.g. `2026-03-30T09-14-22-a3f`). You can use a prefix with any command that takes an `<id>` — as long as it's unambiguous:

```
> /edit 2026-03-30       # works if only one entry that day
> /mood 2026-03          # works if only one match in March
```

### `/list` filters

```
> /list                          # all entries, newest first
> /list --date 2026-03           # entries from March 2026
> /list --date 2026-03-30        # entries from a specific day
> /list --tag work               # entries tagged "work"
> /list --date 2026-03 --tag focus
```

### `/search`

Full-text search across entry bodies and tags (case-insensitive):

```
> /search race condition
> /search anxiety
```

### AI commands

All AI commands require `ANTHROPIC_API_KEY` to be set. Responses stream token-by-token in real time.

**`/chat`** — ask anything about your journal. Claude has access to your most recent entries as context:

```
> /chat what topics keep coming up in my writing?
> /chat when did I last feel really energized at work?
> /chat summarize what I've been working on this week
```

**`/reflect`** — generates a structured reflection with themes, emotional patterns, and notable moments:

```
> /reflect week
> /reflect month
```

**`/mood`** — uses Claude to classify the emotional tone of an entry and writes it to the entry's frontmatter:

```
> /mood                           # tags the most recent entry
> /mood 2026-03-28T14-30-00-x9k  # tags a specific entry
```

---

## Storage format

Entries are stored as Markdown files in `~/.journal/entries/`, one file per entry:

```
~/.journal/
├── config.toml
├── .repl_history
└── entries/
    ├── 2026-03-30T09-14-22-a3f.md
    ├── 2026-03-29T21-05-11-b2m.md
    └── ...
```

Each file uses YAML frontmatter:

```markdown
---
id: 2026-03-30T09-14-22-a3f
date: 2026-03-30 09:14:22
tags:
- work
- shipping
mood: accomplished
word_count: 34
---

Today was a productive day. Shipped the auth refactor and finally fixed that
annoying race condition in the test suite.
```

Because entries are plain Markdown files, you can:
- Read and edit them with any text editor
- Track them in git (`git init ~/.journal`)
- Sync them with any file sync service (iCloud, Dropbox, etc.)
- Search them with `grep` or `ripgrep`

---

## Keyboard shortcuts

| Key | Action |
|---|---|
| `Tab` | Autocomplete slash commands |
| `↑` / `↓` | Navigate command history |
| `Ctrl+C` | Clear the current line (stays in REPL) |
| `Ctrl+D` | Exit journal |
| `Esc` then `Enter` | Submit a multiline inline entry |

---

## Project structure

```
cli-journal/
├── pyproject.toml
└── journal/
    ├── __init__.py      # version constant
    ├── __main__.py      # CLI entry point (click)
    ├── config.py        # Config dataclass, load/save config.toml
    ├── storage.py       # Markdown file CRUD, search, list
    ├── display.py       # rich terminal rendering
    ├── ai.py            # Anthropic API: chat, reflection, mood
    ├── commands.py      # slash command handler functions
    └── repl.py          # prompt_toolkit REPL loop and dispatch
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `rich` | Terminal rendering — panels, tables, Markdown, spinners |
| `prompt_toolkit` | Interactive REPL — history, tab completion, multiline input |
| `anthropic` | Claude API client with streaming support |
| `python-frontmatter` | Parse and write Markdown with YAML frontmatter |
| `click` | CLI argument parsing (`--version`, `--journal-dir`, etc.) |
| `tomli` / `tomli-w` | TOML config file reading and writing (Python < 3.11) |
