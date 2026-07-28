-- Migration: Add email, raw_text, and resume_path to candidates table
-- The upload_resume endpoint inserts these fields but the original schema omitted them.

ALTER TABLE public.candidates
    ADD COLUMN IF NOT EXISTS email       text        NULL,
    ADD COLUMN IF NOT EXISTS raw_text    text        NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS resume_path text        NULL DEFAULT '';

-- Index for fast lookup by email (used by mailing agent)
CREATE INDEX IF NOT EXISTS candidates_email_idx ON public.candidates (email);

COMMENT ON COLUMN public.candidates.email       IS 'Candidate email extracted from parsed resume';
COMMENT ON COLUMN public.candidates.raw_text    IS 'Full plain-text content extracted from the uploaded resume PDF';
COMMENT ON COLUMN public.candidates.resume_path IS 'Local filesystem path to the uploaded resume file';
