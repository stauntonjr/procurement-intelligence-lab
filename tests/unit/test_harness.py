"""M0 harness smoke tests."""

from procurement_intelligence_lab.bootstrap import build_application


def test_composition_root_is_explicit_placeholder() -> None:
    assert build_application() is None
