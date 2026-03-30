from __future__ import annotations

from typing import Iterator

import frontmatter

from journal.config import Config

MAX_CONTEXT_CHARS = 240_000  # ~60k tokens at 4 chars/token

SYSTEM_PROMPT_CHAT = """\
You are a thoughtful journaling assistant. \
You have access to the user's journal entries provided below. \
Answer questions about their writing with warmth, insight, and brevity. \
Reference specific entries when relevant. \
Do not fabricate entries or feelings not present in the text.\
"""

SYSTEM_PROMPT_REFLECT = """\
You are a reflective journaling coach. \
You have access to the user's journal entries for a specific period. \
Identify emotional patterns, recurring themes, notable progress, and areas of growth. \
Be warm, honest, and constructive. \
Structure your response with clear Markdown sections (## headings). \
Keep the total response under 400 words.\
"""

SYSTEM_PROMPT_MOOD = """\
Analyze the emotional tone of this journal entry. \
Respond with exactly ONE word describing the primary mood or emotion. \
Examples: focused, anxious, content, excited, melancholy, grateful, frustrated, calm, hopeful, tired.\
"""


class AINotConfiguredError(Exception):
    pass


def _get_client(config: Config):
    if config.no_ai or not config.api_key:
        raise AINotConfiguredError(
            "AI features require ANTHROPIC_API_KEY. "
            "Set it in ~/.journal/config.toml or as an environment variable."
        )
    import anthropic
    return anthropic.Anthropic(api_key=config.api_key)


def build_context_messages(posts: list[frontmatter.Post]) -> str:
    """Format entries as a compact string for the AI context."""
    lines: list[str] = []
    total_chars = 0
    for post in posts:
        entry_id = post.get("id", "?")
        date = post.get("date", "")
        mood = post.get("mood", "") or ""
        tags = ", ".join(post.get("tags") or [])
        header = f"--- [ID: {entry_id}] [date: {date}]"
        if mood:
            header += f" [mood: {mood}]"
        if tags:
            header += f" [tags: {tags}]"
        entry_text = f"{header}\n{post.content}\n"
        if total_chars + len(entry_text) > MAX_CONTEXT_CHARS:
            lines.append("--- [Additional older entries omitted due to context limits] ---")
            break
        lines.append(entry_text)
        total_chars += len(entry_text)
    return "\n".join(lines)


def stream_chat(
    config: Config,
    question: str,
    context_posts: list[frontmatter.Post],
) -> Iterator[str]:
    client = _get_client(config)
    context = build_context_messages(context_posts)
    user_content = f"Journal entries:\n\n{context}\n\n---\n\nQuestion: {question}"

    with client.messages.stream(
        model=config.model,
        max_tokens=2048,
        system=SYSTEM_PROMPT_CHAT,
        messages=[{"role": "user", "content": user_content}],
    ) as stream:
        for text in stream.text_stream:
            yield text


def stream_reflection(
    config: Config,
    period: str,
    posts: list[frontmatter.Post],
) -> Iterator[str]:
    client = _get_client(config)
    context = build_context_messages(posts)
    period_label = "past week" if period == "week" else "past month"
    user_content = (
        f"Please reflect on my journal entries from the {period_label}:\n\n{context}"
    )

    with client.messages.stream(
        model=config.model,
        max_tokens=1024,
        system=SYSTEM_PROMPT_REFLECT,
        messages=[{"role": "user", "content": user_content}],
    ) as stream:
        for text in stream.text_stream:
            yield text


def classify_mood(config: Config, entry_body: str) -> str:
    client = _get_client(config)
    response = client.messages.create(
        model=config.model,
        max_tokens=10,
        system=SYSTEM_PROMPT_MOOD,
        messages=[{"role": "user", "content": entry_body}],
    )
    raw = response.content[0].text.strip().lower()
    # Take only the first word and strip punctuation
    word = raw.split()[0].rstrip(".,!?;:") if raw else "neutral"
    return word
