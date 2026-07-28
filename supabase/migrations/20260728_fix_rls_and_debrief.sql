-- Migration: Fix RLS policies for candidates, rubrics, scorecards, hr_debrief_sessions, and ensure debrief_id column exists

-- 1. Enable RLS and add public access policies for candidates
ALTER TABLE IF EXISTS public.candidates ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for candidates" ON public.candidates;
CREATE POLICY "Allow all for candidates" ON public.candidates FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- 2. Enable RLS and add public access policies for rubrics
ALTER TABLE IF EXISTS public.rubrics ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for rubrics" ON public.rubrics;
CREATE POLICY "Allow all for rubrics" ON public.rubrics FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- 3. Enable RLS and add public access policies for scorecards
ALTER TABLE IF EXISTS public.scorecards ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for scorecards" ON public.scorecards;
CREATE POLICY "Allow all for scorecards" ON public.scorecards FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- 4. Enable RLS and add public access policies for projects
ALTER TABLE IF EXISTS public.projects ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for projects" ON public.projects;
CREATE POLICY "Allow all for projects" ON public.projects FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- 5. Enable RLS and add public access policies for interview_rooms
ALTER TABLE IF EXISTS public.interview_rooms ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for interview_rooms" ON public.interview_rooms;
CREATE POLICY "Allow all for interview_rooms" ON public.interview_rooms FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- 6. Enable RLS and add public access policies for interview_qa_logs
ALTER TABLE IF EXISTS public.interview_qa_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for interview_qa_logs" ON public.interview_qa_logs;
CREATE POLICY "Allow all for interview_qa_logs" ON public.interview_qa_logs FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- 7. Fix hr_debrief_sessions table schema to ensure debrief_id and all expected columns exist
CREATE TABLE IF NOT EXISTS public.hr_debrief_sessions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    debrief_id        TEXT UNIQUE NULL,
    interview_id      TEXT NOT NULL,
    candidate_id      TEXT NULL,
    meet_link         TEXT NULL,
    room_url          TEXT NULL,
    status            TEXT DEFAULT 'SCHEDULED',
    summary           TEXT DEFAULT '',
    knowledge_context JSONB DEFAULT '{}'::jsonb,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.hr_debrief_sessions ADD COLUMN IF NOT EXISTS debrief_id TEXT;
ALTER TABLE public.hr_debrief_sessions ADD COLUMN IF NOT EXISTS room_url TEXT DEFAULT '';
ALTER TABLE public.hr_debrief_sessions ADD COLUMN IF NOT EXISTS summary TEXT DEFAULT '';
ALTER TABLE public.hr_debrief_sessions ADD COLUMN IF NOT EXISTS knowledge_context JSONB DEFAULT '{}'::jsonb;
ALTER TABLE public.hr_debrief_sessions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all for hr_debrief_sessions" ON public.hr_debrief_sessions;
CREATE POLICY "Allow all for hr_debrief_sessions" ON public.hr_debrief_sessions FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
