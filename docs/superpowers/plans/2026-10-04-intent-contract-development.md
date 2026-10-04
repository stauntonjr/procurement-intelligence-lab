# Intent contract development

> Execute inline using superpowers:executing-plans. Owner-authorized continuation of the approved corpus plan, Task 5/G2.

Spec: ../specs/2026-10-03-procurement-demo-corpus-design.md and ../../adr/032-local-model-intent-and-journal.md.
Primary #53; Part of #72/#70. Base 8afd6de, stacked on draft PR182. No merge or deployment.

## Goal and constraints

Investigate safe but unexpected abstentions observed in the frozen pilot. Clarify the existing bounded intent prompt, preserving server-owned scope/cutoff, literal item validation and exact human approval. Requirement governance and approval applicability are read-only review questions, even when governing evidence is unresolved. Document approval is not human approval to save. A selected aware cutoff supplies the query instant; document-relative predicates do not independently request a new cutoff. Calendar boundary wording may use the supplied instant only when consistent with it. Different explicit dates, inconsistent boundaries and unresolved relative query times require clarification; never calculate a replacement instant.

Use only Atlas/Borealis development failures to design the prompt. Generic examples must contain no actual corpus SKU, project, quantity, gold, case ID or query text. Reuse the loaded local Qwen model, endpoint/budgets/schema/guards unchanged. One attempt per question per frozen configuration, no automatic retries. Preserve the original pilot report and database. All 48 previously inspected queries are development regression evidence from now on; historical split names are retained only for accounting. No broad or held-out quality claim; a fresh independently authored evaluation remains a future gate.

## Task 1: Freeze the development contract and honest report labeling

Interfaces: existing pilot CLI/report; produces development_regression evaluation metadata, consumed by Task 3. No new runtime data path.

1. Add a public-runner assertion that every new report declares development_regression and inspected-case limits. Run the integration test before implementation.
Expected: failure because the metadata is absent.
2. Change new-report labeling only; keep original case IDs, texts, expectations, hashes, scoring and original artifacts unchanged.
3. Freeze a small independent development control manifest before any changed-prompt inference. Include governance, document-relative approval, matching/inconsistent calendar boundary, conflicting explicit date, relative date, aliases, multiple items, wrong scope, unsupported action and injection.
4. Run `.venv/bin/python -m pytest -q tests/integration/test_g2_pilot_failure.py tests/unit/test_g2_pilot_runner.py tests/unit/test_g2_pilot_scoring.py`.
Expected: all pass. Commit the contract/report change.

## Task 2: Reproduce and clarify the prompt

Interfaces: PROMPT sent by existing local adapter; unchanged JSON schema and QuestionReviewService remain authority. Task 3 consumes the frozen installed bytes.

1. Run the four original development misses through the existing clean installed CLI, fresh database, one attempt each. Retain every outcome and version.
Expected: reproduce unsupported governance/approval and/or ambiguous boundary abstentions; any different outcome stays recorded.
2. Change only prompt instructions/examples to clarify Task 1's contract. Update ADR032 and local caller contract explicitly.
3. Build/install a clean wheel in a new environment. Freeze changed prompt/runtime versions before inference. Run the same development probes once plus the frozen independent controls. Keep failures; no hidden reruns or target adjustment.
Expected: investigate supported exact-item/evidence questions and safely abstain on negative controls. A miss is retained, not an external blocker.
4. Run actual installed pilot CLI on all 48 original questions into a fresh report/database, now development regression; preserve complete facts/source, recovery, exact approval and audited save checks.
Expected: full accounting and positive accepted-investigation evidence. Record actual scores even if targets fail; no G2-ready claim.
5. Run focused interpretation/transport/public recovery tests and commit prompt/evidence.
Expected: pass.

## Task 3: Verify, review and publish the bounded slice

Interfaces: immutable live reports and current runtime; produces handoff, revision-bound semantic evidence and draft PR.

1. Update evaluation evidence, handoff and milestone map with actual results and remaining gates. Run `UV_CACHE_DIR=/tmp/pil-uv-cache make check`, `make package-smoke`, and `make challenges`.
Expected: all required deterministic/package/challenge checks pass.
2. One independent whole-branch review using superpowers:requesting-code-review and repository semantic reviewer. Correct Important/Critical findings in one RED/GREEN author pass and rerun invalidated checks; defer optional minors.
3. Validate latest-revision semantic JSON/PR contract, push and create draft stacked PR, inspect CI and live Issues/Project. Update #53/#72 only with concrete branch evidence; preserve all broader acceptance and statuses.
Expected: reviewable unmerged draft with current evidence and confirmed CI state.

## Review Focus

Distinguish document approval applicability from authority to approve/save; selected-cutoff consistency versus an instruction to guess a date; unsupported injection/action and cross-scope wording. Check that development evidence cannot be presented as fresh held-out quality and original reports remain unchanged. Verify actual installed caller, no oracle leakage, no hidden retries, unknown/failure accounting and version binding.
