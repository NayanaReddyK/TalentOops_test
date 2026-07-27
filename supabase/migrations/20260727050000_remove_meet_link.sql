-- Migration: Remove meet_link from hr_debrief_sessions, add room_url
-- ─────────────────────────────────────────────────────────────────────────────
-- ⚠️  CAREFUL EXECUTION GUIDE (read before applying to a live DB)
-- ─────────────────────────────────────────────────────────────────────────────
--
-- STEP 1 — Backup first (ALWAYS do this before schema changes)
--   pg_dump --schema-only -t public.hr_debrief_sessions \
--       "$DATABASE_URL" > backup_hr_debrief_before_remove_meet_link.sql
--
-- STEP 2 — Add new column as NULLABLE (non-breaking, zero downtime)
--   ALTER TABLE public.hr_debrief_sessions
--       ADD COLUMN IF NOT EXISTS room_url TEXT DEFAULT '';
--   → This is safe to run while the app is live. Old rows get an empty string.
--
-- STEP 3 — Backfill existing rows (optional — only if you want to preserve data)
--   UPDATE public.hr_debrief_sessions
--       SET room_url = CONCAT('http://localhost:8000/interview/', id::text)
--   WHERE room_url IS NULL OR room_url = '';
--
-- STEP 4 — Deploy the new app code (app no longer writes meet_link).
--   Make sure the new code is in place and verified working BEFORE step 5.
--
-- STEP 5 — Drop the old column (breaking change — only after code is deployed)
--   ALTER TABLE public.hr_debrief_sessions
--       DROP COLUMN IF EXISTS meet_link;
--
-- STEP 6 — Verify
--   SELECT column_name FROM information_schema.columns
--   WHERE table_name = 'hr_debrief_sessions'
--   AND table_schema = 'public';
--   → Should list room_url, NOT meet_link.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- The statements below execute all steps in a safe, ordered transaction.
-- For a live Supabase project, run steps 2-4 separately (see guide above).
-- ─────────────────────────────────────────────────────────────────────────────

BEGIN;

-- Step 2: Add room_url (nullable, safe to run while app is live)
ALTER TABLE public.hr_debrief_sessions
    ADD COLUMN IF NOT EXISTS room_url TEXT NOT NULL DEFAULT '';

-- Step 3: Backfill existing rows with a sensible placeholder URL
UPDATE public.hr_debrief_sessions
    SET room_url = CONCAT('http://localhost:8000/interview/', id::text)
WHERE room_url = '';

-- Step 5: Drop old meet_link column (run AFTER new code is deployed)
ALTER TABLE public.hr_debrief_sessions
    DROP COLUMN IF EXISTS meet_link;

COMMIT;
