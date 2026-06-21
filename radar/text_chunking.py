from __future__ import annotations

import re
from collections.abc import Iterable


def clean_transcript_text(text: str) -> str:
    """Normalize transcript text while preserving sentence boundaries."""
    text = text.replace("\ufeff", " ").replace("\u200b", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def excerpt(text: str, max_chars: int = 3000) -> str:
    text = clean_transcript_text(text)
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    # Prefer ending on a sentence/paragraph boundary rather than mid-word.
    boundary = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "), cut.rfind("\n"))
    if boundary > max_chars * 0.6:
        cut = cut[: boundary + 1]
    return cut.rstrip() + "…"


def split_text(text: str, max_chars: int = 6000) -> list[str]:
    text = clean_transcript_text(text)
    if not text:
        return []
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            for i in range(0, len(paragraph), max_chars):
                chunks.append(paragraph[i : i + max_chars].strip())
            continue
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current.strip())
            current = paragraph
    if current:
        chunks.append(current.strip())
    return chunks


_ASCII_KEYWORD_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .+/&'-]*$")


def keyword_matcher(keyword: str) -> re.Pattern[str] | None:
    """Compile a keyword into a matcher that avoids garbage substring hits.

    ASCII keywords get a leading word boundary so ``robot`` still matches ``robots`` but ``PI``
    no longer matches inside ``PowerPoint``. Keywords of one or two characters (``PI``, ``AI``,
    ``RL``) require a trailing boundary too, since they are otherwise pure noise. CJK keywords
    have no word boundaries, so they fall back to a plain substring search.
    """
    keyword = keyword.strip()
    if not keyword:
        return None
    if _ASCII_KEYWORD_RE.match(keyword):
        suffix = r"\b" if len(keyword) <= 2 else ""
        return re.compile(rf"\b{re.escape(keyword)}{suffix}", re.IGNORECASE)
    return re.compile(re.escape(keyword), re.IGNORECASE)


def _compile_keywords(keywords: Iterable[str]) -> list[tuple[str, re.Pattern[str]]]:
    compiled: list[tuple[str, re.Pattern[str]]] = []
    for keyword in keywords:
        pattern = keyword_matcher(keyword)
        if pattern is not None:
            compiled.append((keyword.strip(), pattern))
    return compiled


def format_timestamp(seconds: float) -> str:
    """Render a segment start time as M:SS or H:MM:SS for quotable evidence."""
    total = max(0, int(round(float(seconds or 0))))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def evidence_quotes(
    segments: Iterable[dict],
    keywords: Iterable[str],
    max_snippets: int = 8,
    context: int = 2,
) -> list[dict]:
    """Pull keyword-anchored original-language quotes with timestamps from ASR/subtitle segments.

    Unlike ``evidence_snippets`` (which slices raw text and loses time anchors), this keeps
    each quote tied to the segment ``start`` so a report can cite ``"…"[12:34]`` verbatim.
    """
    seg_list = [seg for seg in segments if isinstance(seg, dict) and str(seg.get("text", "")).strip()]
    if not seg_list:
        return []
    compiled = _compile_keywords(keywords)
    if not compiled:
        return []

    # Score each segment by how many distinct keywords it hits. Ranking by density (rather than
    # document order) keeps sponsor reads and intros — which match 0–1 keywords — from crowding
    # out the substantive, on-topic moments deeper in an interview.
    candidates: list[tuple[int, int, str]] = []
    for index, seg in enumerate(seg_list):
        seg_text = str(seg.get("text", ""))
        hits = [keyword for keyword, pattern in compiled if pattern.search(seg_text)]
        if hits:
            candidates.append((len(hits), index, hits[0]))
    candidates.sort(key=lambda candidate: (-candidate[0], candidate[1]))

    quotes: list[dict] = []
    used_spans: list[tuple[int, int]] = []
    for _, index, matched in candidates:
        left = max(0, index - context)
        right = min(len(seg_list), index + context + 1)
        # Skip a hit whose context window overlaps a quote we already kept.
        if any(not (right <= span_left or left >= span_right) for span_left, span_right in used_spans):
            continue
        quote_text = clean_transcript_text(" ".join(str(seg_list[i].get("text", "")).strip() for i in range(left, right)))
        if not quote_text:
            continue
        start = float(seg_list[index].get("start", 0) or 0)
        quotes.append({"timestamp": format_timestamp(start), "start": round(start, 2), "keyword": matched, "text": quote_text})
        used_spans.append((left, right))
        if len(quotes) >= max_snippets:
            break
    quotes.sort(key=lambda quote: quote["start"])
    return quotes


def evidence_snippets(text: str, keywords: Iterable[str], max_snippets: int = 8, window: int = 320) -> list[str]:
    normalized = clean_transcript_text(text)
    snippets: list[str] = []
    seen_spans: list[tuple[int, int]] = []
    for _, pattern in _compile_keywords(keywords):
        for match in pattern.finditer(normalized):
            if len(snippets) >= max_snippets:
                break
            start = match.start()
            left = max(0, start - window)
            right = min(len(normalized), match.end() + window)
            if any(abs(start - prev_start) < window for prev_start, _ in seen_spans):
                continue
            snippet = normalized[left:right].strip()
            if left > 0:
                snippet = "…" + snippet
            if right < len(normalized):
                snippet += "…"
            snippets.append(snippet)
            seen_spans.append((start, right))
        if len(snippets) >= max_snippets:
            break
    return snippets
