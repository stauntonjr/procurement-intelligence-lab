import json
import subprocess
import sys
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


@pytest.mark.parametrize("return_code", [0, 1])
def test_main_writes_results_for_pass_and_failure(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    return_code: int,
) -> None:
    challenge: run_challenges.Challenge = {
        "id": "C001",
        "title": "test challenge",
        "finding_commit": "abc123",
        "oracle": "test oracle",
        "known_bad": "test mutation",
        "test_command": ["test-command"],
        "surfaces": ["test"],
        "prevention": ["test"],
    }
    results_path = tmp_path / "results.json"

    def fake_run(command: list[str], *, cwd: Path, check: bool) -> subprocess.CompletedProcess[str]:
        assert cwd == run_challenges.ROOT
        assert check is False
        return subprocess.CompletedProcess(command, return_code)

    monkeypatch.setattr(run_challenges, "load_challenges", lambda: (challenge,))
    monkeypatch.setattr(run_challenges, "_revision", lambda: "revision")
    monkeypatch.setattr(run_challenges.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["run_challenges", "--results", str(results_path)])

    assert run_challenges.main() == return_code
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    assert payload["revision"] == "revision"
    assert payload["results"][0]["outcome"] == ("passed" if return_code == 0 else "failed")
    assert payload["results"][0]["prevention"] == (
        "not_evaluated_public_oracle_passed"
        if return_code == 0
        else "not_evaluated_public_oracle_failed"
    )
