---
applyTo: "src/procurement_intelligence_lab/platform/**/*.py,src/procurement_intelligence_lab/domains/**/*.py"
---

# Domain review rules

- Domain code must remain framework-independent and should prefer stdlib types/dataclasses plus project-owned value objects.
- Do not import Docling, SQLAlchemy, FastMCP, LangChain/LangGraph, Pydantic, cloud SDKs, model SDKs, or transport clients into the domain layer.
- Intrinsic invariants, calculations, derived properties, and transformations may live on domain objects when strongly coupled to the object.
- Behavior requiring repositories, external services, orchestration, authorization, or cross-aggregate coordination belongs outside domain objects.
- Preserve semantic distinctions among source assertions, entity-resolution decisions, reconciled state, derived facts, predictions, decisions, and actions.
- Do not collapse unresolved source mentions into canonical identity without an auditable resolution decision.
- Money/quantities must not use binary floating point for authoritative values.
- Platform modules must not import a concrete vertical. Ports depend on platform contracts, and
  vertical-specific registration occurs only at the application composition boundary.
