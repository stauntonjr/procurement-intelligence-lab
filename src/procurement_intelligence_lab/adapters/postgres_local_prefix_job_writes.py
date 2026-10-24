"""Transaction-scoped journal mechanics. Caller owns all locks and commit."""

from hashlib import sha256
from typing import Any

import psycopg

from procurement_intelligence_lab.adapters.semantic_codec import SemanticCodec
from procurement_intelligence_lab.platform.execution.identity import canonical
from procurement_intelligence_lab.platform.processing.contracts import (
    JobDefinition,
    JobStatus,
    JobTransition,
)


def write_definition(
    conn: psycopg.Connection[dict[str, Any]], codec: SemanticCodec, job: JobDefinition
) -> None:
    scope = canonical(job.scope).decode()
    arrival = codec.dumps(job.arrival)
    conn.execute(
        "INSERT INTO pil_local_prefix_job_arrivals(scope,event_id,payload,payload_sha256) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
        (scope, job.arrival.event_id, arrival, sha256(arrival.encode()).hexdigest()),
    )
    payload = codec.dumps(job)
    conn.execute(
        "INSERT INTO pil_local_prefix_jobs(scope,job_id,request_digest,payload,payload_sha256) VALUES (%s,%s,%s,%s,%s)",
        (scope, job.job_id, job.request_digest, payload, sha256(payload.encode()).hexdigest()),
    )


def append_transition(
    conn: psycopg.Connection[dict[str, Any]], codec: SemanticCodec, transition: JobTransition
) -> None:
    t = transition
    scope = canonical(t.scope).decode()
    payload = codec.dumps(t)
    conn.execute(
        "INSERT INTO pil_local_prefix_job_transitions(scope,job_id,sequence,record_id,payload,payload_sha256) VALUES (%s,%s,%s,%s,%s,%s)",
        (scope, t.job_id, t.sequence, t.record_id, payload, sha256(payload.encode()).hexdigest()),
    )
    if t.command is not None:
        conn.execute(
            "INSERT INTO pil_local_prefix_job_commands(scope,job_id,family,command_key,sequence) VALUES (%s,%s,%s,%s,%s)",
            (scope, t.job_id, t.command.family, t.command.command_key, t.sequence),
        )
    token = t.attempt
    conn.execute(
        "INSERT INTO pil_local_prefix_job_heads(scope,job_id,sequence,version,status,attempt_id,fence,recorded_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(scope,job_id) DO UPDATE SET sequence=EXCLUDED.sequence,version=EXCLUDED.version,status=EXCLUDED.status,attempt_id=EXCLUDED.attempt_id,fence=EXCLUDED.fence,recorded_at=EXCLUDED.recorded_at",
        (
            scope,
            t.job_id,
            t.sequence,
            t.version,
            t.status.value,
            token.attempt_id if token else None,
            (token.fence + (1 if t.status is JobStatus.ABANDONED else 0)) if token else 0,
            t.recorded_at.isoformat(),
        ),
    )
