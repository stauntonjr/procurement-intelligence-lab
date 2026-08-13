# Procurement use cases and query contracts

These use cases anchor the public synthetic demo. They are user-facing questions,
but each must resolve to an inspectable application query with deterministic
arithmetic where applicable. “Next DC” is intentionally a domain phrase, not a
hard-coded site: the application must identify the project/site and as-of
context or ask for clarification.

## Common response contract

Every response should identify:

- project, site, BOM revision, and as-of time used;
- the answer claims and their epistemic status;
- assumptions, unresolved identities, conflicts, and missing data;
- deterministic calculations and query inputs;
- claim-level `EvidenceRef` values that can be followed to source assertions,
  structured document locations, and the original synthetic artifact.

An LLM may interpret the question and explain the result. It must not invent
quantities, select governing claims, or perform authoritative arithmetic.

## UC-001: Distinct SKUs for the next data center

### User story

As a procurement planner, I want to know which different SKUs are required for
the next data center, so that I can prepare the procurement worklist and detect
items that are unresolved or inconsistently named across documents.

### Query

> What different SKU do we need for the next DC?

### Expected result

Return a deterministic list of distinct canonical procurement items, grouped by
canonical SKU or item identifier, including:

- required quantity and unit of measure;
- manufacturer, vendor, description, and source identifiers;
- aliases and source mentions that were resolved to the item;
- BOM revision and project/site scope;
- unresolved or disputed mentions excluded from the canonical list but shown as
  a review section;
- source precedence and conflicts affecting inclusion.

“Different” means distinct canonical items under an explicit identity policy,
not merely distinct description strings. If “next” cannot be resolved to one
project, site, or approved BOM revision, the system must ask for clarification
instead of silently choosing one.

### Evidence path

`answer claim → canonical item set → reconciliation/state → resolution decisions
→ source assertions → mapped SKU field → structured location → artifact`

### Relevant milestones

M1 supplies structured observations; M2 preserves assertions; M3 resolves
mentions; M4 produces the governed canonical item set; M5 exposes the question
and drill-down in chat.

## UC-002: GPU quantity and model requirements

### User story

As a capacity or procurement planner, I want to know how many GPUs and which GPU
models the next data center requires, so that I can compare the requirement with
ordered, received, and outstanding quantities.

### Query

> How many GPUs do we need for the next DC?

### Expected result

Return a breakdown by canonical GPU SKU/model, with at least:

- required quantity;
- ordered quantity;
- received quantity when available;
- outstanding quantity, calculated deterministically;
- unit and project/site scope;
- BOM revision and effective date;
- substitutions, unresolved identities, and conflicting quantity claims;
- an explicit statement of whether “need” means total requirement,
  unprocured quantity, or another approved measure.

The response must not collapse different GPU models into one total unless the
user requests an aggregate and the aggregation policy permits it. A quantity
from a vendor document is an assertion; it becomes operational state only after
resolution and reconciliation.

### Evidence path

`answer claim → quantity calculation → operational state → reconciliation
decision → canonical GPU → resolution decision → source assertion → BOM/PO
location → artifact`

### Relevant milestones

M1–M4 establish the data and deterministic state query. M5 makes the result
inspectable through chat. M7 may add delivery-risk or capacity predictions, but
those must remain visibly distinct from the requirement calculation.

## UC-003: Scenario cost for a proposed BOM

### User story

As a planner, I want to estimate the cost of a proposed BOM, so that I can
compare design or procurement scenarios before treating one as an approved
commitment.

### Query

> What would the cost be if the BOM looks like this?

### Expected result

Treat this as a scenario calculation, not a claim about current committed cost.
Return:

- the proposed BOM revision or explicit line-item input;
- canonical item, quantity, unit, currency, and unit-price basis for each line;
- line extensions and total calculation;
- price source, effective date, quote/contract reference, and inclusions or
  exclusions such as tax, freight, installation, or escalation;
- missing-price lines and unresolved items separately from priced lines;
- a low/high/range result when the source evidence supports a range;
- comparison with the current reconciled BOM when requested;
- assumptions, stale prices, conflicts, and review requirements.

The system must not silently substitute a similar SKU or fabricate a price. A
scenario may use proposed mappings, but those must be labeled proposed and must
not mutate canonical procurement state without an explicit review and approval
workflow.

### Evidence path

`scenario claim → line-extension calculation → proposed mapping/state → price
assertion → mapped price field → structured location → quote/contract artifact`

### Relevant milestones

M1–M2 establish quantities, locations, and price assertions. M3 handles item
identity. M4 provides governed state and deterministic arithmetic. M5 exposes
the scenario and evidence. M8 is responsible only if the scenario is later
turned into an approval-gated action.

## Acceptance examples for the synthetic corpus

The first corpus should support these questions with deliberately planted
edge cases:

1. Two descriptions and manufacturer part numbers resolve to one canonical SKU.
2. Two similar GPU models remain separate canonical items.
3. A BOM quantity conflicts with a later approved revision.
4. A PO covers only part of the required quantity.
5. A price is missing, stale, or expressed in a different currency.
6. A proposed scenario contains an unresolved SKU and cannot produce a falsely
   precise total.

Each example needs expected answer claims, expected calculations, expected
   abstentions or warnings, and gold evidence locations in a versioned
   evaluation manifest.
