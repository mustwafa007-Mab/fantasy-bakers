from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, Query, Path, Cookie, Response, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from fastapi import UploadFile, File
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Annotated
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import datetime
import random
import json
import os
import sys
import time
import logging
import re
from pathlib import Path as FilePath
from collections import defaultdict
from urllib.parse import urlparse

# Security dependencies
import secrets
import magic
import bleach
from itsdangerous import URLSafeTimedSerializer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ── Env vars ──────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

# Item 9: Startup checks
if not os.environ.get("ADMIN_PASSWORD"):
    print("FATAL: ADMIN_PASSWORD environment variable not set")
    sys.exit(1)

if not os.environ.get("SECRET_KEY"):
    print("FATAL: SECRET_KEY environment variable not set")
    sys.exit(1)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SECRET_KEY = os.environ.get("SECRET_KEY")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
IS_PROD = os.environ.get("ENVIRONMENT", "development") == "production"

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials strictly required in production.")

from supabase import create_client, Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print("[DB] Connected to Supabase ✓")

_ALLOWED_TABLES = frozenset({
    "inventory", "procurements", "pending_posts", "ledger", "logs", "orders", "site_content", "site_layout"
})

def _guard_table(table: str) -> str:
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"disallowed table: {table!r}")
    return table

def db_select(table: str) -> list:
    table = _guard_table(table)
    try:
        res = supabase.table(table).select("*").execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")

def db_insert(table: str, row: dict) -> dict:
    table = _guard_table(table)
    try:
        res = supabase.table(table).insert(row).execute()
        return res.data[0] if res.data else row
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")

def db_update(table: str, match: dict, updates: dict) -> bool:
    table = _guard_table(table)
    try:
        q = supabase.table(table).update(updates)
        for k, v in match.items():
            q = q.eq(k, v)
        q.execute()
        return True
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}")


app = FastAPI(title="Fantasy AI ERP", version="1.0.0")

# Item 6: Audit Logging
logging.basicConfig(
    filename="admin_audit.log",
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)

def audit_log(action: str, ip: str, detail: str = ""):
    logging.info(f"ACTION={action} | IP={ip} | DETAIL={detail}")


from fastapi.responses import JSONResponse

# Item 4: Max Body Size Middleware
class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > 52 * 1024 * 1024:
                return JSONResponse(
                    status_code=413,
                    content={"error": "File too large. Max 5MB images, 50MB video, 20MB GLB."}
                )
        return await call_next(request)

app.add_middleware(MaxBodySizeMiddleware)


# Item 1: Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "frame-ancestors 'none';"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)


# Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

serializer = URLSafeTimedSerializer(SECRET_KEY)

# CORS
_origins_raw = os.environ.get("ALLOWED_ORIGINS") or os.environ.get(
    "ALLOWED_HOSTS", "http://localhost:8000"
)
_allowed_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],  # PATCH: /api/site-config (Next dashboard)
    allow_headers=["*"],
)

# Trusted Hosts — Host header has no scheme; ALLOWED_ORIGINS entries are often full URLs.
def _trusted_hostnames_for_middleware() -> list[str]:
    raw = os.environ.get("ALLOWED_ORIGINS") or os.environ.get(
        "ALLOWED_HOSTS", "http://localhost:8000"
    )
    seen: set[str] = set()
    out: list[str] = []
    for part in raw.split(","):
        p = part.strip()
        if not p:
            continue
        if "://" in p:
            h = urlparse(p).hostname
            if not h:
                continue
        else:
            h = p.split("/")[0].strip()
        if h and h not in seen:
            seen.add(h)
            out.append(h)
    rail = (os.environ.get("RAILWAY_PUBLIC_DOMAIN") or "").strip()
    if rail:
        h = rail.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
        if h and h not in seen:
            seen.add(h)
            out.append(h)
    # Any Railway deploy hostname (*.up.railway.app) when proxying from Next/Vercel.
    if os.environ.get("RAILWAY_ENVIRONMENT") and "*.up.railway.app" not in seen:
        seen.add("*.up.railway.app")
        out.append("*.up.railway.app")
    for h in ("127.0.0.1", "localhost"):
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


_trusted_hosts = _trusted_hostnames_for_middleware()
if _trusted_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_trusted_hosts)

app.mount("/static", StaticFiles(directory="static"), name="static")


def _require_admin_session(admin_session: str | None):
    if not admin_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        serializer.loads(admin_session, max_age=3600)
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired")


async def require_auth(request: Request) -> None:
    """
    FastAPI dependency: require valid admin_session cookie (set by POST /admin/login).
    Use on /api/admin/** routes, e.g. _: Annotated[None, Depends(require_auth)]
    """
    _require_admin_session(request.cookies.get("admin_session"))


def verify_admin(admin_session: str = Cookie(None)):
    _require_admin_session(admin_session)

# Item 2: CSRF Implementation
def generate_csrf_token():
    return secrets.token_hex(32)

@app.get("/admin/csrf-token")
async def get_csrf_token(response: Response, _: None = Depends(verify_admin)):
    token = generate_csrf_token()
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,
        secure=IS_PROD,
        samesite="strict",
        max_age=3600
    )
    return {"csrf_token": token}

def verify_csrf(
    x_csrf_token: str = Header(None, alias="x-csrf-token"),
    csrf_token: str = Cookie(None)
):
    if not x_csrf_token or not csrf_token:
        raise HTTPException(403, "CSRF token missing")
    if not secrets.compare_digest(x_csrf_token, csrf_token):
        raise HTTPException(403, "CSRF token invalid")


DEFAULT_LAYOUT_COMPONENTS = ["hero", "products", "showcase", "map"]
LAYOUT_KEYS = frozenset(DEFAULT_LAYOUT_COMPONENTS)


def verify_layout_write(
    request: Request,
    x_site_config_secret: str | None = Header(None, alias="X-Site-Config-Secret"),
):
    """Railway admin session + CSRF, or Vercel server proxy via SITE_CONFIG_SECRET."""
    expected = os.environ.get("SITE_CONFIG_SECRET")
    if expected and (x_site_config_secret or "").strip() == expected:
        return True
    _require_admin_session(request.cookies.get("admin_session"))
    verify_csrf(
        request.headers.get("x-csrf-token") or "",
        request.cookies.get("csrf_token") or "",
    )
    return True


# =============================================================================
# ADMIN AUTHENTICATION
# =============================================================================

# Item 3: Brute Force Protection
login_attempts = defaultdict(list)
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 900

def check_brute_force(ip: str):
    now = time.time()
    login_attempts[ip] = [t for t in login_attempts[ip] if now - t < LOCKOUT_SECONDS]
    if len(login_attempts[ip]) >= MAX_ATTEMPTS:
        remaining = int(LOCKOUT_SECONDS - (now - login_attempts[ip][0]))
        raise HTTPException(429, f"Too many failed attempts. Try again in {remaining} seconds.")


@app.get("/admin/login")
async def get_admin_login() -> HTMLResponse:
    html = """<!DOCTYPE html>
<html>
<head><title>Admin Login</title></head>
<body style="display:flex; justify-content:center; align-items:center; height:100vh; font-family:sans-serif; background:#f5f5f5; margin:0;">
    <form method="POST" action="/admin/login" style="background:white; padding:40px; border:1px solid #ddd; border-radius:4px; text-align:center;">
        <h2 style="margin-top:0;">Admin Portal</h2>
        <input type="password" name="password" placeholder="Password" required style="padding:10px; width:200px; margin-bottom:15px; border:1px solid #ccc; border-radius:2px; display:block;" />
        <button type="submit" style="width:100%; padding:10px; background:#333; color:white; border:none; border-radius:2px; font-weight:bold; cursor:pointer;">Login</button>
    </form>
</body>
</html>"""
    return HTMLResponse(content=html)

@app.post("/admin/login")
async def admin_login(request: Request, password: str = Form(...)):
    ip = request.client.host if request.client else "unknown"
    check_brute_force(ip)

    if not secrets.compare_digest(password, ADMIN_PASSWORD):
        login_attempts[ip].append(time.time())
        attempts_left = MAX_ATTEMPTS - len(login_attempts[ip])
        audit_log("LOGIN_FAIL", ip, f"{attempts_left} attempts left")
        raise HTTPException(401, f"Invalid password. {attempts_left} attempts remaining.")

    login_attempts[ip] = []
    audit_log("LOGIN_SUCCESS", ip)

    token = serializer.dumps("admin")
    res = RedirectResponse(url="/admin/dashboard", status_code=302)
    res.set_cookie(
        key="admin_session",
        value=token,
        httponly=True,
        secure=IS_PROD,
        samesite="lax",
        max_age=3600
    )
    return res

@app.post("/admin/logout")
async def admin_logout(
    request: Request,
    _: None = Depends(verify_admin),
    __: None = Depends(verify_csrf),
):
    ip = request.client.host if request.client else "unknown"
    audit_log("LOGOUT", ip)
    res = RedirectResponse(url="/admin/login", status_code=302)
    res.delete_cookie("admin_session")
    res.delete_cookie("csrf_token")
    return res

# Item 5: Session Renewal
@app.post("/admin/refresh-session")
async def refresh_session(
    response: Response,
    _: None = Depends(verify_admin),
    __: None = Depends(verify_csrf)
):
    token = serializer.dumps("admin")
    response.set_cookie(
        key="admin_session",
        value=token,
        httponly=True,
        secure=IS_PROD,
        samesite="lax",
        max_age=3600
    )
    return {"status": "refreshed"}


@app.get("/admin/dashboard")
async def admin_dashboard(_: None = Depends(verify_admin)):
    return FileResponse("static/dashboard.html")

@app.get("/admin")
async def old_admin_route():
    return RedirectResponse(url="/admin/dashboard", status_code=302)

# =============================================================================
# SYSTEM LOGGING (INTERNAL ONLY)
# =============================================================================

def log_system_event(event_type: str, description: str, actor_id: str = "system", metadata: dict = None):
    log_entry = {
        "id":          str(uuid.uuid4()),
        "timestamp":   datetime.datetime.now().isoformat(),
        "event_type":  event_type,
        "description": bleach.clean(description),
        "actor_id":    actor_id,
        "metadata":    json.dumps(metadata or {}),
    }
    db_insert("logs", log_entry)


# =============================================================================
# MODULE 1: SMART STOCK & FINANCE
# =============================================================================

class ProcurementRequest(BaseModel):
    item_id: str = Field(..., min_length=1, max_length=128)
    manager_id: str = Field(..., min_length=1, max_length=128)

@app.get("/inventory/predict_procurement")
def predict_procurement():
    inventory_rows = db_select("inventory")
    inventory = {r["id"]: r for r in inventory_rows}

    pending_orders   = db_select("procurements")
    pending_item_ids = {o["item_id"] for o in pending_orders if o.get("status") == "PENDING"}

    alerts = []
    for item_id, item in inventory.items():
        qty    = item.get("quantity_kg", item.get("quantity", 0))
        reorder = item.get("reorder_level_kg", item.get("reorder_level", 0))
        if qty <= reorder:
            alerts.append({
                "item_id":       item_id,
                "item_name":     item.get("name", "Unknown"),
                "current_stock": qty,
                "suggested_order": 50.0,
                "urgency":       "HIGH",
            })
            if item_id not in pending_item_ids:
                db_insert("procurements", {
                    "id":      str(uuid.uuid4()),
                    "item_id": item_id,
                    "amount":  50.0,
                    "status":  "PENDING",
                })
    return {"alerts": alerts}

@app.post("/inventory/approve_order/{order_id}")
def approve_procurement(
    order_id: Annotated[str, Path(min_length=1, max_length=128)],
    req: ProcurementRequest,
    _: None = Depends(verify_admin),
    __: None = Depends(verify_csrf) # Admin action
):
    orders = db_select("procurements")
    for order in orders:
        if order["id"] == order_id and order.get("status") == "PENDING":
            db_update("procurements", {"id": order_id}, {
                "status":      "APPROVED",
                "approved_by": bleach.clean(req.manager_id),
            })
            inv = supabase.table("inventory").select("*").eq("id", order["item_id"]).execute()
            if inv.data:
                item = inv.data[0]
                old_qty = item.get("quantity_kg", 0)
                new_qty = old_qty + order["amount"]
                db_update("inventory", {"id": order["item_id"]}, {"quantity_kg": new_qty})
            return {"message": "Order approved and stock updated."}
    raise HTTPException(status_code=404, detail="Order not found or already processed")

# =============================================================================
# MODULE 2: SOCIAL PIPELINE
# =============================================================================

@app.get("/marketing/pending")
def list_pending_posts():
    posts = db_select("pending_posts")
    return {"pending": [p for p in posts if p.get("status") == "PENDING"]}

@app.post("/marketing/approve_post/{post_id}")
def approve_post(
    post_id: Annotated[str, Path(min_length=1, max_length=128)],
    manager_id: Annotated[str, Query(min_length=1, max_length=128)],
    _: None = Depends(verify_admin),
    __: None = Depends(verify_csrf)
):
    posts = db_select("pending_posts")
    for post in posts:
        if post["id"] == post_id:
            db_update("pending_posts", {"id": post_id}, {
                "status":      "APPROVED",
                "approved_by": bleach.clean(manager_id),
            })
            return {"message": "Post approved."}
    raise HTTPException(status_code=404, detail="Post not found")


# =============================================================================
# MODULE 3: CMS & LANDING PAGE (Secure)
# =============================================================================

ALLOWED_MIME = {
    "image/jpeg", "image/png", "image/webp",
    "video/mp4", "video/webm", "video/quicktime",
}

MAX_IMAGE_SIZE = 5 * 1024 * 1024   # 5MB
MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50MB
MAX_MODEL_SIZE = 20 * 1024 * 1024  # 20MB (GLB)

IMAGE_AND_VIDEO_SLOTS = frozenset({
    "hero", "white-bread", "sugar-rolls", "buns",
    "hero-video", "white-bread-video", "sugar-rolls-video", "buns-video",
})
MODEL_GLB_SLOTS = frozenset({"white-bread-glb", "sugar-rolls-glb", "buns-glb"})
ALLOWED_UPLOAD_SLOTS = IMAGE_AND_VIDEO_SLOTS | MODEL_GLB_SLOTS

def sanitize(text: str) -> str:
    return bleach.clean(text, tags=[], strip=True)

# Item 7: Safe Filename
def safe_filename(slot: str, mime: str) -> str:
    ext = {
        "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
        "video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov",
    }[mime]
    return re.sub(r"[^a-z0-9\-]", "", slot.lower()) + ext


def _is_binary_glb(contents: bytes) -> bool:
    return len(contents) >= 12 and contents[:4] == b"glTF"


async def process_admin_media_upload(request: Request, file: UploadFile, slot: str) -> dict:
    if slot not in ALLOWED_UPLOAD_SLOTS:
        raise HTTPException(400, "Invalid slot")

    contents = await file.read()
    mime = magic.from_buffer(contents, mime=True)
    safe_slot = re.sub(r"[^a-z0-9\-]", "", slot.lower())

    if slot in MODEL_GLB_SLOTS:
        if len(contents) > MAX_MODEL_SIZE:
            raise HTTPException(400, "File too large. Max 20MB for 3D models.")
        if mime not in ("model/gltf-binary", "application/octet-stream"):
            raise HTTPException(400, f"Invalid file type for 3D model: {mime}. Use GLB.")
        if not _is_binary_glb(contents):
            raise HTTPException(400, "Invalid GLB payload (missing glTF header).")
        filename = safe_slot + ".glb"
        store_mime = "model/gltf-binary"
    else:
        if mime not in ALLOWED_MIME:
            raise HTTPException(
                400,
                f"Invalid file type: {mime}. Only JPG, PNG, WebP, MP4, WebM, MOV allowed for this slot.",
            )
        is_video = mime.startswith("video/")
        size_limit = MAX_VIDEO_SIZE if is_video else MAX_IMAGE_SIZE
        if len(contents) > size_limit:
            limit_mb = size_limit // (1024 * 1024)
            raise HTTPException(400, f"File too large. Max {limit_mb}MB for this type.")
        filename = safe_filename(slot, mime)
        store_mime = mime

    try:
        supabase.storage.from_("uploads").upload(
            path=filename,
            file=contents,
            file_options={"content-type": store_mime, "upsert": "true"},
        )
    except Exception as e:
        raise HTTPException(500, f"Storage upload failed: {str(e)}")

    ip = request.client.host if request.client else "unknown"
    audit_log("FILE_UPLOAD", ip, f"slot={slot} mime={store_mime} size={len(contents)}")
    if slot in MODEL_GLB_SLOTS:
        return {"status": "ok", "slot": slot, "filename": filename, "type": "model"}
    return {"status": "ok", "slot": slot, "filename": filename, "type": "video" if is_video else "image"}

@app.get("/api/content")
def get_site_content():
    rows = db_select("site_content")
    if rows:
        return rows[0]
    return {}


_HEX_THEME = re.compile(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")


@app.patch("/api/site-config")
async def patch_site_config_headless(
    request: Request,
    x_site_config_secret: str | None = Header(None, alias="X-Site-Config-Secret"),
):
    """
    Updates a small whitelist of landing fields for the Next.js /admin/dashboard.
    Set SITE_CONFIG_SECRET on Railway and Vercel; add a `background_color` TEXT column
    to `site_content` in Supabase if you use page background overrides.
    """
    expected = os.environ.get("SITE_CONFIG_SECRET")
    if expected and (x_site_config_secret or "").strip() == expected:
        pass
    else:
        _require_admin_session(request.cookies.get("admin_session"))
        verify_csrf(
            request.headers.get("x-csrf-token") or "",
            request.cookies.get("csrf_token") or "",
        )
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body must be an object")

    row = dict(_site_row())
    updates: dict = {}
    for key in ("hero_p", "hero_title", "background_color"):
        if key not in body:
            continue
        val = body[key]
        if val is None:
            updates[key] = None
            continue
        if key == "background_color":
            s = str(val).strip()
            if not s:
                updates[key] = None
            elif not _HEX_THEME.match(s):
                raise HTTPException(status_code=400, detail="Invalid background_color (use #RGB or #RRGGBB)")
            else:
                updates[key] = s
        else:
            updates[key] = sanitize(str(val)) if isinstance(val, str) else sanitize(str(val))

    if not updates:
        return {"ok": True, "updated": []}

    merged = {**row, **updates, "id": "landing_page"}
    try:
        supabase.table("site_content").upsert(merged).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    ip = request.client.host if request.client else "unknown"
    audit_log("SITE_CONFIG_PATCH", ip, ",".join(updates.keys()))
    return {"ok": True, "updated": list(updates.keys())}


def _normalize_layout_components(raw) -> list:
    if not isinstance(raw, list):
        return list(DEFAULT_LAYOUT_COMPONENTS)
    out: list[str] = []
    seen: set[str] = set()
    for x in raw:
        if isinstance(x, str) and x in LAYOUT_KEYS and x not in seen:
            out.append(x)
            seen.add(x)
    return out if out else list(DEFAULT_LAYOUT_COMPONENTS)


@app.get("/api/layout")
def get_layout():
    try:
        rows = db_select("site_layout")
    except Exception:
        return {"components": list(DEFAULT_LAYOUT_COMPONENTS)}
    if not rows:
        return {"components": list(DEFAULT_LAYOUT_COMPONENTS)}
    row = rows[0]
    raw = row.get("components")
    return {"components": _normalize_layout_components(raw)}


@app.post("/api/layout")
async def post_layout(
    request: Request,
    _: None = Depends(verify_layout_write),
):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Body must be an object")
    comps = payload.get("components")
    if not isinstance(comps, list) or len(comps) == 0:
        raise HTTPException(status_code=400, detail="components must be a non-empty array")
    normalized: list[str] = []
    seen: set[str] = set()
    for x in comps:
        if isinstance(x, str) and x in LAYOUT_KEYS and x not in seen:
            normalized.append(x)
            seen.add(x)
    if not normalized:
        raise HTTPException(status_code=400, detail="No valid layout component ids")
    row = {"id": "main", "components": normalized}
    try:
        supabase.table("site_layout").upsert(row).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    ip = request.client.host if request.client else "unknown"
    audit_log("LAYOUT_UPDATE", ip, json.dumps(normalized))
    return {"ok": True, "components": normalized}


def _safe_float(val, default: float) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _site_row() -> dict:
    rows = db_select("site_content")
    return rows[0] if rows else {}


# Stable catalog slots: CMS keys in site_content (Supabase) drive copy & prices.
_SHOWCASE_DEFS = [
    {
        "id": "white-bread",
        "vis_key": "vis_product1",
        "title_key": "title_product1",
        "desc_key": "desc_product1",
        "price_key": "price_product1",
        "model_key": "model_path_product1",
        "default_title": "Fantasy White Bread",
        "default_desc": "Our signature white bread — sliced, sealed, and always fresh.",
        "default_price": 65.0,
        "unit": "per loaf",
        "color": "#d4a96a",
        "emoji": "🍞",
    },
    {
        "id": "sugar-rolls",
        "vis_key": "vis_product2",
        "title_key": "title_product2",
        "desc_key": "desc_product2",
        "price_key": "price_product2",
        "model_key": "model_path_product2",
        "default_title": "Sugar Rolls",
        "default_desc": "Soft, pillowy rolls dusted with golden sugar.",
        "default_price": 45.0,
        "unit": "per pack of 6",
        "color": "#c8872a",
        "emoji": "🥐",
    },
    {
        "id": "buns",
        "vis_key": "vis_product3",
        "title_key": "title_product3",
        "desc_key": "desc_product3",
        "price_key": "price_product3",
        "model_key": "model_path_product3",
        "default_title": "Artisan Buns",
        "default_desc": "Hand-shaped buns with a crisp crust and tender crumb.",
        "default_price": 40.0,
        "unit": "each",
        "color": "#a0522d",
        "emoji": "🫓",
    },
]


@app.get("/api/products")
def get_products():
    # Pull live data from site_content table; defaults match _SHOWCASE_DEFS (single source).
    rows = db_select("site_content")
    cms = rows[0] if rows else {}

    base_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "https://web-production-ffd18d.up.railway.app")

    products = []
    for d in _SHOWCASE_DEFS:
        pid = d["id"]
        products.append(
            {
                "id": pid,
                "name": d["default_title"],
                "price": float(cms.get(d["price_key"], d["default_price"])),
                "visible": cms.get(d["vis_key"], True),
                "image_url": f"{base_url}/api/images/{pid}",
                "video_url": f"{base_url}/api/images/{pid}-video",
                "model_glb_url": f"{base_url}/api/images/{pid}-glb",
            }
        )

    # Filter out hidden products for public endpoint
    return [p for p in products if p["visible"]]

@app.post("/api/content")
async def update_site_content(
    request: Request,
    payload: dict,
    _: None = Depends(verify_admin),
    __: None = Depends(verify_csrf)
):
    payload.pop("id", None)
    
    sanitized_payload = {}
    for key, value in payload.items():
        if isinstance(value, str):
            if str(key).startswith("model_path_"):
                v = value.strip()[:1024]
                if v and not re.match(r"^(/|https://)\S+$", v):
                    raise HTTPException(400, "Invalid GLB path (use /models/... or https://...)")
                sanitized_payload[key] = v
            else:
                sanitized_payload[key] = sanitize(value)
        else:
            sanitized_payload[key] = value

    sanitized_payload["id"] = "landing_page"
    
    try:
        supabase.table("site_content").upsert(sanitized_payload).execute()
    except Exception as e:
        raise HTTPException(500, f"Database error: {str(e)}. Content not saved.")
    
    ip = request.client.host if request.client else "unknown"
    audit_log("PRICE_UPDATE", ip, "Content/prices updated via API")
    return {"message": "Content updated successfully!"}

@app.post("/admin/upload_image")
@limiter.limit("10/minute")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    slot: str = Form(...),
    _: None = Depends(verify_admin),
    __: None = Depends(verify_csrf)
):
    return await process_admin_media_upload(request, file, slot)

admin_api_router = APIRouter(prefix="/api/admin", tags=["admin-api"])


@admin_api_router.get("/session")
async def api_admin_session(_: None = Depends(require_auth)):
    return {"ok": True}


@admin_api_router.post("/upload")
@limiter.limit("10/minute")
async def api_admin_upload(
    request: Request,
    file: UploadFile = File(...),
    slot: str = Form(...),
    _: None = Depends(require_auth),
    __: None = Depends(verify_csrf),
):
    return await process_admin_media_upload(request, file, slot)


app.include_router(admin_api_router)

@app.get("/api/images/{slot}")
async def get_image(slot: str):
    if slot not in ALLOWED_UPLOAD_SLOTS:
        raise HTTPException(404, "Not found")

    # ── Supabase Storage signed URL (1-hour expiry) ───────────────────────────
    # Try each valid extension for this slot.  The filename is deterministic
    # (safe_filename logic with slot + ext), so we probe until one resolves.
    safe_slot = re.sub(r"[^a-z0-9\-]", "", slot.lower())
    for ext in [".jpg", ".png", ".webp", ".mp4", ".webm", ".mov", ".glb"]:
        filename = safe_slot + ext
        try:
            result = supabase.storage.from_("uploads").create_signed_url(
                path=filename,
                expires_in=3600,
            )
            signed_url = (
                result.get("signedURL")
                or result.get("signed_url")
                or result.get("signedUrl")
            )
            if signed_url:
                return RedirectResponse(url=signed_url, status_code=302)
        except Exception:
            continue

    raise HTTPException(404, "File not found")


# =============================================================================
# MODULE 5: FINANCE & DOCUMENTS IMPORT
# =============================================================================

ALLOWED_FINANCE_MIME = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "application/vnd.ms-excel",                                           # xls
    "application/msword",                                                  # doc
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
    "application/pdf"
}

@app.post("/finance/upload_docs")
async def upload_financial_docs(
    request: Request,
    file: UploadFile = File(...),
    _: None = Depends(verify_admin),
    __: None = Depends(verify_csrf)
):
    contents = await file.read()
    mime = magic.from_buffer(contents, mime=True)
    if mime not in ALLOWED_FINANCE_MIME:
        raise HTTPException(400, f"Invalid file type: {mime}. Only Excel, Word, and PDF allowed.")
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large. Max 10MB.")

    if "spreadsheet" in mime or "excel" in mime:
        doc_type       = "Excel Spreadsheet (Bookkeeping)"
        extracted_data = {"revenue": 50000, "expenses": 12000, "net_profit": 38000}
    elif "word" in mime or "msword" in mime:
        doc_type       = "Word Document (Report/Invoice)"
        extracted_data = {"summary": "Monthly Audit Report", "pages": 4}
    elif mime == "application/pdf":
        doc_type       = "PDF Document"
        extracted_data = {"pages": 1}
    else:
        doc_type       = "Generic Document"
        extracted_data = {"size_bytes": len(contents)}

    entry = {
        "id":     str(uuid.uuid4()),
        "date":   datetime.datetime.now().isoformat(),
        "source": bleach.clean(file.filename or "unknown"),
        "type":   doc_type,
        "data":   json.dumps(extracted_data),
        "status": "RECORDED",
    }
    db_insert("ledger", entry)
    ip = request.client.host if request.client else "unknown"
    audit_log("FINANCE_UPLOAD", ip, f"mime={mime} file={file.filename}")
    return {"message": f"Successfully imported & recorded {doc_type}", "filename": file.filename, "recorded_entry": entry}

@app.get("/finance/ledger")
def get_ledger(_: None = Depends(verify_admin)):
    return {"ledger": db_select("ledger")}

# =============================================================================
# MODULE 6: STAFF SCHEDULER
# =============================================================================

@app.get("/staff/roster")
def get_roster():
    return {
        "week_starting": "2026-02-01",
        "shifts": [
            {"day": "Monday",  "driver": "Juma", "baker": "Fatma",  "time": "06:00 - 14:00"},
            {"day": "Monday",  "driver": "Ali",  "baker": "Hassan", "time": "14:00 - 22:00"},
            {"day": "Tuesday", "driver": "Juma", "baker": "Fatma",  "time": "06:00 - 14:00"},
            {"day": "Tuesday", "driver": "Kevin","baker": "Hassan", "time": "14:00 - 22:00"},
        ]
    }

class RecipeRequest(BaseModel):
    target_loaves: int = Field(..., ge=1, le=500_000)

@app.post("/staff/calculate_recipe")
def calculate_recipe(req: RecipeRequest, _: None = Depends(verify_admin), __: None = Depends(verify_csrf)):
    return {
        "target": req.target_loaves,
        "ingredients": {
            "Flour (Wheat)": f"{req.target_loaves * 0.5} kg",
            "Water":         f"{req.target_loaves * 0.3} L",
            "Sugar":         f"{req.target_loaves * 0.05} kg",
            "Yeast":         f"{req.target_loaves * 0.01} kg",
        }
    }

# =============================================================================
# MODULE 7: ORDERS (Public)
# =============================================================================

@app.get("/orders/list")
def list_orders(_: None = Depends(verify_admin)):
    return {"orders": db_select("orders")}

@app.post("/orders/create")
def create_order(
    item: Annotated[str, Query(min_length=1, max_length=200)],
    qty: Annotated[int, Query(ge=1, le=50_000)],
    customer: Annotated[str, Query(min_length=1, max_length=200)],
):
    # This is a PUBLIC endpoint. No admin check, no CSRF check needed.
    order = {
        "id":       str(uuid.uuid4()),
        "item":     sanitize(item),
        "qty":      qty,
        "customer": sanitize(customer),
        "time":     datetime.datetime.now().strftime("%H:%M"),
        "status":   "PENDING",
    }
    db_insert("orders", order)
    return {"message": "Order placed successfully!", "order": order}

# =============================================================================
# ROOT
# =============================================================================

@app.get("/")
def read_root():
    return FileResponse("static/index.html")