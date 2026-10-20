"""Shared source-stage receipt identities, independent of application composition."""

from procurement_intelligence_lab.platform.semantics.identity import stable_id


def normalization_batch_id(
    mapped_document_id: str,
    observation_ids: tuple[str, ...],
    provenance_id: str,
    policy_reference: str,
) -> str:
    return stable_id(
        "normalization-batch",
        mapped_document_id,
        observation_ids,
        provenance_id,
        policy_reference,
    )


def assertion_batch_id(
    origin_id: str,
    assertion_ids: tuple[str, ...],
    mention_ids: tuple[str, ...],
    provenance_id: str,
) -> str:
    return stable_id(
        "source-assertion-batch-v1", origin_id, assertion_ids, mention_ids, provenance_id
    )
