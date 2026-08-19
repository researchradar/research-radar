from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import yaml

from .config import OPTIONAL_CONFIGS, REQUIRED_CONFIGS
from .workspace import workspace_path


@dataclass(frozen=True)
class DoctorIssue:
    level: str
    code: str
    message: str


@dataclass(frozen=True)
class DoctorReport:
    workspace: Path
    issues: tuple[DoctorIssue, ...]

    @property
    def errors(self) -> tuple[DoctorIssue, ...]:
        return tuple(issue for issue in self.issues if issue.level == "error")

    @property
    def warnings(self) -> tuple[DoctorIssue, ...]:
        return tuple(issue for issue in self.issues if issue.level == "warning")

    @property
    def ok(self) -> bool:
        return not self.errors


def _duplicates(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        normalized = str(value).strip().casefold()
        if not normalized:
            continue
        if normalized in seen and normalized not in duplicates:
            duplicates.append(normalized)
        seen.add(normalized)
    return duplicates


def _check_directory(path: Path, label: str, issues: list[DoctorIssue]) -> None:
    if not path.exists():
        issues.append(DoctorIssue("error", "directory.missing", f"Missing {label} directory."))
        return
    if not path.is_dir():
        issues.append(DoctorIssue("error", "directory.type", f"{label} must be a directory."))
        return
    if not os.access(path, os.W_OK | os.X_OK):
        issues.append(DoctorIssue("error", "directory.not_writable", f"{label} is not writable."))


def _load_config_file(path: Path, name: str, issues: list[DoctorIssue]) -> dict[str, Any] | None:
    if not path.exists():
        issues.append(
            DoctorIssue("error", "config.missing", f"Missing required config/{name}.yaml.")
        )
        return None
    if not path.is_file():
        issues.append(
            DoctorIssue("error", "config.type", f"config/{name}.yaml must be a file.")
        )
        return None
    try:
        with path.open(encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as exc:
        issues.append(
            DoctorIssue("error", "config.invalid_yaml", f"config/{name}.yaml: {exc}")
        )
        return None
    if not isinstance(payload, dict):
        issues.append(
            DoctorIssue(
                "error",
                "config.top_level_type",
                f"config/{name}.yaml must contain a top-level mapping.",
            )
        )
        return None
    return payload


def _check_people(payload: dict[str, Any], issues: list[DoctorIssue]) -> None:
    people = payload.get("people")
    if not isinstance(people, list):
        issues.append(
            DoctorIssue("error", "people.type", "config/people.yaml: 'people' must be a list.")
        )
        return

    names: list[str] = []
    for index, person in enumerate(people):
        prefix = f"config/people.yaml: people[{index}]"
        if not isinstance(person, dict):
            issues.append(DoctorIssue("error", "people.entry_type", f"{prefix} must be a mapping."))
            continue
        name = str(person.get("name") or "").strip()
        if not name:
            issues.append(DoctorIssue("error", "people.name", f"{prefix} needs a non-empty name."))
        else:
            names.append(name)
        aliases = person.get("aliases", [])
        if not isinstance(aliases, list):
            issues.append(DoctorIssue("error", "people.aliases_type", f"{prefix}.aliases must be a list."))
        elif duplicates := _duplicates(aliases):
            issues.append(
                DoctorIssue(
                    "warning",
                    "people.duplicate_aliases",
                    f"{prefix}.aliases has duplicate value(s): {', '.join(duplicates)}.",
                )
            )

    if duplicates := _duplicates(names):
        issues.append(
            DoctorIssue(
                "warning",
                "people.duplicates",
                f"Duplicate people name(s): {', '.join(duplicates)}.",
            )
        )


def _check_rss_url(value: Any) -> str | None:
    raw = str(value or "").strip()
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return "must be an absolute http:// or https:// URL"
    if parsed.username or parsed.password:
        return "must not contain embedded credentials"
    return None


def _check_sources(payload: dict[str, Any], issues: list[DoctorIssue]) -> None:
    sources = payload.get("sources")
    if not isinstance(sources, list):
        issues.append(
            DoctorIssue("error", "sources.type", "config/sources.yaml: 'sources' must be a list.")
        )
        return

    names: list[str] = []
    identities: list[str] = []
    enabled_count = 0
    for index, source in enumerate(sources):
        prefix = f"config/sources.yaml: sources[{index}]"
        if not isinstance(source, dict):
            issues.append(DoctorIssue("error", "sources.entry_type", f"{prefix} must be a mapping."))
            continue

        name = str(source.get("name") or "").strip()
        if name:
            names.append(name)
        else:
            issues.append(DoctorIssue("warning", "sources.name", f"{prefix} has no display name."))

        enabled = source.get("enabled", True)
        if not isinstance(enabled, bool):
            issues.append(
                DoctorIssue("error", "sources.enabled_type", f"{prefix}.enabled must be true or false.")
            )
        elif enabled:
            enabled_count += 1

        source_type = str(source.get("type") or "").strip().casefold()
        if source_type not in {"arxiv", "rss"}:
            issues.append(
                DoctorIssue(
                    "error",
                    "sources.unsupported_type",
                    f"{prefix}.type must be 'arxiv' or 'rss'.",
                )
            )
            continue

        if source_type == "arxiv":
            query = str(source.get("query") or "").strip()
            if not query:
                issues.append(
                    DoctorIssue("error", "sources.arxiv_query", f"{prefix} needs a non-empty query.")
                )
            else:
                identities.append(f"arxiv:{query.casefold()}")
        else:
            url = str(source.get("url") or "").strip()
            if problem := _check_rss_url(url):
                issues.append(
                    DoctorIssue("error", "sources.rss_url", f"{prefix}.url {problem}.")
                )
            else:
                identities.append(f"rss:{url.casefold()}")

        priority = source.get("priority", 1.0)
        if isinstance(priority, bool) or not isinstance(priority, (int, float)):
            issues.append(
                DoctorIssue("error", "sources.priority_type", f"{prefix}.priority must be a number.")
            )
        elif priority < 0:
            issues.append(
                DoctorIssue("error", "sources.priority_range", f"{prefix}.priority must not be negative.")
            )

    if sources and not enabled_count:
        issues.append(DoctorIssue("warning", "sources.none_enabled", "No sources are enabled."))
    if duplicates := _duplicates(names):
        issues.append(
            DoctorIssue(
                "warning",
                "sources.duplicate_names",
                f"Duplicate source name(s): {', '.join(duplicates)}.",
            )
        )
    if duplicates := _duplicates(identities):
        issues.append(
            DoctorIssue(
                "warning",
                "sources.duplicates",
                f"Duplicate source configuration(s): {', '.join(duplicates)}.",
            )
        )


def _topic_entries(topics: dict[str, Any] | list[Any]) -> list[tuple[str, Any]]:
    if isinstance(topics, dict):
        return [(str(key), value) for key, value in topics.items()]
    return [(str(index), value) for index, value in enumerate(topics)]


def _check_topics(payload: dict[str, Any], issues: list[DoctorIssue]) -> None:
    topics = payload.get("topics")
    if not isinstance(topics, (dict, list)):
        issues.append(
            DoctorIssue(
                "error",
                "topics.type",
                "config/topics.yaml: 'topics' must be a mapping or list.",
            )
        )
        return
    if not topics:
        issues.append(DoctorIssue("warning", "topics.empty", "No topics are configured."))

    names: list[str] = []
    for key, topic in _topic_entries(topics):
        prefix = f"config/topics.yaml: topics[{key}]"
        if not isinstance(topic, dict):
            issues.append(DoctorIssue("error", "topics.entry_type", f"{prefix} must be a mapping."))
            continue
        name = str(topic.get("label") or topic.get("name") or key).strip()
        if name:
            names.append(name)
        keywords = topic.get("keywords")
        if not isinstance(keywords, list):
            issues.append(DoctorIssue("error", "topics.keywords_type", f"{prefix}.keywords must be a list."))
            continue
        non_empty_keywords = [str(keyword).strip() for keyword in keywords if str(keyword).strip()]
        if not non_empty_keywords:
            issues.append(
                DoctorIssue("warning", "topics.empty_keywords", f"{prefix} has no non-empty keywords.")
            )
        if len(non_empty_keywords) != len(keywords):
            issues.append(
                DoctorIssue("warning", "topics.blank_keywords", f"{prefix}.keywords contains a blank value.")
            )
        if duplicates := _duplicates(non_empty_keywords):
            issues.append(
                DoctorIssue(
                    "warning",
                    "topics.duplicate_keywords",
                    f"{prefix}.keywords has duplicate value(s): {', '.join(duplicates)}.",
                )
            )

    if duplicates := _duplicates(names):
        issues.append(
            DoctorIssue(
                "warning",
                "topics.duplicates",
                f"Duplicate topic name(s): {', '.join(duplicates)}.",
            )
        )


def _check_scoring(payload: dict[str, Any], issues: list[DoctorIssue]) -> None:
    if not isinstance(payload.get("scoring"), dict):
        issues.append(
            DoctorIssue(
                "error",
                "scoring.type",
                "config/scoring.yaml: 'scoring' must be a mapping.",
            )
        )


def doctor_workspace(value: str | Path) -> DoctorReport:
    workspace = workspace_path(value)
    issues: list[DoctorIssue] = []

    _check_directory(workspace, "workspace", issues)
    if not workspace.is_dir():
        return DoctorReport(workspace, tuple(issues))

    config_dir = workspace / "config"
    _check_directory(config_dir, "config", issues)
    _check_directory(workspace / "data", "data", issues)
    _check_directory(workspace / "site", "site", issues)
    if not config_dir.is_dir():
        return DoctorReport(workspace, tuple(issues))

    payloads: dict[str, dict[str, Any]] = {}
    for name in REQUIRED_CONFIGS:
        payload = _load_config_file(config_dir / f"{name}.yaml", name, issues)
        if payload is not None:
            payloads[name] = payload
    for name in OPTIONAL_CONFIGS:
        path = config_dir / f"{name}.yaml"
        if path.exists():
            payload = _load_config_file(path, name, issues)
            if payload is not None:
                payloads[name] = payload

    if "people" in payloads:
        _check_people(payloads["people"], issues)
    if "sources" in payloads:
        _check_sources(payloads["sources"], issues)
    if "topics" in payloads:
        _check_topics(payloads["topics"], issues)
    if "scoring" in payloads:
        _check_scoring(payloads["scoring"], issues)

    return DoctorReport(workspace, tuple(issues))
