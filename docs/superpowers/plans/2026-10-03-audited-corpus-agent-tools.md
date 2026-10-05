# G2 audited corpus tools

Native continuation of approved corpus plan #66/#53; independent review. Base242c271 (PR176).
Contract: docs/product/corpus-agent-tools-v1.md. Governing ADRs019/027/028; no new domain policy.

- [x] RED: typed arguments reject authority keys, malformed identifiers and naive dates.
- [x] RED: actual tool results equal direct service calls, record positive invocation/snapshot,
  preserve missing/conflicting results, and enforce owner/scope/permission before reads.
- [x] RED: timeout/integrity/unknown-source failures are recorded and cannot satisfy success;
  failed audit append cannot fabricate completion.
- [x] Add source-by-ID lookup Protocol and two tool wrappers with explicit DI; share serializers.
- [x] RED/GREEN public CLI: create -> investigate -> source -> finish in separate processes;
  original cells, matching quantities, wrong-project source, failure and incomplete trajectories.
- [x] Clean installed CLI probe, full checks and challenges; final independent review and fix pass.
- [x] Revision-bound semantic evidence, stacked PR, handoff/Issue/Project audit.

Review focus: arguments cannot grant authority; invocation events reflect actual results;
source lookup is one fresh admission; service/status/quantities are shared; source/brief text
cannot mutate policy; audit failure is not successful tool output; fixtures do not become live metrics.

Verification: 445 tests, 88.89% combined coverage and ratchet; two clean wheel environments;
48/48 structured HTTP cases with 464 source resolutions; C001-C016 known-bad rejected.
Independent review found one failure-category blocker. Four real corrupt/missing-file cases
failed before correction and passed afterward; final author fresh pass found no unresolved
findings. Revision-bound PR evidence records the exact committed head.
