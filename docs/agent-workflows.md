# Agent workflows and controls

The agent is a coordinator over typed tools, not an unrestricted operator.

```mermaid
sequenceDiagram
  participant U as User
  participant O as Orchestrator
  participant R as Retrieval
  participant P as Policy
  participant H as Human approver
  participant T as Tool adapter
  participant L as Audit ledger
  U->>O: Ask for procurement status
  O->>R: Retrieve evidence with filters
  R-->>O: Facts + provenance + uncertainty
  O->>P: Classify proposed action
  P-->>O: Read-only or approval required
  alt approval required
    O->>H: Show evidence, diff, impact, expiry
    H-->>O: Approve or reject
  end
  O->>T: Execute idempotent action with scoped token
  T-->>O: Result / failure
  O->>L: Append immutable audit event
```

Required controls include least-privilege service identities, tenant/project scope checks, tool schemas, dry-run previews, approval expiry, idempotency keys, replay protection, rate limits, and a complete record of prompt-independent evidence used for the decision.
