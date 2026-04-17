import logging
import hashlib
import re
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from difflib import SequenceMatcher

from ..models import (
    get_db, Song, Work, Release, Creator, Contract, ContractAsset, RightsSplit,
    RoyaltyStatement, RoyaltyTransaction,
    RoyaltyStatementLine, RoyaltyProcessingRun, RoyaltyLedgerEntry,
    Payee, AdvanceV2, PayoutBatch, PayoutItem, ActionItem,
)
from .classification_engine import classify_line

logger = logging.getLogger(__name__)


def ensure_payee_for_creator(db: Session, org_id: int, creator_id: int) -> Payee:
    payee = db.query(Payee).filter(
        Payee.org_id == org_id,
        Payee.creator_id == creator_id,
    ).first()
    if payee:
        return payee
    creator = db.query(Creator).filter(
        Creator.id == creator_id,
        Creator.organization_id == org_id,
    ).first()
    if not creator:
        raise ValueError(f"Creator {creator_id} not found in org {org_id}")
    payee = Payee(
        org_id=org_id,
        payee_type="CREATOR",
        creator_id=creator_id,
        company_name=None,
        contact_email=creator.email,
    )
    db.add(payee)
    db.flush()
    return payee


def compute_line_hash(line_data: dict) -> str:
    parts = [
        str(line_data.get("isrc") or "").strip().upper(),
        str(line_data.get("track_title") or "").strip().lower(),
        str(line_data.get("artist") or "").strip().lower(),
        str(line_data.get("revenue") or "").strip(),
        str(line_data.get("territory") or "").strip().lower(),
        str(line_data.get("store") or "").strip().lower(),
        str(line_data.get("revenue_type") or "").strip().lower(),
        str(line_data.get("source_detail") or "").strip().lower(),
        str(line_data.get("quantity") or "").strip(),
        str(line_data.get("gross_amount") or "").strip(),
        str(line_data.get("row_index") or "").strip(),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_statement_to_lines(
    db: Session,
    statement_id: int,
    org_id: int,
    column_mapping: dict,
    rows: list,
    pdf_metadata: dict = None,
) -> int:
    try:
        statement = db.query(RoyaltyStatement).filter(
            RoyaltyStatement.id == statement_id,
            RoyaltyStatement.organization_id == org_id,
        ).first()
        if not statement:
            raise ValueError(f"Statement {statement_id} not found for org {org_id}")

        isrc_col = column_mapping.get("isrc")
        upc_col = column_mapping.get("upc")
        iswc_col = column_mapping.get("iswc")
        title_col = column_mapping.get("track_title")
        artist_col = column_mapping.get("artist")
        rev_col = column_mapping.get("revenue")
        qty_col = column_mapping.get("quantity")
        territory_col = column_mapping.get("territory")
        platform_col = column_mapping.get("platform")
        rev_type_col = column_mapping.get("revenue_type")
        release_title_col = column_mapping.get("release_title")
        label_col = column_mapping.get("label")
        gross_col = column_mapping.get("gross_amount")
        currency_col = column_mapping.get("currency")

        def safe_get(row, col):
            if not col:
                return None
            val = row.get(col)
            if val is None:
                return None
            return str(val).strip() or None

        def clean_artist(val):
            """Return artist name only if it looks like a real name.

            Reject percentage strings (e.g. ``50.0%``), digit-only values,
            currency amounts, lone punctuation (``--``, ``—``), and any
            value with no alphabetic characters. Some parsers misalign
            columns and dump the writer/publisher share into the artist
            field; storing those would poison fuzzy matching.
            """
            if val is None:
                return None
            s = str(val).strip()
            if not s:
                return None
            if not re.search(r"[A-Za-z]", s):
                return None
            stripped = s.replace(",", "").replace("$", "").replace("%", "").strip()
            if stripped and re.fullmatch(r"-?\d+(?:\.\d+)?", stripped):
                return None
            return s

        def safe_float(row, col):
            if not col:
                return None
            val = row.get(col)
            if val is None:
                return None
            try:
                s = str(val).strip().replace(",", "").replace("$", "").replace("£", "").replace("€", "")
                if not s or s == "-":
                    return None
                if s.startswith("(") and s.endswith(")"):
                    s = "-" + s[1:-1]
                return float(s)
            except (ValueError, TypeError):
                return None

        count = 0
        existing_hashes = set(
            h[0] for h in db.query(RoyaltyStatementLine.line_hash).filter(
                RoyaltyStatementLine.org_id == org_id,
                RoyaltyStatementLine.statement_id == statement_id,
                RoyaltyStatementLine.line_hash.isnot(None),
            ).all()
        )

        total_revenue = 0.0
        for row_idx, row in enumerate(rows):
            artist_clean = clean_artist(safe_get(row, artist_col))
            hash_data = {
                "isrc": safe_get(row, isrc_col),
                "track_title": safe_get(row, title_col),
                "artist": artist_clean,
                "revenue": safe_get(row, rev_col),
                "territory": safe_get(row, territory_col),
                "store": safe_get(row, platform_col),
                "revenue_type": safe_get(row, rev_type_col),
                "source_detail": safe_get(row, release_title_col) or safe_get(row, label_col),
                "quantity": safe_get(row, qty_col),
                "gross_amount": safe_get(row, gross_col),
                "row_index": str(row_idx),
            }
            line_hash = compute_line_hash(hash_data)

            if line_hash in existing_hashes:
                continue

            net_amount = safe_float(row, rev_col) or 0.0
            gross_amount = safe_float(row, gross_col)
            unit_count_val = safe_float(row, qty_col)

            rev_type_val = safe_get(row, rev_type_col)
            territory_val = safe_get(row, territory_col)
            store_val = safe_get(row, platform_col)

            classification = classify_line(
                revenue_type=rev_type_val,
                usage_type=None,
                store=store_val,
                territory_raw=territory_val,
                net_amount=net_amount,
                gross_amount=gross_amount,
                deductions=None,
            )

            line = RoyaltyStatementLine(
                org_id=org_id,
                statement_id=statement_id,
                line_hash=line_hash,
                isrc=safe_get(row, isrc_col),
                upc=safe_get(row, upc_col),
                iswc=safe_get(row, iswc_col),
                track_title_raw=safe_get(row, title_col),
                artist_name_raw=artist_clean,
                release_title_raw=safe_get(row, release_title_col),
                label_raw=safe_get(row, label_col),
                territory=territory_val,
                store=store_val,
                revenue_type=rev_type_val,
                unit_count=unit_count_val,
                gross_amount=gross_amount,
                net_amount=net_amount,
                net_amount_statement_currency=net_amount,
                currency=safe_get(row, currency_col) or statement.currency,
                match_status="UNMATCHED",
                canonical_right_category=classification["canonical_right_category"],
                canonical_channel=classification["canonical_channel"],
                accounting_flags=classification["accounting_flags"],
                territory_iso2=classification["territory_iso2"],
                territory_confidence=classification["territory_confidence"],
                activity_period_start=statement.period_start,
                activity_period_end=statement.period_end,
            )
            db.add(line)
            existing_hashes.add(line_hash)
            total_revenue += net_amount
            count += 1

        statement.total_transactions = count
        grand_total_net = (pdf_metadata or {}).get("grand_total_net")
        if grand_total_net is not None:
            statement.total_revenue_cents = int(round(grand_total_net * 100))
            logger.info(f"Using PDF Grand Total: ${grand_total_net:.2f} (parsed sum: ${total_revenue:.2f})")
        else:
            statement.total_revenue_cents = int(round(total_revenue * 100))
        db.flush()
        logger.info(f"Parsed {count} lines for statement {statement_id}, total_revenue=${statement.total_revenue_cents / 100:.2f}")
        return count

    except Exception as e:
        logger.error(f"Error parsing statement {statement_id}: {e}")
        raise


def auto_match_lines(db: Session, statement_id: int, org_id: int) -> dict:
    try:
        lines = db.query(RoyaltyStatementLine).filter(
            RoyaltyStatementLine.org_id == org_id,
            RoyaltyStatementLine.statement_id == statement_id,
            RoyaltyStatementLine.match_status == "UNMATCHED",
        ).all()

        org_songs = db.query(Song).filter(Song.organization_id == org_id).all()
        org_releases = db.query(Release).filter(Release.organization_id == org_id).all()

        isrc_map = {}
        for song in org_songs:
            if song.isrc:
                clean_isrc = song.isrc.strip().upper().replace("-", "")
                isrc_map[clean_isrc] = song

        upc_map = {}
        for release in org_releases:
            if release.upc:
                clean_upc = release.upc.strip().upper().replace("-", "")
                upc_map[clean_upc] = release

        stats = {
            "total_lines": len(lines),
            "auto_matched": 0,
            "review_required": 0,
            "unmatched": 0,
            "already_matched": 0,
        }

        for line in lines:
            matched = False

            if line.isrc:
                clean_isrc = line.isrc.strip().upper().replace("-", "")
                if clean_isrc in isrc_map:
                    song = isrc_map[clean_isrc]
                    line.matched_song_id = song.id
                    line.match_status = "AUTO_MATCHED"
                    line.match_confidence = 100.0
                    line.match_method = "ISRC"
                    line.matched_at = datetime.utcnow()
                    stats["auto_matched"] += 1
                    matched = True

            if not matched and line.upc:
                clean_upc = line.upc.strip().upper().replace("-", "")
                if clean_upc in upc_map:
                    release = upc_map[clean_upc]
                    line.matched_release_id = release.id
                    release_tracks = release.release_tracks
                    if release_tracks and len(release_tracks) > 0:
                        if line.track_title_raw and len(release_tracks) > 1:
                            best_track = None
                            best_score = 0.0
                            line_title = line.track_title_raw.lower().strip()
                            for rt in release_tracks:
                                song_obj = rt.song
                                if song_obj:
                                    ratio = SequenceMatcher(None, line_title, song_obj.title.lower().strip()).ratio()
                                    if ratio > best_score:
                                        best_score = ratio
                                        best_track = song_obj
                            if best_track:
                                line.matched_song_id = best_track.id
                        else:
                            line.matched_song_id = release_tracks[0].song_id

                    line.match_status = "AUTO_MATCHED"
                    line.match_confidence = 95.0
                    line.match_method = "UPC"
                    line.matched_at = datetime.utcnow()
                    stats["auto_matched"] += 1
                    matched = True

            if not matched and line.track_title_raw:
                line_title = line.track_title_raw.lower().strip()
                raw_artist = (line.artist_name_raw or "").strip()
                # Treat percentages, digit-only, and any non-alphabetic
                # values the same as a missing artist — otherwise an
                # exact title match gets penalized down into the
                # REVIEW_REQUIRED band by a junk artist score.
                if raw_artist and re.search(r"[A-Za-z]", raw_artist):
                    line_artist = raw_artist.lower()
                else:
                    line_artist = ""
                best_score = 0.0
                best_song = None

                for song in org_songs:
                    song_title = (song.title or "").lower().strip()
                    title_ratio = SequenceMatcher(None, line_title, song_title).ratio()

                    if line_artist and song.primary_artist:
                        song_artist = song.primary_artist.lower().strip()
                        artist_ratio = SequenceMatcher(None, line_artist, song_artist).ratio()
                        combined = (title_ratio * 0.6) + (artist_ratio * 0.4)
                    else:
                        combined = title_ratio

                    if combined > best_score:
                        best_score = combined
                        best_song = song

                confidence = best_score * 100.0

                if best_score >= 0.8 and best_song:
                    line.matched_song_id = best_song.id
                    line.match_status = "AUTO_MATCHED"
                    line.match_confidence = confidence
                    line.match_method = "FUZZY"
                    line.matched_at = datetime.utcnow()
                    stats["auto_matched"] += 1
                    matched = True
                elif best_score >= 0.6 and best_song:
                    line.matched_song_id = best_song.id
                    line.match_status = "REVIEW_REQUIRED"
                    line.match_confidence = confidence
                    line.match_method = "FUZZY"
                    stats["review_required"] += 1
                    matched = True

            if not matched:
                stats["unmatched"] += 1

        db.flush()
        logger.info(f"Auto-match results for statement {statement_id}: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error auto-matching statement {statement_id}: {e}")
        raise


def confirm_match(
    db: Session,
    line_id: int,
    org_id: int,
    song_id: int,
    user_id: int,
    work_id: Optional[int] = None,
    release_id: Optional[int] = None,
):
    try:
        line = db.query(RoyaltyStatementLine).filter(
            RoyaltyStatementLine.id == line_id,
            RoyaltyStatementLine.org_id == org_id,
        ).first()
        if not line:
            raise ValueError(f"Statement line {line_id} not found for org {org_id}")

        line.matched_song_id = song_id
        line.matched_work_id = work_id
        line.matched_release_id = release_id
        line.match_status = "CONFIRMED"
        line.match_confidence = 100.0
        line.match_method = "MANUAL"
        line.matched_by_user_id = user_id
        line.matched_at = datetime.utcnow()
        db.flush()
        logger.info(f"Match confirmed for line {line_id} -> song {song_id}")

    except Exception as e:
        logger.error(f"Error confirming match for line {line_id}: {e}")
        raise


def reject_match(db: Session, line_id: int, org_id: int):
    try:
        line = db.query(RoyaltyStatementLine).filter(
            RoyaltyStatementLine.id == line_id,
            RoyaltyStatementLine.org_id == org_id,
        ).first()
        if not line:
            raise ValueError(f"Statement line {line_id} not found for org {org_id}")

        line.matched_song_id = None
        line.matched_work_id = None
        line.matched_release_id = None
        line.match_status = "UNMATCHED"
        line.match_confidence = None
        line.match_method = None
        line.matched_by_user_id = None
        line.matched_at = None
        db.flush()
        logger.info(f"Match rejected for line {line_id}")

    except Exception as e:
        logger.error(f"Error rejecting match for line {line_id}: {e}")
        raise


def ignore_line(db: Session, line_id: int, org_id: int):
    try:
        line = db.query(RoyaltyStatementLine).filter(
            RoyaltyStatementLine.id == line_id,
            RoyaltyStatementLine.org_id == org_id,
        ).first()
        if not line:
            raise ValueError(f"Statement line {line_id} not found for org {org_id}")

        line.match_status = "IGNORED"
        db.flush()
        logger.info(f"Line {line_id} marked as IGNORED")

    except Exception as e:
        logger.error(f"Error ignoring line {line_id}: {e}")
        raise


def bulk_confirm_high_confidence(
    db: Session,
    statement_id: int,
    org_id: int,
    threshold: float = 85.0,
    user_id: Optional[int] = None,
) -> int:
    try:
        lines = db.query(RoyaltyStatementLine).filter(
            RoyaltyStatementLine.org_id == org_id,
            RoyaltyStatementLine.statement_id == statement_id,
            RoyaltyStatementLine.match_status == "AUTO_MATCHED",
            RoyaltyStatementLine.match_confidence >= threshold,
            RoyaltyStatementLine.matched_song_id.isnot(None),
        ).all()

        count = 0
        for line in lines:
            line.match_status = "CONFIRMED"
            line.match_method = "BULK_CONFIRM"
            line.matched_by_user_id = user_id
            line.matched_at = datetime.utcnow()
            count += 1

        db.flush()
        logger.info(f"Bulk confirmed {count} lines for statement {statement_id} with threshold {threshold}")
        return count

    except Exception as e:
        logger.error(f"Error bulk confirming for statement {statement_id}: {e}")
        raise


def _find_splits_for_song(db: Session, org_id: int, song_id: int) -> List[Tuple]:
    contract_assets = db.query(ContractAsset).join(
        Contract, ContractAsset.contract_id == Contract.id
    ).filter(
        Contract.organization_id == org_id,
        ContractAsset.asset_type == "SONG",
        ContractAsset.asset_id == song_id,
    ).all()

    results = []
    for ca in contract_assets:
        splits = db.query(RightsSplit).filter(
            RightsSplit.contract_asset_id == ca.id,
        ).all()
        for split in splits:
            results.append((ca.contract_id, ca, split))

    return results


def _get_allocation_from_ledger(db: Session, statement_id: int, org_id: int) -> list:
    latest_run = db.query(RoyaltyProcessingRun).filter(
        RoyaltyProcessingRun.org_id == org_id,
        RoyaltyProcessingRun.statement_id == statement_id,
        RoyaltyProcessingRun.status == "SUCCEEDED",
    ).order_by(RoyaltyProcessingRun.run_version.desc()).first()

    if not latest_run:
        return []

    entries = db.query(RoyaltyLedgerEntry).filter(
        RoyaltyLedgerEntry.org_id == org_id,
        RoyaltyLedgerEntry.statement_id == statement_id,
        RoyaltyLedgerEntry.processing_run_id == latest_run.id,
    ).all()

    payee_totals: Dict[int, dict] = {}

    for entry in entries:
        pid = entry.payee_id
        if pid not in payee_totals:
            payee = db.query(Payee).filter(Payee.id == pid).first()
            payee_name = "Unknown"
            if payee and payee.creator_id:
                creator = db.query(Creator).filter(Creator.id == payee.creator_id).first()
                payee_name = creator.display_name if creator else (payee.company_name or "Unknown")
            elif payee:
                payee_name = payee.company_name or "Unknown"
            payee_totals[pid] = {
                "payee_id": pid,
                "payee_name": payee_name,
                "payee_type": payee.payee_type if payee else "OTHER",
                "earnings_cents": 0,
                "fees_cents": 0,
                "recoupment_cents": 0,
                "payable_cents": 0,
            }

        if entry.entry_type == "EARNING":
            payee_totals[pid]["earnings_cents"] += entry.amount_cents
        elif entry.entry_type == "FEE":
            payee_totals[pid]["fees_cents"] += abs(entry.amount_cents)
        elif entry.entry_type == "RECOUPMENT_APPLIED":
            payee_totals[pid]["recoupment_cents"] += abs(entry.amount_cents)
        elif entry.entry_type == "PAYABLE_CREATED":
            payee_totals[pid]["payable_cents"] += entry.amount_cents

    return list(payee_totals.values())


def get_allocation_preview(db: Session, statement_id: int, org_id: int) -> dict:
    try:
        statement = db.query(RoyaltyStatement).filter(
            RoyaltyStatement.id == statement_id,
            RoyaltyStatement.organization_id == org_id,
        ).first()

        is_processed = statement and statement.status == "PROCESSED"

        if is_processed:
            allocations = _get_allocation_from_ledger(db, statement_id, org_id)
            return {"allocations": allocations, "is_processed": True}

        lines = db.query(RoyaltyStatementLine).filter(
            RoyaltyStatementLine.org_id == org_id,
            RoyaltyStatementLine.statement_id == statement_id,
            RoyaltyStatementLine.match_status.in_(["MATCHED", "CONFIRMED", "AUTO_MATCHED"]),
            RoyaltyStatementLine.matched_song_id.isnot(None),
        ).all()

        payee_totals: Dict[int, dict] = {}

        for line in lines:
            song_id = line.matched_song_id
            net_cents = int(round((line.net_amount_statement_currency or 0) * 100))

            splits = _find_splits_for_song(db, org_id, song_id)

            if not splits:
                continue

            for contract_id, ca, split in splits:
                if not split.rights_holder_id:
                    continue

                creator_id = split.rights_holder_id
                payee = ensure_payee_for_creator(db, org_id, creator_id)
                earning_cents = int(round(net_cents * (split.share_percentage or 0) / 100.0))

                if payee.id not in payee_totals:
                    creator = db.query(Creator).filter(Creator.id == creator_id).first()
                    payee_totals[payee.id] = {
                        "payee_id": payee.id,
                        "payee_name": creator.display_name if creator else (payee.company_name or "Unknown"),
                        "payee_type": payee.payee_type,
                        "earnings_cents": 0,
                        "fees_cents": 0,
                        "recoupment_cents": 0,
                        "payable_cents": 0,
                    }

                payee_totals[payee.id]["earnings_cents"] += earning_cents

        for payee_id, totals in payee_totals.items():
            advances = db.query(AdvanceV2).filter(
                AdvanceV2.org_id == org_id,
                AdvanceV2.payee_id == payee_id,
                AdvanceV2.recoupable == True,
                AdvanceV2.outstanding_balance_cents > 0,
            ).order_by(AdvanceV2.recoupment_priority).all()

            remaining = totals["earnings_cents"] - totals["fees_cents"]
            total_recoup = 0
            for adv in advances:
                if remaining <= 0:
                    break
                recoup_amount = min(remaining, adv.outstanding_balance_cents)
                total_recoup += recoup_amount
                remaining -= recoup_amount

            totals["recoupment_cents"] = total_recoup
            totals["payable_cents"] = totals["earnings_cents"] - totals["fees_cents"] - total_recoup

        return {"allocations": list(payee_totals.values()), "is_processed": False}

    except Exception as e:
        logger.error(f"Error getting allocation preview for statement {statement_id}: {e}")
        raise


def _is_mlc_statement(statement) -> bool:
    source_name = (getattr(statement, 'source_name', '') or '').lower()
    source_type = (getattr(statement, 'source_type', '') or '').lower()
    mlc_keywords = ['mlc', 'mechanical licensing collective']
    combined = f"{source_name} {source_type}"
    return any(kw in combined for kw in mlc_keywords)


def _find_multi_client_songs(db: Session, org_id: int, song_id: int) -> list:
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        return [song_id]
    group_id = getattr(song, 'shared_song_group_id', None)
    if group_id:
        sibling_ids = [
            s.id for s in db.query(Song).filter(
                Song.shared_song_group_id == group_id,
                Song.organization_id == org_id,
            ).all()
        ]
        if sibling_ids:
            return sibling_ids

    matched_ids = {song_id}
    if song.isrc:
        isrc_matches = db.query(Song.id).filter(
            Song.isrc == song.isrc,
            Song.organization_id == org_id,
            Song.id != song_id,
        ).all()
        matched_ids.update(s.id for s in isrc_matches)
    if song.iswc:
        iswc_matches = db.query(Song.id).filter(
            Song.iswc == song.iswc,
            Song.organization_id == org_id,
            Song.id != song_id,
        ).all()
        matched_ids.update(s.id for s in iswc_matches)
    return list(matched_ids)


def process_statement(db: Session, statement_id: int, org_id: int, user_id: int) -> int:
    try:
        statement = db.query(RoyaltyStatement).filter(
            RoyaltyStatement.id == statement_id,
            RoyaltyStatement.organization_id == org_id,
        ).first()
        if not statement:
            raise ValueError(f"Statement {statement_id} not found for org {org_id}")

        latest_run = db.query(RoyaltyProcessingRun).filter(
            RoyaltyProcessingRun.org_id == org_id,
            RoyaltyProcessingRun.statement_id == statement_id,
        ).order_by(RoyaltyProcessingRun.run_version.desc()).first()

        run_version = (latest_run.run_version + 1) if latest_run else 1

        processing_run = RoyaltyProcessingRun(
            org_id=org_id,
            statement_id=statement_id,
            run_version=run_version,
            status="RUNNING",
            started_at=datetime.utcnow(),
            started_by_user_id=user_id,
        )
        db.add(processing_run)
        db.flush()

        lines = db.query(RoyaltyStatementLine).filter(
            RoyaltyStatementLine.org_id == org_id,
            RoyaltyStatementLine.statement_id == statement_id,
            RoyaltyStatementLine.match_status != "IGNORED",
        ).all()

        summary = {
            "total_lines_processed": 0,
            "total_earning_entries": 0,
            "total_recoupment_entries": 0,
            "total_payable_entries": 0,
            "total_earnings_cents": 0,
            "total_recouped_cents": 0,
            "total_payable_cents": 0,
            "lines_without_splits": 0,
            "lines_matched_processed": 0,
            "lines_unmatched_processed": 0,
        }

        is_mlc = _is_mlc_statement(statement)
        if is_mlc:
            logger.info(f"MLC statement detected for statement {statement_id} — multi-client distribution enabled")

        for line in lines:
            summary["total_lines_processed"] += 1
            song_id = line.matched_song_id
            work_id = line.matched_work_id
            release_id = line.matched_release_id
            net_cents = int(round((line.net_amount_statement_currency or 0) * 100))

            is_matched = line.match_status in ("MATCHED", "CONFIRMED", "AUTO_MATCHED") and song_id

            if not is_matched:
                summary["lines_unmatched_processed"] += 1
                unmatched_payee = _get_or_create_org_payee(db, org_id)
                entry = RoyaltyLedgerEntry(
                    org_id=org_id,
                    statement_id=statement_id,
                    statement_line_id=line.id,
                    processing_run_id=processing_run.id,
                    song_id=None,
                    work_id=None,
                    release_id=None,
                    payee_id=unmatched_payee.id,
                    entry_type="EARNING",
                    amount_cents=net_cents,
                    revenue_type=line.revenue_type,
                    source=line.store,
                    memo="Unmatched statement line",
                    created_by_user_id=user_id,
                )
                db.add(entry)
                summary["total_earning_entries"] += 1
                summary["total_earnings_cents"] += net_cents
                continue

            summary["lines_matched_processed"] += 1

            all_song_ids = [song_id]
            if is_mlc:
                all_song_ids = _find_multi_client_songs(db, org_id, song_id)

            splits = []
            for sid in all_song_ids:
                splits.extend(_find_splits_for_song(db, org_id, sid))

            if not splits:
                summary["lines_without_splits"] += 1
                no_split_payee = _get_or_create_org_payee(db, org_id)
                entry = RoyaltyLedgerEntry(
                    org_id=org_id,
                    statement_id=statement_id,
                    statement_line_id=line.id,
                    processing_run_id=processing_run.id,
                    song_id=song_id,
                    work_id=work_id,
                    release_id=release_id,
                    payee_id=no_split_payee.id,
                    entry_type="EARNING",
                    amount_cents=net_cents,
                    revenue_type=line.revenue_type,
                    source=line.store,
                    memo="No contract splits found",
                    created_by_user_id=user_id,
                )
                db.add(entry)
                summary["total_earning_entries"] += 1
                summary["total_earnings_cents"] += net_cents
                continue

            total_share = sum((s.share_percentage or 0) for _, _, s in splits if s.rights_holder_id)
            normalize = is_mlc and len(all_song_ids) > 1 and total_share > 100.0

            for contract_id, ca, split in splits:
                if not split.rights_holder_id:
                    continue

                payee = ensure_payee_for_creator(db, org_id, split.rights_holder_id)
                share_pct = split.share_percentage or 0
                if normalize and total_share > 0:
                    share_pct = share_pct * 100.0 / total_share
                earning_cents = int(round(net_cents * share_pct / 100.0))

                earning_entry = RoyaltyLedgerEntry(
                    org_id=org_id,
                    statement_id=statement_id,
                    statement_line_id=line.id,
                    processing_run_id=processing_run.id,
                    song_id=song_id,
                    work_id=work_id,
                    release_id=release_id,
                    contract_id=contract_id,
                    payee_id=payee.id,
                    entry_type="EARNING",
                    amount_cents=earning_cents,
                    revenue_type=line.revenue_type,
                    source=line.store,
                    created_by_user_id=user_id,
                )
                db.add(earning_entry)
                summary["total_earning_entries"] += 1
                summary["total_earnings_cents"] += earning_cents

                payable = earning_cents
                advances = db.query(AdvanceV2).filter(
                    AdvanceV2.org_id == org_id,
                    AdvanceV2.payee_id == payee.id,
                    AdvanceV2.recoupable == True,
                    AdvanceV2.outstanding_balance_cents > 0,
                ).order_by(AdvanceV2.recoupment_priority).all()

                for adv in advances:
                    if payable <= 0:
                        break
                    recoup_amount = min(payable, adv.outstanding_balance_cents)
                    recoup_entry = RoyaltyLedgerEntry(
                        org_id=org_id,
                        statement_id=statement_id,
                        statement_line_id=line.id,
                        processing_run_id=processing_run.id,
                        song_id=song_id,
                        work_id=work_id,
                        release_id=release_id,
                        contract_id=contract_id,
                        payee_id=payee.id,
                        entry_type="RECOUPMENT_APPLIED",
                        amount_cents=-recoup_amount,
                        advance_id=adv.id,
                        recoupment_pool=adv.recoupment_pool,
                        memo=f"Recoupment against advance '{adv.advance_name}'",
                        created_by_user_id=user_id,
                    )
                    db.add(recoup_entry)
                    adv.outstanding_balance_cents -= recoup_amount
                    payable -= recoup_amount
                    summary["total_recoupment_entries"] += 1
                    summary["total_recouped_cents"] += recoup_amount

                if payable > 0:
                    payable_entry = RoyaltyLedgerEntry(
                        org_id=org_id,
                        statement_id=statement_id,
                        statement_line_id=line.id,
                        processing_run_id=processing_run.id,
                        song_id=song_id,
                        work_id=work_id,
                        release_id=release_id,
                        contract_id=contract_id,
                        payee_id=payee.id,
                        entry_type="PAYABLE_CREATED",
                        amount_cents=payable,
                        created_by_user_id=user_id,
                    )
                    db.add(payable_entry)
                    summary["total_payable_entries"] += 1
                    summary["total_payable_cents"] += payable

        statement.status = "PROCESSED"
        processing_run.status = "SUCCEEDED"
        processing_run.completed_at = datetime.utcnow()
        processing_run.summary_json = summary

        db.flush()
        logger.info(f"Statement {statement_id} processed successfully. Run ID: {processing_run.id}")
        return processing_run.id

    except Exception as e:
        logger.error(f"Error processing statement {statement_id}: {e}")
        raise


def _get_or_create_org_payee(db: Session, org_id: int) -> Payee:
    payee = db.query(Payee).filter(
        Payee.org_id == org_id,
        Payee.payee_type == "COMPANY",
        Payee.creator_id.is_(None),
        Payee.company_name == "__ORG_UNALLOCATED__",
    ).first()
    if payee:
        return payee
    payee = Payee(
        org_id=org_id,
        payee_type="COMPANY",
        company_name="__ORG_UNALLOCATED__",
    )
    db.add(payee)
    db.flush()
    return payee


def reprocess_statement(
    db: Session,
    statement_id: int,
    org_id: int,
    user_id: int,
    reason: str,
) -> int:
    try:
        statement = db.query(RoyaltyStatement).filter(
            RoyaltyStatement.id == statement_id,
            RoyaltyStatement.organization_id == org_id,
        ).first()
        if not statement:
            raise ValueError(f"Statement {statement_id} not found for org {org_id}")

        latest_run = db.query(RoyaltyProcessingRun).filter(
            RoyaltyProcessingRun.org_id == org_id,
            RoyaltyProcessingRun.statement_id == statement_id,
            RoyaltyProcessingRun.status == "SUCCEEDED",
        ).order_by(RoyaltyProcessingRun.run_version.desc()).first()

        if not latest_run:
            raise ValueError(f"No successful processing run found for statement {statement_id}")

        existing_entries = db.query(RoyaltyLedgerEntry).filter(
            RoyaltyLedgerEntry.org_id == org_id,
            RoyaltyLedgerEntry.processing_run_id == latest_run.id,
            RoyaltyLedgerEntry.entry_type != "REVERSAL",
        ).all()

        reversal_run = RoyaltyProcessingRun(
            org_id=org_id,
            statement_id=statement_id,
            run_version=latest_run.run_version + 1,
            status="RUNNING",
            started_at=datetime.utcnow(),
            started_by_user_id=user_id,
            notes=f"Reversal: {reason}",
        )
        db.add(reversal_run)
        db.flush()

        for entry in existing_entries:
            reversal = RoyaltyLedgerEntry(
                org_id=org_id,
                statement_id=entry.statement_id,
                statement_line_id=entry.statement_line_id,
                processing_run_id=reversal_run.id,
                song_id=entry.song_id,
                work_id=entry.work_id,
                release_id=entry.release_id,
                contract_id=entry.contract_id,
                payee_id=entry.payee_id,
                entry_type="REVERSAL",
                amount_cents=-entry.amount_cents,
                advance_id=entry.advance_id,
                recoupment_pool=entry.recoupment_pool,
                revenue_type=entry.revenue_type,
                source=entry.source,
                memo=f"Reversal of entry {entry.id}: {reason}",
                created_by_user_id=user_id,
            )
            db.add(reversal)

            if entry.entry_type == "RECOUPMENT_APPLIED" and entry.advance_id:
                adv = db.query(AdvanceV2).filter(
                    AdvanceV2.id == entry.advance_id,
                    AdvanceV2.org_id == org_id,
                ).first()
                if adv:
                    adv.outstanding_balance_cents += abs(entry.amount_cents)

        reversal_run.status = "SUCCEEDED"
        reversal_run.completed_at = datetime.utcnow()
        reversal_run.summary_json = {"reversal_of_run": latest_run.id, "entries_reversed": len(existing_entries)}

        db.flush()

        new_run_id = process_statement(db, statement_id, org_id, user_id)

        logger.info(f"Statement {statement_id} reprocessed. Reversal run: {reversal_run.id}, New run: {new_run_id}")
        return new_run_id

    except Exception as e:
        logger.error(f"Error reprocessing statement {statement_id}: {e}")
        raise


def get_payee_balance(db: Session, payee_id: int, org_id: int) -> dict:
    try:
        payable_sum = db.query(
            func.coalesce(func.sum(RoyaltyLedgerEntry.amount_cents), 0)
        ).filter(
            RoyaltyLedgerEntry.org_id == org_id,
            RoyaltyLedgerEntry.payee_id == payee_id,
            RoyaltyLedgerEntry.entry_type == "PAYABLE_CREATED",
        ).scalar()

        payment_sum = db.query(
            func.coalesce(func.sum(RoyaltyLedgerEntry.amount_cents), 0)
        ).filter(
            RoyaltyLedgerEntry.org_id == org_id,
            RoyaltyLedgerEntry.payee_id == payee_id,
            RoyaltyLedgerEntry.entry_type == "PAYMENT",
        ).scalar()

        reversal_sum = db.query(
            func.coalesce(func.sum(RoyaltyLedgerEntry.amount_cents), 0)
        ).filter(
            RoyaltyLedgerEntry.org_id == org_id,
            RoyaltyLedgerEntry.payee_id == payee_id,
            RoyaltyLedgerEntry.entry_type == "REVERSAL",
        ).scalar()

        total_earnings = db.query(
            func.coalesce(func.sum(RoyaltyLedgerEntry.amount_cents), 0)
        ).filter(
            RoyaltyLedgerEntry.org_id == org_id,
            RoyaltyLedgerEntry.payee_id == payee_id,
            RoyaltyLedgerEntry.entry_type == "EARNING",
        ).scalar()

        total_recouped = db.query(
            func.coalesce(func.sum(RoyaltyLedgerEntry.amount_cents), 0)
        ).filter(
            RoyaltyLedgerEntry.org_id == org_id,
            RoyaltyLedgerEntry.payee_id == payee_id,
            RoyaltyLedgerEntry.entry_type == "RECOUPMENT_APPLIED",
        ).scalar()

        balance_cents = payable_sum - abs(payment_sum) + reversal_sum

        return {
            "payee_id": payee_id,
            "total_earnings_cents": total_earnings,
            "total_recouped_cents": abs(total_recouped),
            "total_payable_cents": payable_sum,
            "total_paid_cents": abs(payment_sum),
            "current_balance_cents": balance_cents,
            "reversals_cents": reversal_sum,
        }

    except Exception as e:
        logger.error(f"Error getting balance for payee {payee_id}: {e}")
        raise


def record_payment_ledger(db: Session, payout_item_id: int, org_id: int, user_id: int):
    try:
        payout_item = db.query(PayoutItem).filter(
            PayoutItem.id == payout_item_id,
            PayoutItem.org_id == org_id,
        ).first()
        if not payout_item:
            raise ValueError(f"PayoutItem {payout_item_id} not found for org {org_id}")

        batch = db.query(PayoutBatch).filter(
            PayoutBatch.id == payout_item.batch_id,
            PayoutBatch.org_id == org_id,
        ).first()

        latest_run = db.query(RoyaltyProcessingRun).filter(
            RoyaltyProcessingRun.org_id == org_id,
        ).order_by(RoyaltyProcessingRun.id.desc()).first()

        if not latest_run:
            raise ValueError(f"No processing run found for org {org_id}")

        latest_statement = db.query(RoyaltyStatement).filter(
            RoyaltyStatement.organization_id == org_id,
        ).order_by(RoyaltyStatement.id.desc()).first()

        statement_id = latest_statement.id if latest_statement else None
        if not statement_id:
            raise ValueError(f"No statement found for org {org_id}")

        payment_entry = RoyaltyLedgerEntry(
            org_id=org_id,
            statement_id=statement_id,
            processing_run_id=latest_run.id,
            payee_id=payout_item.payee_id,
            entry_type="PAYMENT",
            amount_cents=-payout_item.amount_cents,
            memo=f"Payment via payout batch '{batch.name}'" if batch else f"Payment for payout item {payout_item_id}",
            created_by_user_id=user_id,
        )
        db.add(payment_entry)
        payout_item.paid_at = datetime.utcnow()
        db.flush()
        logger.info(f"Payment ledger entry created for payout item {payout_item_id}")

    except Exception as e:
        logger.error(f"Error recording payment for payout item {payout_item_id}: {e}")
        raise


def generate_statement_action_items(db: Session, statement_id: int, org_id: int):
    try:
        statement = db.query(RoyaltyStatement).filter(
            RoyaltyStatement.id == statement_id,
            RoyaltyStatement.organization_id == org_id,
        ).first()
        if not statement:
            return

        unmatched_count = db.query(func.count(RoyaltyStatementLine.id)).filter(
            RoyaltyStatementLine.statement_id == statement_id,
            RoyaltyStatementLine.org_id == org_id,
            RoyaltyStatementLine.match_status.in_(["UNMATCHED", "REVIEW_REQUIRED"]),
        ).scalar() or 0

        if unmatched_count > 0:
            existing = db.query(ActionItem).filter(
                ActionItem.organization_id == org_id,
                ActionItem.entity_type == "STATEMENT",
                ActionItem.action_type == "STATEMENT_UNMATCHED",
                ActionItem.title.contains(f"Statement #{statement_id}"),
                ActionItem.status != "COMPLETED",
            ).first()
            if not existing:
                action = ActionItem(
                    organization_id=org_id,
                    entity_type="STATEMENT",
                    entity_label=f"{statement.source_name} - {statement.period_start} to {statement.period_end}",
                    action_type="STATEMENT_UNMATCHED",
                    title=f"Statement #{statement_id}: {unmatched_count} unmatched lines need review",
                    description=f"The statement from {statement.source_name} has {unmatched_count} lines that need matching. Review in the Matching Console.",
                    priority=2,
                    status="PENDING",
                    is_auto_generated=True,
                )
                db.add(action)

        status = statement.status
        if status in ("PROCESSED", "PARTIALLY_MATCHED", "MAPPING_COMPLETE", "READY_TO_PROCESS"):
            matched_count = db.query(func.count(RoyaltyStatementLine.id)).filter(
                RoyaltyStatementLine.statement_id == statement_id,
                RoyaltyStatementLine.org_id == org_id,
                RoyaltyStatementLine.match_status.in_(["AUTO_MATCHED", "CONFIRMED"]),
            ).scalar() or 0
            total = db.query(func.count(RoyaltyStatementLine.id)).filter(
                RoyaltyStatementLine.statement_id == statement_id,
                RoyaltyStatementLine.org_id == org_id,
            ).scalar() or 1
            if matched_count > 0 and matched_count / total >= 0.5:
                existing = db.query(ActionItem).filter(
                    ActionItem.organization_id == org_id,
                    ActionItem.entity_type == "STATEMENT",
                    ActionItem.action_type == "STATEMENT_READY",
                    ActionItem.title.contains(f"Statement #{statement_id}"),
                    ActionItem.status != "COMPLETED",
                ).first()
                if not existing:
                    action = ActionItem(
                        organization_id=org_id,
                        entity_type="STATEMENT",
                        entity_label=f"{statement.source_name}",
                        action_type="STATEMENT_READY",
                        title=f"Statement #{statement_id} is ready for processing",
                        description=f"The statement from {statement.source_name} has sufficient matches ({matched_count}/{total}) and can be processed.",
                        priority=1,
                        status="PENDING",
                        is_auto_generated=True,
                    )
                    db.add(action)

        db.flush()
        logger.info(f"Generated action items for statement {statement_id}")

    except Exception as e:
        logger.error(f"Error generating action items for statement {statement_id}: {e}")


def generate_reprocess_action_item(db: Session, statement_id: int, org_id: int, run_id: int):
    try:
        statement = db.query(RoyaltyStatement).filter(
            RoyaltyStatement.id == statement_id,
        ).first()
        if not statement:
            return
        action = ActionItem(
            organization_id=org_id,
            entity_type="STATEMENT",
            entity_label=f"{statement.source_name}",
            action_type="REPROCESS_REVIEW",
            title=f"Statement #{statement_id} was reprocessed - review needed",
            description=f"Statement from {statement.source_name} was reprocessed (run #{run_id}). Please review the results.",
            priority=1,
            status="PENDING",
            is_auto_generated=True,
        )
        db.add(action)
        db.flush()
    except Exception as e:
        logger.error(f"Error generating reprocess action item: {e}")
