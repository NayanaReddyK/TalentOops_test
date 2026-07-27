-- Enable pgvector extension for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Create public.embeddings table if it does not exist
CREATE TABLE IF NOT EXISTS public.embeddings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      TEXT NOT NULL,
    kind        TEXT NOT NULL,
    ref_id      TEXT NOT NULL,
    embedding   vector(384),
    metadata    JSONB DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT embeddings_run_kind_ref_id_key UNIQUE (run_id, kind, ref_id)
);

-- Ensure unique constraint exists if table was created previously without it
ALTER TABLE public.embeddings
    DROP CONSTRAINT IF EXISTS embeddings_run_kind_ref_id_key;
ALTER TABLE public.embeddings
    ADD CONSTRAINT embeddings_run_kind_ref_id_key UNIQUE (run_id, kind, ref_id);

-- Create HNSW index on embeddings for fast cosine similarity search
CREATE INDEX IF NOT EXISTS embeddings_hnsw_idx 
ON public.embeddings 
USING hnsw (embedding vector_cosine_ops);

-- Enable Row Level Security (RLS) on embeddings table
ALTER TABLE public.embeddings ENABLE ROW LEVEL SECURITY;

-- Allow anon and authenticated users full access to embeddings for dev/prod service usage
DROP POLICY IF EXISTS "Allow anon all for embeddings" ON public.embeddings;
CREATE POLICY "Allow anon all for embeddings" 
ON public.embeddings 
FOR ALL 
TO anon, authenticated 
USING (true) 
WITH CHECK (true);

-- Create public.events table if it does not exist
CREATE TABLE IF NOT EXISTS public.events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id        TEXT NULL,
    source        TEXT NULL,
    event_type    TEXT NOT NULL,
    candidate_id  TEXT NULL,
    ts            TIMESTAMPTZ DEFAULT NOW(),
    payload       JSONB DEFAULT '{}'::jsonb
);

-- Ensure run_id, source, event_type, candidate_id, ts, and payload columns exist if table was created previously
ALTER TABLE public.events ADD COLUMN IF NOT EXISTS run_id TEXT;
ALTER TABLE public.events ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE public.events ADD COLUMN IF NOT EXISTS event_type TEXT;
ALTER TABLE public.events ADD COLUMN IF NOT EXISTS candidate_id TEXT;
ALTER TABLE public.events ADD COLUMN IF NOT EXISTS ts TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE public.events ADD COLUMN IF NOT EXISTS payload JSONB DEFAULT '{}'::jsonb;

-- Enable Row Level Security (RLS) on events table
ALTER TABLE public.events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow anon insert/select for events" ON public.events;
CREATE POLICY "Allow anon insert/select for events" 
ON public.events 
FOR ALL 
TO anon, authenticated 
USING (true) 
WITH CHECK (true);
