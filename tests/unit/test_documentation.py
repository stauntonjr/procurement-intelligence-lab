from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_prospective_reconciliation_contract_is_durable() -> None:
    adr = ROOT / "docs/adr/034-prospective-human-reconciliation.md"
    assert adr.exists()
    text = adr.read_text()
    for phrase in (
        "item + project + site",
        "server-owned `effective_at`",
        "required rationale",
        "losing assertions",
        "retroactive",
        "external action",
    ):
        assert phrase in text

    fields = "`run_id`, `brief_id`, `digest`, `outcome`, `selected_claim_id`, and `rationale`"
    for relative in (
        "docs/product/local-browser-review-v1.md",
        "docs/product/local-qwen-review-v1.md",
    ):
        contract = " ".join((ROOT / relative).read_text().split())
        assert "POST `/api/reconcile`" in contract
        assert fields in contract
        assert "exactly two eligible conflicting required-quantity claims" in contract
