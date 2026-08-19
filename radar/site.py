from __future__ import annotations

import json
from collections import defaultdict
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from .config import load_config
from .workspace import require_workspace


STYLE = """
:root { color-scheme: light dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
body { max-width: 980px; margin: 0 auto; padding: 28px 20px 60px; line-height: 1.5; }
nav { display: flex; flex-wrap: wrap; gap: 14px; margin: 18px 0 28px; }
nav a { text-decoration: none; font-weight: 600; }
.card { border: 1px solid #8885; border-radius: 12px; padding: 16px; margin: 12px 0; }
.meta { opacity: .72; font-size: .9rem; }
.score { font-weight: 700; }
.tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.tag { border: 1px solid #8885; border-radius: 999px; padding: 2px 8px; font-size: .82rem; }
.explanation { margin-top: 12px; }
.explanation summary { cursor: pointer; font-weight: 600; }
.score-breakdown { display: grid; grid-template-columns: max-content 1fr; gap: 2px 12px; margin: 8px 0; }
.score-breakdown dt { font-weight: 600; }
.score-breakdown dd { margin: 0; }
.matched-signals { margin: 8px 0 0; padding-left: 20px; }
input[type=search] { width: 100%; padding: 10px 12px; font-size: 1rem; margin: 12px 0 20px; }
pre { overflow-x: auto; padding: 14px; border: 1px solid #8885; border-radius: 10px; }
.empty { opacity: .7; font-style: italic; }
""".strip()


NAV = (
    ("Today", "index.html"),
    ("Reading", "reading.html"),
    ("Search", "search.html"),
    ("Archive", "archive.html"),
    ("Following", "following.html"),
)


def _page(title: str, body: str) -> str:
    nav = " ".join(f'<a href="{href}">{escape(label)}</a>' for label, href in NAV)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · Research Radar</title>
<style>{STYLE}</style>
</head>
<body>
<header><h1>Research Radar</h1><nav>{nav}</nav></header>
<main><h2>{escape(title)}</h2>{body}</main>
</body>
</html>
"""


def _load_ranked(workspace: Path) -> list[dict[str, Any]]:
    path = workspace / "data" / "ranked.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def _safe_href(value: Any) -> str:
    raw = str(value or "").strip()
    parsed = urlparse(raw)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        return "#"
    return escape(raw, quote=True)


def _ranking_explanation(candidate: dict[str, Any]) -> str:
    raw_breakdown = candidate.get("score_breakdown", {})
    breakdown = raw_breakdown if isinstance(raw_breakdown, dict) else {}
    breakdown_rows = "".join(
        f"<dt>{escape(str(name).replace('_', ' ').title())}</dt>"
        f"<dd>{escape(str(value))}</dd>"
        for name, value in breakdown.items()
    )
    if not breakdown_rows:
        breakdown_rows = "<dt>Score</dt><dd>No breakdown available</dd>"

    signal_fields = (
        ("People", "matched_people"),
        ("Institutions", "matched_institutions"),
        ("Topics", "matched_topics"),
        ("Questions", "matched_questions"),
    )
    signal_rows = []
    for label, field in signal_fields:
        raw_values = candidate.get(field, [])
        if not isinstance(raw_values, list) or not raw_values:
            continue
        values = ", ".join(escape(str(value)) for value in raw_values)
        signal_rows.append(f"<li><strong>{label}:</strong> {values}</li>")
    signals = (
        f'<ul class="matched-signals">{"".join(signal_rows)}</ul>'
        if signal_rows
        else '<p class="meta">No named signals matched.</p>'
    )

    return f"""<details class="explanation">
<summary>Why this ranked</summary>
<dl class="score-breakdown">{breakdown_rows}</dl>
{signals}
</details>"""


def _card(candidate: dict[str, Any]) -> str:
    item = candidate.get("item", {})
    raw_title = str(item.get("title") or "Untitled")
    raw_source = str(item.get("source") or "Unknown source")
    raw_summary = str(item.get("raw_text") or "")[:600]
    title = escape(raw_title)
    url = _safe_href(item.get("canonical_url"))
    source = escape(raw_source)
    published = escape(str(item.get("published_at") or "Unknown date"))
    score = escape(str(candidate.get("score", 0)))
    summary = escape(raw_summary)
    labels = [*candidate.get("matched_people", []), *candidate.get("matched_topics", [])]
    tags = "".join(f'<span class="tag">{escape(str(label))}</span>' for label in labels)
    explanation = _ranking_explanation(candidate)
    search_text = escape(
        (raw_title + " " + raw_source + " " + raw_summary).casefold(),
        quote=True,
    )
    return f"""<article class="card" data-search="{search_text}">
<h3><a href="{url}" rel="noreferrer">{title}</a></h3>
<div class="meta"><span class="score">Score {score}</span> · {source} · {published}</div>
<p>{summary}</p>
<div class="tags">{tags}</div>
{explanation}
</article>"""


def _cards(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<p class="empty">No items yet. Run <code>research-radar collect</code> first.</p>'
    return "\n".join(_card(item) for item in items)


def _search_page(items: list[dict[str, Any]]) -> str:
    cards = _cards(items)
    script = """
<script>
const box = document.querySelector('#search');
const cards = [...document.querySelectorAll('.card')];
box.addEventListener('input', () => {
  const query = box.value.trim().toLowerCase();
  for (const card of cards) {
    card.hidden = query && !card.dataset.search.includes(query);
  }
});
</script>
"""
    return (
        '<input id="search" type="search" placeholder="Search collected items" autocomplete="off">'
        + cards
        + script
    )


def _archive_page(items: list[dict[str, Any]]) -> str:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in items:
        published = str(candidate.get("item", {}).get("published_at") or "Unknown date")
        groups[published[:10] if len(published) >= 10 else published].append(candidate)
    if not groups:
        return '<p class="empty">No archived items yet.</p>'
    sections = []
    for day in sorted(groups, reverse=True):
        sections.append(f"<h3>{escape(day)}</h3>{_cards(groups[day])}")
    return "\n".join(sections)


def _following_page(workspace: Path) -> str:
    config = load_config(workspace / "config")
    public_view = {
        "people": config.get("people", {}),
        "topics": config.get("topics", {}),
        "sources": config.get("sources", {}),
        "scoring": config.get("scoring", {}),
    }
    rendered = yaml.safe_dump(public_view, sort_keys=False, allow_unicode=False)
    return (
        "<p>Edit these files in your private workspace to change what the radar follows.</p>"
        + f"<pre>{escape(rendered)}</pre>"
    )


def build_site(workspace_value: str | Path) -> Path:
    workspace = require_workspace(workspace_value)
    site_dir = workspace / "site"
    site_dir.mkdir(parents=True, exist_ok=True)
    ranked = _load_ranked(workspace)

    pages = {
        "index.html": _page("Today", _cards(ranked[:50])),
        "reading.html": _page("Reading", _cards(ranked)),
        "search.html": _page("Search", _search_page(ranked)),
        "archive.html": _page("Archive", _archive_page(ranked)),
        "following.html": _page("Following", _following_page(workspace)),
    }
    for name, content in pages.items():
        (site_dir / name).write_text(content, encoding="utf-8")
    return site_dir
