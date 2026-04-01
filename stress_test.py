import time
import sys
import uuid
import random

sys.path.append(".")
from app import app, predict_procurement, approve_procurement, db, ProcurementRequest

def stress_test():
    print("=== Fantasy AI ERP: 20,000 Orders Stress Test ===\n")

    # 1. SETUP: Generate 20,000 Inventory Items
    print(f"Generating 20,000 inventory items...")
    start_setup = time.time()
    
    # Clear existing
    db["inventory"] = {}
    db["procurements"] = []

    for i in range(20000):
        item_id = str(uuid.uuid4())
        # half need reordering
        qty = 5.0 if i % 2 == 0 else 50.0 
        db["inventory"][item_id] = {
            "name": f"Bulk Item {i}",
            "quantity_kg": qty,
            "reorder_level_kg": 10.0
        }
    
    setup_time = time.time() - start_setup
    print(f"Setup complete in {setup_time:.4f} seconds.\n")

    # 2. PREDICTION TEST
    print("Running predict_procurement() on 20,000 items...")
    start_pred = time.time()
    result = predict_procurement()
    pred_time = time.time() - start_pred
    
    alert_count = len(result["alerts"])
    print(f"Prediction complete in {pred_time:.4f} seconds.")
    print(f"Generated {alert_count} alerts (Expected: ~10,000).")
    print(f"Processing rate: {20000 / pred_time:.0f} items/sec")
    
    if pred_time < 2.0:
        print("RESULT: PASS (Fast)")
    else:
        print("RESULT: WARN (Slower than ideal)")
    print("")

    # 3. ORDER APPROVAL TEST
    # At this point, app.py logic has populated db["procurements"] with the alerts
    pending_count = len(db["procurements"])
    print(f"Testing approval lookup against {pending_count} pending orders...")
    
    # Pick the last order (worst case for list search)
    last_order = db["procurements"][-1]
    last_order_id = last_order["id"]
    
    start_approve = time.time()
    req = ProcurementRequest(item_id=last_order["item_id"], manager_id="boss_man")
    approve_procurement(last_order_id, req)
    approve_time = time.time() - start_approve
    
    print(f"Approval complete in {approve_time:.6f} seconds.")
    if approve_time < 0.1:
        print("RESULT: PASS (Instant)")
    else:
        print("RESULT: WARN (List search latency visible)")

if __name__ == "__main__":
    stress_test()
