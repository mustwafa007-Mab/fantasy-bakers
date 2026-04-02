# Fantasy Bakery - Security & Deployment Runbook

This runbook outlines the critical operations required to keep the Fantasy Bakery application secure across environments (Development, Staging, Production).

## 1. Secrets Management
The `.env` file should **never** be committed to version control. The `.gitignore` is configured to ignore `.env*` but keep `.env.example`.

### Rotating Compromised Keys
If a `.env` file containing a real `SUPABASE_KEY` or `ADMIN_API_KEY` was ever accidentally pushed or shared:
1. Log in to the [Supabase Dashboard](https://app.supabase.com).
2. Navigate to **Project Settings > API**.
3. Re-generate the `anon` and `service_role` JWT secrets.
4. Immediately update your local `.env` and the environment variables in your hosting provider (e.g., Railway).

## 2. Environment Variables Checklist
Before deploying to Production, ensure the following environment variables are set securely in your hosting provider's dashboard:

| Variable | Development (Local) | Production |
| :--- | :--- | :--- |
| `SUPABASE_URL` | e.g. `https://xyz.supabase.co` | Same as dev |
| `SUPABASE_KEY` | `your-anon-or-service-key` | `your-production-key` |
| `ADMIN_API_KEY` | (leave blank/unset) | A long, strongly generated cryptographic secret string (e.g. 64-chars). Used to authenticate sensitive admin API routes. |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:8000` | `https://mxtwafa.com,https://api.mxtwafa.com` |
| `TRUSTED_HOSTS` | `localhost,127.0.0.1` | `mxtwafa.com,api.mxtwafa.com` |

## 3. Row Level Security (RLS) in Supabase
When using Supabase, you must enable RLS on all tables to prevent unauthorized data access/mutations by anyone who possesses the public `anon` key.

1. Go to **Authentication > Policies** in Supabase.
2. Click **Enable RLS** on every table (`inventory`, `procurements`, `pending_posts`, `ledger`, `logs`, `orders`).
3. Set your backend FastAPI service to use the `service_role` key (which bypasses RLS).
4. **CRITICAL**: Do NOT create any public access policies for sensitive tables (like `ledger` or `procurements`). The FastAPI backend will handle all read/write operations securely using its `service_role` key.

## 4. Admin API Authentication
FastAPI mutating routes (Approvals, Alerts, Uploads) are protected via the `X-Admin-Key` header.
- When calling these local endpoints during development (if `ADMIN_API_KEY` is not set), you don't need a header.
- In production, you must inject the `ADMIN_API_KEY` into your Frontend GUI or use Postman/cURL with the header: `X-Admin-Key: your_secure_key`.
