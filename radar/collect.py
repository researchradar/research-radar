from __future__ import annotations

import html
import ipaddress
import json
import re
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse

import feedparser
import requests

from .config import load_config
from .identity import canonical_identity
from .models import RawItem
from .ranking import rank
from .workspace import require_workspace


USER_AGENT = "ResearchRadar/0.1 (+https://github.com/researchradar/research-radar)"
MAX_REDIRECTS = 3
MAX_RESPONSE_BYTES = 5 * 1024 * 1024


@dataclass
class CollectionResult:
    collected: int
    ranked: int
    errors: list[str]
    items_path: Path
    ranked_path: Path


def _unsafe_ip(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        )
    )


def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http:// and https:// source URLs are allowed")
    if not parsed.hostname:
        raise ValueError("Source URL must include a hostname")
    if parsed.username or parsed.password:
        raise ValueError("Source URLs with embedded credentials are not allowed")
    host = parsed.hostname.rstrip(".").casefold()
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("Loopback source URLs are not allowed")

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None and _unsafe_ip(str(literal)):
        raise ValueError(
            "Private, loopback, link-local, reserved, or multicast source IPs are not allowed"
        )

    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve source hostname: {host}") from exc
    for address in addresses:
        candidate = address[4][0]
        try:
            unsafe = _unsafe_ip(candidate)
        except ValueError:
            continue
        if unsafe:
            raise ValueError(
                "Source hostname resolves to a private, loopback, link-local, reserved, or multicast address"
            )


def _read_bounded_response(
    response: requests.Response,
    *,
    max_bytes: int = MAX_RESPONSE_BYTES,
) -> None:
    content_length = response.headers.get("Content-Length")
    if content_length:
        try:
            declared = int(content_length)
        except ValueError:
            declared = None
        if declared is not None and declared > max_bytes:
            response.close()
            raise ValueError(
                f"Response is too large ({declared} bytes; limit is {max_bytes} bytes)"
            )

    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        total += len(chunk)
        if total > max_bytes:
            response.close()
            raise ValueError(f"Response exceeded the {max_bytes}-byte size limit")
        chunks.append(chunk)
    response._content = b"".join(chunks)
    response._content_consumed = True


def safe_get(
    url: str,
    *,
    timeout: tuple[float, float] = (5.0, 15.0),
    max_bytes: int = MAX_RESPONSE_BYTES,
) -> requests.Response:
    current = url
    with requests.Session() as session:
        # Do not inherit proxy or netrc credentials when fetching user-configured sources.
        session.trust_env = False
        session.headers.update({"User-Agent": USER_AGENT})
        for _ in range(MAX_REDIRECTS + 1):
            validate_public_url(current)
            response = session.get(
                current,
                timeout=timeout,
                allow_redirects=False,
                stream=True,
            )
            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise ValueError("Redirect response did not include a Location header")
                current = urljoin(current, location)
                continue
            response.raise_for_status()
            _read_bounded_response(response, max_bytes=max_bytes)
            return response
    raise ValueError(f"Too many redirects while fetching {url}")


def _plain_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _entry_link(entry: Any) -> str:
    link = str(getattr(entry, "link", "") or "").strip()
    if link:
        return link
    return str(getattr(entry, "id", "") or "").strip()


def _authors(entry: Any) -> list[str]:
    values = []
    for author in getattr(entry, "authors", []) or []:
        name = str(getattr(author, "name", "") or author.get("name", "")).strip()
        if name:
            values.append(name)
    if not values:
        name = str(getattr(entry, "author", "") or "").strip()
        if name:
            values.append(name)
    return values


def _published(entry: Any) -> str | None:
    return str(
        getattr(entry, "published", "")
        or getattr(entry, "updated", "")
        or ""
    ).strip() or None


def _item_from_entry(
    entry: Any,
    *,
    source_name: str,
    source_type: str,
    priority: float = 1.0,
) -> RawItem | None:
    url = _entry_link(entry)
    title = _plain_text(str(getattr(entry, "title", "") or ""))
    if not title or not url:
        return None
    summary = _plain_text(
        str(getattr(entry, "summary", "") or getattr(entry, "description", "") or "")
    )
    identity = canonical_identity(url, title=title)
    return RawItem(
        id=identity,
        canonical_url=url,
        title=title,
        source=source_name,
        source_type=source_type,
        published_at=_published(entry),
        authors_or_guests=_authors(entry),
        raw_text=summary,
        metadata={"source_priority": float(priority)},
    )


def collect_arxiv(source: dict[str, Any]) -> list[RawItem]:
    query = str(source.get("query", "")).strip()
    if not query:
        raise ValueError("arXiv source requires a non-empty 'query'")
    max_results = max(1, min(int(source.get("max_results", 25)), 100))
    params = urlencode(
        {
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": max_results,
        }
    )
    response = safe_get(
        f"https://export.arxiv.org/api/query?{params}",
        timeout=(5.0, 20.0),
    )
    feed = feedparser.loads(response.content)
    name = str(source.get("name") or "arXiv")
    priority = float(source.get("priority", 1.0))
    items = [
        _item_from_entry(entry, source_name=name, source_type="paper", priority=priority)
        for entry in feed.entries
    ]
    return [item for item in items if item is not None]


def collect_rss(source: dict[str, Any]) -> list[RawItem]:
    url = str(source.get("url", "")).strip()
    if not url:
        raise ValueError("RSS source requires a non-empty 'url'")
    response = safe_get(url)
    feed = feedparser.loads(response.content)
    name = str(source.get("name") or feed.feed.get("title") or urlparse(url).hostname or "RSS")
    priority = float(source.get("priority", 1.0))
    items = [
        _item_from_entry(entry, source_name=name, source_type="rss", priority=priority)
        for entry in feed.entries
    ]
    return [item for item in items if item is not None]


def synthetic_items() -> list[RawItem]:
    now = datetime.now(timezone.utc).isoformat()
    payloads = [
        (
            "Synthetic VLA Benchmark",
            "https://example.org/research/synthetic-vla-benchmark",
            "A synthetic benchmark for vision-language-action research and robot manipulation.",
            ["Example Researcher"],
        ),
        (
            "Research Automation for Literature Triage",
            "https://example.org/research/literature-triage",
            "A synthetic article about literature search, research automation, and information retrieval.",
            [],
        ),
        (
            "World Models for Robot Manipulation",
            "https://example.org/research/world-models",
            "A synthetic paper about world models and robot manipulation.",
            ["Sample Author"],
        ),
    ]
    items: list[RawItem] = []
    for title, url, text, authors in payloads:
        items.append(
            RawItem(
                id=canonical_identity(url, title=title),
                canonical_url=url,
                title=title,
                source="Synthetic Fixtures",
                source_type="paper",
                published_at=now,
                authors_or_guests=authors,
                raw_text=text,
                metadata={"source_priority": 1.0, "fixture": True},
            )
        )
    return items


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def collect_workspace(
    workspace_value: str | Path,
    *,
    offline: bool = False,
    fixture_set: str | None = None,
) -> CollectionResult:
    workspace = require_workspace(workspace_value)
    config = load_config(workspace / "config")
    errors: list[str] = []

    if fixture_set:
        if fixture_set != "synthetic":
            raise ValueError(f"Unknown fixture set: {fixture_set}")
        items = synthetic_items()
    else:
        if offline:
            raise ValueError("--offline requires --fixture-set synthetic")
        items: list[RawItem] = []
        for source in config["sources"].get("sources", []):
            if not source.get("enabled", True):
                continue
            source_type = str(source.get("type", "")).casefold()
            try:
                if source_type == "arxiv":
                    items.extend(collect_arxiv(source))
                elif source_type == "rss":
                    items.extend(collect_rss(source))
                else:
                    errors.append(f"Unsupported source type: {source_type or '<missing>'}")
            except (requests.RequestException, ValueError) as exc:
                errors.append(f"{source.get('name') or source_type}: {exc}")

    ranked = rank(items, config)
    data_dir = workspace / "data"
    items_path = data_dir / "items.json"
    ranked_path = data_dir / "ranked.json"
    _write_json(items_path, [item.as_dict() for item in items])
    _write_json(ranked_path, [candidate.as_dict() for candidate in ranked])
    _write_json(
        data_dir / "last-run.json",
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "collected": len(items),
            "ranked": len(ranked),
            "errors": errors,
            "offline": offline,
            "fixture_set": fixture_set,
        },
    )
    return CollectionResult(len(items), len(ranked), errors, items_path, ranked_path)
