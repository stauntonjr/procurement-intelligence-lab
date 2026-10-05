import json
from pathlib import Path

import pytest

from tools.record_demo_story import (
    RecordingConfig,
    build_banner,
    build_typing_events,
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
