from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TranscriptMeta:
    status: str = "none"
    provider: str | None = None
    source_kind: str | None = None
    confidence: str | None = None
    attempted_providers: list[str] = field(default_factory=list)
    language: str | None = None
    text_path: str | None = None
    segments_path: str | None = None
    char_count: int = 0
    excerpt: str = ""
    evidence_snippets: list[str] = field(default_factory=list)
    evidence_quotes: list[dict[str, Any]] = field(default_factory=list)
    translation_status: str = "not_needed"
    translation_path: str | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RawItem:
    id: str
    canonical_url: str
    title: str
    source: str
    source_type: str
    published_at: str | None = None
    authors_or_guests: list[str] = field(default_factory=list)
    raw_text: str = ""
    transcript: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    transcript_meta: dict[str, Any] = field(default_factory=dict)
    fetched_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Evidence:
    claim: str
    excerpt: str
    source_url: str
    source_type: str
    confidence: str = "high"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RankedItem:
    item: RawItem
    score: float
    score_breakdown: dict[str, float]
    matched_people: list[str]
    matched_institutions: list[str]
    matched_topics: list[str]
    matched_questions: list[str]
    negative_matches: list[str]
    discovery_type: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "item": self.item.as_dict(),
            "score": self.score,
            "score_breakdown": self.score_breakdown,
            "matched_people": self.matched_people,
            "matched_institutions": self.matched_institutions,
            "matched_topics": self.matched_topics,
            "matched_questions": self.matched_questions,
            "negative_matches": self.negative_matches,
            "discovery_type": self.discovery_type,
        }
