# Evidence-contract test matrix

The golden tests protect the public evidence-inspector contract.

- A resolved BOM claim retains artifact identity, hash, sheet, rows, cells, source assertions, resolution, operational state, and reconciliation stages.
- Incomplete prices abstain from cost claims; unresolved identity does not enter canonical operational state.
- Conflicting prices retain every source artifact and surface a reconciliation conflict.

These are semantic tests, not a coverage target. Any new material claim or UI adapter must preserve the same drill-down contract.
