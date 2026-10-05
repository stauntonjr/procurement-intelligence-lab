# G2 run/event foundation evidence — 2026-10-03

Primary #70; part of #68/#72. Base 74321a8 (PR175). This is branch evidence.

The foundation creates separate run/query/attempt/thread identities for independent examples,
retains owned resume across real process exit, and stores immutable version/execution bindings.
SQLite transactions deduplicate exact event replay and reject changed, foreign or causally invalid
events. CLI configuration supplies synthetic principal/scope/permissions. No client arguments grant
permission or choose execution kind. Fixed event DTOs reject non-string fields and unsupported enums.

Independent fresh-context review inspected authorization-before-read, owner scope, event and
metadata replay, lifecycle, missing/foreign traces, concurrency and fixture/live separation.
It found two blockers in pre-fix code: fixture services could record into live runs, and arbitrary
objects/unsupported enum values could enter event serialization. Thirteen targeted cases were
observed failing, then passed after fixes. A final author fresh pass verified the corrected paths
and typed failure catalog; independent review was not repeated after the regression-verified fixes.

Final local verification:

- `make check`: 428 tests passed, 89.61% combined coverage, coverage ratchet and architecture checks passed.
- `make package-smoke`: two isolated installed wheels exercised the CLI in separate processes,
  including persistent resume and foreign-scope denial. Existing corpus/legacy package probes passed.
- `make challenges`: all C001-C016 known-bad implementations rejected.
- Focused public caller and store/evaluator/error tests passed, including version-field changes,
  live/fixture mixing, dict/list/int/bool payload attacks, unsupported enum, corrupt/unsupported
  storage, invalid clock, wrong principal/project, missing permission, terminal tool failure and
  concurrent replay.

No graph/model call, human approval, durable brief save or public deployment is demonstrated by
this foundation. The fixture CLI is a restart test, not live-agent acceptance. Next: two typed
corpus tools that record actual invocation/results, then the serial workflow and exact-brief
approval/recovery. A provider/model configuration must be pinned before live inference acceptance.

Read-only roadmap run 37150358463 failed with upstream 503 high-demand errors. The deliberate
Project audit found no configured omissions; #70 is In Progress. This advisory failure is not a
successful roadmap review or a deterministic implementation-check failure.
