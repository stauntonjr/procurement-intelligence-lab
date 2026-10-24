# Explicit planned source-assertion execution

Feature #226 (M9, parent #12), approved decision #225 and ADR-043 connect the existing full
package planner to actual synchronous INGEST -> STRUCTURE -> MAP -> NORMALIZE -> ASSERT
execution. This is a trusted local caller, not full procurement-package execution.

## Inputs and ownership

The caller supplies the compiled manifest, complete descriptor registry/config, one source,
explicit scope/observed/capture/run/code context, normalization policy and `--stop-after ASSERT`.
The unchanged planner validates the complete twelve-stage declaration. Composition registers
five real implementations; platform admission checks exact selected descriptors, implementation
versions, semantic contracts, settings and resolved references before source/content access.
There is no module import, registry-order choice or provider fallback driven by input files.

`bootstrap.build_planned_bom_service` explicitly composes existing strategies and an injected
content store/clock. Platform contracts/runner import no procurement and branch on catalog stages,
not domain names. Each stage invokes its injected strategy once over the actual previous output.
Shared lineage guards also protect the legacy document/normalization/assertion services.
Current planner, BOM, archive, review and replay callers retain their existing contracts.

| Stage | Actual implementation ID | Implementation/config version |
|---|---|---|
| INGEST | local-file-capture | 1 / 1.0 |
| STRUCTURE | xlsx-cell-structure | 1 / 1.0 |
| MAP | bom-table-map | 1 / 1.0 |
| NORMALIZE | bom-value-normalization | 1 / 1.0 |
| ASSERT | bom-source-assertions | 1 / 1.0 |

Descriptor version is1.0; STRUCTURE advertises tables. Initial adapters have no deployment settings;
non-empty settings or altered advertisements fail rather than silently reconfigure an adapter.
Schema and policy resolution are explicit. A declaration such as
`procurement.normalize/bom-decimal@1` resolves to the exact parameter-instance reference plus its
full SHA256. The receipt retains declaration, instance and content identities separately.
Component policy/schema labels remain explicit registration metadata and bind execution identity.

## Public command

For a synthetic checkout qualification, prepare a context whose caller-pinned revision matches
the explicit fixture configuration (the fixture pin is not production attestation):

```bash
python -m procurement_intelligence_lab.interfaces.domain_package > /tmp/prefix-manifest.json
python - <<'PY'
import json, tomllib
from pathlib import Path
context = json.loads(Path('tests/fixtures/bom-stages/context.json').read_text())
config = tomllib.loads(Path('tests/fixtures/execution/procurement-config.toml').read_text())
context['code_revision'] = config['application_version']
Path('/tmp/prefix-context.json').write_text(json.dumps(context))
PY
python -m procurement_intelligence_lab.interfaces.execute_package \
  src/procurement_intelligence_lab/examples/synthetic_bom_stages.xlsx \
  --manifest /tmp/prefix-manifest.json \
  --registry tests/fixtures/execution/procurement-registry.json \
  --config tests/fixtures/execution/procurement-config.toml \
  --stop-after ASSERT --context /tmp/prefix-context.json \
  --normalization-policy tests/fixtures/bom-stages/normalization-policy.json
```

The complete planner still requires metadata selections for later declared EXECUTE stages.
The fixture's later `fixture.*` advertisements are planning-only: no corresponding executor is
registered and no availability or execution is claimed. These checkout fixtures are passed
explicitly; they are not packaged runtime defaults. Real deployments must pin their own
manifest/config/context. Existing `build_application()` remains unchanged; no implicit universal
application or control plane is created.

## Output, identity and time

The JSON result retains the existing five-stage source/intermediate/normalized/assertion payload
and actual events, plus `execution_receipt`. The receipt includes full plan/hash, encoded execution
context, selected resolved references, twelve ordered entries, execution/receipt digests and
server completion time. Stage-specific immutable payloads retain source/artifact/document/batch,
observation/origin/assertion/mention evidence; arbitrary untyped payloads are not accepted.

Only the first five entries can be SUCCEEDED, with exact real event and input/output references.
All later entries are NOT_EXECUTED / `outside_requested_prefix`, with no invented output/event IDs.
This includes later EMPTY declarations: an unvisited declaration is not a materialized empty
result. `requested_prefix_complete: true` and `package_execution_complete: false` describe the
execution boundary, not resolved identity, reconciled state or extraction quality.

Duplicate rows remain separate claims/mentions. An evidenced zero-row document produces real empty
normalization/assertion batches; unknown fields/values remain unresolved and zero remains a value.
Existing malformed-number failures and explicit each/dozen/currency policy behavior are preserved.

The computation identity binds full plan/config/policy/component/context/source/output evidence.
Equal pinned inputs reproduce it across installed paths. The receipt identity additionally binds
completion time; a fresh local invocation normally returns a different attempt receipt. All times
are aware fixed offsets, observation<=capture=start<=server clock; completion is sampled after the
validated final output and cannot precede the initial server sample. Timestamp offset encoding is
retained in identities. Context/capture metadata is caller-pinned local evidence, not independent
production capture attestation or proof of source freshness.

## Failures and boundaries

Preflight rejects absent/mismatched executors, wrong versions/settings/references, code pin mismatch,
unsupported wider boundaries and in-prefix EMPTY/PASSTHROUGH before source I/O. Initial MAP requires
an explicit schema; NORMALIZE/ASSERT each support one explicit policy. Composite policies and
neutral execution require a separately admitted extension; the runtime does not choose precedence.

PlanningError retains `pil.input.package_planning_invalid` and structured issues. Runtime admission
uses `pil.input.package_execution_invalid`; invoked-output substitution uses
`pil.interpretation.package_execution_contract_invalid`. Existing source/structure/normalization
and infrastructure failures retain their typed codes. The CLI emits sanitized JSON/exit2, no
partial success stdout and no traceback/settings values. Argument failures use the same envelope;
`--help` remains ordinary help. JSON rejects duplicate/unknown fields, invalid Unicode/non-finite
values; manifest/registry/config are bounded at1MiB each, context/policy at32KiB each.

On stage failure no later executor runs and no success receipt is published. Captured bytes may
remain in the attempt's injected store; rollback of arbitrary external side effects is not
claimed. This path adds no database schema, durable run journal, result cache, exactly-once
ingestion, general correction scheduler, authority selection, operational-agent permission,
production authentication, browser or deployment. Archive durability/retry stays a separate API.

## Acceptance

- Neutral typed-output/receipt and admission tests cover malformed metadata, exact lineage,
  scope/time/offsets, incomplete registrations, neutral/unsupported modes and order invariance.
- A non-procurement executable fixture follows the identical runner with actual empty outputs.
- Real adapter contracts forbid legacy pipeline reruns, delete the source after capture and retain
  bytes; compare legacy values/locations/statuses, duplicates, nulls, zero, negatives and policies.
- Real subprocess tests compile a manifest and execute the new CLI, including independently valid
  plans whose unavailable executor/neutral prefix rejects before an intentionally absent source.
- `tools/package_execution_probe.py` runs the actual installed caller outside checkout in two base
  environments and after optional workflow/storage installation. It checks twelve dispositions,
  real quantity/evidence, deterministic repeated computation, duplicate/unknown/zero rows and typed
  unavailable-executor rejection. Baseline wheel07d089b rejects because the CLI is absent; current
  wheel acceptance remains revision-bound to its actual smoke-test result.

Full checks, coverage/ratchet, challenge compatibility, independent review and protected delivery
belong to the latest-revision semantic evidence in the implementation PR. Broader #12/#7/#20/#35/
#36/#75 and neutral/full-stage/governing-policy acceptance remain open.

The approved [completed-prefix archive](planned-execution-archive.md) adds opt-in atomic retention and scoped source-free recovery under #229; default planned execution and legacy source archive contracts remain compatible. See its delivery evidence for branch versus main status.

The approved [local prefix jobs contract](local-prefix-jobs.md) adds explicit durable submission, attempts,
manual retry and fenced abandonment under #232. Source/archive/current-attempt success shares one
transaction; original execution/archive callers remain compatible. Exact qualification, review and
merged-main acceptance are recorded in [Issue #232](https://github.com/stauntonjr/procurement-intelligence-lab/issues/232).
This is a trusted local synchronous profile; queue deployment remains outside its scope.
