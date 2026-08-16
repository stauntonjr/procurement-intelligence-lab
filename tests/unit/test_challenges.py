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
        '{"id":"C001","title":"x","introducing_commit":"x","oracle":"x",'
        '"test_command":["x"],"surfaces":["x"],"prevention":["x"]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(run_challenges, "ROOT", tmp_path)
    monkeypatch.setattr(run_challenges, "MANIFESTS", tmp_path)

    with pytest.raises(ValueError, match="known_bad"):
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
        "introducing_commit": "abc123",
        "oracle": "test oracle",
        "known_bad": "test mutation",
        "known_bad_mutation": [{"path": "x.py", "find": "good", "replace": "bad"}],
        "known_bad_failure_pattern": "expected failure",
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


def test_apply_known_bad_mutation_is_detected(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "behavior.py"
    source.write_text("behavior = 'good'\n", encoding="utf-8")
    challenge: run_challenges.Challenge = {
        "id": "C001",
        "title": "test challenge",
        "introducing_commit": "abc123",
        "oracle": "test oracle",
        "known_bad": "test mutation",
        "known_bad_mutation": [{"path": "behavior.py", "find": "'good'", "replace": "'bad'"}],
        "known_bad_failure_pattern": "expected failure",
        "test_command": ["uv", "run", "pytest", "-q", "test_behavior.py"],
        "surfaces": ["test"],
        "prevention": ["test"],
    }

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        check: bool,
        capture_output: bool,
        text: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        assert command[:3] == [sys.executable, "-m", "pytest"]
        assert (cwd / "behavior.py").read_text(encoding="utf-8") == "behavior = 'bad'\n"
        assert check is False and capture_output is True and text is True
        assert str(cwd / "src") in env["PYTHONPATH"]
        return subprocess.CompletedProcess(command, 1, "", "expected failure")

    monkeypatch.setattr(run_challenges, "ROOT", tmp_path)
    monkeypatch.setattr(run_challenges.subprocess, "run", fake_run)

    completed, duration = run_challenges.run_known_bad(challenge)

    assert completed.returncode == 1
    assert duration >= 0


@pytest.mark.parametrize(
    (
        "known_bad_return_code",
        "known_bad_output",
        "expected_exit",
        "expected_outcome",
        "expected_detection",
    ),
    [
        (1, "expected failure", 0, "rejected", "public_oracle_detected_known_bad"),
        (0, "", 1, "survived", "public_oracle_missed_known_bad"),
        (1, "unrelated error", 1, "wrong_failure", "public_oracle_wrong_known_bad_failure"),
    ],
)
def test_main_requires_known_bad_behavior_to_fail(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    known_bad_return_code: int,
    known_bad_output: str,
    expected_exit: int,
    expected_outcome: str,
    expected_detection: str,
) -> None:
    challenge: run_challenges.Challenge = {
        "id": "C001",
        "title": "test challenge",
        "introducing_commit": "a" * 40,
        "oracle": "test oracle",
        "known_bad": "test mutation",
        "known_bad_mutation": [{"path": "x.py", "find": "good", "replace": "bad"}],
        "known_bad_failure_pattern": "expected failure",
        "test_command": ["test-command"],
        "surfaces": ["test"],
        "prevention": ["test"],
    }
    results_path = tmp_path / "results.json"
    monkeypatch.setattr(run_challenges, "load_challenges", lambda: (challenge,))
    monkeypatch.setattr(run_challenges, "_revision", lambda: "revision")

    def fake_current_run(
        command: list[str], *, cwd: Path, check: bool
    ) -> subprocess.CompletedProcess[str]:
        assert cwd == run_challenges.ROOT and check is False
        return subprocess.CompletedProcess(command, 0)

    def fake_known_bad(
        _: run_challenges.Challenge,
    ) -> tuple[subprocess.CompletedProcess[str], float]:
        return (
            subprocess.CompletedProcess([], known_bad_return_code, known_bad_output, ""),
            0.1,
        )

    monkeypatch.setattr(run_challenges.subprocess, "run", fake_current_run)
    monkeypatch.setattr(run_challenges, "run_known_bad", fake_known_bad)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_challenges", "--verify-known-bad", "--results", str(results_path)],
    )

    assert run_challenges.main() == expected_exit
    result = json.loads(results_path.read_text(encoding="utf-8"))["results"][0]
    assert result["known_bad_outcome"] == expected_outcome
    assert result["known_bad_return_code"] == known_bad_return_code
    assert result["detection"] == expected_detection
