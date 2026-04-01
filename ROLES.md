# ROLES — Fantasy Bakers

This repo may contain **multiple runtimes**. Ownership below keeps the **Next.js 15** showroom and **FastAPI** ERP aligned.

---

## Cursor (Architect)

Owns:

- **Next.js 15** App Router structure under **`web/`** (`app/`, `components/`, `store/`, Tailwind).
- **Zustand** store (`web/store/useStore.ts`) and all **non-Canvas** UI (tabs, cart bar, layout, Framer Motion around the shell).
- **FastAPI** routes in **`app.py`** (inventory, logistics, marketing, etc.) and deployment wiring.
- **Environment**: document `NEXT_PUBLIC_*` in `.env.local`; **never** hardcode the WhatsApp number in components — use `process.env.NEXT_PUBLIC_WHATSAPP_NUMBER` (see `web/lib/whatsapp.ts`).

Does **not** own: custom Three.js shaders, deep lighting tuning inside the canvas beyond scaffolding (unless you collapse roles).

---

## 3D Canvas (Antigravity / Engine)

Owns everything **inside** `<Canvas>` after handoff:

- R3F scene graph, **GLB** loading strategy, materials, lighting tweaks, `OrbitControls` behavior if changed from the foundation.
- Wiring models from **`web/public/models/`** to `Product.modelPath` in the store when assets exist.

Uses the **Zustand** API already defined; avoid prop-drilling scene state to the DOM — prefer store updates for cross-boundary flags if you extend the contract.

---

## Asset pipeline (intent)

**Gemini → Veo → Meshy → `/web/public/models/`** as `.glb` files (e.g. `white-bread.glb`, `sugar-rolls.glb`, `buns.glb`). Update `modelPath` in `web/store/useStore.ts` when each file lands.

---

## WhatsApp

Configure in **`web/.env.local`** (not committed by default):

```env
NEXT_PUBLIC_WHATSAPP_NUMBER=your_number
NEXT_PUBLIC_SITE_NAME=Fantasy Bakers
```

`NEXT_PUBLIC_WHATSAPP_NUMBER` must be digits (country code, no `+`). The UI builds `wa.me` links only from this env.

---

## Related paths

| Area | Path |
|------|------|
| Next showroom | `web/` |
| GLB drop folder | `web/public/models/` |
| Legacy Vite / FastAPI showroom (if used) | `frontend/`, `app.py` |

---

## Audit comments

For cross-agent boundaries, prefer grepping **`[AGENT NOTE]`** in code when you introduce them.
