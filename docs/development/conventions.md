# Development conventions

These conventions are the code-coupled operating contract for human and agent-authored changes.
They apply to repository code, tests, configuration, generated artifacts, and review evidence.

## Python toolchain and checks

- Support Python 3.12 and 3.13 as declared in `pyproject.toml` and exercised by CI.
- Use `uv` for environments, dependency locking, builds, and command execution.
- Use Ruff for formatting and linting, Pyright in strict mode for static typing, and pytest for
  unit, contract, integration, and regression behavior.
- Use Google-style docstrings where a public API needs explanation. Do not add comments that merely
  restate implementation syntax.
- Add or update dependencies only through `pyproject.toml` and `uv.lock`; architecture-affecting
  dependencies require an ADR, and model or algorithm swaps require benchmark evidence.

## Package boundaries and naming

Dependency direction points inward:

1. `platform` semantic contracts depend only on the standard library and never import a vertical.
2. `domains/<vertical>` may bind platform contracts but never import sibling verticals.
3. `ports` expose framework-neutral protocols using platform types and never import a concrete
   vertical.
4. `application` orchestrates platform/domain semantics through explicit ports.
5. `adapters` and `interfaces` own external mechanics and may depend on inward layers.
6. `bootstrap.py` is the visible composition root; import-time service locators and hidden global
   wiring are prohibited.

Use `snake_case` modules and functions, `PascalCase` types, and opaque typed identifiers. Prefer
stdlib dataclasses for immutable semantic records and `Protocol` for substitutable behavior.
Boundary libraries such as Pydantic may validate HTTP, CLI, config, or external payloads, but they
must not become the domain model.

## Failures and stable error codes

Every failure emitted by a platform semantic record or policy belongs to exactly one category:

| Category | Meaning | Retry expectation |
|---|---|---|
| `input` | The supplied value violates a schema or intrinsic invariant | Correct input; do not retry unchanged |
| `interpretation` | Structuring, mapping, or extraction could not produce a supported interpretation | Revise evidence/config or route to review |
| `identity` | Entity identity is unresolved, ambiguous, or conflicts with governed identity evidence | Retain unresolved state or review; never force-merge |
| `policy` | A governing policy rejects an otherwise well-formed request or state transition | Change policy/input explicitly; do not bypass |
| `infrastructure` | A required external mechanism is unavailable or failed | Diagnose the adapter/service boundary |
| `transient` | A bounded operation may succeed unchanged after backoff | Retry only under an explicit bounded policy |
| `authorization` | Scope, principal, approval, or authority does not permit the operation | Obtain authority; never retry as success |

`ErrorCategory` is the closed category vocabulary. `ErrorCode` contains stable implemented codes in
the form `pil.<category>.<condition>`. Codes are append-only public identifiers: do not rename,
reuse, or change the meaning of a released value. Add a new code when callers must distinguish a
new condition. Human-readable messages may add specific evidence and are not stable identifiers.

Platform semantic exceptions expose `category`, `code`, and `as_dict()` while retaining their
established `ValueError`, `TypeError`, or `PermissionError` family for compatibility. Invalid or
missing scope values are `input`; conflicts between otherwise valid governed records are `policy`;
and scope conflicts involving a principal, approval, or authority are `authorization`. Adapters
translate platform failures at system boundaries; they must preserve the stable code and must not
infer success from an unknown code.

## Values, configuration, and observability

- Use `Decimal` for money and other exact quantities. Money always carries currency; quantities
  carry explicit units where the predicate is not inherently unitless. Reject non-finite values and
  invalid negative values at construction.
- Keep unknown, absent, unresolved, zero, and empty distinct. Do not use truthiness where zero or an
  empty-but-valid collection has domain meaning.
- Load configuration explicitly at the composition root. Secrets come from environment variables or
  a secret manager and are never committed, logged, embedded in prompts, or stored in provenance.
- Emit structured logs with stable event/error codes, scope-safe correlation identifiers, and
  evidence references. Logs must support OTel/Logfire hooks without making either dependency
  mandatory. Never log raw secrets, hidden reasoning, or unredacted sensitive payloads.
- Feature flags are explicit, scoped, observable, and removed or ratified after their experiment.

## Models, prompts, and generated artifacts

Prompts, schemas, model configurations, and evaluation definitions are versioned artifacts. Record
provider/model revisions in execution provenance, not domain semantics. Generated code and derived
indexes are disposable outputs: they are never the source of semantic truth and must be reproducible
from reviewed source/configuration. Model or prompt changes require representative evaluation and
error analysis; a successful API call is not quality evidence.

## Definition of done

A change is done only when:

- the linked Issue acceptance criteria are satisfied by current-revision evidence;
- relevant formatter, linter, strict typing, architecture, and layered tests pass;
- semantic scenario families and the real public caller or clean built artifact are exercised;
- typed failures, provenance, uncertainty, and authorization boundaries are preserved;
- documentation, ADR, handoff, milestone, and GitHub Project state are synchronized when affected;
- model/algorithm changes include benchmark evidence and dependency changes include lockfile review;
- a fresh review targets the latest revision with no unresolved actionable findings; and
- no confidential data, credentials, hidden reasoning, or private evaluator content is committed.
