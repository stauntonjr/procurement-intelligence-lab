# Corpus agent tools v1

Primary #66; part of #53/#70/#72. Depends on PR175 and the PR176 run foundation.

Two application-owned capabilities expose the existing deterministic services:

- `investigate_quantity`: exactly `item` and timezone-aware `as_of`; returns the governed
  requirement, qualified assessment, policy/decision/snapshot IDs and original evidence.
- `inspect_source`: exactly `evidence_id`; returns the original admitted quantity cells or
  authority record under the same server-owned scope.

The host supplies the run ID and RequestContext; model arguments cannot supply identity,
project, permissions, execution kind, policy or configuration. Input validation and permissions
precede invocation. Run versions must match `corpus-tools/v1`. Each actual invocation appends
start then success/snapshot or a typed failure; a request or error never counts as inspection.
Audit failure prevents returning a falsely completed tool result. There is no automatic retry;
only timeouts are classified transient. Admission/integrity failure is a distinct non-retryable
infrastructure result; generic unavailable and invalid-result failures do not acquire a transient
classification. A later bounded retry policy must preserve these distinctions.

The tools invoke the complete corpus service and scoped source-by-ID port once; they perform
no quantity arithmetic, ranking or answer selection. Source IDs do not grant scope. Output DTOs
share the existing HTTP serializers, so model/UI callers see the same authoritative fields.

The fixture CLI gains investigate/source/finish operations to exercise this path across processes.
It retains server-configured synthetic identity and returns run metadata beside actual results.
Finish closes execution and scores the recorded trajectory; missing/error events block pass.
Fixture traces remain excluded from live inference aggregates. Natural-language routing and
approval/save remain separate G2 gates. Source text and workbook instructions remain untrusted data.

## Complete result validation

Before recording success, the protected invocation constructs and serializes the complete shared
application payload, including nested evidence and authority JSON. Malformed output or missing/
unbounded snapshot identity records typed `invalid_tool_result`; the public caller cannot turn
a recorded success into an output-parser error. [ADR-033](../adr/033-validated-application-payloads.md)
keeps HTTP links at the interface boundary without importing interfaces into application code.
