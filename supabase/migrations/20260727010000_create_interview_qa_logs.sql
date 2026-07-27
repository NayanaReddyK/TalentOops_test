-- Create interview_qa_logs table for real-time Q&A turn logging
CREATE TABLE IF NOT EXISTS public.interview_qa_logs (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id                  TEXT NOT NULL,
    question_number             INT NOT NULL,
    question_text               TEXT NOT NULL,
    candidate_answer_transcript TEXT NOT NULL,
    confidence_score            FLOAT DEFAULT 0.0,
    metadata                    JSONB NOT NULL DEFAULT '{}'::jsonb,
    timestamp                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_id, question_number)
);

CREATE INDEX IF NOT EXISTS qa_logs_session_idx ON public.interview_qa_logs (session_id);

-- Enable Row Level Security (RLS) on interview_qa_logs
ALTER TABLE public.interview_qa_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow anon all for interview_qa_logs" ON public.interview_qa_logs;
CREATE POLICY "Allow anon all for interview_qa_logs" 
ON public.interview_qa_logs 
FOR ALL 
TO anon, authenticated 
USING (true) 
WITH CHECK (true);
