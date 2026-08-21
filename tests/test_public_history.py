import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


_SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "check_public_history.py"
_SPEC = spec_from_file_location("check_public_history", _SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

check_log = _MODULE.check_log
parse_git_log = _MODULE.parse_git_log


def _record(
    sha="abc123",
    author_email="123+contributor@users.noreply.github.com",
    committer_email="noreply@github.com",
):
    return "\x00".join(
        [sha, "Contributor", author_email, "GitHub", committer_email, "A change"]
    )


def test_public_github_noreply_identities_pass():
    assert check_log(_record()) == []


def test_personal_commit_identities_are_rejected():
    findings = check_log(
        _record(
            author_email="contributor@example.com",
            committer_email="maintainer@example.org",
        )
    )

    assert len(findings) == 2
    assert all("must be a GitHub noreply address" in finding for finding in findings)


def test_empty_log_is_valid():
    assert check_log("") == []


def test_malformed_log_is_rejected():
    with pytest.raises(ValueError, match="expected 6 fields"):
        parse_git_log("abc123\x00only-two-fields")
