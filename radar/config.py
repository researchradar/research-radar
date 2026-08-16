from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REQUIRED_CONFIGS = ("people", "sources", "topics", "scoring")
OPTIONAL_CONFIGS = ("feedback",)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return data


def load_config(config_dir: Path) -> dict[str, Any]:
    config_dir = config_dir.expanduser().resolve()
    missing = [name for name in REQUIRED_CONFIGS if not (config_dir / f"{name}.yaml").exists()]
    if missing:
        joined = ", ".join(f"{name}.yaml" for name in missing)
        raise ValueError(f"Missing required config file(s): {joined}")

    config = {
        name: load_yaml(config_dir / f"{name}.yaml")
        for name in REQUIRED_CONFIGS
    }
    for name in OPTIONAL_CONFIGS:
        path = config_dir / f"{name}.yaml"
        config[name] = load_yaml(path) if path.exists() else {"feedback": []}

    people = config["people"].get("people", [])
    sources = config["sources"].get("sources", [])
    topics = config["topics"].get("topics", {})
    if not isinstance(people, list):
        raise ValueError("config/people.yaml: 'people' must be a list")
    if not isinstance(sources, list):
        raise ValueError("config/sources.yaml: 'sources' must be a list")
    if not isinstance(topics, (dict, list)):
        raise ValueError("config/topics.yaml: 'topics' must be a mapping or list")
    return config
