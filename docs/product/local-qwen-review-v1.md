# Local Qwen evidence review v1

Branch capability, primary #53 (M5), acceptance #72. [ADR-032](../adr/032-local-model-intent-and-journal.md).
The loaded local model is `nvidia/Qwen3.6-35B-A3B-NVFP4` at `http://127.0.0.1:8000/v1`.
The optional workflow extra is required. No model provisioning, reload, paid fallback or trace upload.

## Human commands

```bash
uv run --extra workflow python -m procurement_intelligence_lab.interfaces.live_review \
  --database /tmp/procurement-live.db --project atlas ask \
  --question 'Compare GPU-A orders with the governing requirement and show evidence.' \
  --as-of 2026-10-01T00:00:00Z

uv run --extra workflow python -m procurement_intelligence_lab.interfaces.live_review \
  --database /tmp/procurement-live.db --project atlas recover --run-id RUN_ID

uv run --extra workflow python -m procurement_intelligence_lab.interfaces.live_review \
  --database /tmp/procurement-live.db --project atlas review \
  --run-id RUN_ID --brief-id BRIEF_ID --digest EXACT_DIGEST --decision approve
```

Use the IDs/digest from the persisted response; changing a digest is not an edit operation.
`events --run-id RUN_ID` returns application tool events. CLI code 0 means an acknowledged
interpretation outcome: inspect `interpretation.status` and `workflow`, because failure or clarification
may have no brief. Policy/storage/tool failures use nonzero exit with a closed typed envelope.

For the existing authenticated loopback reviewer, use its private token-file setup and add:

```bash
uv run --extra workflow python -m procurement_intelligence_lab.interfaces.review_web \
  --database /tmp/procurement-live.db --project atlas --token-file /tmp/reviewer-token \
  --port 8001 --model-endpoint http://127.0.0.1:8000/v1
```

The page displays a question input, redacted model outcome/latency/usage, exact deterministic facts,
source drill-down and human review controls. Typed fixture mode remains the default without
`--model-endpoint`. Live mode rejects `/api/start`; POST `/api/ask` accepts exactly `question` and
`as_of`. GET `/api/interpretation?run_id=...` is read-only; POST `/api/recover` can resume accepted
interpretation/checkpoint work. Authentication, owner scope, origin/Host checks and body limits
precede work. Recovery/approval never recall the model. No question/model text or token is put in a
URL. Loading history shows execution kind and immutable-version compatibility.

POST `/api/reconcile` accepts exactly `run_id`, `brief_id`, `digest`, `outcome`,
`selected_claim_id`, and `rationale`. `selected_claim_id` is empty only for a non-selection outcome.
The first resolver supports exactly two eligible conflicting required-quantity claims in the exact
item/project/site scope. The model cannot choose a revision or provide authority, rationale, scope,
or effective time.

## Bounded semantics

One exact catalog item and explicit aware cutoff are supported. Requirement governance, conflict
and document approval applicability are review intents, including unresolved evidence. Document-relative
predicates use the selected cutoff; they do not grant human approval/save authority. Calendar-boundary
wording may use that cutoff only when consistent with it. Restating that same cutoff (for example,
"set the review cutoff to ... and examine ...") is query metadata, not a procurement mutation.
Different dates must clarify; query metadata grants no source edit or approval authority. Conflicting explicit dates, inconsistent
boundaries, unresolved relative query dates, aliases and multi-item requests ask for clarification;
broader fuzzy retrieval is deferred. Scope/date proposals
must match server-owned context, and an investigation must have exactly one literal catalog mention matching its proposed item. The model receives this deterministic mention list as additional evidence; it cannot select an unrelated admitted item. Strict JSON rejects extra/duplicate/missing fields and invented
items. Quantities, unresolved conflicts and absent observations come from existing services.
Model text cannot grant review/save authority. Approval records the exact immutable brief; only
human review plus fresh policy/evidence can save one local demo result.

Each question creates one version-bound LIVE run and an inference journal. Only question hash,
cutoff, closed interpretation fields/reason, measured elapsed time and reported usage persist.
Transport failure has unknown token usage. Interrupted pending attempts remain unknown with no
automatic retry. Accepted intent can recover a crash before checkpoint creation. Model content and
hidden reasoning are neither checkpoint authority nor retained telemetry.

The 30-second socket inactivity timeout is not hard cancellation or proof that server compute stopped.
Nine repeated development walkthroughs are not broad or held-out model accuracy. See the
[execution evidence](../project/local-qwen-review-evidence.md); actual browser/deployment acceptance,
streaming and the full G2 pilot remain open. Original tiny-fixture live routing is now verified
on the [unmerged original-source continuation](../project/original-showcase-live.md).
