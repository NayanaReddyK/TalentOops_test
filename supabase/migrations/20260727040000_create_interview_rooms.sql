-- Migration: Create interview_rooms table (replaces Google Meet links)
-- Purpose  : Each scheduled interview gets a self-hosted room URL instead
--            of a Google Meet link. The room lifecycle (SCHEDULED → WAITING →
--            ACTIVE → COMPLETED) is managed by app/rooms/room_manager.py.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'room_status') THEN
        CREATE TYPE public.room_status AS ENUM (
            'SCHEDULED',
            'WAITING',
            'ACTIVE',
            'COMPLETED'
        );
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.interview_rooms (
    room_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id  TEXT NOT NULL,
    interview_id  TEXT NOT NULL,
    room_url      TEXT NOT NULL,
    status        public.room_status NOT NULL DEFAULT 'SCHEDULED',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at    TIMESTAMPTZ,
    ended_at      TIMESTAMPTZ,
    metadata      JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS interview_rooms_interview_idx ON public.interview_rooms (interview_id);
CREATE INDEX IF NOT EXISTS interview_rooms_candidate_idx ON public.interview_rooms (candidate_id);
CREATE INDEX IF NOT EXISTS interview_rooms_status_idx    ON public.interview_rooms (status);

-- Enable Row Level Security
ALTER TABLE public.interview_rooms ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow anon all for interview_rooms" ON public.interview_rooms;
CREATE POLICY "Allow anon all for interview_rooms"
ON public.interview_rooms
FOR ALL
TO anon, authenticated
USING (true)
WITH CHECK (true);
