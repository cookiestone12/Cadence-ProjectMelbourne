"""
AI-based Schedule A extractor.

Handles unstructured input (free-form text, prose PDFs, screenshots, scanned
pages) by asking the LLM to return a normalized list of song records that
matches the same shape produced by the column-aware tabular parser.

All extractors return:
    {
        "rows":   [ { ...normalized song dict, "_confidence": float, "_source": str } ],
        "method": "<extraction method label>",
        "header_text": "<text used for creator/contract header parsing, if any>",
        "warnings": [str, ...],
    }
"""
import os
import json
import base64
import logging
from io import BytesIO
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cadence")


_NORMALIZED_FIELDS = [
    "title",
    "primary_artist",
    "publishing_percentage",
    "master_percentage",
    "advance_amount",
    "label",
    "isrc",
    "iswc",
    "release_date",
    "status",
    "notes",
]


SYSTEM_PROMPT = """You are a music publishing data analyst. You read free-form
Schedule A / placement / catalog documents (PDFs, screenshots, emails,
spreadsheets pasted as text) and return a strict JSON object describing every
song listed.

Always return JSON of the form:
{
  "header": {
    "creator_name": string|null,
    "pro_name": string|null,
    "ipi": string|null,
    "publisher": string|null,
    "agreement_type": string|null,
    "effective_date": string|null,
    "territory": string|null,
    "term": string|null
  },
  "rows": [
    {
      "title": string,
      "primary_artist": string|null,
      "publishing_percentage": number|null,
      "master_percentage": number|null,
      "advance_amount": number|null,
      "label": string|null,
      "isrc": string|null,
      "iswc": string|null,
      "release_date": string|null,
      "status": string|null,
      "notes": string|null,
      "confidence": number,
      "source": string,
      "field_confidence": {
        "title": number,
        "primary_artist": number,
        "publishing_percentage": number,
        "master_percentage": number,
        "advance_amount": number,
        "label": number,
        "isrc": number,
        "iswc": number,
        "release_date": number
      }
    }
  ]
}

RULES
- "title" is REQUIRED for every row. If you cannot extract a clean title,
  drop the row.
- Numbers MUST be plain JSON numbers (no "%" or "$").
- "publishing_percentage" and "master_percentage" are 0-100. Convert
  decimals like 0.5 to 50.
- "advance_amount" is in dollars (no cents conversion).
- "release_date" is "YYYY-MM-DD" or null.
- "isrc" must be 12-character format (e.g. USRC12100587). Otherwise null.
- "iswc" must be in T-XXX.XXX.XXX-X format. Otherwise null.
- "confidence" is 0.0-1.0 reflecting how sure you are about the row as a
  whole given the source quality.
- "source" is a short snippet (<= 80 chars) showing where this row came
  from in the document, e.g. "page 1, line 5: 'Blinding Lights ...'".
- Do NOT invent fields. Use null when unknown.
- Do NOT include explanatory text or markdown. Return JSON only."""


def _client():
    from openai import OpenAI
    return OpenAI(
        api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"),
        base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL"),
    )


def _log_usage(usage, feature: str, org_id: Optional[int]) -> None:
    if not usage:
        return
    try:
        from .ai_usage import log_ai_usage_standalone
        log_ai_usage_standalone(
            feature=feature,
            model="gpt-4o-mini",
            input_tokens=usage.prompt_tokens or 0,
            output_tokens=usage.completion_tokens or 0,
            org_id=org_id,
        )
    except Exception as e:
        logger.warning(f"Failed to log AI usage for {feature}: {e}")


def _coerce_pct(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return ""
    if f < 0:
        return ""
    if f <= 1.0:
        f *= 100.0
    if f > 100.0:
        f = 100.0
    return f"{f:.2f}".rstrip("0").rstrip(".")


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


_ISRC_RE = __import__("re").compile(r"^[A-Z]{2}[A-Z0-9]{3}\d{7}$")
_ISWC_RE = __import__("re").compile(r"^T-?\d{3}\.?\d{3}\.?\d{3}-?\d$")
_DATE_RE = __import__("re").compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_row_fields(row: Dict[str, Any]) -> List[str]:
    """Return a list of field-level validation flags (e.g. 'isrc:invalid')."""
    flags: List[str] = []
    isrc = row.get("isrc") or ""
    if isrc and not _ISRC_RE.match(isrc.upper()):
        flags.append("isrc:invalid")
    iswc = row.get("iswc") or ""
    if iswc and not _ISWC_RE.match(iswc.upper()):
        flags.append("iswc:invalid")
    rd = row.get("release_date") or ""
    if rd and not _DATE_RE.match(rd):
        flags.append("release_date:invalid")
    for pct_field in ("publishing_percentage", "master_percentage"):
        v = row.get(pct_field)
        if v in (None, ""):
            continue
        try:
            n = float(v)
            if n < 0 or n > 100:
                flags.append(f"{pct_field}:out_of_range")
        except (TypeError, ValueError):
            flags.append(f"{pct_field}:invalid")
    return flags


def _normalize_row(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title = _coerce_text(raw.get("title"))
    if not title:
        return None
    confidence = raw.get("confidence")
    try:
        confidence = float(confidence) if confidence is not None else 0.5
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.5

    notes_parts: List[str] = []
    status_text = _coerce_text(raw.get("status"))
    if status_text:
        notes_parts.append(status_text)
    raw_notes = _coerce_text(raw.get("notes"))
    if raw_notes:
        notes_parts.append(raw_notes)

    advance_raw = raw.get("advance_amount")
    advance = ""
    if advance_raw not in (None, ""):
        try:
            advance = f"{float(advance_raw):.2f}"
        except (TypeError, ValueError):
            advance = ""

    field_conf_raw = raw.get("field_confidence") or {}
    if not isinstance(field_conf_raw, dict):
        field_conf_raw = {}
    field_confidence: Dict[str, float] = {}
    for f in _NORMALIZED_FIELDS:
        v = field_conf_raw.get(f)
        try:
            if v is None:
                field_confidence[f] = round(confidence, 2)
            else:
                field_confidence[f] = round(max(0.0, min(1.0, float(v))), 2)
        except (TypeError, ValueError):
            field_confidence[f] = round(confidence, 2)

    normalized = {
        "title": title,
        "primary_artist": _coerce_text(raw.get("primary_artist")),
        "publishing_percentage": _coerce_pct(raw.get("publishing_percentage")),
        "master_percentage": _coerce_pct(raw.get("master_percentage")),
        "advance_amount": advance,
        "label": _coerce_text(raw.get("label")),
        "isrc": _coerce_text(raw.get("isrc")),
        "iswc": _coerce_text(raw.get("iswc")),
        "release_date": _coerce_text(raw.get("release_date")),
        "notes": " | ".join([p for p in notes_parts if p]),
        "_confidence": round(confidence, 2),
        "_source": _coerce_text(raw.get("source"))[:120],
        "_field_confidence": field_confidence,
    }
    flags = _validate_row_fields(normalized)
    if flags:
        normalized["_flags"] = flags
    return normalized


def _parse_response(text: str) -> Dict[str, Any]:
    """Strip markdown fencing if present and parse JSON."""
    s = text.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        if s.startswith("json"):
            s = s[4:]
        s = s.strip()
        if s.endswith("```"):
            s = s[:-3].strip()
    return json.loads(s)


def extract_from_text(text: str, org_id: Optional[int] = None) -> Dict[str, Any]:
    """Run the AI extractor against raw text input."""
    if not text or not text.strip():
        return {"rows": [], "header": {}, "method": "ai_text", "warnings": ["No text supplied"]}

    truncated = text[:18000]
    try:
        client = _client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"DOCUMENT TEXT:\n---\n{truncated}\n---"},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=4000,
        )
        _log_usage(response.usage, "schedule_a_ai_text", org_id)
        body = response.choices[0].message.content or "{}"
        data = _parse_response(body)
    except Exception as e:
        logger.error(f"AI text extraction failed: {e}")
        return {"rows": [], "header": {}, "method": "ai_text", "warnings": [f"AI extraction failed: {e}"]}

    raw_rows = data.get("rows") or []
    rows = [r for r in (_normalize_row(r) for r in raw_rows) if r]
    return {
        "rows": rows,
        "header": data.get("header") or {},
        "method": "ai_text",
        "warnings": [],
    }


def _images_to_payload(images: List[bytes]) -> List[Dict[str, Any]]:
    payload: List[Dict[str, Any]] = [
        {"type": "text", "text": "Extract all songs from these Schedule A pages."}
    ]
    for img in images[:6]:
        b64 = base64.b64encode(img).decode("ascii")
        payload.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"},
            }
        )
    return payload


def extract_from_images(images: List[bytes], org_id: Optional[int] = None) -> Dict[str, Any]:
    """Run the AI extractor against one or more page images (vision OCR)."""
    if not images:
        return {"rows": [], "header": {}, "method": "ai_vision", "warnings": ["No image data"]}

    try:
        client = _client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _images_to_payload(images)},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=4000,
        )
        _log_usage(response.usage, "schedule_a_ai_vision", org_id)
        body = response.choices[0].message.content or "{}"
        data = _parse_response(body)
    except Exception as e:
        logger.error(f"AI vision extraction failed: {e}")
        return {"rows": [], "header": {}, "method": "ai_vision", "warnings": [f"AI vision failed: {e}"]}

    raw_rows = data.get("rows") or []
    rows = [r for r in (_normalize_row(r) for r in raw_rows) if r]
    return {
        "rows": rows,
        "header": data.get("header") or {},
        "method": "ai_vision",
        "warnings": [],
    }


def render_pdf_pages_to_png(content: bytes, max_pages: int = 6) -> List[bytes]:
    """Render PDF pages to PNG bytes for vision extraction.

    Uses pdfplumber (which uses pdfminer + Wand/PIL fallbacks) when available.
    Returns an empty list if rendering is not possible.
    """
    try:
        import pdfplumber
    except Exception:
        return []
    images: List[bytes] = []
    try:
        with pdfplumber.open(BytesIO(content)) as pdf:
            for page in pdf.pages[:max_pages]:
                try:
                    img = page.to_image(resolution=150)
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    images.append(buf.getvalue())
                except Exception as e:
                    logger.warning(f"Failed to render PDF page: {e}")
    except Exception as e:
        logger.warning(f"Failed to open PDF for rendering: {e}")
    return images
