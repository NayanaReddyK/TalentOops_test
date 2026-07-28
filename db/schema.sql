-- TalentOps Unified Pipeline Schema (Part 1 + Part 2)

create extension if not exists "pgcrypto";
create extension if not exists vector;

-- ============================================================================
-- Events (Append-only audit trail)
-- ============================================================================
create table if not exists public.events (
    id          uuid primary key default gen_random_uuid(),
    run_id      text not null,                 -- correlates all events of one pipeline run
    ts          timestamptz not null default now(),
    source      text not null,                 -- emitting node: 'manager' | 'sourcing' | 'screening' | etc.
    event_type  text not null,                 -- 'run_started' | 'route' | 'agent_started' | 'agent_completed' | 'run_completed'
    payload     jsonb not null default '{}'::jsonb
);

create index if not exists events_run_id_ts_idx on public.events (run_id, ts);
create index if not exists events_type_idx       on public.events (event_type);

-- ============================================================================
-- Rubrics (Frozen per run)
-- ============================================================================
create table if not exists public.rubrics (
    id            uuid primary key default gen_random_uuid(),
    run_id        text not null,                  -- one frozen rubric per run
    role_title    text default 'Senior Backend Engineer',
    content_hash  text default '',
    standard      text not null,
    competencies  jsonb not null default '[]'::jsonb,
    difficulty_level text default 'L2',
    created_at    timestamptz not null default now()
);

-- ============================================================================
-- Vector Store Embeddings (pgvector)
-- ============================================================================
create table if not exists public.embeddings (
    id          uuid primary key default gen_random_uuid(),
    run_id      text not null,
    kind        text not null,                    -- 'jd' | 'candidate'
    ref_id      text not null,
    embedding   vector(384),                      -- 384 dim matching text-embedding-3-small
    metadata    jsonb not null default '{}'::jsonb,
    created_at  timestamptz not null default now(),
    unique (run_id, kind, ref_id)
);

create index if not exists embeddings_run_kind_idx on public.embeddings (run_id, kind);
create index if not exists embeddings_hnsw_idx on public.embeddings using hnsw (embedding vector_cosine_ops);

-- Nearest-neighbour match function
create or replace function public.match_embeddings(
    p_run_id text, p_kind text, p_query vector(384), p_top_k int
)
returns table (ref_id text, score float, metadata jsonb)
language sql stable as $$
    select ref_id, 1 - (embedding <=> p_query) as score, metadata
    from public.embeddings
    where run_id = p_run_id and kind = p_kind
    order by embedding <=> p_query
    limit p_top_k;
$$;

-- ============================================================================
-- Roles, Candidates, Interviews, Scorecards, Demographics, Calibration, Comms
-- ============================================================================
create table if not exists public.roles (
    id                text primary key,
    jd                text not null,
    frozen            boolean default true,
    difficulty_level  text default 'L2',
    rubric            jsonb default '{}'::jsonb,
    created_at        timestamptz default now()
);

create table if not exists public.candidates (
    id           text primary key,
    role_id      text references public.roles(id) on delete cascade,
    name         text not null,
    email        text        null,                   -- extracted from resume PDF
    resume       text        default '',
    raw_text     text        default '',             -- full plain-text of the uploaded resume
    resume_path  text        default '',             -- local path to the uploaded file
    created_at   timestamptz default now()
);

create index if not exists candidates_email_idx on public.candidates (email);

create table if not exists public.interviews (
    id            text primary key,
    role_id       text,
    candidate_id  text,
    transcript    jsonb default '[]'::jsonb,
    questions     jsonb default '[]'::jsonb,
    created_at    timestamptz default now()
);

create table if not exists public.scorecards (
    id                         uuid primary key default gen_random_uuid(),
    interview_id               text,
    candidate_id               text,
    scorecard                  jsonb default '{}'::jsonb,
    behavioral_metrics         jsonb default '{}'::jsonb,
    detailed_competencies      jsonb default '[]'::jsonb,
    full_transcript_evaluations jsonb default '[]'::jsonb,
    final_recommendation       jsonb default '{}'::jsonb,
    created_at                 timestamptz default now()
);

create table if not exists public.demographics (
    id            uuid primary key default gen_random_uuid(),
    candidate_id  text unique,
    cohort        jsonb default '{}'::jsonb,
    created_at    timestamptz default now()
);

create table if not exists public.calibration (
    id            uuid primary key default gen_random_uuid(),
    interview_id  text,
    rtt_ms        float default 0.0,
    jitter_ms     float default 0.0,
    audio_level   float default 0.0,
    passed        boolean default true,
    created_at    timestamptz default now()
);

create table if not exists public.comms (
    id          uuid primary key default gen_random_uuid(),
    "to"        text not null,
    subject     text not null,
    body        text not null,
    status      text default 'sent',
    created_at  timestamptz default now()
);

create table if not exists public.interview_qa_logs (
    id                          uuid primary key default gen_random_uuid(),
    session_id                  text not null,
    question_number             int not null,
    question_text               text not null,
    candidate_answer_transcript text not null,
    confidence_score            float default 0.0,
    metadata                    jsonb not null default '{}'::jsonb,
    timestamp                   timestamptz not null default now(),
    unique (session_id, question_number)
);

create index if not exists qa_logs_session_idx on public.interview_qa_logs (session_id);

create table if not exists public.hr_debrief_sessions (
    id                uuid primary key default gen_random_uuid(),
    interview_id      text not null,
    candidate_id      text not null,
    meet_link         text not null,
    status            text not null default 'Manager Agent Waiting',
    summary           text default '',
    knowledge_context jsonb not null default '{}'::jsonb,
    created_at        timestamptz not null default now(),
    unique (interview_id)
);

create index if not exists hr_debrief_interview_idx on public.hr_debrief_sessions (interview_id);
