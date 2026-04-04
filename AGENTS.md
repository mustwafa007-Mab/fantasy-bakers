# AGENTS.md

## Cursor Cloud specific instructions

### Architecture Overview

Fantasy AI ERP is a bakery management system with three main services:

| Service | Path | Port | Command |
|---|---|---|---|
| FastAPI Backend | `/workspace/app.py` | 8000 | `python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload` |
| Frontend (React+TS 3D Showroom) | `/workspace/frontend/` | 5173 | `npm run dev` (from `frontend/`) |
| Showroom (React+JS 3D Viewer) | `/workspace/showroom/` | 5173 | `npm run dev` (from `showroom/`) — standalone, no backend dependency |

### Key Gotchas

- **`uvicorn` not on PATH**: pip installs to `~/.local/bin` which is not in the default shell PATH. Use `python3 -m uvicorn` instead, or ensure `~/.local/bin` is on PATH.
- **In-memory database**: The backend falls back to an in-memory dict when `SUPABASE_URL`/`SUPABASE_KEY` are not configured (or invalid). This is the expected local dev mode — no external DB needed.
- **`.env` file**: Copy `.env.example` to `.env` for local dev. The placeholder Supabase credentials will cause a connection failure that the app gracefully handles.
- **Frontend proxy**: The `frontend/` Vite config proxies `/api` to `http://127.0.0.1:8000`. The backend must be running for the frontend to fetch product data.

### Lint / Test / Build

- **Lint**: `npm run lint` in `frontend/` and `showroom/` (ESLint). No Python linter configured.
- **Build**: `npm run build` in `frontend/` (runs `tsc -b && vite build`) and `showroom/` (runs `vite build`).
- **Tests**: `verify.py` and `stress_test.py` at root are legacy integration scripts that reference removed functions — they do not run cleanly against the current `app.py`. Use `curl` against the running backend to test API endpoints manually.
- **API docs**: FastAPI auto-generates Swagger UI at `http://localhost:8000/docs`.
