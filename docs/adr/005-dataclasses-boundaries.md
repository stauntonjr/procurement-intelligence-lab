# ADR-0005: Dataclasses in core, Pydantic at boundaries

Status: accepted

Stdlib dataclasses keep semantics framework-independent. Pydantic is permitted for HTTP, CLI, config, and external payload validation only.

