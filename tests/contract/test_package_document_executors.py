from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, NoReturn, cast

import pytest

from procurement_intelligence_lab import bootstrap
from procurement_intelligence_lab.adapters.local_artifacts import MemoryArtifactContent
from procurement_intelligence_lab.application.asserted_document_stages import AssertedDocumentStages
from procurement_intelligence_lab.application.document_stages import DocumentStages
from procurement_intelligence_lab.application.normalized_document_stages import (
    NormalizedDocumentStages,
)
from procurement_intelligence_lab.platform.domain_packages.package import StageId
from procurement_intelligence_lab.platform.execution.contracts import (
    ExecutionRequest,
    StageInvocation,
)
from procurement_intelligence_lab.platform.execution.executors import StageExecutor
from procurement_intelligence_lab.platform.execution.outputs import (
    AssertedOutput,
    CapturedOutput,
    MappedOutput,
    StageInput,
    StageOutput,
    StructuredOutput,
    event,
)
from procurement_intelligence_lab.platform.semantics.errors import (
    PackageExecutionContractError,
    SemanticContractError,
)
from tests.bom_stage_fixtures import AT, HEADER, ROW, provenance, workbook
from tests.contract.test_bom_assertions import POLICY
from tests.contract.test_bom_stage_adapters import source
from tests.planned_bom_fixtures import planned_inputs

pytestmark = pytest.mark.contract


def service():
    assert hasattr(bootstrap, "build_planned_bom_service"), "planned composition is not implemented"
    m, r, c = planned_inputs()
    return bootstrap.build_planned_bom_service(
        manifest=m, registry=r, config=c, policy=POLICY, clock=lambda: AT + timedelta(seconds=1)
    )


@dataclass
class CountingExecutor:
    actual: StageExecutor
    calls: list[StageId]
    corrupt: bool = False

    def invoke(self, inputs: StageInput, *, invocation: StageInvocation) -> StageOutput:
        self.calls.append(invocation.stage)
        result = self.actual.invoke(inputs, invocation=invocation)
        if self.corrupt and type(result) is StructuredOutput:
            p = result.document.provenance
            p = replace(
                p,
                context=replace(
                    p.context,
                    started_at=p.context.started_at.astimezone(timezone(timedelta(hours=2))),
                ),
            )
            d = replace(result.document, provenance=p)
            return StructuredOutput(
                result.previous,
                d,
                event(
                    "document-structuring",
                    p,
                    result.input_ids,
                    result.reference_ids,
                    (result.previous.event.event_id,),
                ),
            )
        return result


def test_real_strategies_run_once_without_legacy_pipeline_and_keep_retained_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    path = workbook(tmp_path / "source.xlsx", HEADER + ROW + ROW.replace("7", "8"))
    ref = source(path)
    content = path.read_bytes()
    expected = bootstrap.build_bom_assertion_service(
        captured_at=AT, context=provenance().context, policy=POLICY
    ).run(ref)

    class Store:
        def __init__(self):
            self.store = MemoryArtifactContent()
            self.puts = 0

        def put(self, content: bytes) -> str:
            self.puts += 1
            key = self.store.put(content)
            path.unlink()
            return key

        def get(self, content_hash: str) -> bytes:
            return self.store.get(content_hash)

    store = Store()

    def forbidden(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("legacy pipeline must not be rerun")

    for cls in [DocumentStages, NormalizedDocumentStages, AssertedDocumentStages]:
        monkeypatch.setattr(cls, "run", forbidden)
    m, r, c = planned_inputs()
    s = bootstrap.build_planned_bom_service(
        manifest=m,
        registry=r,
        config=c,
        policy=POLICY,
        clock=lambda: AT + timedelta(seconds=1),
        content_store=store,
    )
    factory = s.executor_factory
    calls: list[StageId] = []

    def counted(at: datetime):
        e = factory(at)
        return replace(
            e,
            registrations=tuple(
                replace(x, executor=CountingExecutor(x.executor, calls)) for x in e.registrations
            ),
        )

    s = replace(s, executor_factory=counted)
    result = s.execute(ExecutionRequest(ref, provenance().context, AT, StageId.ASSERT))
    assert calls == list(StageId)[:5] and store.puts == 1 and not path.exists()
    captured = result.execution.output.chain[0]
    assert type(captured) is CapturedOutput
    assert store.get(captured.artifact.content_hash) == content
    assert [x.value for x in result.execution.output.assertions] == [
        x.value for x in expected.assertions
    ]
    assert [x.evidence.cells for x in result.execution.output.assertions] == [
        x.evidence.cells for x in expected.assertions
    ]
    body = result.as_dict()
    assert body["executed_stages"] == [x.value for x in list(StageId)[:5]]
    assert len(body["transformations"]) == 5
    assert body["execution_receipt"]["package_execution_complete"] is False


@pytest.mark.parametrize(
    "rows",
    [
        HEADER,
        HEADER + ROW,
        HEADER + '<row r="7"><c r="C7"><v>0</v></c></row>',
        HEADER + ROW.replace("<v>0.5</v>", "<v>-1.25</v>"),
        HEADER + ROW.replace("<v>0.5</v>", "<v>invalid</v>"),
    ],
    ids=["empty", "one", "missing-zero", "negative", "invalid"],
)
def test_values_unknown_and_empty_batches_match_legacy(tmp_path: Path, rows: str):
    ref = source(workbook(tmp_path / "source.xlsx", rows))
    ctx = provenance().context
    if "invalid" in rows:
        with pytest.raises(SemanticContractError) as planned_error:
            service().execute(ExecutionRequest(ref, ctx, AT, StageId.ASSERT))
        with pytest.raises(SemanticContractError) as legacy_error:
            bootstrap.build_bom_assertion_service(captured_at=AT, context=ctx, policy=POLICY).run(
                ref
            )
        assert planned_error.value.code is legacy_error.value.code
        return
    actual = service().execute(ExecutionRequest(ref, ctx, AT, StageId.ASSERT)).execution.output
    expected = bootstrap.build_bom_assertion_service(
        captured_at=AT, context=ctx, policy=POLICY
    ).run(ref)
    assert [(x.value, x.evidence.cells) for x in actual.assertions] == [
        (x.value, x.evidence.cells) for x in expected.assertions
    ]
    assert [x.status for x in actual.previous.observations] == [
        x.status for x in expected.normalized.observations
    ]


def test_offset_substituted_actual_executor_stops_before_mapping(tmp_path: Path):
    s = service()
    factory = s.executor_factory
    calls: list[StageId] = []

    def corrupt(at: datetime):
        e = factory(at)
        return replace(
            e,
            registrations=tuple(
                replace(x, executor=CountingExecutor(x.executor, calls, True))
                for x in e.registrations
            ),
        )

    s = replace(s, executor_factory=corrupt)
    with pytest.raises(PackageExecutionContractError):
        s.execute(
            ExecutionRequest(
                source(workbook(tmp_path / "source.xlsx", HEADER + ROW)),
                provenance().context,
                AT,
                StageId.ASSERT,
            )
        )
    assert calls == [StageId.INGEST, StageId.STRUCTURE]


@pytest.mark.parametrize("mode", ["version", "id", "settings", "policy", "schema"])
def test_incompatible_real_composition_fails_before_nonexistent_source(mode: str, tmp_path: Path):
    m, r, c = planned_inputs()
    if mode in ("version", "id", "settings"):
        d = r.implementations[0]
        sel = c.selections[0]
        if mode == "version":
            d = replace(d, implementation_version="2")
        elif mode == "id":
            d = replace(d, implementation_id="unavailable")
            sel = replace(sel, implementation_id="unavailable")
        else:
            d = replace(d, optional_settings=("option",))
            sel = replace(sel, settings=(("option", "unsupported"),))
        r = replace(r, implementations=(d, *r.implementations[1:]))
        c = replace(c, selections=(sel, *c.selections[1:]))
    else:
        import json

        payload = json.loads(m)
        payload["stages"][3 if mode == "policy" else 2][
            "policy_refs" if mode == "policy" else "domain_config_ref"
        ] = ["other.policy/values@1"] if mode == "policy" else "other.mapping/schema@1"
        m = json.dumps(payload).encode()
    with pytest.raises(SemanticContractError) as caught:
        s = bootstrap.build_planned_bom_service(
            manifest=m, registry=r, config=c, policy=POLICY, clock=lambda: AT
        )
        s.execute(
            ExecutionRequest(
                source(tmp_path / "does-not-exist.xlsx"), provenance().context, AT, StageId.ASSERT
            )
        )
    assert caught.value.category.value != "infrastructure"


def test_success_receipt_cannot_drop_resolved_policy_evidence(tmp_path: Path):
    result = service().execute(
        ExecutionRequest(
            source(workbook(tmp_path / "source.xlsx", HEADER + ROW)),
            provenance().context,
            AT,
            StageId.ASSERT,
        )
    )
    with pytest.raises(SemanticContractError):
        replace(result.execution.receipt, references=())


def test_policy_parameters_bind_actual_result_and_execution_identity(tmp_path: Path):
    from procurement_intelligence_lab.domains.procurement.normalization import (
        BomNormalizationPolicy,
        CountUnit,
    )

    m, r, c = planned_inputs()
    ref = source(workbook(tmp_path / "source.xlsx", HEADER + ROW))
    ctx = provenance().context
    q = ExecutionRequest(ref, ctx, AT, StageId.ASSERT)
    s = service()
    first = s.execute(q)
    policy = BomNormalizationPolicy(CountUnit.DOZEN, "GBP", CountUnit.DOZEN)
    other = bootstrap.build_planned_bom_service(
        manifest=m, registry=r, config=c, policy=policy, clock=lambda: AT + timedelta(seconds=1)
    ).execute(q)
    legacy = bootstrap.build_bom_assertion_service(captured_at=AT, context=ctx, policy=policy).run(
        ref
    )
    assert [x.value for x in other.execution.output.assertions] == [
        x.value for x in legacy.assertions
    ]
    assert other.execution.receipt.execution_digest != first.execution.receipt.execution_digest
    assert other.execution.output.previous.policy_reference == policy.reference_id


def test_service_rejects_untyped_request_before_factory_io():
    from typing import Any, cast

    with pytest.raises(SemanticContractError):
        service().execute(cast(Any, None))


@pytest.mark.parametrize("mode", ["mention-offset", "mention-claim-offset", "mutable-map"])
def test_real_runtime_rejects_inexact_or_mutable_executor_output(tmp_path: Path, mode: str):
    s = service()
    factory = s.executor_factory
    calls: list[StageId] = []

    @dataclass
    class CorruptingExecutor:
        actual: StageExecutor

        def invoke(self, inputs: StageInput, *, invocation: StageInvocation) -> StageOutput:
            calls.append(invocation.stage)
            result = self.actual.invoke(inputs, invocation=invocation)
            if mode.startswith("mention-") and type(result) is AssertedOutput:
                mention = result.mentions[0]
                if mode == "mention-offset":
                    mention = replace(
                        mention,
                        observed_at=mention.observed_at.astimezone(timezone(timedelta(hours=2))),
                    )
                else:
                    claim = mention.assertions[0]
                    assert claim.context is not None
                    p = claim.context.provenance
                    p = replace(
                        p,
                        context=replace(
                            p.context,
                            started_at=p.context.started_at.astimezone(
                                timezone(timedelta(hours=2))
                            ),
                        ),
                    )
                    claim = replace(claim, context=replace(claim.context, provenance=p))
                    assert claim.assertion_id == mention.assertions[0].assertion_id
                    mention = replace(mention, assertions=(claim, *mention.assertions[1:]))
                return replace(result, mentions=(mention, *result.mentions[1:]))
            if mode == "mutable-map" and type(result) is MappedOutput:
                return replace(
                    result,
                    document=replace(
                        result.document, fields=cast(Any, list(result.document.fields))
                    ),
                )
            return result

    def corrupt(at: datetime):
        registry = factory(at)
        return replace(
            registry,
            registrations=tuple(
                replace(x, executor=CorruptingExecutor(x.executor)) for x in registry.registrations
            ),
        )

    s = replace(s, executor_factory=corrupt)
    with pytest.raises(PackageExecutionContractError):
        s.execute(
            ExecutionRequest(
                source(workbook(tmp_path / "source.xlsx", HEADER + ROW)),
                provenance().context,
                AT,
                StageId.ASSERT,
            )
        )
    assert calls == list(StageId)[: (5 if mode.startswith("mention-") else 3)]
