"""
Product CRUD routes — MySQL-backed, per-user products.

GET    /api/v1/products          → list current user's products
POST   /api/v1/products          → create product
PUT    /api/v1/products/{id}     → update product
DELETE /api/v1/products/{id}     → delete product
POST   /api/v1/products/import   → bulk CSV import
"""
import aiomysql
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime

from .auth_routes import get_current_user
from ...infrastructure.database.session import get_conn

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


# ── Models ─────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str
    base_price: float
    cost_price: float
    min_acceptable_price: Optional[float] = None
    max_loss_percent: float = 0
    mode: str = "MAX_PROFIT"
    max_rounds: int = 10
    category: str = "General"

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Product name is required")
        return v.strip()

    @field_validator("base_price", "cost_price")
    @classmethod
    def price_positive(cls, v):
        if v <= 0:
            raise ValueError("Price must be positive")
        return v


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    base_price: Optional[float] = None
    cost_price: Optional[float] = None
    min_acceptable_price: Optional[float] = None
    max_loss_percent: Optional[float] = None
    mode: Optional[str] = None
    max_rounds: Optional[int] = None
    category: Optional[str] = None
    status: Optional[str] = None


class ProductOut(BaseModel):
    id: int
    user_id: int
    name: str
    base_price: float
    cost_price: float
    min_acceptable_price: float
    max_loss_percent: float
    mode: str
    max_rounds: int
    category: str
    status: str
    stats: dict
    created_at: str
    updated_at: str


class CSVImportResult(BaseModel):
    created: int
    errors: List[str]


# ── Helpers ────────────────────────────────────────────────────────

def _row_to_product(row: dict) -> dict:
    """Convert a DB row to a ProductOut-compatible dict."""
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "name": row["name"],
        "base_price": float(row["base_price"]),
        "cost_price": float(row["cost_price"]),
        "min_acceptable_price": float(row["min_acceptable_price"]),
        "max_loss_percent": float(row["max_loss_percent"]),
        "mode": row["mode"],
        "max_rounds": row["max_rounds"],
        "category": row["category"],
        "status": row["status"],
        "stats": {
            "totalSessions": row["total_sessions"],
            "acceptedDeals": row["accepted_deals"],
            "avgMargin": float(row["avg_margin"]),
            "revenue": float(row["revenue"]),
        },
        "created_at": row["created_at"].isoformat() if isinstance(row["created_at"], datetime) else str(row["created_at"]),
        "updated_at": row["updated_at"].isoformat() if isinstance(row["updated_at"], datetime) else str(row["updated_at"]),
    }


# ── Routes ─────────────────────────────────────────────────────────

@router.get("", response_model=List[ProductOut])
async def list_products(user=Depends(get_current_user)):
    """Get all products for the current user."""
    async with get_conn() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT * FROM products WHERE user_id = %s ORDER BY created_at DESC",
                (user["id"],),
            )
            rows = await cur.fetchall()
    return [_row_to_product(r) for r in rows]


@router.post("", response_model=ProductOut, status_code=201)
async def create_product_route(body: ProductCreate, user=Depends(get_current_user)):
    """Create a new product for the current user."""
    min_price = body.min_acceptable_price if body.min_acceptable_price is not None else body.cost_price

    async with get_conn() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """INSERT INTO products 
                   (user_id, name, base_price, cost_price, min_acceptable_price, 
                    max_loss_percent, mode, max_rounds, category)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (user["id"], body.name, body.base_price, body.cost_price,
                 min_price, body.max_loss_percent, body.mode, body.max_rounds, body.category),
            )
            product_id = cur.lastrowid

            await cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
            row = await cur.fetchone()

    return _row_to_product(row)


@router.put("/{product_id}", response_model=ProductOut)
async def update_product_route(product_id: int, body: ProductUpdate, user=Depends(get_current_user)):
    """Update a product (only if owned by current user)."""
    # Build dynamic SET clause from non-None fields
    field_map = {
        "name": "name", "base_price": "base_price", "cost_price": "cost_price",
        "min_acceptable_price": "min_acceptable_price", "max_loss_percent": "max_loss_percent",
        "mode": "mode", "max_rounds": "max_rounds", "category": "category", "status": "status",
    }
    updates = {}
    for py_field, db_col in field_map.items():
        val = getattr(body, py_field)
        if val is not None:
            updates[db_col] = val

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{col} = %s" for col in updates.keys())
    values = list(updates.values()) + [product_id, user["id"]]

    async with get_conn() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                f"UPDATE products SET {set_clause} WHERE id = %s AND user_id = %s",
                values,
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Product not found")

            await cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
            row = await cur.fetchone()

    return _row_to_product(row)


@router.delete("/{product_id}", status_code=204)
async def delete_product_route(product_id: int, user=Depends(get_current_user)):
    """Delete a product (only if owned by current user)."""
    async with get_conn() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "DELETE FROM products WHERE id = %s AND user_id = %s",
                (product_id, user["id"]),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Product not found")
    return None


@router.post("/import", response_model=CSVImportResult)
async def import_csv(body: dict, user=Depends(get_current_user)):
    """Bulk import products from CSV text. Expects { csv_text: "..." }."""
    csv_text = body.get("csv_text", "")
    if not csv_text:
        raise HTTPException(status_code=400, detail="csv_text is required")

    lines = csv_text.strip().split("\n")
    if len(lines) < 2:
        return CSVImportResult(created=0, errors=["CSV must have a header row and at least one data row."])

    header = [h.strip().lower() for h in lines[0].split(",")]
    name_idx = header.index("name") if "name" in header else -1
    base_idx = next((i for i, h in enumerate(header) if h in ("baseprice", "base_price", "base price")), -1)
    cost_idx = next((i for i, h in enumerate(header) if h in ("costprice", "cost_price", "cost price")), -1)
    cat_idx = next((i for i, h in enumerate(header) if h == "category"), -1)

    if name_idx == -1 or base_idx == -1 or cost_idx == -1:
        return CSVImportResult(created=0, errors=["CSV must contain columns: name, basePrice, costPrice"])

    created = 0
    errors = []

    async with get_conn() as conn:
        async with conn.cursor() as cur:
            for i, line in enumerate(lines[1:], start=2):
                cols = [c.strip() for c in line.split(",")]
                try:
                    name = cols[name_idx]
                    base_price = float(cols[base_idx])
                    cost_price = float(cols[cost_idx])
                    category = cols[cat_idx] if cat_idx != -1 and cat_idx < len(cols) else "General"

                    if not name:
                        errors.append(f"Row {i}: missing name"); continue
                    if base_price <= 0:
                        errors.append(f"Row {i}: invalid base price"); continue
                    if cost_price <= 0:
                        errors.append(f"Row {i}: invalid cost price"); continue
                    if cost_price >= base_price:
                        errors.append(f"Row {i}: cost price must be less than base price"); continue

                    await cur.execute(
                        """INSERT INTO products 
                           (user_id, name, base_price, cost_price, min_acceptable_price, category)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (user["id"], name, base_price, cost_price, cost_price, category),
                    )
                    created += 1
                except (ValueError, IndexError) as e:
                    errors.append(f"Row {i}: {str(e)}")

    return CSVImportResult(created=created, errors=errors)


@router.get("/{product_id}/stats")
async def get_product_stats(product_id: int, user=Depends(get_current_user)):
    """Compute live analytics for a product from chat_sessions data."""
    async with get_conn() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # Verify product ownership
            await cur.execute(
                "SELECT id, name, base_price, cost_price FROM products WHERE id = %s AND user_id = %s",
                (product_id, user["id"]),
            )
            product = await cur.fetchone()
            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            product_name = product["name"]

            # Aggregate stats from chat_sessions for this product
            await cur.execute(
                """SELECT
                       COUNT(*)                                              AS total_sessions,
                       SUM(CASE WHEN deal_closed = 1 THEN 1 ELSE 0 END)     AS accepted_deals,
                       SUM(CASE WHEN deal_closed = 0 AND status != 'active'
                                THEN 1 ELSE 0 END)                          AS rejected_deals,
                       SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END)   AS active_sessions,
                       AVG(rounds_used)                                      AS avg_rounds,
                       AVG(CASE WHEN deal_closed = 1 THEN final_price END)   AS avg_final_price,
                       MIN(CASE WHEN deal_closed = 1 THEN final_price END)   AS min_deal_price,
                       MAX(CASE WHEN deal_closed = 1 THEN final_price END)   AS max_deal_price,
                       SUM(CASE WHEN deal_closed = 1 THEN final_price ELSE 0 END) AS total_revenue,
                       AVG(CASE WHEN deal_closed = 1 AND final_price IS NOT NULL
                                THEN ((final_price - %s) / final_price * 100)
                           END)                                              AS avg_margin,
                       AVG(CASE WHEN deal_closed = 1 THEN buyer_last_offer END) AS avg_buyer_offer,
                       AVG(CASE WHEN deal_closed = 1 THEN seller_last_offer END) AS avg_seller_offer
                   FROM chat_sessions
                   WHERE user_id = %s AND product_name = %s""",
                (float(product["cost_price"]), user["id"], product_name),
            )
            row = await cur.fetchone()

            # Recent sessions (last 10)
            await cur.execute(
                """SELECT id, status, deal_closed, final_price, rounds_used,
                          buyer_last_offer, seller_last_offer, created_at, closed_at
                   FROM chat_sessions
                   WHERE user_id = %s AND product_name = %s
                   ORDER BY created_at DESC LIMIT 10""",
                (user["id"], product_name),
            )
            recent_rows = await cur.fetchall()

    total = int(row["total_sessions"] or 0)
    deals = int(row["accepted_deals"] or 0)
    rejected = int(row["rejected_deals"] or 0)

    recent = []
    for r in recent_rows:
        recent.append({
            "id": r["id"],
            "status": r["status"],
            "deal_closed": bool(r["deal_closed"]),
            "final_price": float(r["final_price"]) if r["final_price"] else None,
            "rounds_used": r["rounds_used"],
            "buyer_last_offer": float(r["buyer_last_offer"]) if r["buyer_last_offer"] else None,
            "seller_last_offer": float(r["seller_last_offer"]) if r["seller_last_offer"] else None,
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "closed_at": r["closed_at"].isoformat() if r["closed_at"] else None,
        })

    return {
        "product_id": product_id,
        "product_name": product_name,
        "total_sessions": total,
        "accepted_deals": deals,
        "rejected_deals": rejected,
        "active_sessions": int(row["active_sessions"] or 0),
        "accept_rate": round(deals / total * 100, 1) if total > 0 else 0,
        "avg_rounds": round(float(row["avg_rounds"] or 0), 1),
        "avg_final_price": round(float(row["avg_final_price"] or 0), 2),
        "min_deal_price": round(float(row["min_deal_price"] or 0), 2),
        "max_deal_price": round(float(row["max_deal_price"] or 0), 2),
        "total_revenue": round(float(row["total_revenue"] or 0), 2),
        "avg_margin": round(float(row["avg_margin"] or 0), 1),
        "avg_buyer_offer": round(float(row["avg_buyer_offer"] or 0), 2),
        "avg_seller_offer": round(float(row["avg_seller_offer"] or 0), 2),
        "recent_sessions": recent,
    }
