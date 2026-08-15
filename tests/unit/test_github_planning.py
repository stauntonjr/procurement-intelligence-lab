"""Tests for the credentialed GitHub planning harness."""

import json
from pathlib import Path

import pytest

from tools.github_planning import (
    DesiredView,
    delete_view,
    load_config,
    missing_names,
    plan_view_operations,
    require_expected_identity,
)


def test_view_plan_is_idempotent_when_live_state_matches() -> None:
    desired = [DesiredView("Evidence queue", "TABLE_LAYOUT", "Evidence:Yes")]
    existing = [
        {
            "id": "PVTV_1",
            "name": "Evidence queue",
            "layout": "TABLE_LAYOUT",
            "filter": "Evidence:Yes",
        }
    ]

    assert plan_view_operations(existing, desired) == []


def test_view_plan_creates_missing_and_updates_drifted_views() -> None:
    desired = [
        DesiredView("Missing", "TABLE_LAYOUT", "is:issue"),
        DesiredView("Drifted", "BOARD_LAYOUT", "status:Todo"),
    ]
    existing = [
        {
            "id": "PVTV_2",
            "name": "Drifted",
            "layout": "TABLE_LAYOUT",
            "filter": None,
        }
    ]

    operations = plan_view_operations(existing, desired)

    assert [
        (operation.action, operation.desired.name, operation.view_id) for operation in operations
    ] == [
        ("create", "Missing", None),
        ("update", "Drifted", "PVTV_2"),
    ]


def test_missing_names_is_ordered_and_ignores_extra_live_state() -> None:
    assert missing_names(["Status", "Risk", "Area"], ["Status", "Area", "Extra"]) == ["Risk"]


def test_load_config_rejects_non_object(tmp_path: Path) -> None:
    path = tmp_path / "planning.json"
    path.write_text(json.dumps([]), encoding="utf-8")

    with pytest.raises(TypeError, match="JSON object"):
        load_config(path)


def test_load_config_rejects_missing_required_section(tmp_path: Path) -> None:
    path = tmp_path / "planning.json"
    path.write_text(json.dumps({"repository": "owner/repo"}), encoding="utf-8")

    with pytest.raises(ValueError, match="missing 'project'"):
        load_config(path)


def test_load_config_rejects_missing_nested_project_key(tmp_path: Path) -> None:
    path = tmp_path / "planning.json"
    path.write_text(
        json.dumps(
            {
                "repository": "owner/repo",
                "project": {"owner": "owner", "number": 6, "id": "PVT_1"},
                "required_fields": [],
                "required_milestones": [],
                "required_labels": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing 'views'"):
        load_config(path)


def test_delete_view_refuses_a_configured_view_before_network_access() -> None:
    config = {
        "project": {
            "owner": "owner",
            "number": 6,
            "views": [{"name": "Managed", "layout": "TABLE_LAYOUT", "filter": ""}],
        }
    }

    with pytest.raises(ValueError, match="remove configured view"):
        delete_view(config, name="Managed", apply=True)


def test_identity_guard_rejects_wrong_authenticated_login() -> None:
    with pytest.raises(RuntimeError, match="does not match owner"):
        require_expected_identity(
            owner="expected",
            expected_project_id="PVT_1",
            viewer="other",
            live_project_id="PVT_1",
        )


def test_identity_guard_rejects_wrong_project_node() -> None:
    with pytest.raises(RuntimeError, match="does not match configured"):
        require_expected_identity(
            owner="expected",
            expected_project_id="PVT_1",
            viewer="expected",
            live_project_id="PVT_2",
        )
