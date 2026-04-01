from fastapi import FastAPI, HTTPException, Depends, Header, Query, Path, Cookie, Response, Form, Request
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
    "inventory", "procurements", "pending_posts", "ledger", "logs", "orders", "site_content"
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
                    content={"error": "File too large. Max 5MB for images, 50MB for videos."}
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
_origins_raw = os.environ.get("ALLOWED_HOSTS", "http://localhost:8000")
_allowed_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Trusted Hosts
_trusted_hosts = [h.strip() for h in _origins_raw.split(",") if h.strip()]
if _trusted_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_trusted_hosts)

app.mount("/static", StaticFiles(directory="static"), name="static")


def verify_admin(admin_session: str = Cookie(None)):
    if not admin_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        serializer.loads(admin_session, max_age=3600)
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired")

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
    __: None = Depends(verify_csrf)
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
    "video/mp4", "video/webm", "video/quicktime"
}

MAX_IMAGE_SIZE = 5 * 1024 * 1024   # 5MB
MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50MB

def sanitize(text: str) -> str:
    return bleach.clean(text, tags=[], strip=True)

# Item 7: Safe Filename
def safe_filename(slot: str, mime: str) -> str:
    ext = {
        "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
        "video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov"
    }[mime]
    return re.sub(r"[^a-z0-9\-]", "", slot.lower()) + ext

@app.get("/api/content")
def get_site_content():
    rows = db_select("site_content")
    if rows:
        return rows[0]
    return {}

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
    ALLOWED_SLOTS = {
        "hero", "white-bread", "sugar-rolls", "buns",
        "hero-video", "white-bread-video", "sugar-rolls-video", "buns-video"
    }
    if slot not in ALLOWED_SLOTS:
        raise HTTPException(400, "Invalid slot")

    contents = await file.read()
    mime = magic.from_buffer(contents, mime=True)
    if mime not in ALLOWED_MIME:
        raise HTTPException(400, f"Invalid file type: {mime}. Only JPG, PNG, WebP, MP4, WebM, MOV allowed.")

    is_video = mime.startswith("video/")
    size_limit = MAX_VIDEO_SIZE if is_video else MAX_IMAGE_SIZE

    if len(contents) > size_limit:
        limit_mb = size_limit // (1024 * 1024)
        raise HTTPException(400, f"File too large. Max {limit_mb}MB for this type.")

    filename = safe_filename(slot, mime)

    # ── Supabase Storage (ephemeral-filesystem-safe) ──────────────────────────
    # upsert=True overwrites the existing file for the same slot so old files
    # don't accumulate.  The 'uploads' bucket must be created in Supabase
    # Storage dashboard and set to Private before first deploy.
    try:
        supabase.storage.from_("uploads").upload(
            path=filename,
            file=contents,
            file_options={"content-type": mime, "upsert": "true"},
        )
    except Exception as e:
        raise HTTPException(500, f"Storage upload failed: {str(e)}")

    ip = request.client.host if request.client else "unknown"
    audit_log("FILE_UPLOAD", ip, f"slot={slot} mime={mime} size={len(contents)}")
    return {"status": "ok", "slot": slot, "filename": filename, "type": "video" if is_video else "image"}

@app.get("/api/images/{slot}")
async def get_image(slot: str):
    ALLOWED_SLOTS = {
        "hero", "white-bread", "sugar-rolls", "buns",
        "hero-video", "white-bread-video", "sugar-rolls-video", "buns-video"
    }
    if slot not in ALLOWED_SLOTS:
        raise HTTPException(404, "Not found")

    # ── Supabase Storage signed URL (1-hour expiry) ───────────────────────────
    # Try each valid extension for this slot.  The filename is deterministic
    # (safe_filename logic with slot + ext), so we probe until one resolves.
    safe_slot = re.sub(r"[^a-z0-9\-]", "", slot.lower())
    for ext in [".jpg", ".png", ".webp", ".mp4", ".webm", ".mov"]:
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
