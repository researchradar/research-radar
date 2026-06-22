from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse, urlunparse

ARXIV_ID_RE = re.compile(r"(?P<id>\d{4}\.\d{4,5})(?:v\d+)?", re.I)
YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def arxiv_id_from_url(url: str) -> str | None:
    parsed = urlparse(str(url).strip())
    host = parsed.netloc.casefold().replace("www.", "")
    if not host.endswith("arxiv.org"):
        return None
    path = parsed.path.strip("/")
    if path.startswith(("abs/", "pdf/", "html/")):
        path = path.split("/", 1)[1]
    match = ARXIV_ID_RE.search(path)
    return match.group("id") if match else None


def youtube_id_from_url(url: str) -> str | None:
    parsed = urlparse(str(url).strip())
    host = parsed.netloc.casefold().replace("www.", "")
    if host in {"youtu.be"}:
        candidate = parsed.path.strip("/").split("/")[0]
        return candidate if YOUTUBE_ID_RE.match(candidate) else None
    if host.endswith("youtube.com"):
        if parsed.path == "/watch":
            video_id = (parse_qs(parsed.query).get("v") or [""])[0]
            return video_id if YOUTUBE_ID_RE.match(video_id) else None
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] in {"shorts", "embed", "live"}:
            return parts[1] if YOUTUBE_ID_RE.match(parts[1]) else None
    return None


def normalized_url(url: str) -> str:
    parsed = urlparse(str(url).strip())
    scheme = "https" if parsed.scheme in {"http", "https"} else parsed.scheme
    netloc = parsed.netloc.casefold().replace("www.", "")
    path = parsed.path.rstrip("/")
    return urlunparse((scheme, netloc, path, "", "", ""))


def canonical_identity(url: str, *, title: str | None = None) -> str:
    """Return a stable cross-source identity for known content types.

    - arXiv abs/pdf/html URLs normalize to arxiv:<paper_id> without version.
    - YouTube watch/short/embed/live URLs normalize to youtube:<video_id>.
    - Other URLs normalize scheme/host/path and drop query/fragment.
    - Empty URLs fall back to a normalized title identity.
    """

    value = str(url or "").strip()
    if value:
        arxiv_id = arxiv_id_from_url(value)
        if arxiv_id:
            return f"arxiv:{arxiv_id}"
        youtube_id = youtube_id_from_url(value)
        if youtube_id:
            return f"youtube:{youtube_id}"
        return f"url:{normalized_url(value)}"
    return "title:" + re.sub(r"\W+", "", str(title or "").casefold())
