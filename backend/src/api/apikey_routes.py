"""
API Key management routes.
Sellers can generate, list, and revoke API keys for programmatic access.
"""
import secrets
from fastapi import APIRouter, Depends, HTTPException
import aiomysql

from ..db.mysql import get_conn
from .auth_routes import get_current_user

router = APIRouter(prefix="/api/v1/api-keys", tags=["API Keys"])


def _generate_key() -> str:
    """Generate a 48-char hex API key prefixed with 'tm_'."""
    return "tm_" + secrets.token_hex(24)


@router.post("")
async def create_api_key(body: dict = None, user=Depends(get_current_user)):
    """Generate a new API key for the authenticated user."""
    label = (body or {}).get("label", "Default")
    key = _generate_key()
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO api_keys (user_id, api_key, label) VALUES (%s, %s, %s)",
                (user["id"], key, label),
            )
            key_id = cur.lastrowid
    return {"id": key_id, "api_key": key, "label": label}


@router.get("")
async def list_api_keys(user=Depends(get_current_user)):
    """List all API keys for the authenticated user (key is masked)."""
    async with get_conn() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """SELECT id, api_key, label, created_at, last_used_at, is_active
                   FROM api_keys WHERE user_id = %s ORDER BY created_at DESC""",
                (user["id"],),
            )
            rows = await cur.fetchall()
    # Return masked keys for security — only show last 8 chars
    for row in rows:
        full = row["api_key"]
        row["api_key_masked"] = full[:3] + "•" * (len(full) - 11) + full[-8:]
        row["api_key_full"] = full  # frontend needs it for copy
        row["created_at"] = str(row["created_at"]) if row["created_at"] else None
        row["last_used_at"] = str(row["last_used_at"]) if row["last_used_at"] else None
    return {"keys": rows}


@router.delete("/{key_id}")
async def revoke_api_key(key_id: int, user=Depends(get_current_user)):
    """Revoke (delete) an API key."""
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM api_keys WHERE id = %s AND user_id = %s",
                (key_id, user["id"]),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="API key not found")
    return {"deleted": True}
