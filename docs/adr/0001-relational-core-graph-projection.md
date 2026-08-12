# ADR 0001: Relational core with graph projection

## Decision

Keep canonical records and temporal state in a relational-shaped model; project selected relationships for graph traversal and exploration.

## Context

Procurement facts need constraints, uniqueness, updates, and auditability. Graph traversal is valuable for questions such as “which milestones depend on vendors with open commitments?”

## Consequences

This adds synchronization work, but keeps the source of truth easier to validate and lets graph technology be adopted where it provides measurable value.
