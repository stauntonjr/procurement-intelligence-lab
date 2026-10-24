# Independent whole-branch architecture and semantic review

Reviewed revision: `0890acb8efa78621b31988e57c97599beda7e261`.
Baseline: `88d32d4f5da0f5cae500d465f80173b213ee71d0`.
Review date: 2026-10-24. One independent review; no product edits or delegated reviews.

Read AGENTS.md, current handoff, retained verified Issues235/236, ADR046,
approved design and implementation plan, review diff, and progress ledger. Applied
architecture-review and review-semantic-change, plus adapter/public/package review guidance.
Inspected actual changed source, tests, fixtures, probe and package-smoke integration;
traced reused five-stage receipt, source validation, archive and codec contracts.

## Findings and verdict

- Critical: none found.
- Important: none found.
- Minor: none found.

The reviewed code is fit for the bounded approved slice, subject to the outstanding
Task7 qualification and delivery gates below. This is not completion or merge approval
while required deterministic checks or final evidence remain pending.

## Review-focus conclusions

1. Catalog semantic identity sorts exact keys and excludes original JSON bytes. Raw bytes
   are reparsed against the snapshot and retained separately; computation and receipt
   projections distinguish format changes. Execution, storage and public recovery tests
   verify current versus first-retained audit evidence.
2. The six-stage result binds its exact actual embedded prefix. ArchivedResolvedPrefix
   separately binds the first retained prefix using full computation equality, allowing
   different completion receipts. Actual Postgres and public tests cover earlier retention.
3. Outcome order and exact mention/claim membership are checked; procurement independently
   checks complete source rows and exact HAS_SKU evidence. Duplicate text retains distinct
   row decisions. Linked/unlinked membership is exhaustive and null-SKU claims stay visible.
4. Namespace/policy and actual sixth registration are admitted before source/storage access.
   Public tests intentionally remove the source. Fixed-offset canonical encoding preserves
   differing offset identities while comparisons admit equal instants.
5. Codec reconstruction runs intrinsic constructors, storage verifies source/prefix joins,
   and the reader independently validates recorded procurement semantics. Tests reseal
   malformed graphs and construct coherent but policy-invalid graphs; these fail rather
   than becoming successful recovery. Database-owner arbitrary coherent rewriting is not
   an authenticity guarantee and is outside the stated boundary.

## Seven scenario families inspected

| Family | Review disposition |
|---|---|
| Empty/missing/unknown | Empty document has real sixth event; explicit empty catalog abstains; missing catalog fails; null/blank SKU produces unlinked claims; invalid normalized mention abstains. |
| One/many/duplicate/conflict | Unique/no-match/collision outcomes, raw duplicate rejection, duplicate source-row evidence, complete catalog retention and immutable first-retention conflict checks inspected. |
| Scope/time/as-of | Full four-field encoded scope, future catalog/source admission through reused prefix contract, equal/older times and offset identity inspected. No unstated freshness policy. |
| Numeric/boundaries | Zero/negative/fractional/unknown claims preserved; 0/1/256/257 keys, 256-character keys and 32KiB input bounds covered. Existing 16MiB/50,000-node/depth64 codec limits remain unchanged. |
| Unsupported/malformed | Strict duplicate/unknown fields, types, Unicode, policy, descriptor/settings/code pins and stop boundary; rejection before absent source/storage inspected. |
| Public/artifact | Actual subprocess execution/recovery tests, installed base3.12/base3.13/storage receipts, atomic append/rollback/race/ack-loss code and tests inspected. Final qualification remains separate. |
| Safe counterexample | First-five runner/types and old codec wire behavior preserved; neutral non-procurement executor fixture supported; no source-inferred catalog, unresolved canonical link, score, governed state or six-stage local-job widening. |

## Independent verification and evidence limits

Ran at reviewed revision:

```text
UV_CACHE_DIR=/tmp/pil-uv-cache uv run --extra workflow pytest -q tests/unit/test_resolution_inputs.py tests/unit/test_planned_bom_resolution.py tests/unit/test_resolved_execution.py tests/unit/test_resolved_execution_contracts.py tests/unit/test_resolved_execution_archive_codec.py tests/contract/test_planned_resolved_bom_execution.py tests/integration/test_execute_resolved_package_cli.py
92 passed in 8.04s
git diff --check 88d32d4f5da0f5cae500d465f80173b213ee71d0..HEAD
passed
```

Inspected external `/tmp/pil-resolve-qualification/{base312,base313,storage}-receipt.json`:
all passed, wheel SHA256 `318222913bb98e9851144d86ada7659ebc18836ed0078e8eadd3445140e4e3cb`.
Base runtimes3.12.3/3.13.14 explicitly exercised absent storage extra; storage receipt
records source/input deletion and exact source/catalog recovery. Baseline probe log fails
because the new command is absent. These receipts use synthetic `code_revision=test-revision`;
they do not independently attest the final Git revision or merged-main pins.
Postgres tests were inspected, not independently rerun during this review.

Full `make check`, final `make package-smoke`, exact-source artifact attribution, schema-valid
latest-revision semantic evidence, author final-head pass, protected required checks and
merged-main installed proof are still required as applicable. No finding is inferred solely
from these explicitly pending tasks. The six-case corpus demonstrates rule/integration
agreement only (3 accepted,3 abstained); general identity quality, broader M3 completion,
production operation, catalog truth, later stages and six-stage job support are not judged.
