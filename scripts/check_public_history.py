#!/usr/bin/env python3
"""Check commit identities before public history is published."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass


_FIELD_COUNT = 6
_PUBLIC_EMAIL = re.compile(
    r"(?:^[^@\s]+@users\.noreply\.github\.com$|^noreply@github\.com$)",
    re.IGNORECASE,
)
_LOG_FORMAT = "%H%x00%an%x00%ae%x00%cn%x00%ce%x00%s"


@dataclass(frozen=True)
class CommitIdentity:
    sha: str
    author_name: str
    author_email: str
    committer_name: str
    committer_email: str
    subject: str


def parse_git_log(payload: str) -> list[CommitIdentity]:
    commits: list[CommitIdentity] = []
    for line_number, line in enumerate(payload.splitlines(), start=1):
        if not line:
            continue
        fields = line.split("\x00")
        if len(fields) != _FIELD_COUNT:
            raise ValueError(
                f"Malformed git log record on line {line_number}; expected {_FIELD_COUNT} fields"
            )
        commits.append(CommitIdentity(*fields))
    return commits


def check_identities(commits: list[CommitIdentity]) -> list[str]:
    findings: list[str] = []
    for commit in commits:
        for role, email in (
            ("author", commit.author_email),
            ("committer", commit.committer_email),
        ):
            if not _PUBLIC_EMAIL.fullmatch(email.strip()):
                findings.append(
                    f"{commit.sha} {role} email must be a GitHub noreply address"
                )
    return findings


def check_log(payload: str) -> list[str]:
    return check_identities(parse_git_log(payload))


def _git_log(revision: str) -> str:
    command = ["git", "log", "--format=" + _LOG_FORMAT, revision]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode:
        detail = result.stderr.strip() or "git log failed"
        raise RuntimeError(detail)
    return result.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that selected git commits use public GitHub noreply identities."
    )
    revisions = parser.add_mutually_exclusive_group(required=True)
    revisions.add_argument("--range", dest="revision_range", help="Git revision range to inspect")
    revisions.add_argument("--all", action="store_true", help="Inspect all reachable refs")
    args = parser.parse_args(argv)

    revision = args.revision_range or "--all"
    try:
        findings = check_log(_git_log(revision))
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Commit metadata check failed: {exc}", file=sys.stderr)
        return 2

    if findings:
        print("Commit metadata check failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("Commit metadata check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
