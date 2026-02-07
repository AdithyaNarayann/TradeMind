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
from ..db.mysql import get_conn

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
    return {"closed": True, "session_id": session_id}
