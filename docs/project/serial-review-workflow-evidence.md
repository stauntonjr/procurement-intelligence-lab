# Serial fixture checkpoint evidence — 2026-10-03

Primary #53; part of #68/#70. Basee7f4370 (PR178). Branch work, not main or deployment.

The optional runtime uses actual audited corpus tools and application-owned exact briefs,
receipts/results. Typed fixture input bypasses model interpretation explicitly. Graph state
is execution metadata; no checkpoint can grant review/save permission or manufacture a
saved result/rejection without its ledger record.

Initial RED evidence: missing adapter prevented collection. A separate two-case RED pass
demonstrated absent orphan-draft recovery and unvalidated terminal rejection. Both are
corrected with durable draft reuse and authoritative receipt reads.

Verification includes actual public CLI start/status/review processes, a process terminated
with exit86 immediately after durable save and before graph checkpoint completion, restarted
save acknowledgment, repeated/concurrent resumes, wrong digest/scope/configuration, operational
authority denial, expiry equality, changed core snapshot and tampered checkpoint binding.
Base clean-wheel commands run without optional dependencies; optional installed-wheel
restart/review/save uses the frozen transitive lock and produces one saved row.

Implementation decisions, in order:

- Continue isolated stacked feature branches in the primary checkout after verifying clean
  state. Cost if wrong: unrelated edits could mix; branch boundaries are explicitly checked.
- Typed fixture input precedes model interpretation because no operational model is selected.
  Cost if wrong: persistence evidence cannot establish natural-language/live-model quality.
- Cooperative deadline and one read attempt preserve synchronous tool behavior. Cost if wrong:
  a blocked call can overrun the deadline; live inference needs deliberate cancellation handling.

Pre-review verification: `make check`512 tests,89.12% combined coverage, coverage ratchet,
strict typing, architecture and deterministic checks passed. `make package-smoke` passed two
base-wheel environments and the optional frozen-dependency workflow install. C001-C016
rejected their known-bad mutations. Focused error/graph/public caller suite:48 tests passed.

Read-only planning audit:106 issues,107 Project items,25 fields,11 views, no configured
omissions. Roadmap advisory37156365460 failed GitHub503; retry37157489605 reached the advisory
model but failed upstream429 (Gemini CLI173). Neither produced a usable roadmap report.

Independent review disposition and final revision checks follow after review.
Broader #53/#68/#70, browser controls/streams and live-model gates remain open.
