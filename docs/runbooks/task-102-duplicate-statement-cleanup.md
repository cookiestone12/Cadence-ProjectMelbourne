# Runbook: Task #102 — Run duplicate-statement cleanup against production

**Status:** Handed off to operator (master-admin). The script is merged and
tested in dev; the actual prod data fix must be performed by a human with
master-admin credentials in the production shell. Replit Agent cannot reach
prod data from the dev environment.

## Background

Task #98 added `backend/scripts/cleanup_duplicate_statements_98.py`, a
one-shot, dry-run-by-default cleanup for two known pre-guard duplicate
royalty statements that were uploaded before the dedupe guard from task #94
shipped:

| Duplicate | Original | Description                       | Amount      |
|-----------|----------|-----------------------------------|-------------|
| #17       | #18      | BMI Jan–Jun 2024                  | $18,622.98  |
| #11       | #15      | Marri BMI 2026                    | $48.30      |
| **Total** |          |                                   | **$18,671.28** |

The script reuses the same `_perform_statement_delete` cascade used by the
user-facing delete button (lines, ledger entries, action items,
transactions/allocations, advance-balance restore, payout unwind, audit log,
file-on-disk cleanup) and writes audit-log rows automatically.

Safety properties:
- Defaults to dry-run; `--apply` is required to write.
- Idempotent: missing targets are logged as "skipped" and not retried.
- Verifies `organization_id` and `total_revenue_cents` of duplicate vs.
  original before deleting; mismatched targets are skipped.

## Operator steps (run in the prod shell)

1. SSH / open a shell on the prod backend with master-admin access.
2. Identify the master-admin user id you will run as (`<master_admin_id>`).
3. **Dry run first.** Capture stdout to the change-record:
   ```
   python -m backend.scripts.cleanup_duplicate_statements_98 \
       --as-user-id <master_admin_id>
   ```
4. Visually confirm the printed plan names exactly:
   - Statement **#17** → duplicate of #18, BMI Jan–Jun 2024, **$18,622.98**
   - Statement **#11** → duplicate of #15, Marri BMI 2026, **$48.30**
   - Both rows show the same `organization_id` as their original.
   - **If anything else is printed, STOP** and escalate. Do not pass `--apply`.
5. **Apply.** Capture stdout to the change-record:
   ```
   python -m backend.scripts.cleanup_duplicate_statements_98 \
       --as-user-id <master_admin_id> --apply
   ```
6. Verify in the prod UI:
   - Royalties page total has dropped by **exactly $18,671.28**.
   - Reconciliation report shows **zero `DUPLICATE_FILE` flags** for the
     affected org.
   - Tenant Admin → Audit Log shows **two new DELETE/STATEMENT rows**
     attributed to `<master_admin_id>`.
7. Save both transcripts (dry-run + apply) to the ticket / change-record /
   as a comment on task #102.

## Rollback

There is no in-place undo (the cascade is destructive). If the apply step
deleted the wrong rows, restore from the most recent prod DB backup taken
before the run. Take a fresh backup *before* step 5 if the change window
allows it.

## Why this isn't auto-runnable from dev

The dev environment has no network path to the prod database, no
master-admin session, and no access to the prod audit-log UI for
verification. This is intentional — destructive prod data fixes go through
a human operator.

## References

- Script: `backend/scripts/cleanup_duplicate_statements_98.py`
- Tests:  `backend/tests/test_cleanup_duplicate_statements_98.py`
- Reconciliation endpoint: `backend/routes/royalty_processing.py`
- Originating tasks: #94 (dedupe guard), #98 (script), #102 (this run)
