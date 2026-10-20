# Provenance-complete BOM source assertions

Issue #211 adopts `AssertStrategy` after explicit BOM normalization, under #33 and
[ADR-037](../../adr/037-provenance-complete-source-assertion-adoption.md). Run the actual caller:

```bash
python -m procurement_intelligence_lab.interfaces.bom_stages \
  src/procurement_intelligence_lab/examples/synthetic_bom_stages.xlsx \
  --context tests/fixtures/bom-stages/context.json \
  --normalization-policy tests/fixtures/bom-stages/normalization-policy.json --assertions
```

The existing three-stage default and four-stage normalization output remain compatible. ASSERT
requires the explicit normalization policy; it never guesses a unit or currency. The fixture
policy is a synthetic experiment declaration, not a fact inferred from the workbook.

Each normalized observation becomes one immutable claim, in source order. BOM fields map to
`has_sku`, `has_description`, `has_quantity`, `has_unit_price`, or `unmapped_field`. Missing and
unmapped values remain null, unresolved and diagnostic-bearing; the exact normalized observation
and original mapped field are retained. A real zero remains an observed Decimal. Negative and
fractional quantities remain claims, without an approval or positivity decision. Duplicate and
conflicting source rows remain distinct; the row hint is not a canonical entity key.

Each claim's optional shared `SourceAssertionContext` carries the exact observation, captured
artifact, normalization batch/event, explicit recording timestamp, assertion component provenance
and confidence diagnostic. Deterministic confidence is **not estimated**, without a numeric score.
The content hash is the immutable document version; an externally supplied source-version label
remains independently nullable. Source observation time, capture time and assertion recording time
remain distinct. Source scope/time is retained without stale/as-of filtering or authority selection.
Recording must be timezone-aware and cannot precede capture. The composition root injects the
strategy factory and recording time explicitly; no ambient clock or domain-name runtime branching.

Legacy assertions without context retain their established IDs. Context-bearing assertions use
a separate versioned namespace with typed values and derivation context. Null without unresolved
context now fails typed admission; C030 protects this previously admitted runtime defect.
Claims reference the upstream NORMALIZE event. The fifth ASSERT event outputs its application
batch receipt, claims and mentions, with NORMALIZE as parent; there is no event/claim identity
cycle. Header-only input yields an empty claim/mention tuple and a real receipt/event.

Entity mentions use only nonblank source SKU text and attach all row claims with source scope/time.
Missing SKU creates no mention; the public claim includes an explicit missing-mention diagnostic.
All mentions await resolution. The CLI exposes `assertion_batch`, full claim evidence and per-claim
traces through observation → mapped field/document → structured document → captured artifact.
The application rejects dropped/duplicate claims, foreign context/provenance and unsupported
mention lineage. In-memory ledger append retains complete claim objects and conflicting revisions;
the CLI does not persist them. Deterministic replay identity is not an exactly-once guarantee.

Malformed assertion profiles/origins return `pil.interpretation.source_assertion_invalid`;
producer lineage violations return `pil.input.document_stage_invalid`. `--assertions` without
policy returns the latter. Existing normalization/capture failures retain their codes. Semantic
failures produce exit 2, stderr JSON and no partial stdout; argument syntax/help uses argparse.

```bash
uv run --extra workflow python -m tools.benchmark_bom_assertions \
  --output /tmp/bom-assertions-conformance.json
```

The runner requires clean verified HEAD/import origin, pins nine source hashes and independent
worksheet-XML gold for 1,608 claims and 322 mentions, and verifies attached observations, origins,
provenance, IDs and fifth-stage serialization. It records revision, policy/manifest identity,
latency and zero inference calls/cost; compute cost is unknown. Wrong source hashes/gold, dirty
checkouts and revision mismatch cannot report success. This is deterministic synthetic conformance,
not an extractor/model comparison, production quality result or entity-resolution benchmark.
Clean-wheel smoke exercises three/four/five modes and typed dependency failure outside checkout,
with output compared across two clean installations.

#33 stays open for broader assertion profiles, confidence/provenance and conflicting claims across
other document types. #13/#35/#37 retain durable storage/index/replay acceptance; #31 retains broader
normalization. Resolution, governing-source policy, canonical state and general physical-plan
execution remain separate. The next core slice should pin ledger/content serialization, append and
replay semantics against #13/#35/#37 before wiring the assertions into downstream runtime state.
