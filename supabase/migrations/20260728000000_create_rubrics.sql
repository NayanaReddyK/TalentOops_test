-- Migration: Create rubrics table for role-based evaluation standards and competencies
CREATE TABLE IF NOT EXISTS public.rubrics (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id           TEXT NOT NULL,
    role_title       TEXT NOT NULL DEFAULT 'Senior Backend Engineer',
    standard         TEXT NOT NULL DEFAULT 'Strong experience with async Python, distributed systems, and SQL optimization',
    competencies     JSONB NOT NULL DEFAULT '[{"competency_id": "python_backend", "keywords": ["python", "async", "fastapi"]}, {"competency_id": "system_design", "keywords": ["architecture", "scaling", "distributed"]}, {"competency_id": "databases", "keywords": ["sql", "postgres", "indexing"]}]'::jsonb,
    difficulty_level TEXT DEFAULT 'L2',
    content_hash     TEXT DEFAULT '',
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS rubrics_run_id_idx ON public.rubrics (run_id);

ALTER TABLE public.rubrics ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for rubrics" ON public.rubrics;
CREATE POLICY "Allow all for rubrics" ON public.rubrics FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
