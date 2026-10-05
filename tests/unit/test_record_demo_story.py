import json
from pathlib import Path

import pytest

from tools.record_demo_story import (
    RecordingConfig,
    build_banner,
    build_typing_events,
    extract_reconciliation_result,
    extract_unresolved_facts,
    ordered_slides,
    prepare_output,
    public_report,
)


def test_slides_are_ordered_numerically_and_safe_area_is_fixed(tmp_path: Path) -> None:
    for number in (8, 2, 1, 3):
        (tmp_path / f"slide-{number}.png").touch()
    slides = ordered_slides(tmp_path)
    assert [path.name for path in slides] == [
        "slide-1.png",
        "slide-2.png",
        "slide-3.png",
        "slide-8.png",
    ]
    config = RecordingConfig(
        origin="http://127.0.0.1:8001",
        token_file=tmp_path / "token",
        slides=tmp_path,
        output=tmp_path / "fresh",
    )
    assert (config.width, config.height, config.banner_height) == (1440, 900, 96)


def test_banner_requires_complete_five_question_explanation() -> None:
    values = {
        "who": "A buyer and reviewer",
        "what": "Resolve one quantity conflict",
        "why": "Avoid false certainty",
        "how": "Trace sources through policy",
        "when": "Before approval",
    }
    banner = build_banner(**values)
    assert banner == values
    with pytest.raises(ValueError, match="why"):
        build_banner(**(values | {"why": ""}))


def test_visible_input_is_character_by_character_not_atomic_fill() -> None:
    assert build_typing_events("GPU-C", delay_ms=45) == [
        {"kind": "key", "text": character, "delay_ms": 45} for character in "GPU-C"
    ]


def test_public_report_redacts_token_and_refuses_existing_output(tmp_path: Path) -> None:
    token_file = tmp_path / "token"
    token_file.write_text("private-token-value")
    config = RecordingConfig(
        origin="http://127.0.0.1:8001",
        token_file=token_file,
        slides=tmp_path,
        output=tmp_path / "fresh",
    )
    report = public_report(config, {"scenario": "GPU-C"})
    serialized = json.dumps(report)
    assert "private-token-value" not in serialized
    assert "token" not in serialized.lower()
    prepare_output(config.output)
    with pytest.raises(FileExistsError, match="never overwrite"):
        prepare_output(config.output)


def test_recording_requires_the_narrated_unresolved_requirement() -> None:
    evidence = [
        {"evidence_id": "bom-a", "artifact_id": "bom-a.xlsx"},
        {"evidence_id": "bom-b", "artifact_id": "bom-b.xlsx"},
        {"evidence_id": "order", "artifact_id": "po.xlsx"},
    ]
    payload = {
        "workflow": {
            "brief": {
                "content_json": json.dumps(
                    {
                        "status": "not_assessed",
                        "reason": "unresolved_requirement",
                        "required_quantity": None,
                        "ordered_quantity": "2",
                        "evidence": evidence,
                    }
                )
            }
        }
    }
    facts = extract_unresolved_facts(payload)
    assert facts == {
        "status": "not_assessed",
        "reason": "unresolved_requirement",
        "required_quantity": None,
        "ordered_quantity": "2",
        "evidence_ids": ["bom-a", "bom-b", "order"],
    }
    bad = json.loads(json.dumps(payload))
    bad["workflow"]["brief"]["content_json"] = json.dumps(
        {
            "status": "not_assessed",
            "reason": "missing_observation",
            "required_quantity": "4",
            "ordered_quantity": None,
            "evidence": evidence,
        }
    )
    with pytest.raises(ValueError, match="unresolved_requirement"):
        extract_unresolved_facts(bad)


def test_recording_requires_exact_prospective_reconciliation_result() -> None:
    payload = {
        "decision": {
            "decision_id": "decision-1",
            "outcome": "select_governing_revision",
            "selected_claim_id": "claim-b",
            "candidate_claim_ids": ["claim-a", "claim-b"],
            "rationale": "Revision B governs this item prospectively.",
            "subject_key": "GPU-C",
            "scope": {"tenant_id": "local-review", "project_id": "atlas", "site_id": "default"},
            "effective_at": "2026-10-05T12:00:00+00:00",
            "evidence_ids": ["bom-a", "bom-b"],
        },
        "current_assessment": {
            "status": "shortfall",
            "required_quantity": "6",
            "ordered_quantity": "2",
        },
    }
    result = extract_reconciliation_result(
        payload,
        historical={
            "status": "not_assessed",
            "reason": "unresolved_requirement",
            "required_quantity": None,
            "ordered_quantity": "2",
            "evidence_ids": ["bom-a", "bom-b", "order"],
        },
        original_cutoff="2026-10-01T00:00:00Z",
    )
    assert result["exact_scope"] == {
        "tenant_id": "local-review",
        "project_id": "atlas",
        "site_id": "default",
        "item": "GPU-C",
    }
    assert result["historical_assessment_unchanged"] is True
    assert result["selected_claim_id"] == "claim-b"
    assert result["retained_evidence_ids"] == ["bom-a", "bom-b", "order"]

    invalid = json.loads(json.dumps(payload))
    invalid["decision"]["effective_at"] = "2026-09-01T00:00:00+00:00"
    with pytest.raises(ValueError, match="prospective"):
        extract_reconciliation_result(
            invalid,
            historical={
                "status": "not_assessed",
                "reason": "unresolved_requirement",
                "required_quantity": None,
                "ordered_quantity": "2",
                "evidence_ids": ["bom-a", "bom-b", "order"],
            },
            original_cutoff="2026-10-01T00:00:00Z",
        )
