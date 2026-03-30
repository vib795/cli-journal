import random
import string
from datetime import datetime, timedelta
from pathlib import Path

import frontmatter

from journal.config import Config


class EntryNotFoundError(Exception):
    pass


def generate_entry_id() -> str:
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=3))
    return f"{timestamp}-{suffix}"


def entry_path(config: Config, entry_id: str) -> Path:
    return config.entries_dir / f"{entry_id}.md"


def _find_entry_path(config: Config, entry_id: str) -> Path:
    """Return the path for an entry ID, with fuzzy prefix matching."""
    exact = config.entries_dir / f"{entry_id}.md"
    if exact.exists():
        return exact

    # Fuzzy prefix match
    matches = sorted(config.entries_dir.glob(f"{entry_id}*.md"))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        ids = ", ".join(p.stem for p in matches)
        raise EntryNotFoundError(
            f"Ambiguous ID '{entry_id}' — matches: {ids}"
        )
    raise EntryNotFoundError(f"Entry '{entry_id}' not found.")


def create_entry(
    config: Config,
    body: str,
    tags: list[str] | None = None,
) -> frontmatter.Post:
    entry_id = generate_entry_id()
    now = datetime.now()
    post = frontmatter.Post(
        body.strip(),
        id=entry_id,
        date=now.strftime("%Y-%m-%d %H:%M:%S"),
        tags=tags or [],
        mood="",
        word_count=len(body.split()),
    )
    path = entry_path(config, entry_id)
    with open(path, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))
    return post


def read_entry(config: Config, entry_id: str) -> frontmatter.Post:
    path = _find_entry_path(config, entry_id)
    with open(path, encoding="utf-8") as f:
        return frontmatter.load(f)


def update_entry(
    config: Config,
    entry_id: str,
    body: str | None = None,
    metadata_updates: dict | None = None,
) -> frontmatter.Post:
    path = _find_entry_path(config, entry_id)
    with open(path, encoding="utf-8") as f:
        post = frontmatter.load(f)

    if body is not None:
        post.content = body.strip()
        post["word_count"] = len(body.split())

    if metadata_updates:
        for key, value in metadata_updates.items():
            post[key] = value

    with open(path, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))
    return post


def delete_entry(config: Config, entry_id: str) -> None:
    path = _find_entry_path(config, entry_id)
    path.unlink()


def list_entries(
    config: Config,
    date_filter: str | None = None,
    tag_filter: str | None = None,
    limit: int | None = None,
    since: datetime | None = None,
) -> list[frontmatter.Post]:
    all_paths = sorted(config.entries_dir.glob("*.md"), reverse=True)
    posts = []
    for path in all_paths:
        stem = path.stem
        if date_filter and not stem.startswith(date_filter):
            continue
        with open(path, encoding="utf-8") as f:
            post = frontmatter.load(f)
        if tag_filter:
            entry_tags = [t.lower() for t in (post.get("tags") or [])]
            if tag_filter.lower() not in entry_tags:
                continue
        if since:
            try:
                entry_date = datetime.strptime(post["date"], "%Y-%m-%d %H:%M:%S")
                if entry_date < since:
                    continue
            except (KeyError, ValueError):
                pass
        posts.append(post)
        if limit and len(posts) >= limit:
            break
    return posts


def search_entries(config: Config, query: str) -> list[frontmatter.Post]:
    q = query.lower()
    results = []
    for path in sorted(config.entries_dir.glob("*.md"), reverse=True):
        with open(path, encoding="utf-8") as f:
            post = frontmatter.load(f)
        body = post.content.lower()
        tags = " ".join(post.get("tags") or []).lower()
        if q in body or q in tags:
            results.append(post)
    return results


def count_entries(config: Config) -> int:
    return len(list(config.entries_dir.glob("*.md")))


def get_latest_entry(config: Config) -> frontmatter.Post | None:
    paths = sorted(config.entries_dir.glob("*.md"), reverse=True)
    if not paths:
        return None
    with open(paths[0], encoding="utf-8") as f:
        return frontmatter.load(f)
