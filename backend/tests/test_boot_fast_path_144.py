"""Task #144 — Boot critical path must stay fast.

Pins the contract that importing `backend.main` only runs the FAST
health-recompute path (`bulk_recompute_health_scores`) and NEVER touches
the slow per-song `sync_stale_health_scores` at module import time.

Background: at production scale (~1,512 songs) the per-song sync took
60+ seconds, exceeding Replit VM's 60-second port-bind timeout and
preventing gunicorn from ever opening port 5000. The slow sync now runs
in `_deferred_startup_tasks()` AFTER the worker is already serving
traffic. This test prevents a future regression where someone adds the
slow sync back to the boot path.
"""
import importlib
import sys
from unittest.mock import patch


def test_module_level_health_recompute_uses_only_fast_path():
    """When `_module_level_health_recompute` runs, it MUST call only
    `seed_checklist_items` + `bulk_recompute_health_scores`. It MUST NOT
    call `sync_stale_health_scores` (which iterates every song with
    per-song commits and blocks the boot port-bind window)."""
    # Drop any cached import so the module-level code re-runs under our patches.
    for mod in ["backend.main", "backend.db_setup"]:
        sys.modules.pop(mod, None)

    with patch("backend.db_setup.bulk_recompute_health_scores") as fast, \
         patch("backend.db_setup.sync_stale_health_scores") as slow, \
         patch("backend.db_setup.seed_checklist_items") as seed:
        importlib.import_module("backend.main")

        assert fast.called, (
            "Boot path must call bulk_recompute_health_scores (fast SQL "
            "path). Without it, production health scores stay stuck at 0."
        )
        assert seed.called, (
            "Boot path must call seed_checklist_items so checklist weights "
            "are correct before the bulk recompute reads them."
        )
        assert not slow.called, (
            "Boot path must NOT call sync_stale_health_scores — it iterates "
            "~1500 songs with per-song commits and at production scale takes "
            "60+ seconds, which exceeds Replit VM's 60-second port-bind "
            "timeout and makes the deploy fail with 'a port configuration "
            "was specified but the required port was never opened'. The "
            "slow per-song sync runs in _deferred_startup_tasks() instead."
        )


def test_bulk_recompute_function_exists_and_is_separate():
    """`bulk_recompute_health_scores` must exist as its own top-level
    function in `backend.db_setup`, distinct from `sync_stale_health_scores`.
    A future refactor that collapses them back together would re-introduce
    the boot-timeout regression."""
    from backend import db_setup

    assert hasattr(db_setup, "bulk_recompute_health_scores"), (
        "bulk_recompute_health_scores must exist as a top-level function "
        "so the boot path can call it without dragging in the slow per-song "
        "loop."
    )
    assert hasattr(db_setup, "sync_stale_health_scores"), (
        "sync_stale_health_scores must still exist for db_setup.main() "
        "(used by local run_backend.sh) and the deferred startup path."
    )
    assert (
        db_setup.bulk_recompute_health_scores
        is not db_setup.sync_stale_health_scores
    ), "The two functions must remain distinct."
