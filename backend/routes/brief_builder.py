from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import logging
import json
import os

from ..models import (
    get_db, User, OrganizationMember, Song, AudioAsset, AudioAnalysis,
    AudioTag, AudioAssetTag,
)
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/brief-builder", tags=["brief-builder"])
logger = logging.getLogger("cadence")


class BriefSearchRequest(BaseModel):
    query: Optional[str] = None
    bpm_min: Optional[float] = None
    bpm_max: Optional[float] = None
    key: Optional[str] = None
    moods: Optional[List[str]] = None
    textures: Optional[List[str]] = None
    vocal_present: Optional[bool] = None
    has_stems: Optional[bool] = None
    analyzed_only: Optional[bool] = False
    limit: int = 20


def _get_org_id(current_user: User, db: Session) -> int:
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="No organization membership found")
    return membership.organization_id


@router.post("/search")
def search_brief(
    request: BriefSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = _get_org_id(current_user, db)

    parsed_criteria = {}
    if request.query:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"), base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL"))

            prompt = f"""Parse this music brief search query into structured criteria. Return JSON with any of these fields that apply:
- bpm_min (number)
- bpm_max (number)
- key (string, e.g. "C Major")
- moods (list of strings)
- textures (list of strings)
- genres (list of strings)
- vocal_present (boolean)
- energy_level (string: LOW/MEDIUM/HIGH)

Query: "{request.query}"

Respond ONLY with valid JSON."""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            parsed_criteria = json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.warning(f"OpenAI query parsing failed: {e}")

    bpm_min = request.bpm_min or parsed_criteria.get("bpm_min")
    bpm_max = request.bpm_max or parsed_criteria.get("bpm_max")
    key = request.key or parsed_criteria.get("key")
    moods = request.moods or parsed_criteria.get("moods", [])
    textures = request.textures or parsed_criteria.get("textures", [])
    vocal_present = request.vocal_present if request.vocal_present is not None else parsed_criteria.get("vocal_present")
    energy_level = parsed_criteria.get("energy_level")
    genres = parsed_criteria.get("genres", [])

    has_strict_filters = bool(bpm_min or bpm_max or key or vocal_present is not None or energy_level)

    if request.analyzed_only:
        q = (
            db.query(Song, AudioAnalysis)
            .join(AudioAsset, AudioAsset.song_id == Song.id)
            .join(AudioAnalysis, AudioAnalysis.audio_asset_id == AudioAsset.id)
            .filter(
                Song.organization_id == org_id,
                AudioAnalysis.status == "SUCCEEDED",
            )
        )

        if bpm_min:
            q = q.filter(AudioAnalysis.bpm >= bpm_min)
        if bpm_max:
            q = q.filter(AudioAnalysis.bpm <= bpm_max)
        if key:
            q = q.filter(AudioAnalysis.musical_key.ilike(f"%{key}%"))
        if vocal_present is not None:
            q = q.filter(AudioAnalysis.vocal_present == vocal_present)
        if energy_level:
            q = q.filter(AudioAnalysis.energy_level == energy_level)

        results_raw = q.distinct().limit(request.limit * 3).all()
    else:
        q = (
            db.query(Song, AudioAnalysis)
            .outerjoin(AudioAsset, AudioAsset.song_id == Song.id)
            .outerjoin(AudioAnalysis, (AudioAnalysis.audio_asset_id == AudioAsset.id) & (AudioAnalysis.status == "SUCCEEDED"))
            .filter(Song.organization_id == org_id)
        )
        results_raw = q.distinct().limit(request.limit * 5).all()

    seen_song_ids = set()
    scored_results = []
    for song, analysis in results_raw:
        if song.id in seen_song_ids:
            continue
        seen_song_ids.add(song.id)

        score = 0.0
        match_reasons = []
        is_analyzed = analysis is not None

        if analysis:
            if bpm_min or bpm_max:
                if analysis.bpm:
                    if (not bpm_min or analysis.bpm >= bpm_min) and (not bpm_max or analysis.bpm <= bpm_max):
                        score += 20
                        match_reasons.append(f"BPM: {analysis.bpm}")

            if key and analysis.musical_key and key.lower() in analysis.musical_key.lower():
                score += 15
                match_reasons.append(f"Key: {analysis.musical_key}")

            if vocal_present is not None and analysis.vocal_present == vocal_present:
                score += 10
                match_reasons.append(f"Vocals: {'Yes' if vocal_present else 'No'}")

        asset_ids = [a.id for a in db.query(AudioAsset).filter(AudioAsset.song_id == song.id).all()]
        if asset_ids:
            song_tags = (
                db.query(AudioTag)
                .join(AudioAssetTag, AudioAssetTag.audio_tag_id == AudioTag.id)
                .filter(AudioAssetTag.audio_asset_id.in_(asset_ids))
                .all()
            )
            song_tag_names = {t.name.lower() for t in song_tags}

            for mood in moods:
                if mood.lower() in song_tag_names:
                    score += 15
                    match_reasons.append(f"Mood: {mood}")

            for texture in textures:
                if texture.lower() in song_tag_names:
                    score += 10
                    match_reasons.append(f"Texture: {texture}")

            for genre in genres:
                if genre.lower() in song_tag_names:
                    score += 10
                    match_reasons.append(f"Genre: {genre}")

        if request.has_stems:
            stem_assets = db.query(AudioAsset).filter(
                AudioAsset.song_id == song.id,
                AudioAsset.file_type == "STEMS",
            ).count()
            if stem_assets > 0:
                score += 10
                match_reasons.append("Has stems")

        if not is_analyzed and not request.analyzed_only:
            if not match_reasons:
                match_reasons.append("Not yet analyzed")

        include = score > 0 or not (moods or textures or genres or bpm_min or bpm_max or key)
        if not is_analyzed and not request.analyzed_only and not include:
            include = True

        if include:
            scored_results.append({
                "song_id": song.id,
                "title": song.title,
                "primary_artist": song.primary_artist,
                "bpm": analysis.bpm if analysis else None,
                "musical_key": analysis.musical_key if analysis else None,
                "energy_level": analysis.energy_level if analysis else None,
                "vocal_present": analysis.vocal_present if analysis else None,
                "is_analyzed": is_analyzed,
                "score": score,
                "match_reasons": match_reasons if match_reasons else ["Catalog match"],
            })

    scored_results.sort(key=lambda x: (0 if x["is_analyzed"] else 1, -x["score"]))
    return {"results": scored_results[:request.limit], "total": len(scored_results)}
