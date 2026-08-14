# ADR-016: Expected-versus-observed anomaly contract

Status: accepted

## Context

The architecture distinguishes operational state from derived intelligence. An anomaly is a typed deviation between an expected value or state and an observed value or state; it is not itself a prediction, decision, or action.

Anomaly detection must remain deterministic and explainable where practical. Thresholds must be explicit and auditable, and an anomaly must retain the evidence used for both sides of the comparison. The repository currently has a small operational-state projection but no anomaly contract.

## Decision

Define a framework-independent anomaly contract:

- AnomalyKind names the supported deviation categories: missing PO, quantity mismatch, stale revision, substitution, late commitment, price deviation, unresolved identity, and coverage gap.
- Anomaly is immutable and carries the subject, expected and observed values, severity, lifecycle status, policy identifier, detection timestamp, and source evidence.
- AnomalyPolicy holds explicit non-negative quantity, price, and schedule tolerances.
- Deterministic helpers emit an open warning only when a comparison exceeds the configured tolerance. They return no anomaly within tolerance.
- State orchestration consumes `ExpectedObservedState`: it emits missing-PO, quantity-mismatch, substitution, and coverage-gap anomalies where the state contract provides the required inputs. It does not infer revision, price, schedule, or identity anomalies from incomplete state.
- Detection timestamps must be timezone-aware. Anomaly IDs are stable for the same semantic inputs and evidence references.

This slice provides the core contract and representative deterministic comparisons. Broader detection orchestration and durable anomaly persistence remain later work.

## Consequences

Anomalies can be reviewed, suppressed, resolved, and traced without conflating them with canonical state or predictions. Policy changes are visible through their policy identifiers and produce distinct anomaly identities. The domain remains independent of persistence, model, and transport frameworks.

Future adapters may persist anomalies or project them into retrieval/review surfaces, but those mechanisms must preserve this contract.
