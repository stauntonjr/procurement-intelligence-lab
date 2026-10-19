# Deterministic runtime package planning

Issue [#205](https://github.com/stauntonjr/procurement-intelligence-lab/issues/205) implements
ADR-022's deployment admission and physical planning boundary. It does not implement an executor,
check service availability, load policy parameters, materialize state, or authorize an action.
The shipped procurement manifest uses planning-only descriptors in acceptance fixtures; existing
BOM services still compose directly in `bootstrap.py`.

## Contract and ownership

Authoritative inputs are the ratified compiler JSON, platform stage/semantic-contract registries,
a deployment-owned descriptor registry, and an explicit deployment configuration. The platform
imports no vertical. The same `plan_manifest(manifest: bytes, *, registry: ImplementationRegistry,
config: ImplementationConfig) -> PhysicalPlan` path handles procurement and a non-procurement
conformance fixture. Frozen stdlib dataclasses and nested tuples keep input records immutable.
File access belongs to the CLI; the planner and loaders perform no I/O or ambient configuration.

`PhysicalPlan` contains canonical UTF-8 JSON bytes and their SHA-256. The public CLI emits
`{"plan": {...}, "plan_hash": "..."}` plus one newline. Hashes exclude that envelope/newline.
JSON uses sorted object keys, compact separators, unescaped Unicode and finite values only.
Manifest formatting/key order are normalized by revalidation and recompilation; the retained
manifest hash identifies compiler-canonical semantics, not an arbitrary input file's byte hash.

Schema versions are exact, never best-effort: manifest `1.0`, registry `1.0`, config `1.0`, plan
`1.0`. Domain/profile versions are independent; deployment pins the profile ID and version exactly.
Concrete input/output contracts have initial version `1.0` in `CONTRACT_VERSIONS`, independently
of manifest and planning schemas. A contract change requires an intentional supported revision.
Descriptor version, implementation version, optional provider/model versions, application/code
version, manifest hash and runtime-config hash are all retained independently. This is a planning
identity, with no business scope/as-of timestamp or source-data acceptance; execution owns those.

## Deployment input schemas

A descriptor registry is JSON with exactly `schema_version` and `implementations`. Each entry has:

| Field | Meaning |
|---|---|
| `implementation_id` | Explicit deployment selection key, unique across registry |
| `descriptor_version` | Numeric MAJOR.MINOR[.PATCH] advertisement revision |
| `implementation_version` | Non-empty implementation build/version identity |
| `stage` | One catalog stage |
| `input_contract`, `output_contract` | Objects with exactly `name` and `version`, matching the stage and supported semantic revision |
| `capabilities` | Unique catalogued capability IDs; requirements must be a subset |
| `config_schema_version` | Numeric version that the selected configuration must match exactly |
| `required_settings`, `optional_settings` | Optional arrays (default empty), disjoint unique lowercase identifier keys |
| `provider_version`, `model_version` | Optional non-empty version identities, or null |

Registry entries advertise compatibility, not health, executor registration, benchmark quality or
business authority. All entries undergo admission, including unused entries. No imports, callbacks,
provider autodetection, or registry-order selection occur. Adding a compatible unused descriptor
cannot change the plan. Selected descriptors' unordered capabilities/settings keys are normalized.

Configuration is TOML. This excerpt selects one stage; every EXECUTE binding requires its own
selection, and neutral bindings must have none:

```toml
schema_version = "1.0"
source_profile = "bom-table"
source_profile_version = "1.0.0"
application_version = "deployment-code-revision"

[[selections]]
stage = "INGEST"
implementation_id = "fixture.ingest"
config_schema_version = "1.0"
[selections.settings]
endpoint_ref = "fixture://offline"
```

An entirely neutral package uses `selections = []`. Settings are non-empty string values with
unique keys; no implicit defaults or scalar coercion. The descriptor defines allowed/required keys
and an exact schema revision; this planner does not validate technology-specific endpoint syntax,
resolve secrets, or interpret business quantities. Use references for secrets, never inline secret
values. Canonical config hashing normalizes stage selection and setting order. Plans expose only
the config digest, not settings values. Changing any explicit setting changes that digest/plan.

## Planning and failure behavior

The planner strictly admits JSON/TOML (including duplicate-key rejection), reconstructs only the
ratified manifest fields, then invokes the domain compiler to validate stage order, modes,
capabilities, portable references and neutral semantics. It rejects missing/extra fields rather
than dropping future semantics. It checks the exact profile pin and all descriptor contracts.
For each EXECUTE stage it requires one selected registered ID belonging to that stage, sufficient
capabilities, matching config revision and valid required/optional settings. It never substitutes
EMPTY for an absent/incompatible implementation.

Every plan retains all twelve bindings, semantic references, contract versions and capability
checks. `physical_steps` lists only explicitly selected EXECUTE stage IDs in catalog order.
Neutral stages retain `TYPED_EMPTY` or `VALIDATE_PASSTHROUGH`, null implementation and their
stage-specific declaration. PASSTHROUGH's manifest flag records an authoring prerequisite;
a future executor must validate actual data and retain its evidence. Neither this flag nor a plan
is proof that source data met the output contract, approvals exist, or any action succeeded.
No semantic trace/execution receipt is fabricated. These steps do not yet specify physical
wiring, execution scheduling, policy resolution or data transport.

Failures use `PlanningError` / `pil.input.package_planning_invalid`, category `input`, with
stable diagnostic codes, paths and messages. Plan incompatibilities identify profile/stage;
malformed inputs identify their field or file kind. CLI failures exit 2, produce no stdout and
emit the error plus `issues` on stderr, without settings values or Python tracebacks. CLI argument
syntax/help follows argparse. No failed plan is returned. Existing normalization/assertion policy
Issues #31/#32/#33 and authority boundaries are unchanged.

## Public and installed acceptance

From a checkout or clean installed wheel, compile the real procurement declaration, then plan
against the deliberately external planning fixtures:

```bash
python -m procurement_intelligence_lab.interfaces.domain_package > /tmp/procurement-manifest.json
python -m procurement_intelligence_lab.interfaces.plan_package \
  --manifest /tmp/procurement-manifest.json \
  --registry tests/fixtures/planning/procurement-registry.json \
  --config tests/fixtures/planning/procurement-config.toml
```

Fixture paths above belong to the checkout and are passed explicitly; fake executors/configuration
are not shipped as production resources. `tools/package_smoke.py` builds one wheel, installs it
in two fresh environments, invokes the installed manifest/planner commands outside the checkout,
checks procurement and non-procurement plan content/hashes and typed unavailable-selection failure,
and compares byte-identical output across installation paths.

| Scenario | Evidence |
|---|---|
| Real procurement; all twelve stages, first nine EXECUTE and final three EMPTY | `tests/unit/test_package_planning.py`, `tests/integration/test_package_planning_cli.py` |
| Non-procurement, EXECUTE/PASSTHROUGH/EMPTY; entirely neutral package | Same unit tests; public conformance CLI fixture |
| Missing/unknown/duplicate providers or selections; cross-stage selection | Unit tests and public missing-registry case |
| Insufficient capability; contract/config/profile version incompatibility | Unit tests, strict registry/config loaders |
| Unknown/malformed/duplicate fields, non-finite JSON, invalid Unicode; immutable input | Unit tests and public malformed-input cases |
| Numeric settings, zero/negative/fractional and container values | Typed rejection; string-valued options remain opaque, no quantity calculation |
| Equivalent JSON/registry/config order; relevant version/settings change | Unit determinism/metamorphic tests; two clean installed paths |
| Business scope/as-of, stale/future source claims, approvals | Not evaluated by planning; no source data or execution authority input |

Next work adapts real procurement services to universal stage contracts with source/evidence
acceptance, then adds execution receipts and durable ledger/replay. Forecasting, decision/action
policies, provider/model selection benchmarks and second-production-vertical acceptance remain
separate deliverables.
