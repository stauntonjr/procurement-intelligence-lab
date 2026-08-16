import json
from pathlib import Path

import pytest

from tools.check_actions_supply_chain import validate, workflow_references


def test_all_workflow_actions_are_immutable_and_allowlisted() -> None:
    assert workflow_references()
    assert validate() == []


def write_policy(path: Path, repositories: list[str]) -> None:
    path.write_text(
        json.dumps(
            {"allowed_actions": [{"repository": repository} for repository in repositories]}
        ),
        encoding="utf-8",
    )


def test_workflow_references_discovers_yml_and_yaml(tmp_path: Path) -> None:
    (tmp_path / "one.yml").write_text("- uses: owner/one@revision # v1\n", encoding="utf-8")
    (tmp_path / "two.yaml").write_text("uses : owner/two@revision # v2\n", encoding="utf-8")

    assert [reference[2] for reference in workflow_references(tmp_path)] == [
        "owner/one@revision",
        "owner/two@revision",
    ]


@pytest.mark.parametrize(
    ("reference", "comment", "expected"),
    [
        ("malformed", "v1", "malformed Action reference"),
        ("stranger/action@" + "a" * 40, "v1", "is not allowlisted"),
        ("owner/action@v1", "v1", "is not pinned to a full SHA"),
        ("owner/action@" + "a" * 40, "release", "needs a readable version comment"),
        ("owner/action@" + "a" * 40, "issue 123", "needs a readable version comment"),
    ],
)
def test_validate_rejects_unsafe_references(
    tmp_path: Path, reference: str, comment: str, expected: str
) -> None:
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "test.yml").write_text(f"- uses: {reference} # {comment}\n", encoding="utf-8")
    allowlist = tmp_path / "allowlist.json"
    write_policy(allowlist, ["owner/action"])

    errors = validate(workflow_dir=workflow_dir, allowlist=allowlist)

    assert any(expected in error for error in errors)


@pytest.mark.parametrize(
    ("contents", "error_type"),
    [
        ("not-json", "JSONDecodeError"),
        (json.dumps({"wrong_key": []}), "KeyError"),
    ],
)
def test_validate_fails_closed_on_invalid_allowlist(
    tmp_path: Path, contents: str, error_type: str
) -> None:
    allowlist = tmp_path / "allowlist.json"
    allowlist.write_text(contents, encoding="utf-8")

    errors = validate(workflow_dir=tmp_path, allowlist=allowlist)

    assert len(errors) == 1
    assert "invalid actions allowlist" in errors[0]
    assert error_type in errors[0]


def test_validate_fails_closed_on_missing_allowlist(tmp_path: Path) -> None:
    errors = validate(workflow_dir=tmp_path, allowlist=tmp_path / "missing.json")

    assert len(errors) == 1
    assert "invalid actions allowlist" in errors[0]
    assert "FileNotFoundError" in errors[0]
