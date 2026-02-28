"""
Chat Session persistence routes — MySQL-backed, per-user chat history.

POST   /api/v1/chat-sessions                      → create / start a chat session
GET    /api/v1/chat-sessions                       → list user's chat sessions
GET    /api/v1/chat-sessions/{id}                  → get single session + messages
POST   /api/v1/chat-sessions/{id}/messages         → save a round (user msg + bot reply)
PUT    /api/v1/chat-sessions/{id}/close            → close session with final outcome
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from .auth_routes import get_current_user
from ...infrastructure.database.session import get_conn
from .email_routes import get_user_email_settings, send_notification_email
from ...services.email_service import template_deal_notification, template_new_session

import asyncio
import structlog
_email_logger = structlog.get_logger("email_notifications")

router = APIRouter(prefix="/api/v1/chat-sessions", tags=["Chat Sessions"])


# ── Models ─────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    product_name: str
    mode: str = "MAX_PROFIT"
    base_price: float
    cost_price: float
    min_price: float
    max_rounds: int = 10
    negotiate_session_id: Optional[str] = None  # UUID from negotiation engine

class SaveMessageRequest(BaseModel):
    round_number: int = 0
    user_message: Optional[str] = None
    bot_reply: Optional[str] = None
    offered_price: Optional[float] = None
    counter_price: Optional[float] = None
    decision: Optional[str] = None  # accept / counter / reject / chat

class CloseSessionRequest(BaseModel):
    status: str                         # accepted / rejected / expired / walked_away
    final_price: Optional[float] = None
    final_decision: str                 # accepted / rejected / expired / walked_away
    deal_closed: bool = False
    buyer_last_offer: Optional[float] = None
    seller_last_offer: Optional[float] = None
    rounds_used: int = 0

class CallbackRequest(BaseModel):
    session_id: int
    phone_number: str
    product_name: Optional[str] = None
    negotiation_status: Optional[str] = None
    final_price: Optional[float] = None


# ── Helpers ────────────────────────────────────────────────────────

def _row_to_session(row, cols):
    d = dict(zip(cols, row))
    for k in ("created_at", "closed_at"):
        if d.get(k) and isinstance(d[k], datetime):
            d[k] = d[k].isoformat()
    # Convert Decimals to float
    for k in ("base_price", "cost_price", "min_price", "final_price",
              "buyer_last_offer", "seller_last_offer"):
        if d.get(k) is not None:
            d[k] = float(d[k])
    d["deal_closed"] = bool(d.get("deal_closed"))
    return d

def _row_to_message(row, cols):
    d = dict(zip(cols, row))
    if d.get("created_at") and isinstance(d["created_at"], datetime):
        d["created_at"] = d["created_at"].isoformat()
    for k in ("offered_price", "counter_price"):
        if d.get(k) is not None:
            d[k] = float(d[k])
    return d


# ── Routes ─────────────────────────────────────────────────────────

@router.post("")
async def start_session(body: StartSessionRequest, user=Depends(get_current_user)):
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """INSERT INTO chat_sessions
                   (user_id, product_name, mode, base_price, cost_price,
                    min_price, max_rounds)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (user["id"], body.product_name, body.mode,
                 body.base_price, body.cost_price, body.min_price,
                 body.max_rounds),
            )
            session_id = cur.lastrowid
            await conn.commit()

    # ── Fire new-session email (non-blocking) ──
    async def _send_new_session_email():
        try:
            settings = await get_user_email_settings(user["id"])
            if settings and settings.get("notifications_enabled") and settings.get("notify_on_new_session"):
                subject, html = template_new_session(
                    seller_name=user["full_name"],
                    product_name=body.product_name,
                    session_id=str(session_id),
                )
                await send_notification_email(user["id"], subject, html)
        except Exception as e:
            _email_logger.error("new_session_email_failed", error=str(e))
    asyncio.create_task(_send_new_session_email())

    return {"id": session_id, "status": "active"}


@router.get("")
async def list_sessions(user=Depends(get_current_user)):
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT id, product_name, mode, base_price, cost_price,
                          min_price, max_rounds, rounds_used, status,
                          final_price, final_decision, deal_closed,
                          buyer_last_offer, seller_last_offer,
                          created_at, closed_at
                   FROM chat_sessions
                   WHERE user_id = %s
                   ORDER BY created_at DESC""",
                (user["id"],),
            )
            cols = [d[0] for d in cur.description]
            rows = await cur.fetchall()
    return [_row_to_session(r, cols) for r in rows]


# ── Callback request endpoints (MUST be before /{session_id}) ─────

@router.post("/callback-request")
async def create_callback_request(body: CallbackRequest, user=Depends(get_current_user)):
    """Save a callback/phone request when buyer wants to schedule a professional call."""
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            # Verify session ownership
            await cur.execute(
                "SELECT id FROM chat_sessions WHERE id = %s AND user_id = %s",
                (body.session_id, user["id"]),
            )
            if not await cur.fetchone():
                raise HTTPException(404, "Session not found")

            await cur.execute(
                """INSERT INTO callback_requests
                   (user_id, session_id, phone_number, product_name,
                    negotiation_status, final_price)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (user["id"], body.session_id, body.phone_number,
                 body.product_name, body.negotiation_status, body.final_price),
            )
            req_id = cur.lastrowid
            await conn.commit()
    return {"id": req_id, "saved": True, "message": "Callback request saved successfully"}


@router.get("/callback-requests")
async def list_callback_requests(user=Depends(get_current_user)):
    """List all callback requests for the current user."""
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT cr.id, cr.session_id, cr.phone_number, cr.product_name,
                          cr.status, cr.negotiation_status, cr.final_price, cr.created_at
                   FROM callback_requests cr
                   WHERE cr.user_id = %s
                   ORDER BY cr.created_at DESC""",
                (user["id"],),
            )
            cols = [d[0] for d in cur.description]
            rows = await cur.fetchall()
            results = []
            for row in rows:
                d = dict(zip(cols, row))
                if d.get("created_at") and isinstance(d["created_at"], datetime):
                    d["created_at"] = d["created_at"].isoformat()
                if d.get("final_price") is not None:
                    d["final_price"] = float(d["final_price"])
                results.append(d)
    return results


@router.get("/{session_id}")
async def get_session(session_id: int, user=Depends(get_current_user)):
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            # Session
            await cur.execute(
                """SELECT id, product_name, mode, base_price, cost_price,
                          min_price, max_rounds, rounds_used, status,
                          final_price, final_decision, deal_closed,
                          buyer_last_offer, seller_last_offer,
                          created_at, closed_at
                   FROM chat_sessions
                   WHERE id = %s AND user_id = %s""",
                (session_id, user["id"]),
            )
            cols = [d[0] for d in cur.description]
            row = await cur.fetchone()
            if not row:
                raise HTTPException(404, "Session not found")
            session = _row_to_session(row, cols)

            # Messages
            await cur.execute(
                """SELECT id, round_number, user_message, bot_reply,
                          offered_price, counter_price, decision, created_at
                   FROM chat_messages
                   WHERE session_id = %s AND user_id = %s
                   ORDER BY round_number, id""",
                (session_id, user["id"]),
            )
            msg_cols = [d[0] for d in cur.description]
            msg_rows = await cur.fetchall()
            session["messages"] = [_row_to_message(r, msg_cols) for r in msg_rows]

            # Include callback info if any
            await cur.execute(
                """SELECT phone_number, product_name AS cb_product, status AS cb_status,
                          negotiation_status, final_price AS cb_final_price, created_at AS cb_created_at
                   FROM callback_requests
                   WHERE session_id = %s AND user_id = %s
                   ORDER BY created_at DESC LIMIT 1""",
                (session_id, user["id"]),
            )
            cb_cols = [d[0] for d in cur.description]
            cb_row = await cur.fetchone()
            if cb_row:
                cb = dict(zip(cb_cols, cb_row))
                if cb.get("cb_created_at") and isinstance(cb["cb_created_at"], datetime):
                    cb["cb_created_at"] = cb["cb_created_at"].isoformat()
                if cb.get("cb_final_price") is not None:
                    cb["cb_final_price"] = float(cb["cb_final_price"])
                session["callback"] = cb
            else:
                session["callback"] = None

    return session


@router.post("/{session_id}/messages")
async def save_message(session_id: int, body: SaveMessageRequest, user=Depends(get_current_user)):
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            # Verify ownership
            await cur.execute(
                "SELECT id FROM chat_sessions WHERE id = %s AND user_id = %s",
                (session_id, user["id"]),
            )
            if not await cur.fetchone():
                raise HTTPException(404, "Session not found")

            await cur.execute(
                """INSERT INTO chat_messages
                   (session_id, user_id, round_number, user_message,
                    bot_reply, offered_price, counter_price, decision)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (session_id, user["id"], body.round_number,
                 body.user_message, body.bot_reply,
                 body.offered_price, body.counter_price, body.decision),
            )
            msg_id = cur.lastrowid

            # Update rounds_used on session
            await cur.execute(
                """UPDATE chat_sessions
                   SET rounds_used = GREATEST(rounds_used, %s)
                   WHERE id = %s""",
                (body.round_number, session_id),
            )
            await conn.commit()
    return {"id": msg_id, "saved": True}


@router.put("/{session_id}/close")
async def close_session(session_id: int, body: CloseSessionRequest, user=Depends(get_current_user)):
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id FROM chat_sessions WHERE id = %s AND user_id = %s",
                (session_id, user["id"]),
            )
            if not await cur.fetchone():
                raise HTTPException(404, "Session not found")

            await cur.execute(
                """UPDATE chat_sessions
                   SET status = %s,
                       final_price = %s,
                       final_decision = %s,
                       deal_closed = %s,
                       buyer_last_offer = %s,
                       seller_last_offer = %s,
                       rounds_used = %s,
                       closed_at = NOW()
                   WHERE id = %s""",
                (body.status, body.final_price, body.final_decision,
                 body.deal_closed, body.buyer_last_offer,
                 body.seller_last_offer, body.rounds_used, session_id),
            )
            await conn.commit()

    # ── Fire deal-outcome email (non-blocking) ──
    if body.status in ("accepted", "rejected"):
        async def _send_deal_email():
            try:
                settings = await get_user_email_settings(user["id"])
                if settings and settings.get("notifications_enabled") and settings.get("notify_on_deal"):
                    # Fetch base_price from the session
                    async with get_conn() as conn2:
                        async with conn2.cursor() as cur2:
                            await cur2.execute(
                                "SELECT product_name, base_price FROM chat_sessions WHERE id = %s",
                                (session_id,),
                            )
                            row = await cur2.fetchone()
                    product_name = row[0] if row else "Unknown"
                    base_price = float(row[1]) if row and row[1] else 0.0
                    subject, html = template_deal_notification(
                        seller_name=user["full_name"],
                        product_name=product_name,
                        outcome=body.status,
                        final_price=body.final_price or 0.0,
                        original_price=base_price,
                        rounds=body.rounds_used,
                        session_id=str(session_id),
                    )
                    await send_notification_email(user["id"], subject, html)
            except Exception as e:
                _email_logger.error("deal_email_failed", error=str(e))
        asyncio.create_task(_send_deal_email())

    return {"closed": True, "session_id": session_id}


# ── Dashboard endpoints ────────────────────────────────────────────

@router.get("/dashboard/summary")
async def dashboard_summary(user=Depends(get_current_user)):
    """Real-time dashboard stats for the seller."""
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            uid = user["id"]
            # Overall counts
            await cur.execute(
                """SELECT
                     COUNT(*) AS total,
                     SUM(status = 'accepted') AS accepted,
                     SUM(status = 'rejected') AS rejected,
                     SUM(status = 'active')   AS active,
                     SUM(status = 'expired')  AS expired,
                     SUM(status = 'walked_away') AS walked_away,
                     COALESCE(SUM(CASE WHEN deal_closed THEN final_price END), 0) AS total_revenue,
                     COALESCE(AVG(CASE WHEN deal_closed THEN final_price END), 0) AS avg_deal_price,
                     COALESCE(AVG(CASE WHEN deal_closed THEN rounds_used END), 0) AS avg_rounds,
                     COALESCE(AVG(base_price), 0) AS avg_base_price,
                     COALESCE(MAX(CASE WHEN deal_closed THEN final_price END), 0) AS best_deal,
                     COALESCE(MIN(CASE WHEN deal_closed THEN final_price END), 0) AS worst_deal
                   FROM chat_sessions WHERE user_id = %s""",
                (uid,),
            )
            cols = [d[0] for d in cur.description]
            row = await cur.fetchone()
            summary = dict(zip(cols, row))
            # Convert Decimals
            for k in summary:
                if summary[k] is not None:
                    summary[k] = float(summary[k])
                else:
                    summary[k] = 0

            # Recent closed deals (last 20)
            await cur.execute(
                """SELECT cs.id, cs.product_name, cs.status, cs.base_price, cs.final_price,
                          cs.rounds_used, cs.final_decision, cs.deal_closed,
                          cs.buyer_last_offer, cs.seller_last_offer,
                          cs.created_at, cs.closed_at,
                          cr.phone_number AS callback_phone,
                          cr.created_at AS callback_requested_at
                   FROM chat_sessions cs
                   LEFT JOIN callback_requests cr ON cr.session_id = cs.id AND cr.user_id = cs.user_id
                   WHERE cs.user_id = %s AND cs.status != 'active'
                   ORDER BY cs.closed_at DESC LIMIT 20""",
                (uid,),
            )
            cols2 = [d[0] for d in cur.description]
            rows2 = await cur.fetchall()
            closed_sessions = []
            for r in rows2:
                s = _row_to_session(r, cols2)
                # Ensure callback fields are serialized
                if s.get("callback_requested_at") and isinstance(s["callback_requested_at"], datetime):
                    s["callback_requested_at"] = s["callback_requested_at"].isoformat()
                closed_sessions.append(s)

            # Active sessions
            await cur.execute(
                """SELECT id, product_name, status, base_price, rounds_used,
                          buyer_last_offer, seller_last_offer,
                          max_rounds, created_at
                   FROM chat_sessions
                   WHERE user_id = %s AND status = 'active'
                   ORDER BY created_at DESC""",
                (uid,),
            )
            cols3 = [d[0] for d in cur.description]
            rows3 = await cur.fetchall()
            active_sessions = [_row_to_session(r, cols3) for r in rows3]

    return {
        "summary": summary,
        "closed_sessions": closed_sessions,
        "active_sessions": active_sessions,
    }


@router.get("/{session_id}/export")
async def export_session(session_id: int, user=Depends(get_current_user)):
    """Export full session details + messages for download."""
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT id, product_name, mode, base_price, cost_price,
                          min_price, max_rounds, rounds_used, status,
                          final_price, final_decision, deal_closed,
                          buyer_last_offer, seller_last_offer,
                          created_at, closed_at
                   FROM chat_sessions
                   WHERE id = %s AND user_id = %s""",
                (session_id, user["id"]),
            )
            cols = [d[0] for d in cur.description]
            row = await cur.fetchone()
            if not row:
                raise HTTPException(404, "Session not found")
            session = _row_to_session(row, cols)

            await cur.execute(
                """SELECT round_number, user_message, bot_reply,
                          offered_price, counter_price, decision, created_at
                   FROM chat_messages
                   WHERE session_id = %s AND user_id = %s
                   ORDER BY round_number, id""",
                (session_id, user["id"]),
            )
            msg_cols = [d[0] for d in cur.description]
            msg_rows = await cur.fetchall()
            session["messages"] = [_row_to_message(r, msg_cols) for r in msg_rows]

    return session
