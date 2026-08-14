# M1 XLSX evidence-backed slice

This slice implements the first executable path from the roadmap: a dependency-free synthetic XLSX BOM adapter, typed line-level EvidenceRefs, deterministic SKU/GPU/cost queries, and explicit abstention when cost inputs are incomplete.

It also preserves source assertions, conservative resolution decisions, operational-state projection, deterministic reconciliation, and a framework-independent evidence chain. The committed `examples/synthetic_bom.xlsx` fixture and `make demo` provide a runnable, inspectable path through these layers.

The adapter intentionally handles the constrained synthetic fixture shape. Production document structuring, persistence, UI inspection, and richer XLSX features remain subsequent slices.
