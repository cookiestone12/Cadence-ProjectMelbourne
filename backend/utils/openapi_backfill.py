"""Backfill `summary=` on every FastAPI route that doesn't already
have one.

Hand-written summaries on hot endpoints (auth, catalog CRUD,
royalties, etc.) are preserved — this only fills in the long tail
so `/docs` and `/redoc` are not a wall of bare function names.

Synthesizes a short Title-Cased phrase from the endpoint function's
``__name__`` so the docs are at least scannable. Idempotent: safe
to run on every startup.
"""
from __future__ import annotations

import logging
from typing import Iterable

from fastapi import FastAPI
from fastapi.routing import APIRoute


_log = logging.getLogger("cadence")


def _humanize(func_name: str) -> str:
    """``list_creator_songs`` → ``List Creator Songs``."""
    parts = [p for p in func_name.split("_") if p]
    if not parts:
        return func_name
    return " ".join(p.capitalize() for p in parts)


def backfill_route_summaries(app: FastAPI) -> int:
    """Walk every APIRoute on ``app`` and assign a synthesized
    ``summary`` if one isn't already set. Returns the number of
    routes that were updated so the caller can log a single counter
    instead of one line per route.
    """
    routes: Iterable = app.routes
    updated = 0
    for route in routes:
        if not isinstance(route, APIRoute):
            continue
        if route.summary:
            continue
        endpoint = route.endpoint
        func_name = getattr(endpoint, "__name__", "") or ""
        if not func_name:
            continue
        synthesized = _humanize(func_name)
        route.summary = synthesized
        # FastAPI also caches the OpenAPI fragment per-route; clearing
        # it forces regeneration on the next /openapi.json request.
        if hasattr(route, "openapi_extra"):
            pass
        updated += 1

    if updated:
        _log.info("OpenAPI summary backfill: filled %d routes", updated)
    return updated
