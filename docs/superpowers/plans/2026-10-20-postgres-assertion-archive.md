# Atomic Postgres assertion archive implementation plan

Spec: ADR-038 and the durable archive Issue under #37. Owner authorized inline implementation;
use executing-plans/TDD and one fresh-context whole-branch review before merge.

- [x] Add failing snapshot/codec tests. Implement neutral frozen snapshot/receipt and archive port;
  add typed failure envelopes and a strict, versioned, content-addressed typed graph codec.
- [x] Add real Postgres contract tests before the adapter: init/version admission, atomic writes,
  exact retry/concurrency, scope isolation, immutable guards, reopen, corruption and rollback.
  Implement optional driver adapter; do not modify legacy in-memory ledger semantics.
- [x] Add actual CLI tests before bootstrap/caller changes. Inject captured content explicitly;
  opt-in --archive preserves existing modes. Add init/show/history/content commands with no DSN
  arguments or output and no mutable-source replay. Verify empty receipts and conflicting revisions.
- [x] Add required Postgres CI services and clean-wheel storage checks. Update README, archive
  contract, ADR-015/022, milestone and handoff. No shipped defect/model swap is claimed.
- [ ] Seal code after focused/coverage-gap checks. Run exact-head make check, package smoke,
  all 30 public challenge/mutation oracles, source conformance and independent semantic/architecture
  review. Resolve all present automated findings. Embed validated latest-revision JSON in PR.
- [ ] Merge only with every required deterministic check green; verify main tree and real caller,
  synchronize only the bounded Issue/Project state and record advisory audit/provider limits.

Review focus: missing is not empty success; no lost null/Decimal/enum/time/provenance; original
bytes survive deletion; same IDs with different payload conflict; concurrent retries and failed
writes create no partial snapshot; SQL/data ownership is not operational-agent authority.

Orientation: main9793149 clean; parent #37/#13, later #35/#36/#38/#40/#41 read. Planning audit has
zero missing configured objects and Project reviewed. Pre-slice advisory run39443547796 failed
Gemini HTTP503; no report or successful-provider claim. Known unrelated drift remains #109's
unchecked completed #112/#115, duplicate ADR-033 and explicitly superseded historical demo logs.
Baseline23 ledger/BOM assertion tests pass. Existing worktrees and shared services preserved.
