from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
import uuid
import datetime
import random
import json
import os

# ── Env vars ──────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# ── Supabase client (graceful fallback to in-memory if not configured) ────────
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client, Client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[DB] Connected to Supabase ✓")
    except Exception as e:
        print(f"[DB] Supabase connection failed: {e} — using in-memory fallback")
else:
    print("[DB] No Supabase credentials found — using in-memory fallback (local dev mode)")


# ── In-memory fallback DB (used when Supabase is unavailable) ─────────────────
_mem_db = {
    "inventory": {
        "uuid-flour": {"name": "Wheat Flour", "quantity_kg": 50.0, "reorder_level_kg": 20.0},
        "uuid-sugar": {"name": "Sugar",       "quantity_kg":  5.0, "reorder_level_kg": 10.0},
    },
    "sales":          [],
    "procurements":   [],
    "pending_posts":  [],
    "orders":         [],
    "ledger":         [],
    "logs": []
}

# ── DB Helper: wraps Supabase table ops, falls back to _mem_db ────────────────

def db_select(table: str) -> list:
    """Read all rows from a table."""
    if supabase:
        try:
            res = supabase.table(table).select("*").execute()
            return res.data or []
        except Exception as e:
            print(f"[DB] select {table} failed: {e}")
    return list(_mem_db.get(table, []))

def db_insert(table: str, row: dict) -> dict:
    """Insert a row and return it."""
    if supabase:
        try:
            res = supabase.table(table).insert(row).execute()
            return res.data[0] if res.data else row
        except Exception as e:
            print(f"[DB] insert {table} failed: {e}")
    _mem_db.setdefault(table, []).append(row)
    return row

def db_update(table: str, match: dict, updates: dict) -> bool:
    """Update rows matching `match` dict with `updates`."""
    if supabase:
        try:
            q = supabase.table(table).update(updates)
            for k, v in match.items():
                q = q.eq(k, v)
            q.execute()
            return True
        except Exception as e:
            print(f"[DB] update {table} failed: {e}")
    # In-memory fallback
    for row in _mem_db.get(table, []):
        if all(row.get(k) == v for k, v in match.items()):
            row.update(updates)
    return True

app = FastAPI(title="Fantasy AI ERP", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

# =============================================================================
# MODULE 4: SECURITY & COMPLIANCE
# =============================================================================

def log_system_event(event_type: str, description: str, actor_id: str = "system", metadata: dict = None):
    """Logs system events for KEBS audit trail."""
    log_entry = {
        "id":          str(uuid.uuid4()),
        "timestamp":   datetime.datetime.now().isoformat(),
        "event_type":  event_type,
        "description": description,
        "actor_id":    actor_id,
        "metadata":    json.dumps(metadata or {}),
    }
    db_insert("logs", log_entry)
    print(f"[AUDIT LOG] {event_type}: {description}")

def trigger_security_alert(message: str, severity: str = "HIGH"):
    alert = {
        "id":           str(uuid.uuid4()),
        "timestamp":    datetime.datetime.now().isoformat(),
        "severity":     severity,
        "message":      message,
        "odpc_reported": True,
    }
    log_system_event("SECURITY_ALERT", f"{severity} Alert: {message}", metadata=alert)
    return {"status": "Alert Logged", "odpc_report": "Prepared for submission"}

class SecurityAlertRequest(BaseModel):
    message: str
    severity: str = "HIGH"

@app.post("/security/trigger_alert")
def api_trigger_security_alert(req: SecurityAlertRequest):
    result = trigger_security_alert(req.message, req.severity)
    return {"message": f"SECURITY_ALERT raised: {req.message}", "report": result}

def mask_sensitive_data(data: dict):
    masked = data.copy()
    if "phone" in masked:
        masked["phone"] = masked["phone"][:4] + "****" + masked["phone"][-3:]
    return masked

# =============================================================================
# MODULE 1: SMART STOCK & FINANCE
# =============================================================================

class ProcurementRequest(BaseModel):
    item_id:    str
    manager_id: str

@app.get("/inventory/predict_procurement")
def predict_procurement():
    """Checks stock levels and suggests orders based on logic."""
    # Read inventory from DB
    if supabase:
        inventory_rows = db_select("inventory")
        inventory = {r["id"]: r for r in inventory_rows}
    else:
        inventory = _mem_db["inventory"]

    pending_orders   = db_select("procurements")
    pending_item_ids = {o["item_id"] for o in pending_orders if o.get("status") == "PENDING"}

    alerts = []
    for item_id, item in inventory.items():
        qty    = item.get("quantity_kg", item.get("quantity", 0))
        reorder = item.get("reorder_level_kg", item.get("reorder_level", 0))
        if qty <= reorder:
            alerts.append({
                "item_id":       item_id,
                "item_name":     item["name"],
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

    if alerts:
        log_system_event("STOCK_ALERT", f"Found {len(alerts)} low stock items.")
    return {"alerts": alerts}

@app.post("/inventory/approve_order/{order_id}")
def approve_procurement(order_id: str, req: ProcurementRequest):
    orders = db_select("procurements")
    for order in orders:
        if order["id"] == order_id and order.get("status") == "PENDING":
            db_update("procurements", {"id": order_id}, {
                "status":      "APPROVED",
                "approved_by": req.manager_id,
            })
            # Update stock
            if supabase:
                inv = supabase.table("inventory").select("*").eq("id", order["item_id"]).execute()
                if inv.data:
                    item = inv.data[0]
                    old_qty = item.get("quantity_kg", 0)
                    new_qty = old_qty + order["amount"]
                    db_update("inventory", {"id": order["item_id"]}, {"quantity_kg": new_qty})
                    log_system_event("STOCK_UPDATE", f"Restocked {item['name']}",
                                     actor_id=req.manager_id,
                                     metadata={"old": old_qty, "new": new_qty})
            else:
                item = _mem_db["inventory"].get(order["item_id"])
                if item:
                    old_qty = item["quantity_kg"]
                    item["quantity_kg"] += order["amount"]
                    log_system_event("STOCK_UPDATE", f"Restocked {item['name']}",
                                     actor_id=req.manager_id,
                                     metadata={"old": old_qty, "new": item["quantity_kg"]})
            return {"message": "Order approved and stock updated."}
    raise HTTPException(status_code=404, detail="Order not found or already processed")

# =============================================================================
# MODULE 2: SOCIAL PIPELINE (manual posts only — AI generator removed)
# =============================================================================

@app.get("/marketing/pending")
def list_pending_posts():
    posts = db_select("pending_posts")
    return {"pending": [p for p in posts if p.get("status") == "PENDING"]}

@app.post("/marketing/approve_post/{post_id}")
def approve_post(post_id: str, manager_id: str):
    posts = db_select("pending_posts")
    for post in posts:
        if post["id"] == post_id:
            db_update("pending_posts", {"id": post_id}, {
                "status":      "APPROVED",
                "approved_by": manager_id,
            })
            log_system_event("MARKETING_APPROVE", f"Post {post_id} approved.", actor_id=manager_id)
            return {"message": "Post approved for publishing."}
    raise HTTPException(status_code=404, detail="Post not found")


# =============================================================================
# MODULE 5: FINANCE & DOCUMENTS IMPORT
# =============================================================================

@app.post("/finance/upload_docs")
async def upload_financial_docs(file: UploadFile = File(...)):
    filename = file.filename.lower()
    if "xlsx" in filename or "xls" in filename:
        doc_type       = "Excel Spreadsheet (Bookkeeping)"
        extracted_data = {"revenue": 50000, "expenses": 12000, "net_profit": 38000}
    elif "docx" in filename or "doc" in filename:
        doc_type       = "Word Document (Report/Invoice)"
        extracted_data = {"summary": "Monthly Audit Report", "pages": 4}
    else:
        doc_type       = "Generic Document"
        extracted_data = {"size_bytes": 1024}

    entry = {
        "id":     str(uuid.uuid4()),
        "date":   datetime.datetime.now().isoformat(),
        "source": filename,
        "type":   doc_type,
        "data":   json.dumps(extracted_data),
        "status": "RECORDED",
    }
    db_insert("ledger", entry)
    log_system_event("AUTO_RECORD", f"Recorded financial data from {filename}", metadata=extracted_data)
    return {"message": f"Successfully imported & recorded {doc_type}", "filename": file.filename, "recorded_entry": entry}

@app.get("/finance/ledger")
def get_ledger():
    return {"ledger": db_select("ledger")}

# =============================================================================
# MODULE 6: STAFF SCHEDULER
# =============================================================================

@app.get("/staff/roster")
def get_roster():
    return {
        "week_starting": "2026-02-01",
        "shifts": [
            {"day": "Monday",  "driver": "Juma (Tuktuk 1)", "baker": "Fatma",  "time": "06:00 - 14:00"},
            {"day": "Monday",  "driver": "Ali (Tuktuk 2)",  "baker": "Hassan", "time": "14:00 - 22:00"},
            {"day": "Tuesday", "driver": "Juma (Tuktuk 1)", "baker": "Fatma",  "time": "06:00 - 14:00"},
            {"day": "Tuesday", "driver": "Kevin (Tuktuk 3)","baker": "Hassan", "time": "14:00 - 22:00"},
        ]
    }

class RecipeRequest(BaseModel):
    target_loaves: int

@app.post("/staff/calculate_recipe")
def calculate_recipe(req: RecipeRequest):
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
# MODULE 7: ORDERS
# =============================================================================

@app.get("/orders/list")
def list_orders():
    return {"orders": db_select("orders")}

@app.post("/orders/create")
def create_order(item: str, qty: int, customer: str):
    order = {
        "id":       str(uuid.uuid4()),
        "item":     item,
        "qty":      qty,
        "customer": customer,
        "time":     datetime.datetime.now().strftime("%H:%M"),
        "status":   "PENDING",
    }
    db_insert("orders", order)
    log_system_event("ORDER_CREATED", f"New order: {qty}x {item} for {customer}")
    return {"message": "Order placed successfully!", "order": order}

# =============================================================================
# MODULE 8: FINANCIAL ADVISER & MARKET ANALYSIS
# =============================================================================

@app.get("/finance/market_analysis")
def get_market_analysis():
    return {
        "market_sentiment": "Bullish",
        "competitors": [
            {"name": "Super Loaf",         "status": "Price Hike (+5 KES)",  "impact": "High Opportunity"},
            {"name": "Local Kiosk Network", "status": "Stock Shortage",       "impact": "Increase Supply"},
        ],
        "recommendation": "Increase production of Sweet Bread by 15% to capture market gap.",
    }

# =============================================================================
# ROOT
# =============================================================================

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.get("/admin")
def read_admin():
    return FileResponse("static/admin.html")
