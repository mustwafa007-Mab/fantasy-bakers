-- Run once in Supabase SQL editor. Stores homepage section order as JSON array.

CREATE TABLE IF NOT EXISTS public.site_layout (
  id text PRIMARY KEY DEFAULT 'main',
  components jsonb NOT NULL DEFAULT '["hero","products","showcase","map"]'::jsonb,
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.site_layout IS 'Single-row layout: ordered list of homepage section ids (hero, products, showcase, map).';
