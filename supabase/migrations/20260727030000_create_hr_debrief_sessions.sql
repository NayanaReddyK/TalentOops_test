-- Migration: Create hr_debrief_sessions table for Manager Agent Post-Interview HR Debrief System
CREATE TABLE IF NOT EXISTS public.hr_debrief_sessions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_id      TEXT NOT NULL,
    candidate_id      TEXT NOT NULL,
    meet_link         TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'Manager Agent Waiting',
    summary           TEXT DEFAULT '',
    knowledge_context JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (interview_id)
);

CREATE INDEX IF NOT EXISTS hr_debrief_interview_idx ON public.hr_debrief_sessions (interview_id);

-- Enable Row Level Security (RLS)
ALTER TABLE public.hr_debrief_sessions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow anon all for hr_debrief_sessions" ON public.hr_debrief_sessions;
CREATE POLICY "Allow anon all for hr_debrief_sessions"
ON public.hr_debrief_sessions
FOR ALL
TO anon, authenticated
USING (true)
WITH CHECK (true);
