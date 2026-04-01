# Fantasy Bakery 3D Showroom — Agent Roles

## Antigravity (Engine)
**Owns everything inside `<Canvas />`.**

| File | Responsibility |
|------|---------------|
| `src/components/ShowroomCanvas.jsx` | Root `<Canvas />`, lights, environment |
| `src/components/ProductViewer.jsx` | GLB loading, rotation loop, shader overlay |
| `src/shaders/plasticWrap.glsl.js` | GLSL plastic-wrap shader |
| `src/store/useShowroomStore.js` | **Writes** `meshLoaded`, `rotationDeg`, `facingCamera` |
| `public/models/*.glb` | 3D assets (from Meshy AI) |

### Antigravity Rules
- Call `useShowroomStore.getState().setMeshLoaded(true)` after GLB resolves.
- All rotation is in `useFrame` — never manipulate rotation from outside the Canvas.
- GLSL changes stay in `plasticWrap.glsl.js`. No inline shader strings elsewhere.
- **Do not touch** `app.py`, `static/`, or `ProductSelector.jsx` (UI stub owned by Cursor).

---

## Cursor (UI Layer)
**Owns the 2D interface and FastAPI routes.**

| File | Responsibility |
|------|---------------|
| `src/components/ProductSelector.jsx` | Product switching UI panel |
| `src/store/useShowroomStore.js` | **Writes** `activeProduct` |
| `../../app.py` | FastAPI backend routes |
| `../../static/` | HTML/CSS/JS customer & admin pages |

### Cursor Rules
- Switch products via `setProduct('bread' | 'sugarRolls' | 'buns')` — **never** mutate the mesh directly.
- Read `meshLoaded` from the store to show/hide loading states.
- **Do not touch** `ShowroomCanvas.jsx`, `ProductViewer.jsx`, or shader files.

---

## Shared State Bridge

```
Zustand store: src/store/useShowroomStore.js
```

```
Cursor writes ──► activeProduct ──► Antigravity reads (switches GLB)
Antigravity writes ──► meshLoaded, rotationDeg, facingCamera ──► Cursor reads (UI states)
```

## `// [AGENT NOTE]:` Convention
All cross-boundary concerns are tagged `// [AGENT NOTE]:` — grep for this to surface every handoff point without manual hunting.
