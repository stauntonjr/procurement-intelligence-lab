# ADR039: Preserve document-value reviews as separate append-only lineage

Status: accepted for the owner-authorized bounded Issue216 increment under41/37/13.

Use neutral frozen review proposal/task/decision/history records and a DocumentReviewJournal port.
Implement document_value first; entity and operational reviews are separate unsupported variants.
Tasks bind one exact archived assertion, its source evidence, typed previous/proposed value,
rationale, actor and recording time. Decisions bind the complete task SHA256 digest, actor,
outcome and rationale. One task has one terminal decision; separate proposals remain separate.
Exact command retries retain the first receipt/time and changed immutable requests conflict.

An approved correction is a separate policy-relevant review record with prospective effective time
and recomputation-required signal. It never rewrites a SourceAssertion, silently selects a governing
source, changes original unit/predicate/entity identity, or claims downstream discovery/recomputation
has occurred. Unknown downstream impact remains not_evaluated. ADR023/024/034 policies remain intact.

Postgres adds explicitly initialized review schema1 beside unchanged archive schema1, with
transactional command replay, archive-membership foreign keys, strict typed graph storage and
append-only guards. Bootstrap supplies the adapter and domain validator. RequestContext scope and
REVIEW permission are application-owned; operational-agent contexts do not gain authority. A separate
local human shell boundary is trusted development configuration, not production authentication.

[Full contract](../superpowers/specs/2026-10-20-document-review-lineage-design.md) defines temporal,
identity, failure, as-of and public packaging acceptance. Broader41/37/13 remain open.
