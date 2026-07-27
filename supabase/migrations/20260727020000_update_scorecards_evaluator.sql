-- Migration: Add detailed evaluator report JSONB columns to public.scorecards
ALTER TABLE public.scorecards 
    ADD COLUMN IF NOT EXISTS behavioral_metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS detailed_competencies JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS full_transcript_evaluations JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS final_recommendation JSONB NOT NULL DEFAULT '{}'::jsonb;
