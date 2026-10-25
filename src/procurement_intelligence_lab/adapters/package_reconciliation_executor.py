"""Translate a neutral invocation into the explicitly composed domain strategy."""

from collections.abc import Callable
from dataclasses import dataclass

from procurement_intelligence_lab.domains.procurement.retained_reconciliation import (
    build_reconciliation_audit,
    quantity_assertions,
)
from procurement_intelligence_lab.platform.execution.reconciliation_contracts import (
    ReconcileInvocation,
)
from procurement_intelligence_lab.platform.execution.reconciliation_inputs import (
    RetainedReconciliationInputs,
)
from procurement_intelligence_lab.platform.execution.reconciliation_outputs import ReconciledOutput
from procurement_intelligence_lab.platform.semantics.strategies import ReconcileStrategy


@dataclass(frozen=True)
class PackageReconciliationExecutor:
    strategy: ReconcileStrategy
    validate_output: Callable[[ReconciledOutput], None]

    def invoke(
        self, inputs: RetainedReconciliationInputs, *, invocation: ReconcileInvocation
    ) -> ReconciledOutput:
        assertions = quantity_assertions(inputs)
        decisions, states = self.strategy.reconcile(
            assertions,
            scope=invocation.scope,
            as_of=invocation.as_of,
            provenance=invocation.provenance,
        )
        consumed = {a.assertion.assertion_id for d in decisions for a in (*d.governing, *d.losing)}
        outside = tuple(
            sorted(
                a.assertion_id
                for p in inputs.recorded_producers
                for a in p.completed.execution.output.previous.assertions
                if a.assertion_id not in consumed
            )
        )
        output = ReconciledOutput(
            inputs,
            decisions,
            states,
            outside,
            build_reconciliation_audit(inputs, decisions, states, provenance=invocation.provenance),
            invocation.provenance,
        )
        self.validate_output(output)
        return output
