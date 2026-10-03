# G2 audited corpus tools evidence — 2026-10-03

Primary #66; part of #53/#70/#72. Base 242c271 (PR176). This is branch evidence.

The host supplies RequestContext and owned run identity; tools accept only item/as-of or
evidence ID. Both call existing deterministic services and retain original cells, authority,
policy, snapshot and qualified assessment IDs through the same public DTOs as HTTP. A
source ID cannot grant scope. Actual tool invocations record start and a successful snapshot
or a closed failure code. A failed audit append cannot return completed tool success.

Independent fresh-context review found one blocker: CorpusAdmissionError inherits ValueError
and was incorrectly classified as an input failure. Four regressions corrupt or remove actual
workbooks and exercise both tools. All four were observed RED, then GREEN after admission
failures received a distinct non-retryable infrastructure code. The final author fresh pass
checked the corrected ordering, owner/permission gates, shared DTOs, one source admission,
audit failure and fixture/live separation. Independent review was not repeated after the fix.

Final local verification:

- `make check`: 445 tests, 88.89% combined coverage; ratchet, typing and architecture passed.
- `make package-smoke`: two clean wheel environments exercised create/investigate/source/finish
  across actual processes, persistent run identity, source evidence and foreign-scope denial.
- HTTP corpus evaluation: 48/48 authored structured cases passed, 464 original references resolved.
- `make challenges`: C001-C016 known-bad implementations rejected.
- Focused public/error/tool suite: 34 tests passed, including real corrupt/missing evidence.

Parity compares public authoritative DTOs rather than the detector's observation timestamps:
separate calls legitimately observe different instants. Existing core tests retain internal
semantic coverage; no quantities, ranking or policy changed. No model inference, human approval,
brief save or deployment is demonstrated. Fixture trajectory completeness is distinct from
natural-language routing, evidence entailment and live-run acceptance.
