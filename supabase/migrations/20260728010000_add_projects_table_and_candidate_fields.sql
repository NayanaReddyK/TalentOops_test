-- Migration: Add projects table and structured section columns to candidates table

-- 1. Create projects table
CREATE TABLE IF NOT EXISTS public.projects (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id TEXT NOT NULL REFERENCES public.candidates(id) ON DELETE CASCADE,
    title        TEXT NOT NULL,
    description  TEXT DEFAULT '',
    technologies JSONB DEFAULT '[]'::jsonb,
    url          TEXT DEFAULT '',
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Index for candidate_id lookup on projects
CREATE INDEX IF NOT EXISTS projects_candidate_id_idx ON public.projects (candidate_id);

-- 2. Add structured resume section columns to candidates table
ALTER TABLE public.candidates
    ADD COLUMN IF NOT EXISTS skills     JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS experience JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS education  JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS phone      TEXT  DEFAULT '',
    ADD COLUMN IF NOT EXISTS summary    TEXT  DEFAULT '';

COMMENT ON TABLE  public.projects             IS 'Candidate projects extracted from resume section';
COMMENT ON COLUMN public.candidates.skills     IS 'Extracted candidate technical & soft skills';
COMMENT ON COLUMN public.candidates.experience IS 'Extracted work experience entries';
COMMENT ON COLUMN public.candidates.education  IS 'Extracted education & degree entries';
COMMENT ON COLUMN public.candidates.phone      IS 'Candidate phone number extracted from resume';
COMMENT ON COLUMN public.candidates.summary    IS 'Candidate resume professional summary';
