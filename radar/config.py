from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return data


def load_config(config_dir: Path) -> dict[str, Any]:
    required_names = ("people", "sources", "topics", "questions", "feedback")
    optional_names = ("transcripts", "asr_lexicon")
    config = {name: load_yaml(config_dir / f"{name}.yaml") for name in required_names}
    for name in optional_names:
        path = config_dir / f"{name}.yaml"
        config[name] = load_yaml(path) if path.exists() else {}
    for name in ("people", "sources", "topics", "questions"):
        if not config[name]:
            raise ValueError(f"config/{name}.yaml cannot be empty")
    return config
