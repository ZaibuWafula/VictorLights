"""
auth.py — tiny shared-secret auth for admin endpoints. No user accounts, no
session store, no password DB to secure. The shop owner keeps the key in a
password manager and pastes it into request headers (curl, Postman, or the
auto-generated /docs "Authorize" won't apply here since this is a plain
header, not OAuth — just add it manually in a tool like Postman/Insomnia).
"""
import os
from fastapi import Header, HTTPException


def require_admin(x_admin_key: str = Header(default=None)) -> None:
    admin_key = os.getenv("ADMIN_KEY")
    if not admin_key:
        raise HTTPException(status_code=500, detail="Server misconfigured: ADMIN_KEY is not set")
    if not x_admin_key or x_admin_key != admin_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
