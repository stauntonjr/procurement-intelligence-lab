# ADR-033: Original showcase sources behind the existing review workflow

Status: Accepted for owner-authorized demo continuation; unmerged.
Date:2026-10-04. Primary#71; governing#53/#66/#67/#68/#70/#72/#74.

The approved corpus plan requires retaining the original three live walkthrough outcomes.
They all use GPU-A at2026-01-15T00:00:00Z in synthetic-project/synthetic-site, and their
original showcase service owns claim/policy identity. Mapping them into new corpus claims
would change those identities. Reuse showcase_order_comparison through a small Investigator
Protocol consumed by the existing tools. Domain calculations and approval mechanics are unchanged.

ReviewSources exposes only an admitted item catalog, fresh source snapshot identity and scoped
source lookup. Complete admitted source IDs fence misconfigured original service/source pairs. Default SyntheticCorpusReader implements it over its existing admitted inventory.
The original-source adapter verifies a packaged hash manifest and original XLSX bytes, then
returns literal catalog items/source rows. It cannot supply decisions. The composition root selects
physical source sets before inference: A+order, A+B+order or A-only. No source-set/scenario label,
quantity, outcome or evaluator metadata enters model input. The original deterministic bridge
uses the corresponding existing fixture service, exact original scope/item/cutoff and unchanged
assessment/governance IDs. These are explicit fixed synthetic source configurations, not uploads,
retrieval or natural-language scenario classifiers.

Run fixture versions bind source-set identity and manifest/source hashes; application versions
bind code. Changing sources refuses old recovery/review. Permission/scope and hash admission
precede reads. Source lookups accept only admitted original EvidenceRefs. Existing source files,
legacy routes/gold and corpus defaults remain unchanged. No new data or model/prompt swap.

The original comparison retains observed order2 with an unresolved requirement. The new original
brief retains that value and not_assessed status, and the page labels it an order observation;
it is not an assessed quantity or evidence of reconciliation. Corpus quantity semantics and page
labels remain unchanged. Missing observation staysnull. Unsupported original item/date is typed
input failure and cannot silently use the fixed cutoff. Models only route exact human intent;
human exact review remains the only save authority. Live authored trials are not held-out accuracy.
