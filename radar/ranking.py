from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from .identity import canonical_identity
from .models import RankedItem, RawItem


def text_for(item: RawItem) -> str:
    return " ".join([item.title, item.raw_text, item.transcript, " ".join(item.authors_or_guests)]).casefold()


def contains(text: str, phrase: str) -> bool:
    return phrase.casefold() in text


def weight(priority: str) -> float:
    return {"high": 1.0, "medium": 0.65, "low": 0.35}.get(priority, 0.5)


def _dedup_preference(item: RawItem) -> tuple[int, int, int, int]:
    metadata = item.metadata or {}
    return (
        1 if item.source_type != "aggregator" else 0,
        1 if item.source_type == "paper" else 0,
        1 if metadata.get("article_fetched") else 0,
        len(item.raw_text or ""),
    )


def deduplicate(items: list[RawItem]) -> list[RawItem]:
    selected: dict[str, RawItem] = {}
    title_to_identity: dict[str, str] = {}
    for item in items:
        identity = canonical_identity(item.canonical_url, title=item.title)
        title_key = "title:" + (re.sub(r"\W+", "", item.title.casefold()) or item.canonical_url)
        existing_identity = title_to_identity.get(title_key, identity)
        current = selected.get(existing_identity)
        if current is None or _dedup_preference(item) > _dedup_preference(current):
            if existing_identity != identity:
                selected.pop(existing_identity, None)
            selected[identity] = item
            title_to_identity[title_key] = identity
    return list(selected.values())


def feedback_adjustments(feedback: list[dict[str, Any]]) -> dict[str, float]:
    adjustments: dict[str, float] = defaultdict(float)
    for entry in feedback:
        value = {"interested": 5, "read": 3, "track": 4, "not_interested": -8, "too_far": -6, "too_shallow": -3, "insufficient_evidence": -4, "block_source": -20}.get(entry.get("action"), 0)
        for target in entry.get("targets", []):
            adjustments[target.casefold()] += value
    return adjustments


def rank(items: list[RawItem], config: dict[str, Any]) -> list[RankedItem]:
    people = config["people"].get("people", [])
    institutions = config["people"].get("institutions", [])
    topics = config["topics"].get("topics", [])
    negatives = config["topics"].get("negative_topics", [])
    questions = config["questions"].get("questions", [])
    adjustments = feedback_adjustments(config["feedback"].get("feedback", []))
    ranked: list[RankedItem] = []

    for item in deduplicate(items):
        body = text_for(item)
        matched_people = [p["name"] for p in people if any(contains(body, alias) for alias in p.get("aliases", [p["name"]]))]
        matched_institutions = [i["name"] for i in institutions if any(contains(body, alias) for alias in i.get("aliases", [i["name"]]))]
        matched_topics = [t["name"] for t in topics if any(contains(body, keyword) for keyword in t.get("keywords", []))]
        matched_questions = [q["question"] for q in questions if any(contains(body, keyword) for keyword in q.get("keywords", []))]
        negative_matches = [term for term in negatives if contains(body, term)]
        if negative_matches:
            continue

        topic_score = min(25, sum(25 * weight(t["priority"]) for t in topics if t["name"] in matched_topics))
        entity_score = min(20, 10 * len(matched_people) + 5 * len(matched_institutions))
        evidence_score = 15 if item.source_type == "paper" else 10 if item.source_type in {"blog", "podcast"} else 3
        novelty_score = 20 if item.source_type == "paper" else 12
        question_score = min(10, 5 * len(matched_questions))
        source_score = 0 if item.source_type == "aggregator" else 5
        discovery_score = 5 if matched_topics and not matched_people and not matched_institutions else 0
        feedback_score = sum(value for target, value in adjustments.items() if target in body or target == item.source.casefold())
        total = max(0, topic_score + entity_score + evidence_score + novelty_score + question_score + source_score + discovery_score + feedback_score)
        ranked.append(RankedItem(item, round(total, 1), {"topic": topic_score, "entity": entity_score, "novelty": novelty_score, "evidence": evidence_score, "question": question_score, "source": source_score, "discovery": discovery_score, "feedback": feedback_score}, matched_people, matched_institutions, matched_topics, matched_questions, negative_matches, "two-hop" if discovery_score else "direct"))
    return sorted(ranked, key=lambda candidate: candidate.score, reverse=True)
