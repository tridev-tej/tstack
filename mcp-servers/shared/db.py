"""Read-only PostgreSQL database connection with tenant isolation.

CRITICAL: This module ONLY allows SELECT queries.
All write operations (INSERT, UPDATE, DELETE, etc.) are strictly forbidden.
"""

import os
import re
from contextlib import contextmanager
from typing import Any, Generator

import psycopg2
from psycopg2.extras import RealDictCursor

FORBIDDEN_KEYWORDS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "TRUNCATE",
    "ALTER",
    "CREATE",
    "GRANT",
    "REVOKE",
    "COPY",
    "LOCK",
    "VACUUM",
    "ANALYZE",
    "REINDEX",
    "CLUSTER",
    "REFRESH",
    "COMMENT",
    "SECURITY",
    "OWNER",
]


def validate_read_only(query: str) -> bool:
    """Validate query is read-only SELECT statement.

    Raises ValueError if query contains forbidden operations.
    """
    normalized = " ".join(query.split()).upper()

    if not normalized.startswith("SELECT") and not normalized.startswith("WITH"):
        raise ValueError("Only SELECT queries allowed")

    for keyword in FORBIDDEN_KEYWORDS:
        pattern = rf"\b{keyword}\b"
        if re.search(pattern, normalized):
            raise ValueError(f"Forbidden keyword: {keyword}")

    return True


def get_connection_params() -> dict:
    """Get database connection parameters from environment."""
    return {
        "host": os.environ.get("SOC_DB_HOST", "localhost"),
        "port": int(os.environ.get("SOC_DB_PORT", "5432")),
        "dbname": os.environ.get("SOC_DB_NAME", "soc"),
        "user": os.environ.get("SOC_DB_USER", "soc_readonly"),
        "password": os.environ.get("SOC_DB_PASSWORD", ""),
        "options": "-c default_transaction_read_only=on",
        "connect_timeout": 10,
    }


@contextmanager
def get_connection(tenant: str) -> Generator[psycopg2.extensions.connection, None, None]:
    """Get database connection with tenant schema set.

    Args:
        tenant: Tenant name (schema name directly)

    Yields:
        Database connection with search_path set to tenant schema
    """
    if not tenant:
        raise ValueError("Tenant parameter is required")

    schema = tenant
    conn = psycopg2.connect(**get_connection_params())

    try:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO %s, public", (schema,))
        yield conn
    finally:
        conn.close()


def execute_query(
    tenant: str,
    query: str,
    params: tuple | dict | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Execute a read-only SELECT query.

    Args:
        tenant: Tenant name (required)
        query: SQL SELECT query
        params: Query parameters
        limit: Optional result limit

    Returns:
        List of row dictionaries

    Raises:
        ValueError: If query is not read-only
    """
    validate_read_only(query)

    if limit and "LIMIT" not in query.upper():
        query = f"{query.rstrip().rstrip(';')} LIMIT {int(limit)}"

    with get_connection(tenant) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]


def execute_public_query(
    query: str,
    params: tuple | dict | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Execute a read-only SELECT query on public schema.

    For queries that don't need tenant context (e.g., listing tenants).
    """
    validate_read_only(query)

    if limit and "LIMIT" not in query.upper():
        query = f"{query.rstrip().rstrip(';')} LIMIT {int(limit)}"

    params_dict = get_connection_params()
    conn = psycopg2.connect(**params_dict)

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SET search_path TO public")
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_tenant_list() -> list[str]:
    """Get list of available tenants."""
    query = """
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT LIKE 'pg_%'
          AND schema_name NOT IN ('information_schema', 'public')
        ORDER BY schema_name
    """
    rows = execute_public_query(query)
    return [row["schema_name"] for row in rows]
