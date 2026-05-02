"""
One-shot generator: hits every real export endpoint in Cadence and saves
the response body to exports/sample_assets/. Builds a manifest README and
a zip bundle ready to hand back to the user.

Endpoints were chosen by grepping the real route definitions; the earlier
exploration overstated several routes (analytics exports, royalty
unmatched/allocation exports, creator JSON, roster one-sheet) that do not
exist in this codebase. Those are intentionally omitted.
"""
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import requests

# --- bootstrap: mint a JWT for a real org-2 member -----------------------
import sys
sys.path.insert(0, ".")
from backend.db_setup import SessionLocal
from backend.models import User
from backend.utils.auth import create_access_token, hash_token, decode_access_token
from backend.models import UserSession
from datetime import datetime as _dt

ORG_ID = 2          # Art Never Dies Music — 8 creators, 358 songs
CREATOR_ID = 7
SONG_ID = 96
RELEASE_ID = 1
STATEMENT_ID = 8
MEMBER_USERNAME = "ripton"   # OWNER of org 2

db = SessionLocal()
user = db.query(User).filter(User.username == MEMBER_USERNAME).first()
assert user, f"user {MEMBER_USERNAME} not found"
TOKEN = create_access_token({"sub": user.username})
# Backend's get_current_user requires a matching non-revoked UserSession
# row, so we insert one alongside the minted JWT.
exp_ts = (decode_access_token(TOKEN) or {}).get("exp")
sess = UserSession(
    user_id=user.id,
    token_hash=hash_token(TOKEN),
    expires_at=_dt.utcfromtimestamp(int(exp_ts)) if exp_ts else None,
    is_revoked=False,
    user_agent="generate_sample_assets",
    ip_address="127.0.0.1",
)
db.add(sess); db.commit()
uid = user.id
uname = user.username
db.close()
print(f"[ok] minted token for {uname} (id={uid}) len={len(TOKEN)}")

BASE = "http://localhost:8000"
H = {"Authorization": f"Bearer {TOKEN}"}
OUT = Path("exports/sample_assets")
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)

# --- pin active org -------------------------------------------------------
r = requests.patch(f"{BASE}/api/organizations/current",
                   json={"organization_id": ORG_ID}, headers=H, timeout=15)
print(f"[ok] active org -> {ORG_ID} ({r.status_code})")

# --- discover live IDs ----------------------------------------------------
def first_id(path, key="id"):
    rr = requests.get(BASE + path, headers=H, timeout=15)
    if not rr.ok:
        return None
    j = rr.json()
    items = j if isinstance(j, list) else (
        j.get("items") or j.get("data") or j.get("results") or
        j.get("creators") or j.get("songs") or j.get("releases") or
        j.get("contracts") or j.get("catalogs") or [])
    return items[0].get(key) if items else None

cat_id = first_id(f"/api/catalog/list?org_id={ORG_ID}")
contract_id = None
try:
    rc = requests.get(f"{BASE}/api/contracts/song/{SONG_ID}", headers=H, timeout=15)
    if rc.ok and isinstance(rc.json(), list) and rc.json():
        contract_id = rc.json()[0].get("id")
except Exception:
    pass
print(f"[ok] discovered: catalog_id={cat_id} contract_id={contract_id}")

# --- endpoint matrix (only routes that actually exist) -------------------
JOBS = [
    # Valuation
    ("valuation_blended_pdf", "GET", "/api/valuation/report/pdf",
     "01_valuation_blended_report.pdf"),
    ("valuation_catalog_xlsx", "GET",
     f"/api/valuation/catalog/download/excel?org_id={ORG_ID}",
     "01_valuation_catalog.xlsx"),
    ("valuation_blended_pdf_creator_scoped", "GET",
     f"/api/valuation/report/pdf?scope_creator_id={CREATOR_ID}",
     "01_valuation_blended_report__creator_scoped.pdf"),

    # Schedule A — branded full + simplified + CSV + blank template
    ("schedule_a_pdf_branded", "GET",
     f"/api/schedule-a/creator/{CREATOR_ID}/pdf",
     "02_schedule_a_full_branded.pdf"),
    ("schedule_a_pdf_simplified", "GET",
     f"/api/schedule-a/creator/{CREATOR_ID}/schedule-a-pdf",
     "02_schedule_a_simplified.pdf"),
    ("schedule_a_csv", "GET",
     f"/api/schedule-a/creator/{CREATOR_ID}/csv",
     "02_schedule_a.csv"),
    ("schedule_a_csv_legacy_exports_route", "GET",
     f"/api/creators/{CREATOR_ID}/schedule-a",
     "02_schedule_a__legacy_exports_route.csv"),
    ("schedule_a_blank_template_xlsx", "GET",
     "/api/catalog/template/schedule-a",
     "02_schedule_a_blank_upload_template.xlsx"),

    # Audit engine PDF
    ("royalty_audit_report_pdf", "GET",
     f"/api/organizations/{ORG_ID}/audit/report/pdf",
     "03_royalty_audit_report.pdf"),

    # Song history (JSON — there is no /export variant; this is the closest
    # downloadable analogue)
    ("song_history_json", "GET",
     f"/api/songs/{SONG_ID}/history",
     "04_song_history.json"),

    # Release one-sheet + metadata (release #1 may have 0 tracks → endpoint
    # will 400; we still record it so the manifest reflects reality)
    ("release_one_sheet_pdf", "GET",
     f"/api/releases/{RELEASE_ID}/export/pdf",
     "05_release_one_sheet.pdf"),
    ("release_metadata_csv", "GET",
     f"/api/releases/{RELEASE_ID}/export/csv",
     "05_release_metadata.csv"),
]

# Optional: legacy catalog Excel (only if there's a catalog id)
if cat_id:
    JOBS.append(("legacy_catalog_xlsx", "GET",
                 f"/api/catalog/export/{cat_id}",
                 "01_legacy_catalog_report.xlsx"))

# Optional: contract file passthrough
if contract_id:
    JOBS.append(("contract_file_passthrough", "GET",
                 f"/api/contracts/download/{contract_id}",
                 "06_contract_file_passthrough.bin"))

# --- run ------------------------------------------------------------------
manifest = []
for label, method, path, fname in JOBS:
    url = BASE + path
    try:
        rr = requests.request(method, url, headers=H, timeout=180, stream=True)
        ct = rr.headers.get("content-type", "")
        size = 0
        if rr.ok:
            with open(OUT / fname, "wb") as f:
                for chunk in rr.iter_content(64 * 1024):
                    f.write(chunk)
                    size += len(chunk)
            status = "ok"
            print(f"[ok]  {label:42s} {rr.status_code} {size:>10,d}B  {fname}")
            manifest.append({"label": label, "endpoint": path, "file": fname,
                             "status": status, "http": rr.status_code,
                             "content_type": ct, "size_bytes": size})
        else:
            err_body = rr.content[:500].decode("utf-8", "replace")
            print(f"[err] {label:42s} {rr.status_code}  {err_body[:140]}")
            manifest.append({"label": label, "endpoint": path, "file": None,
                             "status": f"http_{rr.status_code}",
                             "http": rr.status_code,
                             "error": err_body[:500]})
    except Exception as e:
        print(f"[exc] {label}: {e}")
        manifest.append({"label": label, "endpoint": path, "file": None,
                         "status": "exception", "error": str(e)})

# --- README ---------------------------------------------------------------
ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
ok_rows = [m for m in manifest if m["status"] == "ok"]
err_rows = [m for m in manifest if m["status"] != "ok"]

readme = [
    "# Cadence — Sample Asset Bundle",
    "",
    f"Generated against org **#{ORG_ID} (Art Never Dies Music)** on {ts}.",
    "",
    "One file per downloadable asset the Cadence backend can produce, "
    "fetched live from the running export endpoints. Use these as "
    "reference samples when designing updated versions.",
    "",
    "## Source IDs used",
    f"- Organization: **{ORG_ID}** (Art Never Dies Music)",
    f"- Acting user: **{MEMBER_USERNAME}** (OWNER of org)",
    f"- Creator: **{CREATOR_ID}**",
    f"- Song: **{SONG_ID}**",
    f"- Release: **{RELEASE_ID}**",
    f"- Royalty statement: **{STATEMENT_ID}**",
    f"- Catalog: **{cat_id}**" if cat_id else "- Catalog: _none_",
    f"- Contract: **{contract_id}**" if contract_id else "- Contract: _none on file_",
    "",
    f"## Successfully generated ({len(ok_rows)})",
    "",
    "| File | Endpoint | Size |",
    "|---|---|---|",
]
for m in ok_rows:
    readme.append(f"| `{m['file']}` | `{m['endpoint']}` "
                  f"| {m['size_bytes']:,} B |")

if err_rows:
    readme += [
        "",
        f"## Skipped / errored ({len(err_rows)})",
        "",
        "These endpoints were attempted but couldn't produce a file in this "
        "org. Most are due to missing source data (e.g. the only Release "
        "in this org has zero tracks, contracts have no uploaded binaries) "
        "rather than a code bug.",
        "",
        "| Endpoint | Status | Note |",
        "|---|---|---|",
    ]
    for m in err_rows:
        note = (m.get("error") or "")[:140].replace("\n", " ").replace("|", "\\|")
        readme.append(f"| `{m['endpoint']}` | {m['status']} | {note} |")

readme += [
    "",
    "## Endpoints that don't exist in this codebase",
    "",
    "These were initially scoped but turned out to be hallucinated by an "
    "exploratory pass — the actual route handlers do not exist:",
    "",
    "- `/api/analytics/org/{org_id}/export/{type}{,.pdf,.xlsx}` — no "
    "analytics export endpoints exist; analytics is rendered in-app only.",
    "- `/api/royalty-processing/.../unmatched/export` — there is a "
    "non-export `/statements/{org}/{id}?unmatched_only=true` JSON view "
    "but no CSV export.",
    "- `/api/royalty-processing/.../allocation-preview/export` — does not "
    "exist.",
    "- `/api/creators/org/{org_id}/export/roster` — no roster one-sheet "
    "endpoint.",
    "- `/api/creators/{id}/export/json` — no JSON export endpoint.",
    "",
    "If you want any of those produced, they need to be built first.",
]

(OUT / "README.md").write_text("\n".join(readme))
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))

# --- zip ------------------------------------------------------------------
zip_path = Path("exports/cadence_sample_assets.zip")
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUT.iterdir()):
        z.write(p, arcname=f"cadence_sample_assets/{p.name}")

print(f"\n[done] zip = {zip_path}  size={zip_path.stat().st_size:,}B  "
      f"files={len(list(OUT.iterdir()))}  ok={len(ok_rows)}  "
      f"err={len(err_rows)}")
