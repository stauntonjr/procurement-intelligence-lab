# Local fixture browser review evidence

Primary #74; part of #53/#67/#68/#70. Stacked on PR179 (4247519). ADR-031 and
[public contract](../product/local-browser-review-v1.md) define the boundary.

Owned run discovery failed before implementation; 21 run-store contract tests passed after.
The new HTTP test first failed on missing module, then exact runtime behavior was exercised
through real loopback requests. Focused tests cover missing/wrong token before run/checkpoint
access, origin/host protection, bounded/repeated/unknown fields, scope isolation, source
membership, allowlisted timeline, exact digest rejection, real server lifetime restart,
idempotent review, rejected and unresolved briefs, numeric cases, corruption, expiry, evidence
change and historical incompatible configuration discovery. An installed-process probe starts
the actual CLI twice and recovers/reviews the persisted run; it checks one saved-result row.

Browser tools: inventory returned no enabled browsers; IAB creation returned `Browser is not
available: iab`. No real browser interaction, keyboard, focus, contrast, screenshot or deployed
acceptance is claimed. These #74 acceptance gates stay open. HTTP/form/source checks and clean
package verification cannot substitute for them. Live inference and streaming are also open.

The read-only roadmap stewardship run 37160330994 failed due to Gemini daily quota (429,
exit173). It produced no usable advisory report. The deliberate live Project read and configured
planning audit passed: 106 issues,107 items,25 fields,11 views,31 labels,10 milestones; no
configured omissions. #74 was Todo before this slice; broader issue criteria remain open.

Verification counts, current revision and review disposition are recorded in the PR's
revision-bound semantic JSON. Nothing in this slice merges the existing stack or changes the
public deployment. No model choice, inference, trace export or external action was made.

Initial author verification: `make check` passed 526 tests,89.04% combined coverage and
coverage ratchet; formatting, lint, strict typing, architecture and required checks passed.
`make package-smoke` passed two dependency-free clean wheels plus optional locked workflow
installation and installed authenticated HTTP process restart/review/repeated save.
`make challenges` rejected C001-C016 known-bad implementations. JavaScript syntax and a
small renderer unit probe verified column-coordinate highlighting, null quantities and exact
digest/focus request; this unit probe is not browser accessibility or interaction evidence.
