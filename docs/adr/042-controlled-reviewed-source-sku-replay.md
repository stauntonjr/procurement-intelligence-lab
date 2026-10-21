# ADR-042: Explicit reviewed source-SKU replay and correction inputs

Status: accepted policy, approved by the maintainer on 2026-10-21; implementation planned.

Issue #222 follows ADR-039/040/041. The original source query executes and retains dependencies;
read-only impact already flags registered references as potentially stale. Controlled replay needs
an explicit selection and correction-input policy rather than another stale flag.

Use a separately invoked source-local reviewed view over one exact archive and an explicit
bounded set of approved SKU review tasks at an inclusive as-of. Apply selected proposals by source
assertion identity, reject conflicting selected tasks, and retain original source/query values.
Missing/proposed-null values remain unresolved. No latest-winner, governing state or globally fresh
result is implied; unselected reviews are not evaluated by this view.

Review proposals supply actual values and therefore are data dependencies. Introduce a neutral,
typed approved-correction root validated against retained task/digest/decision/correction evidence.
Do not hide it in producer metadata. Each actual row-application event consumes original assertion
and correction; the actual set-query event consumes at most32 original/reviewed row outputs. This
preserves per-producer bounds and records both source and human-decision lineage.

Keep domain semantics deterministic and framework-independent. Compose source/review admission,
producer, clock and dependency ports explicitly. Require REVIEW plus READ_EVIDENCE before I/O,
prospective execution/registration, exact retries and typed failures with no partial success.
Any dependency storage capability/version change must be explicit; preserve old record shapes
and readability and leave archive/review records unchanged. Generic registration remains declared
evidence, not execution attestation. No new result cache or automatic approval-triggered work.

The alternative of latest-approved replay invents precedence absent from the review contract.
A general scheduler/executor is premature before one honest correction-data contract. The
[approved specification](../superpowers/specs/2026-10-21-reviewed-sku-replay-design.md) defines the
decision and required scenarios; the native implementation plan carries the maintainer's authorization to proceed.
