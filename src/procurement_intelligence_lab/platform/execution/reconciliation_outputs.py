"""One actual reconciliation output with exhaustive source-claim membership."""

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from procurement_intelligence_lab.platform.execution.identity import canonical, digest, same
from procurement_intelligence_lab.platform.execution.outputs import event, immutable_output, require
from procurement_intelligence_lab.platform.execution.reconciliation_inputs import (
    RetainedReconciliationInputs,
)
from procurement_intelligence_lab.platform.semantics.provenance import (
    ComponentKind,
    DecisionProvenance,
)
from procurement_intelligence_lab.platform.semantics.reconciliation import ReconciliationDecision
from procurement_intelligence_lab.platform.semantics.state import OperationalState


@dataclass(frozen=True)
class ReconciledOutput:
    inputs: RetainedReconciliationInputs
    decisions: tuple[ReconciliationDecision, ...]
    states: tuple[OperationalState, ...]
    outside_predicate_ids: tuple[str, ...]
    domain_audit: bytes
    provenance: DecisionProvenance

    def __post_init__(self) -> None:
        immutable_output(self)
        require(
            type(self.inputs) is RetainedReconciliationInputs
            and type(self.provenance) is DecisionProvenance
        )
        require(
            type(self.decisions) is tuple
            and all(type(d) is ReconciliationDecision for d in self.decisions)
        )
        require(
            type(self.states) is tuple and all(type(s) is OperationalState for s in self.states)
        )
        require(
            type(self.outside_predicate_ids) is tuple
            and self.outside_predicate_ids == tuple(sorted(set(self.outside_predicate_ids)))
        )
        require(type(self.domain_audit) is bytes and 0 < len(self.domain_audit) <= 4 * 1024 * 1024)

        def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
            obj: dict[str, Any] = {}
            for key, value in items:
                require(key not in obj)
                obj[key] = value
            return obj

        def invalid_constant(value: str) -> None:
            require(False)

        try:
            audit = json.loads(
                self.domain_audit.decode("utf-8"),
                object_pairs_hook=pairs,
                parse_constant=invalid_constant,
            )
            require(type(audit) is dict and canonical(audit) == self.domain_audit)
        except (ValueError, UnicodeError, RecursionError):
            require(False)
        require(
            self.provenance.component_kind is ComponentKind.DETERMINISTIC
            and self.provenance.policy_version == self.inputs.policy.reference.reference_id
        )
        require(
            all(
                getattr(self.provenance, k) is None
                for k in (
                    "model_provider",
                    "model_id",
                    "model_revision",
                    "prompt_version",
                    "schema_version",
                )
            )
        )
        require(set(self.inputs.input_ids) <= set(self.provenance.context.input_snapshot_ids))
        source = {
            a.assertion_id: a
            for p in self.inputs.recorded_producers
            for a in p.completed.execution.output.previous.assertions
        }
        links = {
            a.canonicalized_assertion_id: a
            for p in self.inputs.recorded_producers
            for a in p.completed.execution.output.canonicalized
        }
        consumed: list[str] = []
        require(
            tuple(d.subject_key for d in self.decisions)
            == tuple(sorted({d.subject_key for d in self.decisions}))
        )
        for d in self.decisions:
            require(
                same(d.provenance, self.provenance)
                and d.policy_id == self.inputs.policy.reference.reference_id
            )
            for a in (*d.governing, *d.losing):
                require(same(links.get(a.canonicalized_assertion_id), a))
                consumed.append(a.assertion.assertion_id)
        require(len(set(consumed)) == len(consumed))
        require(
            not set(consumed) & set(self.outside_predicate_ids)
            and set(consumed) | set(self.outside_predicate_ids) == set(source)
        )
        decisions = {d.reconciliation_id: d for d in self.decisions}
        require(len({s.subject_key for s in self.states}) == len(self.states))
        for s in self.states:
            require(
                s.reconciliation_id in decisions
                and decisions[s.reconciliation_id].subject_key == s.subject_key
                and same(s.provenance, self.provenance)
                and same(s.as_of, self.inputs.as_of)
            )

    @property
    def semantic_output(self):
        return (
            self.decisions,
            self.states,
            self.outside_predicate_ids,
            self.domain_audit,
            self.provenance,
        )

    @property
    def batch_id(self) -> str:
        return "reconciliation-batch-v1:" + digest(
            (self.inputs.semantic_payload, self.semantic_output)
        )

    @property
    def reference_ids(self) -> tuple[str, ...]:
        return (
            self.batch_id,
            *(d.reconciliation_id for d in self.decisions),
            *(s.state_id for s in self.states),
            sha256(self.domain_audit).hexdigest(),
        )

    @property
    def event(self):
        return event(
            "required-quantity-reconciliation",
            self.provenance,
            self.inputs.input_ids,
            self.reference_ids,
            tuple(
                p.completed.execution.output.event.event_id for p in self.inputs.recorded_producers
            ),
        )
