# Explicit BOM normalization adoption

Issue #209; parent #31; ADR-022 and ADR-017. Extend the approved core-stage adoption,
retaining the installed three-stage default. Implement inline with one independent final review.

## Contract and design

`BomNormalizationPolicy` declares quantity unit, price denominator unit (each/dozen), and a
three-uppercase-letter currency label. Its content-derived identity enters normalization provenance.
`BomNormalize.normalize(MappedDocument, provenance=...)` implements the existing shared Protocol.
It returns one source-linked observation per field, preserving source order and source-row identity.
Quantities become exact Decimal each; prices remain Decimal in the declared currency/denominator.
SKU/description stay unchanged; missing/unmapped fields remain unresolved. ASCII fixed-point
numbers only, at most 128 characters; signed/fractional values retained and no ambient rounding.
Source observation time/scope are authoritative. No assertion, matching, authority or persistence.

An application wrapper composes the current three stages with NormalizeStrategy. It validates
returned lineage and provenance and records an actual fourth transformation. An immutable batch
receipt identifies successful empty normalization without inventing an observation. The real CLI
opts in with `--normalization-policy`; absent flag retains its previous payload.

## Tasks

1. Add failing domain contract tests for exact decimals/unit conversion, context independence,
   unresolved source values, unmapped fields, duplicate rows, policy/profile validation, scope/time
   and source evidence. Implement policy and normalizer in `domains/procurement/normalization.py`;
   add typed normalization failure under platform errors.
2. Add failing application/public CLI tests for opt-in/default behavior, four-stage parentage,
   empty batch receipts, changed-policy identity and invalid values/config. Implement wrapper in
   `application/normalized_document_stages.py`, explicit bootstrap wiring and strict boundary loader.
3. Add nine-source deterministic normalization conformance, clean-wheel acceptance and docs:
   adoption contract, ADR-022, README, milestone map and handoff. Preserve legacy fixtures and callers.
4. Run focused tests, `make check`, `make package-smoke`, 29 public challenge/mutation checks;
   retain exact-revision semantic JSON and fresh independent review. Merge only with required CI
   green and actionable review threads resolved; verify main CLI/conformance and close only #209.

## Review focus

- Missing quantity must not become zero; raw text/evidence and status survive normalization.
- Decimal multiplication must remain exact under a hostile ambient context.
- Unit/currency are explicit policy; changing content changes IDs without changing upstream outputs.
- Duplicate/missing SKU rows must not collapse into a canonical entity.
- Empty input emits a real batch receipt and event, never a fabricated observation.

## Execution evidence

Baseline at main `c9a3c83`: 98 shared-stage service/adapter/CLI tests passed. Planning audit found
no missing configured fields/labels/milestones/views. Hosted read-only audit 39362894091 attempt 2
passed on that revision; its advisory findings were reviewed. Confirmed unrelated drift remains
#109's unchecked #112/#115 and the duplicate ADR-033 filenames. Historical branch notes are
explicitly superseded; missing-intake suggestions do not prove absent Issue linkage.
