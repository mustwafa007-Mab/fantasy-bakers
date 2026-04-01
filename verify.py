import sys
import os

# Ensure we can import app
sys.path.append(".")

from app import (
    app, 
    predict_procurement, 
    generate_social_content, 
    find_best_tuktuk, 
    trigger_security_alert, 
    VideoUpload,
    db
)

def run_verification():
    print("=== Fantasy AI ERP MVP Verification ===\n")

    # 1. Test Stock Prediction
    print("--- Module 1: Stock & Finance ---")
    print("Checking for low stock...")
    result = predict_procurement()
    alerts = result.get("alerts", [])
    if alerts:
        print(f"SUCCESS: Alert generated for {alerts[0]['item_name']}")
        print(f"Alert Details: {alerts[0]}")
    else:
        print("FAILURE: No alerts generated (Check app.py logic)")
    print("")

    # 2. Test Social Pipeline
    print("--- Module 2: AI Social Pipeline ---")
    video_input = VideoUpload(description="Staff baking fresh bread in the morning", uploader_id="user123")
    print(f"Generating content for: '{video_input.description}'")
    social_res = generate_social_content(video_input)
    
    # Check captions from the response directly or DB
    post_id = social_res["post_id"]
    # Retrieve from DB to confirm storage
    saved_post = next((p for p in db["pending_posts"] if p["id"] == post_id), None)
    
    if saved_post:
        print(f"SUCCESS: Post generated and saved.")
        print(f"Swahili Caption: {saved_post['caption_swahili']}")
        print(f"English Caption: {saved_post['caption_english']}")
    else:
        print("FAILURE: Post not saved in DB.")
    print("")

    # 3. Test Logistics
    print("--- Module 3: Tuktuk Logistics ---")
    customer_id = "c1"
    print(f"Finding Tuktuk for Customer {customer_id}...")
    try:
        logistics_res = find_best_tuktuk(customer_id)
        if "assigned_tuktuk" in logistics_res:
            print(f"SUCCESS: Assigned to {logistics_res['assigned_tuktuk']}")
            print(f"Freshness Score: {logistics_res['freshness_score']}")
            print(f"Estimated Temp: {logistics_res['estimated_temp_celsius']}C")
            print(f"Customer Data (Masked): {logistics_res['customer']['phone']}")
        else:
            print("FAILURE: No assignment made.")
    except Exception as e:
        print(f"ERROR: {e}")
    print("")

    # 4. Test Security
    print("--- Module 4: Security & Compliance ---")
    print("Triggering Security Alert...")
    sec_res = trigger_security_alert("Unauthorized access detected on Port 8080")
    
    # Check logs
    last_log = db["logs"][-1]
    if last_log["event_type"] == "SECURITY_ALERT":
        print("SUCCESS: Security alert logged in audit trail.")
        print(f"Log Message: {last_log['description']}")
        print(f"ODPC Report Status: {sec_res.get('odpc_report')}")
    else:
        print("FAILURE: Alert not found in logs.")

if __name__ == "__main__":
    run_verification()
