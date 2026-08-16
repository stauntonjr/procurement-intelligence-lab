# Domain vertical registry and expansion contract

Status: accepted planning and architecture contract. This page is the durable answer to
“which verticals exist, where are they tracked, and how does the next one get added?” GitHub
issues and milestones track delivery; this registry tracks semantic ownership and implementation
status.

## Registry

| Domain ID | Name | Status | Evidence and delivery boundary |
|---|---|---|---|
| `procurement` | Procurement Intelligence | Active, first vertical | [`src/procurement_intelligence_lab/domains/procurement/`](../../src/procurement_intelligence_lab/domains/procurement/), including BOM, initial BoQ and PO records, procurement state/reconciliation/anomaly behavior, the [semantic model](../domains/procurement/semantic-model.md), and the procurement mapping in the [conformance contract](domain-package-conformance.md). M0.34 compiler/manifest work is [Issue #135](https://github.com/stauntonjr/procurement-intelligence-lab/issues/135); platform ownership correction and BoQ/PO pressure tests are [Issue #149](https://github.com/stauntonjr/procurement-intelligence-lab/issues/149). |

There is currently one implemented vertical. The compiler accepts a stable domain ID rather than
branching on `procurement`; acceptance of another ID is an extensibility property, not evidence
that another vertical has been designed or implemented.

## Next-vertical gate

**Next vertical: unselected / gated.** No second vertical is claimed until procurement's package
has been extracted without behavioral or provenance regression, the shared conformance and
evaluation fixtures are runnable, and a separate GitHub issue records the candidate, rationale,
owner, and acceptance evidence. The open design question is tracked in
[architecture open questions](open-questions.md).

The roadmap is therefore:

1. M0: compile and validate the provider-neutral package contract ([Issue #135](https://github.com/stauntonjr/procurement-intelligence-lab/issues/135)).
2. M1–M4: extract and preserve the procurement semantics, evidence, reconciliation, and state
   behavior ([Issue #15](https://github.com/stauntonjr/procurement-intelligence-lab/issues/15)).
3. M8: exercise package authoring and evaluation against the retrieval/UX work.
4. M9: select and implement one second vertical as a portability proof, with its own issue and
   milestone acceptance record.

## Expansion rules

A new vertical is a new declarative package, not a new platform fork. Its contribution must:

- choose a stable `domain_id` and independent domain version;
- provide all twelve catalog bindings and complete source profiles;
- express requirements, policy, and evaluation references without provider, model, service,
  credential, region, deployment, or executable callback names;
- pass the shared compiler, conformance, determinism, provider-neutrality, and provenance
  regression suites; and
- reuse `platform/semantics` without requiring platform or ports to import the new vertical; and
- add its own registry row and GitHub issue before it is called active.

If the candidate needs a different stage order, output contract, or neutral mode, that is a
platform architecture change requiring an ADR and migration evidence—not ordinary domain
configuration. Runtime/provider selection remains outside the package.

The executable extensibility guard is
`tests/unit/test_domain_package_compiler.py::test_compile_is_vertical_neutral`: it compiles an
`inventory` package-shaped fixture through the same catalog without adding an inventory-specific
branch. The fixture is a harness challenge, not a second production vertical.
