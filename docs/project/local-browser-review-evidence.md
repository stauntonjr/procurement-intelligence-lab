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

One independent review of cf277d374394de774bd812f16ae132ade46670ee found one Important
recovery defect: selecting a discovered run whose status had no displayable brief hid and
disabled recovery. A unit simulation executing the shipped JavaScript event wiring failed
before the fix and passed after. Selection now retains the run ID independently of the brief;
recovery stays visible, while approval still requires loaded exact content. A real HTTP
failure-injection test confirms failed start -> owned discovery -> failed status -> recovery.
The Node wiring probe is optional when Node is absent and does not claim browser acceptance.

The author's malformed-target counterexample also failed: an invalid absolute URI escaped
URL parsing and closed the connection. It now returns a closed 422 input response. Both fixes
are in one author pass; no independent re-review or deferred minors. Final verification and
latest author fresh-pass revision are in the PR semantic JSON.

Rulings: the isolated feature checkout was reused (coordination cost if concurrent work);
typed fixtures precede model interpretation (later model integration still required); the
local bearer capability is not production identity (separate production adapter required);
application event snapshots precede streaming (stream redaction gate remains); the actual
run-store contract test path superseded the plan's nonexistent unit path (test-selection
correction); unavailable browser verification remains open (visual/accessibility defects may
remain). Review's declined production/public hosting, live inference/NL/streaming/external
actions and broader #74 completion remain outside this bounded draft (separate integration
and acceptance work remains). Actual browser interaction remains an explicit required gate.

The same final author pass reproduced a credential fallback defect: the HTML sign-in form
would default to GET if its JavaScript did not execute, placing the token in a URL. The
public form parser regression failed, then passed after an explicit POST-only unsupported
auth fallback was added. That fallback cannot authenticate or create work without the
bearer header. This is a local form contract check, not a browser execution claim.

Final author verification after the entire fix pass: 530 tests passed,89.04% combined
coverage and ratchet; all required deterministic checks passed. Final clean-wheel HTTP
process restart/recover/exact review/repeated save passed after the credential fallback fix.
No unresolved code findings or deferred minors. Actual browser interaction remains open.
Primary #74 Project item is verified In Progress (107 total items); no Issue is closed.
