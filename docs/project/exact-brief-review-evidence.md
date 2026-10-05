# Exact-brief review/save evidence — 2026-10-03

Primary #67; part of #68/#53/#72. Base489f1a2 (PR177). Branch evidence, not main or deployment.

Immutable deterministic briefs retain exact core values/status/uncertainty, request, snapshot,
original source references and complete run/query/attempt/thread/configuration bindings. A separate
local human CLI creates exact approval/rejection receipts and saves only the active approved version.
Runtime read permissions cannot approve/save. No model narrative or external action is introduced.

Independent fresh-context review found six material gaps: missing evidence permission on reads,
unvalidated embedded run binding, pre-lock expiry timestamp, corrupt receipt chronology, unchecked
relational save key, and missing/incorrect active state. Thirteen cases reproduced these findings.
One author fix pass addressed all six; five binding cases also reproduced the draft path before
its correction. The final author fresh pass inspected corrected ordering, complete bindings,
serialized expiry, relational IDs/keys, stored chronology, current-source validation and replay.
Independent review was not repeated after regression-verified fixes; no optional minors remain.

Final verification:

- `make check`:479 tests,89.01% combined coverage; typing,architecture and coverage ratchet passed.
- `make package-smoke`:two isolated installed wheels; actual create/draft/review/save processes
  and repeated save after process exit acknowledge one identical durable result.
- `make challenges`:C001-C016 known-bad rejected.
- Focused public/store/error suite:48 cases passed before the final parser test; all current
  cases are covered by the final whole-suite run. Real parser verifies early failure envelopes
  without replacing context, services or adapters; subprocess tests retain real-caller acceptance.

Earlier full runs passed461/478 tests but missed the line coverage ratchet. No coverage threshold
or exclusion changed. Actual caller and failure verification resolved the coverage gap.

Tests retain unresolved/conflicting facts, reject altered digests/keys, cross-run/scope approvals,
rejection, replacement, expiry equality, corruption and authority instructions. An actual modified
workbook blocks saving with an infrastructure failure and zero saved rows. Four concurrent saves
produce one result; a write-lock expiry race fails closed. Completed exact replay can acknowledge
the existing result after expiry, while still checking scope, bindings and current evidence.

Implementation decisions, in order:

- Approval precedes graph integration while provider/model choice is pending. The application
  contract is already approved; cost if wrong: adjust graph integration.
- Separate fixed local human CLI supplies review/save permissions. This demonstrates mechanics,
  not production authentication; cost if wrong: browser authentication remains required.
- Adapters share the public run decoder instead of a private import. Cost if wrong: extract shared
  serialization mechanics without changing the port.
- Review requires evidence access together with REVIEW/READ_STATE because it reads the packet.
  Cost if wrong: adjust reviewer assignment before browser integration.

Graph checkpoint restart, authenticated browser review, model interpretation/drafting and live
inference acceptance remain subsequent G2 gates. The provider/model is not pinned. The local
fixture CLI does not demonstrate those capabilities. See the official-source
[graph integration notes](../langchain-ref/approval-integration-2026-10-03.md).
