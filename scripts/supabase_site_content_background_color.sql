-- Run once in Supabase → SQL Editor (matches globals.css --cream #fdf6ec).
-- New rows get a safe cream tint; cleared values (NULL) let the Next app use body background only.

ALTER TABLE public.site_content
  ADD COLUMN IF NOT EXISTS background_color text DEFAULT '#fdf6ec';

COMMENT ON COLUMN public.site_content.background_color IS
  'Optional landing page background hex. NULL = Next.js does not set inline background (body --cream applies).';
