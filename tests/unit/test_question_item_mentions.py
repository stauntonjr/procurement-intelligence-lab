"""Literal catalog support does not guess aliases or collapse ambiguity."""

import pytest

from procurement_intelligence_lab.application.question_intent import canonical_item_mentions


@pytest.mark.parametrize(
    "question,items,expected",
    [
        ("Compare GPU-A", ("GPU-A", "GPU-B"), ("GPU-A",)),
        ("Compare gpu-a.", ("GPU-A",), ("GPU-A",)),
        ("Compare GPU-A and GPU-B", ("GPU-B", "GPU-A"), ("GPU-A", "GPU-B")),
        ("Compare the GPU", ("GPU-A", "GPU-B"), ()),
        ("Compare GPU-AB", ("GPU-A",), ()),
        ("Compare GPU-A-extra", ("GPU-A",), ()),
        ("GPU-A, GPU-A", ("GPU-A", "GPU-A"), ("GPU-A",)),
    ],
)
def test_literal_mentions(question: str, items: tuple[str, ...], expected: tuple[str, ...]) -> None:
    assert canonical_item_mentions(question, items) == expected
