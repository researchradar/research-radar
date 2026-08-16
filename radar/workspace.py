from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIGS: dict[str, dict[str, Any]] = {
    "people": {
        "people": [
            {
                "name": "Example Researcher",
                "aliases": [],
                "arxiv_author": True,
                "priority": 1.0,
            }
        ]
    },
    "topics": {
        "topics": {
            "embodied_ai": {
                "label": "Embodied AI",
                "keywords": [
                    "vision-language-action",
                    "robot manipulation",
                    "world model",
                ],
                "priority": 1.0,
            },
            "research_tools": {
                "label": "Research Tools",
                "keywords": [
                    "literature search",
                    "research automation",
                    "information retrieval",
                ],
                "priority": 0.7,
            },
        }
    },
    "sources": {
        "sources": [
            {
                "type": "arxiv",
                "name": "arXiv",
                "enabled": True,
                "query": "all:robotics OR cat:cs.AI",
                "lookback_days": 2,
            },
            {
                "type": "rss",
                "name": "Example Lab",
                "enabled": False,
                "url": "https://example.org/feed.xml",
            },
        ]
    },
    "scoring": {
        "scoring": {
            "recency_weight": 1.0,
            "followed_person_bonus": 20,
            "topic_match_bonus": 10,
            "source_priority_weight": 1.0,
            "interest_model": {"enabled": False},
        }
    },
    "feedback": {"feedback": []},
}


def workspace_path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def init_workspace(value: str | Path) -> tuple[Path, list[str]]:
    workspace = workspace_path(value)
    config_dir = workspace / "config"
    data_dir = workspace / "data"
    site_dir = workspace / "site"
    config_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    site_dir.mkdir(parents=True, exist_ok=True)

    created: list[str] = []
    for name, payload in DEFAULT_CONFIGS.items():
        path = config_dir / f"{name}.yaml"
        if path.exists():
            continue
        path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
            encoding="utf-8",
        )
        created.append(str(path.relative_to(workspace)))

    return workspace, created


def require_workspace(value: str | Path) -> Path:
    workspace = workspace_path(value)
    if not (workspace / "config").is_dir():
        raise ValueError(
            f"Not a Research Radar workspace: {workspace}. "
            "Run 'research-radar init WORKSPACE' first."
        )
    (workspace / "data").mkdir(parents=True, exist_ok=True)
    (workspace / "site").mkdir(parents=True, exist_ok=True)
    return workspace
