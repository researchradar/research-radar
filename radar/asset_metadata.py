"""Tolerant metadata reader for canonical research assets.

Asset templates have moved their metadata around over time: older reports keep it
in a ```yaml fence, newer v2.7+ reports keep it in an HTML comment. Strict
yaml.safe_load also drops the whole block when a value contains ': ' (e.g. a
title with a subtitle). That drift has bitten beliefs.py and paper_asset_state.py
independently, so this is the single tolerant reader all consumers route through.

Parsing is line-based and therefore tolerant of ': ' in values; it reads both
metadata locations and returns the first block carrying a signal key.
"""

from __future__ import annotations

import re
from typing import Any

_FENCE_RE = re.compile(r"```ya?ml\s*\n(.*?)```", re.DOTALL)
_COMMENT_RE = re.compile(r"<!--\s*(.*?)\s*-->", re.DOTALL)
_LINE_RE = re.compile(r"^([A-Za-z0-9_\-]+):\s*(.*)$")

# Keys that mark a block as asset metadata (vs. an arbitrary yaml/comment block).
DEFAULT_SIGNAL_KEYS = ("title", "source_url", "asset_type", "source_type", "id", "identity")


def parse_meta_lines(block: str) -> dict[str, Any]:
    """Parse `key: value` lines, tolerant of ': ' inside the value."""
    data: dict[str, Any] = {}
    for line in block.splitlines():
        match = _LINE_RE.match(line)
        if match and match.group(2).strip():
            data[match.group(1)] = match.group(2).strip().strip("'\"")
    return data


def _candidate_blocks(text: str) -> list[str]:
    # Fences first, then HTML comments (a clean yaml fence wins when both exist).
    return [m.group(1) for m in _FENCE_RE.finditer(text)] + [m.group(1) for m in _COMMENT_RE.finditer(text)]


def scan_metadata(text: str, signal_keys: tuple[str, ...] = DEFAULT_SIGNAL_KEYS) -> dict[str, Any]:
    """Return the first metadata block containing any signal key, or {}."""
    for block in _candidate_blocks(text):
        data = parse_meta_lines(block)
        if any(key in data for key in signal_keys):
            return data
    return {}


def get(text: str, key: str, default: str = "") -> str:
    value = scan_metadata(text).get(key)
    return str(value).strip() if value else default


def source_url(text: str) -> str:
    return get(text, "source_url")
