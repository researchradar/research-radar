from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .identity import canonical_identity
from .models import RankedItem, RawItem


def text_for(item: RawItem) -> str:
    return " ".join(
        [item.title, item.raw_text, item.transcript, " ".join(item.authors_or_guests)]
    ).casefold()


def contains(text: str, phrase: str) -> bool:
    return phrase.casefold() in text


def _priority(value: Any) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, float(value))
    return {"high": 1.0, "medium": 0.65, "low": 0.35}.get(str(value).casefold(), 0.5)


def _topic_entries(config: dict[str, Any]) -> list[dict[str, Any]]:
    raw = config.get("topics", {}).get("topics", {})
    if isinstance(raw, list):
        return raw
    entries: list[dict[str, Any]] = []
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        entries.append(
            {
                "name": str(value.get("label") or key),
                "keywords": list(value.get("keywords", [])),
                "priority": value.get("priority", 1.0),
            }
        )
    return entries


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
    values = {
        "star": 5,
        "interested": 5,
        "read": 3,
        "track": 4,
        "not_interested": -8,
        "too_far": -6,
        "too_shallow": -3,
        "insufficient_evidence": -4,
        "block_source": -20,
    }
    for entry in feedback:
        value = values.get(str(entry.get("action", "")).casefold(), 0)
        for target in entry.get("targets", []):
            adjustments[str(target).casefold()] += value
    return adjustments


def _recency_score(published_at: str | None, weight: float) -> float:
    if not published_at:
        return 0.0
    try:
        parsed = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        age_days = max(
            0.0,
            (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 86400,
        )
    except ValueError:
        return 0.0
    return round(max(0.0, 10.0 - age_days) * weight, 2)


def rank(items: list[RawItem], config: dict[str, Any]) -> list[RankedItem]:
    people_config = config.get("people", {})
    people = people_config.get("people", [])
    institutions = people_config.get("institutions", [])
    topics_config = config.get("topics", {})
    topics = _topic_entries(config)
    negatives = topics_config.get("negative_topics", [])
    questions = config.get("questions", {}).get("questions", [])
    feedback = config.get("feedback", {}).get("feedback", [])
    scoring = config.get("scoring", {}).get("scoring", {})

    followed_person_bonus = float(scoring.get("followed_person_bonus", 20))
    institution_bonus = float(scoring.get("institution_bonus", 5))
    topic_match_bonus = float(scoring.get("topic_match_bonus", 25))
    question_match_bonus = float(scoring.get("question_match_bonus", 10))
    source_priority_weight = float(scoring.get("source_priority_weight", 1.0))
    recency_weight = float(scoring.get("recency_weight", 1.0))
    adjustments = feedback_adjustments(feedback if isinstance(feedback, list) else [])

    ranked: list[RankedItem] = []
    for item in deduplicate(items):
        body = text_for(item)
        negative_matches = [str(term) for term in negatives if contains(body, str(term))]
        if negative_matches:
            continue

        matched_people: list[str] = []
        person_score = 0.0
        for person in people:
            name = str(person.get("name", "")).strip()
            aliases = [name, *person.get("aliases", [])]
            if name and any(alias and contains(body, str(alias)) for alias in aliases):
                matched_people.append(name)
                person_score += followed_person_bonus * _priority(person.get("priority", 1.0))

        matched_institutions: list[str] = []
        institution_score = 0.0
        for institution in institutions:
            name = str(institution.get("name", "")).strip()
            aliases = [name, *institution.get("aliases", [])]
            if name and any(alias and contains(body, str(alias)) for alias in aliases):
                matched_institutions.append(name)
                institution_score += institution_bonus * _priority(institution.get("priority", 1.0))

        matched_topics: list[str] = []
        topic_score = 0.0
        for topic in topics:
            if any(contains(body, str(keyword)) for keyword in topic.get("keywords", [])):
                matched_topics.append(str(topic.get("name", "Topic")))
                topic_score += topic_match_bonus * _priority(topic.get("priority", 1.0))

        matched_questions: list[str] = []
        question_score = 0.0
        for question in questions:
            label = str(question.get("question", "")).strip()
            if label and any(contains(body, str(keyword)) for keyword in question.get("keywords", [])):
                matched_questions.append(label)
                question_score += question_match_bonus * _priority(question.get("priority", 1.0))

        recency_score = _recency_score(item.published_at, recency_weight)
        source_priority = float((item.metadata or {}).get("source_priority", 1.0))
        source_score = 5.0 * source_priority * source_priority_weight
        evidence_score = 15.0 if item.source_type == "paper" else 10.0 if item.source_type in {"blog", "podcast", "rss"} else 3.0
        feedback_score = sum(
            value
            for target, value in adjustments.items()
            if target in body or target == item.source.casefold()
        )
        total = max(
            0.0,
            person_score
            + institution_score
            + topic_score
            + question_score
            + recency_score
            + source_score
            + evidence_score
            + feedback_score,
        )
        ranked.append(
            RankedItem(
                item=item,
                score=round(total, 2),
                score_breakdown={
                    "people": round(person_score, 2),
                    "institutions": round(institution_score, 2),
                    "topics": round(topic_score, 2),
                    "questions": round(question_score, 2),
                    "recency": round(recency_score, 2),
                    "source": round(source_score, 2),
                    "evidence": round(evidence_score, 2),
                    "feedback": round(feedback_score, 2),
                },
                matched_people=matched_people,
                matched_institutions=matched_institutions,
                matched_topics=matched_topics,
                matched_questions=matched_questions,
                negative_matches=negative_matches,
                discovery_type=(
                    "direct"
                    if matched_people or matched_institutions
                    else "topic"
                    if matched_topics
                    else "source"
                ),
            )
        )
    return sorted(
        ranked,
        key=lambda candidate: (candidate.score, candidate.item.published_at or ""),
        reverse=True,
    )
