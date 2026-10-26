# Issue #20: shared vocabulary acceptance

Baseline main: `03b08260e8888f77840a47354d968f561019e861`.
This is a documentation-only consolidation of accepted ADR-003/ADR-022 and existing contracts.
No business calculation, enum, schema, adapter, public caller, package resource, model or authority
changes. Semantic evidence JSON and a clean artifact rebuild are not applicable to this slice.
No regression challenge is added: no shipped runtime semantic defect is being repaired.

## Acceptance matrix

| Issue criterion | Documentation / existing executable evidence |
|---|---|
| Source assertions are claims, not truth | Shared glossary SourceAssertion row and evidence/authority section; context-free legacy records are explicitly distinguished from the provenance-complete path |
| ER after assertions, before canonical state | Conceptual sequence, fixed twelve-stage catalog and intermediate record explanation; existing registry and universal-stage tests |
| Explicit governing-claim choice | Separate CanonicalizedAssertion, ReconciliationDecision and OperationalState definitions; procurement policy v1/ADR-023 links, retention of losing claims |
| Provenance and epistemic context survive | Per-concept source/type links; OBSERVED/INFERRED/UNRESOLVED distinguished from dispute, resolution, freshness and authority; source drill-down and missing-link boundaries |
| State, prediction, decision and action remain distinct | Separate glossary rows, scoped input/authority/approval/idempotency explanation; existing non-procurement complete-topology fixture and action-contract tests |
| Glossary cross-references Issue contracts | Every artifact-through-action row links its governing Issue(s); broader open acceptance is not claimed complete |

## Verification

- `UV_CACHE_DIR=/tmp/pil-uv-cache uv run --extra workflow pytest -q tests/contract/test_stage_contract_registry.py tests/unit/test_universal_stage_semantics.py tests/regression/test_stage_contract_invariants.py`:27 passed on baseline and documentation candidate.
- `UV_CACHE_DIR=/tmp/pil-uv-cache uv run --extra workflow make check-fast`:passed; formatting/lint/type/architecture/challenge-manifest/semantic-harness/PR-contract/dependency/Actions controls unchanged.
- `git diff --check`:passed. Local Markdown targets in the initial nine changed pages:241 checked,
  zero missing (see documentation-validation.json). No source, test, tool, example, package,
  workflow or evaluation bytes changed against baseline.
- Live preflight and structural Project audit:authenticated stauntonjr;129 Project items/25 fields/
  11 views;zero missing configured fields, labels, milestones or views (planning-before.json).
- Hosted advisory run40247832626 succeeded on the baseline; its findings and direct dispositions
  are recorded in the linked project audit. This is not source review or provider replacement.

## Review and delivery

One independent whole-branch architecture/documentation review is requested against the committed
candidate. The final reviewed revision, findings and required-check/main delivery receipts belong
in Issue #20 and the PR; this pre-review record does not assert that delivery has happened.
The shared glossary is `docs/architecture/semantic-model.md`; the exact scoped runtime boundaries
remain in the linked #226/#236/#239 contracts. Broader M0–M9 milestones remain open.
