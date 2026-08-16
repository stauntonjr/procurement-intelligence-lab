# Platform semantics and vertical ownership

Status: accepted implementation contract for Issues #149 and #151.

## Dependency direction

The reusable semantic platform owns contracts that every vertical can use. A vertical imports and
specializes those contracts. The platform never imports a concrete vertical.

```text
platform  <-  domains.procurement
    ^                 ^
  ports      application/composition

platform !-> domains.*
domains.a !-> domains.b
ports !-> domains.procurement
```

`tools/check_architecture.py` enforces these rules in local checks and CI. Platform-owned contracts
are imported from `platform`; the procurement package does not retain generic forwarding modules
that obscure ownership.

## Repository layout

```text
src/procurement_intelligence_lab/
  platform/
    domain_packages/   # stage catalog, concrete contract registry, schema, compiler
    semantics/         # universal stage records, evidence foundations, strategy Protocols
  domains/
    procurement/       # BOM, BoQ, PO and procurement policy/algorithms
```

`platform` replaces the ambiguous singular `domain` package. `domain` beside `domains` encouraged
whole-file classification and made it unclear whether a type described the package compiler, a
shared semantic contract, or one vertical. The earlier root-level `procurement_lab/` prototype is
also superseded by the installable `src/procurement_intelligence_lab/` package and must remain
absent.

## Ownership matrix

| Platform-owned | Procurement-owned |
|---|---|
| Typed evidence locations and `EvidenceRef` | BOM, BoQ, and Purchase Order records |
| Stable semantic identity | Procurement assertion predicates and builders |
| Execution and decision provenance | SKU normalization and exact-match resolver |
| Source-assertion and append-only ledger records | Quantity/price reconciliation records and executor |
| Resolution decision/status envelope | Expected requirements and observed procurement state |
| Request authorization and versioned state scope | Procurement anomaly kinds and typed details |
| State freshness vocabulary | Per-kind procurement anomaly policy parameters |
| Source-precedence strategy and typed failure | Procurement evidence-chain assembly |
| Retrieval projection lifecycle contracts | Procurement DomainPackage bindings and policy references |
| Anomaly severity/lifecycle and evidence envelope | |
| Concrete contracts and strategy Protocols for all twelve logical stages | |
| DomainPackage catalog, semantic contract registry, and compiler | |

Mixed modules are split at the record or behavior boundary. A generic filename is not sufficient
evidence that every implementation inside it belongs to the platform.

## Registration boundary

Platform protocols describe executable strategy behavior. DomainPackage authoring data contains
only versioned references and parameters, never callbacks. The application composition root may
import both the platform registry and a selected vertical implementation and register them there.
The generic anomaly/reconciliation modules therefore never import procurement detectors.

The full contract map and the distinction between semantic and operational completeness are
authoritative in [Universal logical-stage semantics](universal-stage-semantics.md).

## Procurement pressure tests

The initial `Boq`/`BoqLine` and `PurchaseOrder`/`PurchaseOrderLine` records deliberately introduce
planned-versus-ordered quantities, document revision, supplier identity, currency, schedule, and
cross-document line references. They remain procurement-owned while reusing platform evidence,
scope, and identity contracts. This is a realism probe, not a complete ERP or purchasing model.
