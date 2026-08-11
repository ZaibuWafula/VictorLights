import json
import random
import re
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.db import db_cursor
from app.auth import require_admin

router = APIRouter()

VALID_STATUSES = {"new", "confirmed", "shipped", "delivered", "cancelled"}


def generate_order_number() -> str:
    """Short, human-readable, readable-aloud-over-a-phone-call: VL-260808-4821"""
    date_part = datetime.now(timezone.utc).strftime("%y%m%d")
    rand_part = random.randint(1000, 9999)
    return f"VL-{date_part}-{rand_part}"


class OrderItemIn(BaseModel):
    slug: str
    qty: int

    @field_validator("qty")
    @classmethod
    def qty_at_least_one(cls, v):
        if v < 1:
            raise ValueError("qty must be at least 1")
        return v


class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=1)
    phone: str
    address: Optional[str] = None
    items: List[OrderItemIn]

    @field_validator("phone")
    @classmethod
    def phone_has_enough_digits(cls, v):
        if len(re.sub(r"\D", "", v)) < 9:
            raise ValueError("A valid phone number is required")
        return v

    @field_validator("items")
    @classmethod
    def items_not_empty(cls, v):
        if not v:
            raise ValueError("items must be a non-empty array")
        return v


# ---- Public: place and track orders ----

@router.post("", status_code=201)
def create_order(payload: OrderCreate):
    with db_cursor() as cur:
        # Never trust prices/quantities from the client — look them up server-side.
        order_items = []
        total = 0
        for item in payload.items:
            cur.execute("SELECT * FROM products WHERE slug = ? AND active = 1", (item.slug,))
            product = cur.fetchone()
            if not product:
                raise HTTPException(status_code=400, detail=f"Unknown product: {item.slug}")
            if product["stock"] < item.qty:
                raise HTTPException(
                    status_code=409,
                    detail=f"{product['name']} only has {product['stock']} in stock",
                )
            order_items.append({
                "product_id": product["id"],
                "slug": product["slug"],
                "name": product["name"],
                "qty": item.qty,
                "price": product["price"],
            })
            total += product["price"] * item.qty

        order_number = generate_order_number()
        cur.execute(
            """
            INSERT INTO orders (order_number, customer_name, phone, address, items_json, total)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (order_number, payload.customer_name, payload.phone, payload.address,
             json.dumps(order_items), total),
        )
        for it in order_items:
            cur.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (it["qty"], it["product_id"]))

    import os
    return {
        "order_number": order_number,
        "total": total,
        "items": order_items,
        "whatsapp_number": os.getenv("WHATSAPP_NUMBER"),
    }


@router.get("/{order_number}")
def track_order(order_number: str, phone: str):
    """Requires the phone number too, so an order number alone can't be used to snoop."""
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT order_number, customer_name, items_json, total, status, created_at
            FROM orders WHERE order_number = ? AND phone = ?
            """,
            (order_number, phone),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    result = dict(row)
    result["items"] = json.loads(result.pop("items_json"))
    return result


# ---- Admin: see and manage all orders ----

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def status_is_valid(cls, v):
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {', '.join(VALID_STATUSES)}")
        return v


@router.get("/admin/all", dependencies=[Depends(require_admin)])
def list_all_orders(status: Optional[str] = None):
    with db_cursor() as cur:
        if status:
            cur.execute("SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC", (status,))
        else:
            cur.execute("SELECT * FROM orders ORDER BY created_at DESC")
        rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r["items"] = json.loads(r.pop("items_json"))
    return rows


@router.patch("/admin/{order_id}", dependencies=[Depends(require_admin)])
def update_order(order_id: int, payload: OrderUpdate):
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="Nothing to update")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [order_id]
    with db_cursor() as cur:
        cur.execute(f"UPDATE orders SET {set_clause} WHERE id = ?", values)
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Order not found")
    return {"updated": True}
