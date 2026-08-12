# Security and guardrails

## Threats

- Malicious or compromised vendor documents containing instruction-like text.
- Cross-project or cross-tenant data leakage through retrieval filters.
- Hallucinated commitments or dates presented as facts.
- Replay, duplicate, or unauthorized procurement actions.
- Sensitive commercial data copied into logs or model prompts.

## Controls

- Treat all ingested text as untrusted data, never as policy.
- Enforce authorization before retrieval and again before action.
- Carry provenance and confidence through every transformation.
- Redact secrets and minimize payloads sent to models.
- Use typed tool contracts, allowlists, dry-run mode, approval workflows, and idempotency keys.
- Log decisions and evidence references, not unnecessary raw sensitive content.
- Provide deletion/retention policies and incident-response hooks before production use.

The prototype demonstrates the policy boundary but cannot provide real isolation, secrets management, or compliance guarantees.
