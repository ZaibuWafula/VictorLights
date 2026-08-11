import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.db import db_cursor
from app.auth import require_admin

router = APIRouter()


def row_to_product(row) -> dict:
    """Turns a DB row into the API shape, parsing images_json into a list."""
    d = dict(row)
    d["images"] = json.loads(d.pop("images_json", "[]") or "[]")
    return d


# ---- Public catalog ----

@router.get("")
def list_products():
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, slug, name, description, details, images_json,
                   price, compare_price, tag, stock
            FROM products WHERE active = 1 ORDER BY id ASC
            """
        )
        return [row_to_product(r) for r in cur.fetchall()]


@router.get("/{slug}")
def get_product(slug: str):
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, slug, name, description, details, images_json,
                   price, compare_price, tag, stock
            FROM products WHERE slug = ? AND active = 1
            """,
            (slug,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return row_to_product(row)


# ---- Admin: manage catalog without redeploying the site ----

class ProductCreate(BaseModel):
    slug: str
    name: str
    description: str = ""       # short blurb shown on the product card
    details: str = ""           # longer copy shown on the product detail view
    images: List[str] = []      # image URLs, first = primary/cover image
    price: int
    compare_price: Optional[int] = None
    tag: Optional[str] = None
    stock: int = 0


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    details: Optional[str] = None
    images: Optional[List[str]] = None
    price: Optional[int] = None
    compare_price: Optional[int] = None
    tag: Optional[str] = None
    stock: Optional[int] = None
    active: Optional[int] = None


@router.get("/admin/all", dependencies=[Depends(require_admin)])
def list_all_products():
    with db_cursor() as cur:
        cur.execute("SELECT * FROM products ORDER BY id ASC")
        return [row_to_product(r) for r in cur.fetchall()]


@router.post("/admin", status_code=201, dependencies=[Depends(require_admin)])
def create_product(payload: ProductCreate):
    with db_cursor() as cur:
        try:
            cur.execute(
                """
                INSERT INTO products
                    (slug, name, description, details, images_json, price, compare_price, tag, stock)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (payload.slug, payload.name, payload.description, payload.details,
                 json.dumps(payload.images), payload.price, payload.compare_price,
                 payload.tag, payload.stock),
            )
        except Exception as e:
            if "UNIQUE" in str(e):
                raise HTTPException(status_code=409, detail="A product with that slug already exists")
            raise HTTPException(status_code=500, detail="Could not create product")
        return {"id": cur.lastrowid}


@router.patch("/admin/{product_id}", dependencies=[Depends(require_admin)])
def update_product(product_id: int, payload: ProductUpdate):
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    # images comes in as a list from the client but is stored as a JSON string column
    if "images" in fields:
        fields["images_json"] = json.dumps(fields.pop("images"))
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [product_id]
    with db_cursor() as cur:
        cur.execute(f"UPDATE products SET {set_clause} WHERE id = ?", values)
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Product not found")
    return {"updated": True}


@router.delete("/admin/{product_id}", dependencies=[Depends(require_admin)])
def deactivate_product(product_id: int):
    """Soft delete — keeps order history pointing at a real product row."""
    with db_cursor() as cur:
        cur.execute("UPDATE products SET active = 0 WHERE id = ?", (product_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Product not found")
    return {"deactivated": True}
