# G2 exact-brief approval and durable save

Spec: docs/product/exact-brief-review-v1.md; ADR-029. Primary #67; part #68/#53/#72.
Base489f1a2 (PR177). Native execution and one independent whole-slice review.

- [x] RED records/service/store contract: exact digest, active version, permission/scope,
  expiry equality, rejection, changed evidence, repeated/concurrent review/save and corrupt state.
- [x] Implement neutral immutable records, BriefStore Protocol, scoped atomic SQLite adapter,
  deterministic brief construction and current-evidence validation.
- [x] RED real CLI processes: draft -> review -> save -> repeated save after process exit;
  wrong project/digest/key, rejection and stale evidence. Implement fixed human CLI composition.
- [x] Clean installed CLI probe; full checks/challenges; independent review and RED/GREEN fixes.
- [x] Final revision-bound evidence, stacked PR and Issue/Project synchronization.

Review focus: changed version cannot inherit receipt; expiry cannot renew on replay; receipt
cannot cross run; save transaction cannot race active replacement; model/document arguments
cannot grant permissions; corrupt stored records and storage failure cannot fabricate success;
completed replay acknowledges one result; current evidence validation fails closed.

Verification:479 tests,89.01% coverage,ratchet,2cleanwheel environments,C001-C016.
Independent pre-fix review6 findings;13 regressions RED/GREEN, final author fresh pass.
Revision-bound evidence and published stacked PR record the exact committed head.
