import os
import socket

import yaml

from radar.cli import main
from radar.doctor import doctor_workspace
from radar.workspace import init_workspace


def _write_config(workspace, name, payload):
    (workspace / "config" / f"{name}.yaml").write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def _codes(report):
    return {issue.code for issue in report.issues}


def test_doctor_accepts_default_workspace_without_network_access(tmp_path, monkeypatch, capsys):
    workspace, _ = init_workspace(tmp_path / "radar")

    def fail_dns(*args, **kwargs):
        raise AssertionError("doctor must not perform DNS or network checks")

    monkeypatch.setattr(socket, "getaddrinfo", fail_dns)

    report = doctor_workspace(workspace)
    assert report.ok
    assert report.issues == ()
    assert main(["doctor", "--workspace", str(workspace)]) == 0
    assert capsys.readouterr().out == "Workspace check passed.\n"


def test_doctor_reports_missing_structure_and_unwritable_directories(tmp_path, monkeypatch):
    missing = doctor_workspace(tmp_path / "missing")
    assert not missing.ok
    assert "directory.missing" in _codes(missing)

    workspace, _ = init_workspace(tmp_path / "radar")
    real_access = os.access

    def deny_site(path, mode):
        if path == workspace / "site":
            return False
        return real_access(path, mode)

    monkeypatch.setattr("radar.doctor.os.access", deny_site)
    report = doctor_workspace(workspace)

    assert not report.ok
    assert any(
        issue.code == "directory.not_writable" and issue.message == "site is not writable."
        for issue in report.errors
    )


def test_doctor_aggregates_invalid_yaml_and_required_types(tmp_path):
    workspace, _ = init_workspace(tmp_path / "radar")
    (workspace / "config" / "people.yaml").write_text("people: [\n", encoding="utf-8")
    _write_config(workspace, "sources", {"sources": "not-a-list"})
    _write_config(workspace, "topics", {"topics": [{"keywords": "not-a-list"}]})
    _write_config(workspace, "scoring", {"scoring": []})

    report = doctor_workspace(workspace)

    assert not report.ok
    assert {
        "config.invalid_yaml",
        "sources.type",
        "topics.keywords_type",
        "scoring.type",
    }.issubset(_codes(report))


def test_doctor_checks_source_configuration_without_resolving_hosts(tmp_path, monkeypatch):
    workspace, _ = init_workspace(tmp_path / "radar")
    _write_config(
        workspace,
        "sources",
        {
            "sources": [
                {
                    "type": "rss",
                    "enabled": "yes",
                    "url": "ftp://example.org/feed.xml",
                    "priority": "high",
                },
                {
                    "type": "arxiv",
                    "name": "arXiv",
                    "query": "",
                    "priority": -1,
                },
                {"type": "custom", "name": "Unsupported"},
            ]
        },
    )

    def fail_dns(*args, **kwargs):
        raise AssertionError("doctor must not resolve source hosts")

    monkeypatch.setattr(socket, "getaddrinfo", fail_dns)
    report = doctor_workspace(workspace)

    assert not report.ok
    assert {
        "sources.name",
        "sources.enabled_type",
        "sources.rss_url",
        "sources.priority_type",
        "sources.arxiv_query",
        "sources.priority_range",
        "sources.unsupported_type",
    }.issubset(_codes(report))


def test_doctor_warns_about_empty_and_duplicate_configuration(tmp_path, capsys):
    workspace, _ = init_workspace(tmp_path / "radar")
    _write_config(
        workspace,
        "people",
        {
            "people": [
                {"name": "Ada Example", "aliases": ["A. Example", "a. example"]},
                {"name": "ada example", "aliases": []},
            ]
        },
    )
    _write_config(
        workspace,
        "sources",
        {
            "sources": [
                {
                    "type": "rss",
                    "name": "Example Feed",
                    "enabled": False,
                    "url": "https://example.org/feed.xml",
                },
                {
                    "type": "rss",
                    "name": "example feed",
                    "enabled": False,
                    "url": "https://example.org/feed.xml",
                },
            ]
        },
    )
    _write_config(
        workspace,
        "topics",
        {
            "topics": {
                "robot_learning": {
                    "label": "Robot Learning",
                    "keywords": ["robot learning", "", "Robot Learning"],
                },
                "robot_learning_again": {
                    "label": "robot learning",
                    "keywords": [],
                },
            }
        },
    )

    report = doctor_workspace(workspace)

    assert report.ok
    assert {
        "people.duplicate_aliases",
        "people.duplicates",
        "sources.none_enabled",
        "sources.duplicate_names",
        "sources.duplicates",
        "topics.empty_keywords",
        "topics.blank_keywords",
        "topics.duplicate_keywords",
        "topics.duplicates",
    }.issubset(_codes(report))
    assert main(["doctor", "--workspace", str(workspace)]) == 0
    output = capsys.readouterr().out
    assert "[WARNING]" in output
    assert "0 error(s)" in output
