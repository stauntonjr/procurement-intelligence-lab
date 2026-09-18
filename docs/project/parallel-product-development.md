# Parallel product development and showcase plan

Date: 2026-09-18

## Agreed direction

The owner prioritizes two independent products that can be shown to prospective employers as
soon as possible, with planning for smooth, efficient integrations. Each product keeps its own
roadmap, acceptance criteria, release cadence, and demonstration. Integration readiness supports
delivery; a shared-platform migration is not a prerequisite for either showcase.

This document records that direction and proposes the delivery process below. It does not mark
showcase artifacts complete, schedule model execution, or authorize deployment. GitHub Issues and
accepted ADRs remain authoritative for implementation. The SciFact-specific proposals must be
recorded in that repository's work items before implementation; this document does not replace
its roadmap.

## First showcase milestones

| Product | Demonstrate now from accepted capabilities | Evidence and limits to show | Separate follow-on |
|---|---|---|---|
| [SciFact RAG](https://github.com/stauntonjr/scifact-rag) | Search, cited answer, explicit insufficiency, and inspection of supplied evidence through its accepted UI | One fixed retrieval comparison and latency tradeoff; citation validity versus semantic support; DGX-local deployment boundary | Bounded Evidence Inference reader research; its results are not required for the existing prototype showcase |
| Procurement Intelligence Lab | Synthetic BOM question, deterministic quantity or cost, evidence drill-down to the source, and a verified unresolved/conflict case | Source assertions versus governing claims, calculation provenance, and the current scope of the runnable inspector | Broader BoQ/PO governing-claim acceptance under [Issue #15](https://github.com/stauntonjr/procurement-intelligence-lab/issues/15), then dependent anomaly work |

Before presenting a case, verify it through the actual public entry point at a recorded commit.
Use existing acceptance examples where possible. Do not present planned ordered/received/
outstanding calculations, complete review workflows, or research outcomes as delivered behavior.

Each first showcase should have a short README entry, a three-to-five-minute walkthrough,
screenshots or a recording, a simple architecture diagram, reproduction instructions, and links
to supporting evaluation or acceptance evidence. A recording permits asynchronous employer
review without requiring their access to the DGX. Identify recorded output as recorded output;
public hosting is a separate scope decision. Existing usable artifacts should be reused.

The showcase is ready when a reviewer can understand the problem, observe a working outcome,
inspect its evidence, and identify the project's limitations without reading the full roadmap.
Completion of every umbrella milestone is not required.

## Parallel delivery process

1. Maintain one primary delivery slice per repository. Initially, prioritize each product's
   showcase packet and close only the concrete gaps that prevent its walkthrough from working.
   Keep ongoing research separate from the stable demonstration revision.
2. Give each implementation task one repository and an isolated checkout. Record its governing
   issue, acceptance examples, touched contracts, and evidence. Review against the final revision
   using the repository's existing process; avoid creating a second engineering harness.
3. Keep a small cross-project integration queue in linked issues. Review it after a relevant
   capability lands or a showcase milestone completes, rather than coupling routine releases.
   A coordinating task records dependencies and decisions; repository artifacts carry handoffs.
4. Merge and release independently. Consumer changes must pass their own public-caller tests.
   Any adopted external artifact is pinned to a revision or version, with a documented fallback
   where the consumer requires one. Do not require simultaneous merges across repositories.
5. Allow CPU development, fixture preparation, and documentation to proceed concurrently. GPU
   execution follows the resource owner's allocation and each experiment's existing budget and
   readiness gates, including the current Lattice boundary. No task implicitly restarts or
   reconfigures another project's services.

## Integration entry criteria

A transfer starts only when a consumer has a concrete use case. Its linked work items record:

- producer repository, source revision, and capability;
- input/output contract, evidence identity, typed failures, and dependency requirements;
- consumer-specific acceptance examples and measured benefit;
- ownership, compatibility/version policy, and rollback or fallback behavior.

Transfer patterns and test cases first when that is sufficient. Extract a shared package only
after both products demonstrate a stable common behavior and shared maintenance is worth the
release/dependency cost. Research scripts do not become production dependencies merely because
an experiment completed.

| Candidate transfer | Consumer acceptance boundary |
|---|---|
| SciFact evaluation methods and retrieval adapters into procurement | [Issue #62](https://github.com/stauntonjr/procurement-intelligence-lab/issues/62): synthetic procurement gold evidence, identifiers, scope, revisions, numerical support, latency, and stale-index behavior; public-proxy scores cannot establish domain quality |
| SciFact shared-application and MCP pattern into procurement | [Issue #66](https://github.com/stauntonjr/procurement-intelligence-lab/issues/66): deterministic services retain authority, explicit request scope, typed failures, and CLI/MCP parity |
| Procurement evidence and semantic contracts into SciFact | A new bounded SciFact issue must demonstrate improved traceability or conformance without changing accepted answer behavior; a DomainPackage migration remains optional |

## Next planning actions

- In each repository, inventory existing showcase artifacts and define one bounded issue for
  missing presentation or reproducibility work. Reuse existing issues where their scope fits.
- Capture the walkthrough acceptance cases before expanding features. Use the accepted SciFact
  prototype and the current runnable procurement slice as the initial baselines.
- After those packets are reviewable, select the next product slice independently and admit at
  most one concrete integration pilot. A procurement-specific retrieval benchmark specification
  is a candidate; adapter adoption depends on its evidence.
- Keep the distinction between runnable capabilities, verified showcase cases, and broader
  milestone completion visible in each handoff and README.
