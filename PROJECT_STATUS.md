# Fantasy Bakery - Project Status & Handoff

## Current State of UI Overhaul
- **Main Landing Page (`static/index.html`)**: Successfully rebuilt. Replaced bloated NicePage framework with a premium, lightning-fast, hand-coded Vanilla HTML/CSS page featuring a modern aesthetic and parallax imagery.
- **3D Showroom (`showroom/`)**: Architecture successfully overhauled. 
  - Migrated from heavy, pre-computed `.glb` meshes to highly-performant **Procedural Geometry** (`<RoundedBox>`).
  - Implemented dynamic **WebP PBR Texture Mapping** (Albedo, Roughness, Displacement) generated from static high-res images using our `make_textures.js` script.
  - Upgraded the `ProductSelector` interface to a premium glassmorphic design with gold/purple branding.
- **Backend (`app.py`)**: Cleaned up infrastructure. Removed outdated AI and logistics bloat to streamline the FastAPI server for production deployment.

## Next Development Steps
1. **Admin Dashboard Refactor**: Apply the new premium "Dark/Gold" design system to `static/admin.html` to unify the brand identity.
2. **Remaining Textures**: Process the source images for the remaining products (Sugar Rolls, Buns) through `showroom/make_textures.js` to create their optimal WebP maps.
3. **API Routing Validation**: Ensure the production frontend correctly points to the Railway deployment URL (`https://api.mxtwafa.com`) instead of local testing endpoints.

---

## Cursor Security Checkup Prompt
*Copy and paste the text below into Cursor to initiate a comprehensive security audit.*

```text
Please perform a comprehensive Security Audit and Checkup on this Fantasy Bakery codebase. 

Specifically, review the following critical areas and identify any vulnerabilities:

1. **Backend API (`app.py` & FastAPI configuration)**:
   - Analyze database helper functions (`db_select`, `db_insert`, `db_update`) for potential SQL Injection vulnerabilities or unsafe queries to Supabase.
   - Review the CORS configuration. It is currently set to `allow_origins=["*"]`. Help me restrict this safely to `mxtwafa.com`.
   - Audit all exposed routes (like `/api/inventory` or `/api/orders`) for proper input validation to prevent malicious payloads.

2. **Environment Variables & Secrets**:
   - Scan the codebase to ensure no `SUPABASE_KEY` or other sensitive tokens are hardcoded.
   - Verify that `.env` is properly excluded in `.gitignore`.

3. **Frontend Security**:
   - Check for Cross-Site Scripting (XSS) risks in `static/index.html` and `static/admin.html`, particularly where API data is rendered into the DOM.

4. **Supabase Database Security**:
   - Review how we are exposing our database. Since we use an `anon` key on the frontend/backend, provide recommendations for setting up Row Level Security (RLS) policies so users cannot maliciously drop or manipulate tables.

Please output a prioritized list of vulnerabilities (High, Medium, Low) and provide the exact code patches required to secure the application for production.
```
