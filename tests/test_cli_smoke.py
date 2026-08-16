import json

from radar.cli import main
from radar.config import load_config


def test_offline_quick_start(tmp_path):
    workspace = tmp_path / "radar"

    assert main(["init", str(workspace)]) == 0
    assert (workspace / "config" / "people.yaml").exists()
    assert (workspace / "config" / "feedback.yaml").exists()

    assert (
        main(
            [
                "collect",
                "--workspace",
                str(workspace),
                "--offline",
                "--fixture-set",
                "synthetic",
            ]
        )
        == 0
    )
    assert main(["build-site", "--workspace", str(workspace)]) == 0

    ranked = json.loads((workspace / "data" / "ranked.json").read_text(encoding="utf-8"))
    assert len(ranked) == 3
    assert ranked[0]["score"] >= ranked[-1]["score"]

    for name in ("index.html", "reading.html", "search.html", "archive.html", "following.html"):
        path = workspace / "site" / name
        assert path.exists()
        assert "Research Radar" in path.read_text(encoding="utf-8")


def test_feedback_is_optional(tmp_path):
    workspace = tmp_path / "radar"
    assert main(["init", str(workspace)]) == 0
    (workspace / "config" / "feedback.yaml").unlink()

    config = load_config(workspace / "config")
    assert config["feedback"] == {"feedback": []}


def test_init_does_not_overwrite_existing_config(tmp_path):
    workspace = tmp_path / "radar"
    assert main(["init", str(workspace)]) == 0
    people = workspace / "config" / "people.yaml"
    people.write_text("people: []\n", encoding="utf-8")

    assert main(["init", str(workspace)]) == 0
    assert people.read_text(encoding="utf-8") == "people: []\n"
