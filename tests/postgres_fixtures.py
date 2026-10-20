"""Isolated schemas on an explicitly selected disposable Postgres server."""

import os
from collections.abc import Iterator
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo


@pytest.fixture
def archive_dsn() -> Iterator[str]:
    dsn = os.environ.get("PIL_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("explicit disposable Postgres opt-in required")
    schema = "pil_test_" + uuid4().hex
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    try:
        yield make_conninfo(dsn, options=f"-c search_path={schema}")
    finally:
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
