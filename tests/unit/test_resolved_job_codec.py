from pathlib import Path

from procurement_intelligence_lab.bootstrap import archive_codec
from procurement_intelligence_lab.platform.processing.resolved_contracts import (
    ResolvedJobJournalReceipt,
)
from procurement_intelligence_lab.platform.processing.resolved_lifecycle import (
    submission_transition,
)
from tests.local_prefix_job_fixtures import NOW
from tests.resolved_job_fixtures import job_input


def test_new_job_graph_roundtrip_uses_distinct_tags_and_preserves_raw_catalog(tmp_path: Path):
    job, _, _ = job_input(tmp_path)
    codec = archive_codec()
    encoded = codec.dumps(job)
    assert "ResolvedJobDefinition" in encoded
    assert codec.dumps(codec.loads(encoded)) == encoded
    receipt = ResolvedJobJournalReceipt(submission_transition(job, now=NOW))
    assert codec.loads(codec.dumps(receipt)) == receipt
