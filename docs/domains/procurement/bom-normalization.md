# Explicit BOM normalization

Issue #209 is a bounded adoption of #31 under ADR-022. The existing BOM caller runs
`INGEST → STRUCTURE → MAP` by default. Supplying a normalization policy adds the existing
`NormalizeStrategy` contract after mapping; the general physical planner still does not execute.

```bash
python -m procurement_intelligence_lab.interfaces.bom_stages \
  src/procurement_intelligence_lab/examples/synthetic_bom_stages.xlsx \
  --context tests/fixtures/bom-stages/context.json \
  --normalization-policy tests/fixtures/bom-stages/normalization-policy.json
```

The explicit policy is strict JSON with exactly four text fields:

```json
{"profile":"bom-decimal@1","quantity_unit":"each","currency":"USD","price_unit":"each"}
```

`quantity_unit` and `price_unit` each admit `each` or `dozen`. Currency is an explicit
three-uppercase-letter label, not an inferred fact or a claim of ISO registry validation.
The fixture's USD/each declarations are synthetic experiment inputs. A real source without a
known unit/currency requires an informed declaration before this profile can be used.

## Governing rules

- Quantity becomes a Decimal in `each`; a declared dozen multiplies by exactly 12. Price remains
  Decimal in `CURRENCY/price_unit`. No denominator conversion, rounding, or exchange-rate lookup.
- Numeric syntax is ASCII `[+-]?[0-9]+(\.[0-9]+)?`, after trimming surrounding ASCII space,
  tab, CR and LF, with at most 128 characters in the trimmed lexeme. Grouping separators,
  currency symbols, exponent notation, non-finite values and non-text source numbers fail closed.
- Zero, signed negative and fractional values remain observations. This stage neither approves
  them for procurement nor invents a positivity/integrality rule. Conversion uses an isolated
  Decimal context large enough for the admitted range; ambient precision/traps cannot round it.
- SKU and description retain exact text. No case folding, identifier canonicalization or matching.
- Every mapped field yields one observation in source order. Missing values remain unresolved
  with their mapping diagnostic. Extra unmapped fields remain unresolved with an explicit
  normalization diagnostic and their original raw field. A source-row hint, separate from SKU,
  keeps duplicate/missing-SKU rows distinct; it is not a canonical entity identity.
- Scope and effective time retain the source scope and observation timestamp. Execution/capture
  time does not become an authority/effective-date decision. No stale/as-of filtering occurs.

## Evidence and identity

Procurement owns the frozen policy and normalizer. The platform's existing NormalizedObservation
and NormalizeStrategy stay domain-neutral; bootstrap wires the concrete implementation explicitly.
Policy content has a deterministic reference retained in normalization provenance, input snapshot
IDs and the CLI payload. Changing policy preserves upstream artifact/structure/mapping output and
changes normalization provenance, observation IDs and batch identity.

Each observation retains its exact MappedField, raw value, original source artifact/hash/location,
status, diagnostic, scope/time and component provenance. The mapped document in the same payload
links to its structured document and original versioned artifact. The application rejects dropped
or duplicated observations, foreign fields/scope/time or ignored injected provenance.

The normalization batch is an application receipt, not an additional platform logical stage.
Its content-derived ID and all observation IDs are outputs of the fourth transformation, whose
parent is the mapping event and whose inputs include the mapped document and policy reference.
A header-only document produces an empty observation tuple and a real batch receipt/event; it
does not fabricate a source claim. This process-local receipt does not establish durable replay.

## Failure boundary and acceptance

Malformed/missing policy JSON or unsupported declarations return
`pil.input.normalization_policy_invalid`. Unsupported mapping profiles, inconsistent fields or
ambiguous/invalid numbers return `pil.interpretation.normalization_invalid`. Returned stage
lineage violations remain `pil.input.document_stage_invalid`. The CLI exits 2, writes stderr JSON,
and emits no partial-success stdout. Argument syntax/help retains argparse behavior.

Contract tests cover signed/zero/fractional/maximum-precision numbers, exact dozen conversion,
hostile Decimal context, missing/unmapped fields, duplicate rows, scope/version/time identity and
typed profile/value failures. Real subprocess CLI tests prove default compatibility, opt-in,
policy changes, evidence/parent links and empty receipts. Clean-wheel smoke exercises both modes,
typed invalid-policy failure and stable output across two clean installations outside checkout.

```bash
uv run --extra workflow python -m tools.benchmark_bom_normalization \
  --output /tmp/bom-normalization-conformance.json
```

The conformance runner verifies clean Git HEAD and imported source identity, pins nine workbook
hashes and independently transcribed XML expectations over 1,608 observations, and checks attached
source fields/evidence, scope/time and unique IDs. Reports retain manifest/revision/policy identity,
latency and zero inference calls/cost; compute cost is unknown. Wrong hashes/gold and dirty or
mismatched revisions cannot report success. This is deterministic profile conformance, not model,
OCR or production quality evidence. The corpus manifest/gold stays outside the installed wheel.

## Remaining work

#31 remains open for dates/time zones, broader unit conversions, currency/identifier/revision
policies and richer mapped sources under #32. #33 owns source assertions and conflicting claims;
#34 owns the wider inspection/query surface. No assertions, entity resolution, authority selection,
canonical state, database, durable ledger/content/replay or general package executor is added.
