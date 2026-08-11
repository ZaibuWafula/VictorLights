import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.ratelimit import RateLimitMiddleware
from app.routers import products, orders

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"

app = FastAPI(title="Victor Lights API", docs_url="/api/docs", redoc_url=None)

init_db()

cors_origin = os.getenv("CORS_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if cors_origin == "*" else cors_origin.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# General API limit, then a tighter one specifically for order creation to
# stop both scraping and accidental client retry-loops from hammering SQLite.
app.add_middleware(RateLimitMiddleware, window_seconds=15 * 60, max_requests=300, path_prefix="/api")
app.add_middleware(RateLimitMiddleware, window_seconds=60 * 60, max_requests=20, path_prefix="/api/orders")

app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])


@app.get("/api/health")
def health():
    from datetime import datetime, timezone
    return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}


@app.get("/api/config")
def config():
    """Public, non-secret site config the frontend needs at load time."""
    return {"whatsapp_number": os.getenv("WHATSAPP_NUMBER", "")}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": "Something went wrong"})


# Serve the storefront itself from the same process — one service to deploy,
# one URL, no separate static host to pay for.
app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="static")
