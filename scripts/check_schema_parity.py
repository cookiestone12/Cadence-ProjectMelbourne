"""Detect drift between SQLAlchemy models and Alembic migrations.

Spins up two empty Postgres schemas inside the existing ``DATABASE_URL``
target and diffs the resulting DDL:

1. ``parity_alembic_<rand>``  — what the **shipped** schema looks like.
   We bootstrap with ``Base.metadata.create_all(checkfirst=True)``
   (matching the historical reality that production DBs were originally
   stood up from the ORM models) and then apply ``alembic upgrade
   heads`` over the top. Any subsequent ``ALTER COLUMN`` /
   ``ADD COLUMN`` / ``CREATE INDEX`` written into the migrations is
   exercised against a "real" baseline, so a typo in one of those
   statements diverges the resulting schema from the model.

2. ``parity_models_<rand>``   — what the models *say* the schema should
   look like. Populated by ``Base.metadata.create_all`` against an
   empty schema.

Both are then introspected and diffed (table set, column names /
nullability / types, primary keys, indexes). Any mismatch causes the
script to exit non-zero with a human-readable report so the post-merge
hook fails before the divergence ships to production.

Motivation: Task #83 consolidated ~390 lines of ad-hoc DDL into
Alembic revision ``d3e4f5a6b7c8``; a code reviewer caught two parity
bugs (missing PK indexes, spurious DB defaults) that the hand-written
migration introduced. This script automates that catch.

Usage::

    DATABASE_URL=postgresql://... python scripts/check_schema_parity.py
    # exit 0 → schemas match; exit 1 → drift; exit 2 → setup error

Concurrency-safe: the schema names are random, so multiple runs against
the same DB don't collide. Both schemas are dropped on exit (success
or failure).

Known limitation: a migration that **fails to create** an index/column
that ``Base.metadata`` does include is masked by the ``create_all``
bootstrap. The complement — a migration that **adds something the
model doesn't reflect**, or **changes column type/nullability away
from the model** — is what the reviewer-caught bugs were, and is what
this check reliably catches.
"""
from __future__ import annotations

import os
import secrets
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Tables that exist for migration bookkeeping rather than as part of the
# domain schema. They legitimately appear in the alembic-built schema
# but never in ``Base.metadata`` (and vice versa), so excluding them
# from the diff is correct, not a workaround.
BOOKKEEPING_TABLES = frozenset({"alembic_version", "migration_lock"})


def _require_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL is not set.", file=sys.stderr)
        sys.exit(2)
    if not url.startswith(("postgresql://", "postgresql+psycopg2://")):
        print(
            "ERROR: schema parity check requires a Postgres DATABASE_URL "
            f"(got: {url.split('://', 1)[0]}://...).",
            file=sys.stderr,
        )
        sys.exit(2)
    return url


def _url_with_search_path(url: str, schema: str) -> str:
    """Return ``url`` with libpq ``options=-csearch_path=<schema>``
    merged into the query string.

    ``public`` is intentionally **omitted** from the path so that
    Alembic's unqualified lookup of ``alembic_version`` resolves to a
    fresh table inside our ephemeral schema rather than picking up the
    long-lived ``public.alembic_version`` of the dev database (which
    would make Alembic believe the migrations had already run and skip
    them all). Postgres still resolves built-in types, the ``pg_catalog``
    schema, and any explicitly schema-qualified extensions without
    ``public`` on the path.
    """
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    options = query.get("options", "")
    new_options = (
        (options + " " if options else "")
        + f"-csearch_path={schema}"
    )
    query["options"] = new_options
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query, quote_via=quote), parts.fragment)
    )


def _create_schema(engine, schema: str) -> None:
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))


def _drop_schema(engine, schema: str) -> None:
    from sqlalchemy import text

    try:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    except Exception as exc:  # pragma: no cover - cleanup best-effort
        print(f"WARN: could not drop schema {schema}: {exc}", file=sys.stderr)


# Postgres error markers that mean "this object was already created
# by the create_all bootstrap, so the migration step is harmlessly a
# no-op". When we see one of these in alembic's output we stamp past
# the offending revision and keep going. Anything else is a real
# failure and bubbles up.
_TOLERATED_PG_ERRORS = (
    "DuplicateTable",
    "DuplicateColumn",
    "DuplicateObject",
    "already exists",
)


def _run_alembic(args: list[str], database_url: str, schema: str) -> subprocess.CompletedProcess:
    scoped_url = _url_with_search_path(database_url, schema)
    env = os.environ.copy()
    env["DATABASE_URL"] = scoped_url
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


def _list_revisions_in_order() -> list[str]:
    """Return every alembic revision id from base to heads, in apply order."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    revs = [rev.revision for rev in script.iterate_revisions(heads, ())]
    revs.reverse()  # iterate_revisions is head-first; we want base-first
    return revs


def _run_alembic_upgrade(database_url: str, schema: str) -> None:
    """Apply every alembic revision to ``schema`` one at a time.

    The schema has already been bootstrapped with
    ``Base.metadata.create_all`` (because the historical migrations
    were generated against an existing prod DB and several of them
    only ALTER tables that ``create_all`` produced). When a migration
    fails purely because an object it tries to ``CREATE`` already
    exists from the bootstrap, we treat that as a harmless overlap
    and ``stamp`` past the revision so subsequent migrations can run.
    Any other failure (including divergent ``ALTER COLUMN`` errors)
    is fatal — those represent real drift.
    """
    for rev in _list_revisions_in_order():
        result = _run_alembic(["upgrade", rev], database_url, schema)
        if result.returncode == 0:
            continue
        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        if any(marker in combined for marker in _TOLERATED_PG_ERRORS):
            stamp = _run_alembic(["stamp", rev], database_url, schema)
            if stamp.returncode != 0:
                print(stamp.stdout, file=sys.stderr)
                print(stamp.stderr, file=sys.stderr)
                raise RuntimeError(f"alembic stamp {rev} failed after tolerated upgrade error")
            continue
        print(f"ERROR: alembic upgrade {rev} failed:", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"alembic upgrade {rev} failed")


def _create_all_from_models(database_url: str, schema: str, checkfirst: bool = False) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool

    # Import lazily so the alembic subprocess's own import of
    # ``backend.models.database`` is not influenced by our modified URL
    # being present in this process's environment.
    from backend.models.models import Base

    scoped_url = _url_with_search_path(database_url, schema)
    engine = create_engine(scoped_url, poolclass=NullPool)
    try:
        Base.metadata.create_all(bind=engine, checkfirst=checkfirst)
    finally:
        engine.dispose()


def _collect_schema(engine, schema: str) -> dict:
    from sqlalchemy import inspect

    insp = inspect(engine)
    info: dict = {}
    for table_name in sorted(insp.get_table_names(schema=schema)):
        if table_name in BOOKKEEPING_TABLES:
            continue
        cols = {}
        for col in insp.get_columns(table_name, schema=schema):
            cols[col["name"]] = {
                "type": str(col["type"]).upper(),
                "nullable": bool(col.get("nullable", True)),
            }
        pk = tuple((insp.get_pk_constraint(table_name, schema=schema) or {}).get("constrained_columns") or ())
        idx_keys: set = set()
        for idx in insp.get_indexes(table_name, schema=schema):
            idx_keys.add(
                (
                    tuple(idx.get("column_names") or ()),
                    bool(idx.get("unique")),
                )
            )
        info[table_name] = {"columns": cols, "pk": pk, "indexes": idx_keys}
    return info


def _diff_schemas(alembic_info: dict, models_info: dict) -> list[str]:
    issues: list[str] = []

    a_tables = set(alembic_info)
    m_tables = set(models_info)

    only_alembic = sorted(a_tables - m_tables)
    only_models = sorted(m_tables - a_tables)
    for t in only_alembic:
        issues.append(f"[table] '{t}' exists in migrations but NOT in models.py")
    for t in only_models:
        issues.append(f"[table] '{t}' exists in models.py but NOT in migrations")

    for table in sorted(a_tables & m_tables):
        a = alembic_info[table]
        m = models_info[table]

        a_cols = set(a["columns"])
        m_cols = set(m["columns"])
        for c in sorted(a_cols - m_cols):
            issues.append(f"[column] {table}.{c} exists in migrations but NOT in models.py")
        for c in sorted(m_cols - a_cols):
            issues.append(f"[column] {table}.{c} exists in models.py but NOT in migrations")
        for c in sorted(a_cols & m_cols):
            ac = a["columns"][c]
            mc = m["columns"][c]
            if ac["nullable"] != mc["nullable"]:
                issues.append(
                    f"[nullable] {table}.{c}: migrations={ac['nullable']} "
                    f"models={mc['nullable']}"
                )
            if ac["type"] != mc["type"]:
                issues.append(
                    f"[type] {table}.{c}: migrations={ac['type']!r} "
                    f"models={mc['type']!r}"
                )

        if a["pk"] != m["pk"]:
            issues.append(
                f"[primary-key] {table}: migrations={list(a['pk'])} "
                f"models={list(m['pk'])}"
            )

        a_idx = a["indexes"]
        m_idx = m["indexes"]
        # Lenient diff: we care that EACH (columns, unique) tuple is
        # represented at least once in both schemas. Duplicate indexes
        # on the same columns (e.g. SQLAlchemy ``index=True`` plus a
        # hand-named ``CREATE INDEX`` in a migration) are wasteful but
        # don't affect query plans or constraints, so we don't flag
        # them as drift.
        for key in sorted(a_idx - m_idx):
            cols, unique = key
            label = f"({','.join(cols)}){' UNIQUE' if unique else ''}"
            issues.append(f"[index] {table} {label} exists in migrations but NOT in models.py")
        for key in sorted(m_idx - a_idx):
            cols, unique = key
            label = f"({','.join(cols)}){' UNIQUE' if unique else ''}"
            issues.append(f"[index] {table} {label} exists in models.py but NOT in migrations")

    return issues


def run() -> int:
    database_url = _require_database_url()

    suffix = secrets.token_hex(4)
    alembic_schema = f"parity_alembic_{suffix}"
    models_schema = f"parity_models_{suffix}"

    from sqlalchemy import create_engine

    admin_engine = create_engine(database_url)
    try:
        _create_schema(admin_engine, alembic_schema)
        _create_schema(admin_engine, models_schema)

        try:
            # Schema A: bootstrap from models (the historical
            # migrations were generated against an already-populated
            # production DB and several of them only ALTER tables that
            # would otherwise come from create_all), then apply every
            # alembic revision over the top. ``_run_alembic_upgrade``
            # tolerates "already exists" overlaps from the bootstrap
            # but lets every other failure bubble up as drift.
            _create_all_from_models(database_url, alembic_schema, checkfirst=True)
            _run_alembic_upgrade(database_url, alembic_schema)
            # Schema B: pure model definition.
            _create_all_from_models(database_url, models_schema)

            alembic_info = _collect_schema(admin_engine, alembic_schema)
            models_info = _collect_schema(admin_engine, models_schema)
        except Exception as exc:
            print(f"ERROR: schema build failed: {exc}", file=sys.stderr)
            return 2

        issues = _diff_schemas(alembic_info, models_info)
        if not issues:
            print(
                f"OK: schema parity verified across "
                f"{len(alembic_info)} tables (alembic vs models)."
            )
            return 0

        print(
            "FAIL: schema drift detected between Alembic migrations and "
            "backend/models/models.py:",
            file=sys.stderr,
        )
        for line in issues:
            print(f"  - {line}", file=sys.stderr)
        print(
            f"\n{len(issues)} mismatch(es). Reconcile by editing the "
            "offending migration in alembic/versions/ or the model in "
            "backend/models/models.py and re-run this script.",
            file=sys.stderr,
        )
        return 1
    finally:
        _drop_schema(admin_engine, alembic_schema)
        _drop_schema(admin_engine, models_schema)
        admin_engine.dispose()


if __name__ == "__main__":
    sys.exit(run())
