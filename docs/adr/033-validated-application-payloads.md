# ADR-033: Validate application payloads before audited tool completion

Status: accepted for the #72 integration-review correction; governed by #66/#68 and ADR-028.

Tool success must establish that the actual result can be consumed by the public caller. Snapshot
identity alone cannot establish validity of nested domain output. Shared serializable payloads
therefore live in an application-owned stdlib module; the audited invocation constructs and
serializes them inside its protected error boundary before recording success. Malformed nested
results produce a typed failed invocation. HTTP interfaces decorate admitted evidence with links,
without making application services import interface code. Existing public field names and domain
policy remain unchanged. There is no new agent authority or external dependency.

The same payload is used for tool validation and public rendering so validators cannot drift from
serializers. A failure after durable append due to storage/transport remains a distinct failure;
this decision does not claim to atomically couple HTTP delivery and database writes.
