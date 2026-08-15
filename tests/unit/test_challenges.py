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
