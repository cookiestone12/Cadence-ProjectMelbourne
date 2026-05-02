from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import os
import json
import logging

from ..models import get_db, User, OrganizationMember
from ..utils.auth import get_current_user
from ..services import assistant_tools

logger = logging.getLogger("cadence")
router = APIRouter(prefix="/api/assistant", tags=["AI Assistant"])

MAX_TOOL_ITERATIONS = 5
MODEL_NAME = "gpt-4o-mini"

# ---------------------------------------------------------------------------
# Knowledge base — loaded once at module import.
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _read_kb(filename: str) -> str:
    path = _DATA_DIR / filename
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("Assistant KB file missing: %s", path)
        return ""


APP_GUIDE = _read_kb("assistant_app_guide.md")
INDUSTRY_KB = _read_kb("assistant_industry_knowledge.md")

BASE_SYSTEM_PROMPT = (
    APP_GUIDE
    + "\n\n---\n\n"
    + INDUSTRY_KB
    + "\n\n---\n\nWhen tools are available, you may call them to answer "
      "questions about the user's actual data. Always pass real values from "
      "the page-context block when relevant. For write actions, propose them "
      "via the matching tool and explain in the chat what the user is about "
      "to confirm — do not pretend the action is already done."
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str
    content: str


class PageContext(BaseModel):
    page: Optional[str] = None
    path: Optional[str] = None
    song_id: Optional[int] = None
    creator_id: Optional[int] = None
    placement_id: Optional[int] = None
    contract_id: Optional[int] = None
    work_id: Optional[int] = None
    release_id: Optional[int] = None


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context: Optional[PageContext] = None


class ConfirmActionResponse(BaseModel):
    success: bool
    kind: str
    entity_type: str
    entity_id: int
    entity_name: Optional[str] = None
    result: dict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_role_context(current_user: User, membership) -> str:
    user_role = membership.role if membership else "MEMBER"
    if user_role == "CLIENT":
        return ("\n\nThis user is a CLIENT. They can only access: Client "
                "Portal, Support, and Settings. Do not reference other pages "
                "they cannot access. Most write tools are still allowed but "
                "scope every result to their own catalog.")
    if getattr(current_user, "is_super_admin", False):
        return ("\n\nThis user is a Super Admin. They have access to all "
                "features including the Master Admin dashboard.")
    return ""


def _build_page_context_block(ctx: Optional[PageContext]) -> str:
    if ctx is None:
        return ""
    bits = []
    if ctx.page:
        bits.append(f"page={ctx.page}")
    if ctx.path:
        bits.append(f"path={ctx.path}")
    if ctx.song_id is not None:
        bits.append(f"song_id={ctx.song_id}")
    if ctx.creator_id is not None:
        bits.append(f"creator_id={ctx.creator_id}")
    if ctx.placement_id is not None:
        bits.append(f"placement_id={ctx.placement_id}")
    if ctx.contract_id is not None:
        bits.append(f"contract_id={ctx.contract_id}")
    if ctx.work_id is not None:
        bits.append(f"work_id={ctx.work_id}")
    if ctx.release_id is not None:
        bits.append(f"release_id={ctx.release_id}")
    if not bits:
        return ""
    return ("\n\nCURRENT PAGE CONTEXT (the user is currently looking at this; "
            "use these ids when relevant):\n  " + ", ".join(bits))


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, default=str)}\n\n"


def _sum_usage(running: dict, usage_obj) -> None:
    if not usage_obj:
        return
    try:
        running["input"] += int(getattr(usage_obj, "prompt_tokens", 0) or 0)
        running["output"] += int(getattr(usage_obj, "completion_tokens", 0) or 0)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/chat",
    summary="Send a message to the AI assistant",
    description=(
        "Sends a chat turn to the in-app assistant (OpenAI-backed) with the "
        "calling user's org context, plus an optional page-context block. "
        "Streams SSE events: `tool_running` (a tool is executing), "
        "`tool_result` (a small summary), `proposed_action` (a write tool "
        "produced an unconfirmed mutation), `content` (chunks of the final "
        "reply), `error`, and `done`.\n\n"
        "**Body:** `{ messages: [{role, content}], context?: {page?, path?, "
        "song_id?, creator_id?, placement_id?, contract_id?} }`.\n"
        "**Auth:** Bearer JWT."
    ),
)
async def assistant_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
    base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")

    if not api_key:
        raise HTTPException(status_code=503, detail="AI service not configured")

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    org_id = membership.organization_id if membership else None

    system_prompt = (
        BASE_SYSTEM_PROMPT
        + _build_role_context(current_user, membership)
        + _build_page_context_block(request.context)
    )

    conversation: list[dict] = [{"role": "system", "content": system_prompt}]
    for msg in request.messages[-20:]:
        if msg.role in ("user", "assistant"):
            conversation.append({"role": msg.role, "content": msg.content})

    # Snapshot user/org so the streaming generator doesn't keep stale ORM
    # references after the request scope.
    user_id = current_user.id

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
    except Exception as e:
        logger.error(f"Assistant client init error: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialise AI client")

    async def generate():
        usage_running = {"input": 0, "output": 0}
        try:
            iterations = 0
            while iterations < MAX_TOOL_ITERATIONS:
                iterations += 1
                # Step 1 — model decides whether to call a tool. Non-stream
                # so we get tool_calls in one piece.
                resp = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=conversation,
                    tools=assistant_tools.TOOL_SCHEMAS,
                    tool_choice="auto",
                    temperature=0.3,
                    max_tokens=600,
                )
                _sum_usage(usage_running, getattr(resp, "usage", None))
                msg = resp.choices[0].message
                tool_calls = msg.tool_calls or []

                if not tool_calls:
                    # Final text answer — stream it as content chunks.
                    final_text = msg.content or ""
                    if final_text:
                        # Chunk by ~24 chars to simulate streaming output;
                        # one round-trip would also be fine but the chunked
                        # version lets the UI grow the bubble incrementally.
                        chunk = 24
                        for i in range(0, len(final_text), chunk):
                            yield _sse({"content": final_text[i:i + chunk]})
                    break

                # Append the assistant's tool_call message back into the conv
                conversation.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                })

                for tc in tool_calls:
                    name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}

                    yield _sse({"tool_running": {"name": name}})

                    result = assistant_tools.dispatch_tool(
                        name, args,
                        db=db, org_id=org_id, user_id=user_id,
                    )

                    # Surface a compact tool_result event for the UI
                    if "proposed_action" in result:
                        yield _sse({
                            "proposed_action": result["proposed_action"],
                        })
                    else:
                        # Trim large arrays before sending to the UI; the
                        # full result still goes back to the model below.
                        ui_result = result
                        if isinstance(result, dict) and "results" in result:
                            ui_result = {
                                "count": result.get("count"),
                                "preview": (result.get("results") or [])[:3],
                            }
                        yield _sse({
                            "tool_result": {"name": name, "data": ui_result},
                        })

                    conversation.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, default=str),
                    })
                # loop again so the model can use the tool output
            else:
                yield _sse({
                    "content": (
                        "\n\n(I hit the tool-call limit while working on this. "
                        "Please rephrase or break the request into smaller "
                        "steps.)"
                    )
                })

            # Log usage once at the end
            try:
                if usage_running["input"] or usage_running["output"]:
                    from ..services.ai_usage import log_ai_usage
                    log_ai_usage(
                        db=db,
                        feature="assistant_chat",
                        model=MODEL_NAME,
                        input_tokens=usage_running["input"],
                        output_tokens=usage_running["output"],
                        org_id=org_id,
                    )
            except Exception as e:
                logger.warning(f"Failed to log assistant AI usage: {e}")

            yield _sse({"done": True})

        except Exception as e:
            logger.exception("Assistant streaming error: %s", e)
            yield _sse({"error": "Something went wrong. Please try again."})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Confirm / cancel proposed actions
# ---------------------------------------------------------------------------

@router.post(
    "/actions/{action_id}/confirm",
    response_model=ConfirmActionResponse,
    summary="Confirm a proposed assistant action",
    description=(
        "Executes a write action that the assistant previously proposed via "
        "a tool call. The action_id is the uuid the assistant returned in a "
        "`proposed_action` SSE event. Mutations and an audit-log entry "
        "(tagged `source=\"assistant\"`) are written in a single transaction. "
        "Proposed actions expire after 10 minutes."
    ),
)
def confirm_action(
    action_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = assistant_tools.execute_proposed_action(
            action_id, db=db, user=current_user,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.exception("Assistant confirm failed: %s", e)
        raise HTTPException(status_code=500,
                            detail="Failed to execute the proposed action.")

    return ConfirmActionResponse(
        success=True,
        kind=result["kind"],
        entity_type=result["entity_type"],
        entity_id=result["entity_id"],
        entity_name=result.get("entity_name"),
        result=result["result"],
    )


@router.delete(
    "/actions/{action_id}",
    summary="Cancel a proposed assistant action",
    description=(
        "Drops a proposed action from the in-memory store without executing "
        "it. Always returns 200 — cancelling a missing or expired action is "
        "a no-op."
    ),
)
def cancel_action(
    action_id: str,
    current_user: User = Depends(get_current_user),
):
    pa = assistant_tools.get_proposed_action(action_id)
    if pa and pa.user_id != current_user.id and not getattr(current_user, "is_super_admin", False):
        raise HTTPException(status_code=403,
                            detail="This action belongs to a different user.")
    assistant_tools.remove_proposed_action(action_id)
    return {"success": True}
