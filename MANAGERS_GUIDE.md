# Fantasy AI ERP - Manager's Guide

## Welcome
This system automates inventory, marketing, and delivery. As a manager, your role is to **approve** the AI's suggestions to ensure quality and compliance.

## 1. Inventory & Stock (Predictive Ledger)
The system automatically tracks flour, yeast, and sugar.
- **Alerts**: You will be notified when stock is predicted to run out within 48 hours.
- **Action**: Check the `Procurement Suggestions` on your dashboard.
- **Approval**: Click "Approve" (Endpoint `POST /inventory/approve_order`) to confirm the purchase. This updates the `system_logs` for KEBS audits.

## 2. Marketing (AI Social Pipeline)
Staff upload raw videos of the bakery. The AI generates captions in English and Coastal Swahili.
- **Review**: Go to `Pending Posts`.
- **Content**: Check the Swahili slang (e.g., "Vibe la Pwani") and hashtags.
- **Approval**: If good, click "Approve" (Endpoint `POST /marketing/approve_post`).

## 3. Delivery (Tuktuk Logistics)
The system assigns Tuktuks based on a **Freshness Score**.
- **The Goal**: Deliver bread at >50°C.
- **Score Calculation**: `Score = 100 - (TravelTime * 1.5)`.
- If a delivery score is too low, the system might flag it for manual review.

## 4. Security & Compliance
- **Data Privacy**: Customer phone numbers are masked (e.g., `+2547...123`) in the system to comply with ODPC.
- **Breach Protocol**: If multiple failed access attempts occur, the system triggers a `SECURITY_ALERT` and prepares a report.
- **Audit**: All your approvals are logged.

## Quick API Reference (MVP)
- **Status Check**: `GET /`
- **Predict Stock**: `GET /inventory/predict_procurement`
- **Generate Caption**: `POST /marketing/generate_content`
- **Optimize Delivery**: `GET /logistics/find_best_tuktuk`
