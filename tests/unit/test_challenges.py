from pathlib import Path

import pytest
from pytest import MonkeyPatch

from tools import run_challenges


def test_challenge_manifest_must_be_a_json_object(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "C001.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(run_challenges, "ROOT", tmp_path)
    monkeypatch.setattr(run_challenges, "MANIFESTS", tmp_path)

    with pytest.raises(TypeError, match="must be a JSON object"):
        run_challenges.load_challenges()


def test_challenge_manifest_requires_known_bad_behavior(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "C001.json").write_text(
        '{"id":"C001","title":"x","finding_commit":"x","oracle":"x",'
        '"test_command":["x"],"surfaces":["x"],"prevention":["x"]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(run_challenges, "ROOT", tmp_path)
    monkeypatch.setattr(run_challenges, "MANIFESTS", tmp_path)

    with pytest.raises(ValueError, match=r"missing \['known_bad'\]"):
        run_challenges.load_challenges()
