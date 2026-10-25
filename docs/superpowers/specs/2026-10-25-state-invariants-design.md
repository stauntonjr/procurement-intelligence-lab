# Expected/observed state invariant completion

Binding specification: Issue #118, accepted ADR-020, and the existing expected/observed public Python API. The owner selected #118 by instructing proceed on 2026-10-25. This enforces existing semantics; it introduces no authority, aggregation, anomaly or unknown-value policy.

## Intent and boundary

Intrinsic construction must reject negative/non-finite quantities, missing evidence and naive as-of timestamps. Expected/observed pairs require matching canonical key and complete StateScope. Every nonnegative finite Decimal, including zero, fractions and overages, remains representable. Missing observation remains None with UNKNOWN freshness; existing outstanding arithmetic is unchanged. Distinct observation timestamps are allowed; comparison keeps the existing latest-in-scope/as-of rule.

Current constructors already implement most of this. The remaining reproducible gap is checking only `tzinfo is None`: a tzinfo implementation can return None from utcoffset(), meaning the datetime is still naive. Both constructors and both public helper cutoffs must reject it, including empty helper inputs.

## Approach

Use one private as-of guard in domains/procurement/state.py and invoke it at all four existing boundaries. It requires both a tzinfo and a non-None UTC offset, raises existing TemporalContractError (a ValueError subclass), and preserves valid offsets and messages. Keep existing quantity/key/scope/evidence validation and valid-output calculations unchanged.

Application-only validation cannot satisfy direct-construction acceptance. Adding new state models or generalized platform validation would expand this bounded Issue. The existing Issue/ADR already select intrinsic domain validation.

## Evidence and limits

Expand C008 regression coverage across all six quantity fields, non-finite and negative values, nonnegative properties, zero/fractions, empty evidence, each scope axis/key mismatch, partial/missing observations and overages. Add C031 for the shipped offsetless-tzinfo defect with exact introducing revision and an executable known-bad guard mutation. Keep C008's original oracle/mutation compatible.

Exercise the actual public constructors/helpers in the checkout and from a clean installed wheel; retain the normal HTTP/CLI integration regression suite. Preserve package metadata/resources, policy and all prior valid outputs. Run make check with disposable real Postgres, package smoke and all public challenge/known-bad checks. Record public-oracle results separately from agent-quality evaluation.

One independent final whole-branch review follows inline implementation, with any important correction verified RED/GREEN and rerun affected checks. Required checks precede normal protected merge. Only #118 closes after main acceptance; #109, M4 and other broader work remain open. Update ADR-020, handoff and Project evidence. Cleanup removes only this slice's recorded worktree/container/environments.
