"""Explicit recorded-producer loading, admission and one current stage execution."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from procurement_intelligence_lab.application.archived_resolved_execution import (
    ResolvedExecutionArchiveReader,
)
from procurement_intelligence_lab.platform.execution.contracts import plan_payload, validate_context
from procurement_intelligence_lab.platform.execution.identity import aware, digest_text, same, text
from procurement_intelligence_lab.platform.execution.reconciliation_admission import (
    ReconcileExecutorRegistration,
    prepare_reconciliation,
)
from procurement_intelligence_lab.platform.execution.reconciliation_contracts import (
    ReconciliationOperationReceipt,
    RetainedReconciliationRequest,
)
from procurement_intelligence_lab.platform.execution.reconciliation_inputs import (
    OperationAuthorityEvidence,
    ReconciliationPolicyEvidence,
    RetainedReconciliationInputs,
)
from procurement_intelligence_lab.platform.execution.reconciliation_outputs import ReconciledOutput
from procurement_intelligence_lab.platform.execution.reconciliation_runner import run_reconciliation
from procurement_intelligence_lab.platform.execution.resolution_archive import (
    ArchivedResolvedPrefix,
)
from procurement_intelligence_lab.platform.execution.resolution_inputs import admit
from procurement_intelligence_lab.platform.planning.contracts import (
    ImplementationConfig,
    ImplementationDescriptor,
    ImplementationRegistry,
    PhysicalPlan,
)
from procurement_intelligence_lab.platform.planning.planner import plan_manifest
from procurement_intelligence_lab.platform.semantics.errors import (
    ArchiveContractError,
    ArchiveIntegrityError,
    PackageExecutionContractError,
    UnsupportedReconciliationInputError,
)
from procurement_intelligence_lab.platform.semantics.provenance import ProvenanceContext
from procurement_intelligence_lab.platform.semantics.scope import StateScope


@dataclass(frozen=True)
class RetainedReconciliationService:
    manifest: bytes
    registry: ImplementationRegistry
    config: ImplementationConfig
    policy: ReconciliationPolicyEvidence
    authority: OperationAuthorityEvidence
    producer_reader_factory: Callable[[], ResolvedExecutionArchiveReader]
    measure_producer: Callable[[ArchivedResolvedPrefix], tuple[int, int]]
    executor_factory: Callable[[RetainedReconciliationInputs], ReconcileExecutorRegistration]
    validate_inputs: Callable[[RetainedReconciliationInputs, datetime], None]
    validate_output: Callable[[ReconciledOutput], None]
    clock: Callable[[], datetime]
    validate_static: Callable[
        [OperationAuthorityEvidence, ReconciliationPolicyEvidence, tuple[str, ...]], None
    ]

    expected_descriptor: ImplementationDescriptor
    validate_receipt: Callable[[ReconciliationOperationReceipt], None]

    def preflight(
        self,
        *,
        scope: StateScope,
        as_of: datetime,
        context: ProvenanceContext,
        producer_digests: tuple[str, ...],
    ) -> PhysicalPlan:
        admit(type(scope) is StateScope)
        for v in vars(scope).values():
            text(v)
        validate_context(context)
        aware(as_of)
        admit(as_of <= context.started_at)
        admit(
            type(producer_digests) is tuple
            and 1 <= len(producer_digests) <= 8
            and len(set(producer_digests)) == len(producer_digests)
        )
        for d in producer_digests:
            digest_text(d)
        now = self.clock()
        aware(now)
        admit(now >= context.started_at)
        self.validate_static(self.authority, self.policy, producer_digests)
        plan = plan_manifest(self.manifest, registry=self.registry, config=self.config)
        b = plan_payload(plan)["stages"][6]
        admit(
            self.config.application_version == context.code_revision
            and b["mode"] == "EXECUTE"
            and b["domain_config_ref"] is None
            and b["policy_refs"] == [self.policy.reference.declaration_ref]
        )
        selected = next(
            (
                d
                for d in self.registry.implementations
                if d.implementation_id == b["implementation"]["implementation_id"]
            ),
            None,
        )
        admit(same(selected, self.expected_descriptor))
        # Metadata is inspected here; no executor factory is called until all producer evidence is admitted.
        admit(
            b["implementation"]["provider_version"] is None
            and b["implementation"]["model_version"] is None
        )
        return plan

    def execute(
        self,
        *,
        scope: StateScope,
        as_of: datetime,
        context: ProvenanceContext,
        producer_digests: tuple[str, ...],
    ) -> ReconciliationOperationReceipt:
        self.preflight(scope=scope, as_of=as_of, context=context, producer_digests=producer_digests)
        reader = self.producer_reader_factory()
        reader.archive.check_ready()
        producers: list[ArchivedResolvedPrefix] = []
        byte_count = 0
        node_count = 0
        for d in sorted(producer_digests):
            p = reader.show(scope, d).retained
            nbytes, nodes = self.measure_producer(p)
            admit(type(nbytes) is int and type(nodes) is int and nbytes >= 0 and nodes >= 0)
            a = p.completed.prefix.snapshot.artifact
            byte_count += nbytes + a.byte_length
            node_count += nodes
            if byte_count > 4 * 1024 * 1024 or node_count > 12500:
                raise UnsupportedReconciliationInputError(
                    "selected producer graph exceeds aggregate reconciliation budget"
                )
            content = reader.content(scope, d)
            if len(content) != a.byte_length or sha256(content).hexdigest() != a.content_hash:
                raise ArchiveIntegrityError(
                    "retained producer source content does not match artifact"
                )
            producers.append(p)
        inputs = RetainedReconciliationInputs(
            scope, as_of, tuple(producers), self.authority, self.policy
        )
        self.validate_inputs(inputs, context.started_at)
        request = RetainedReconciliationRequest(inputs, context)
        registration = self.executor_factory(inputs)
        prepared = prepare_reconciliation(
            self.manifest,
            registry=self.registry,
            config=self.config,
            request=request,
            registration=registration,
            now=self.clock(),
        )
        receipt = run_reconciliation(prepared, clock=self.clock)
        self.validate_output(receipt.output)
        try:
            self.validate_receipt(receipt)
        except ArchiveContractError:
            raise PackageExecutionContractError(
                "reconciliation result exceeds its operation evidence bound"
            ) from None
        return receipt
