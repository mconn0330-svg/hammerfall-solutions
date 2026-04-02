-- Hammerfall Brain — Core Memory Table
-- Lives in the hammerfall-brain Supabase project (NOT per-app projects)

create table if not exists helm_memory (
  id uuid primary key default gen_random_uuid(),
  project text not null,
  agent text not null,
  memory_type text not null check (memory_type in ('behavioral', 'scratchpad', 'archive', 'sync', 'monologue', 'coherence_check', 'external_knowledge')),
  -- behavioral: architectural decisions, preferences, key learnings
  -- scratchpad: active session working memory (flushed at session end)
  -- archive: long-term archived entries
  -- sync: entries pending sync to Core Helm
  -- monologue: inner monologue entries (Phase 2 — DGX Spark daemon)
  -- coherence_check: behavioral coherence audit results (Phase 2)
  -- external_knowledge: domain research from external sources (Phase 3)
  content text not null,
  sync_ready boolean default false,
  synced_to_core boolean default false,
  session_date date default current_date,
  created_at timestamptz default now()
);

-- Index for common query patterns
create index idx_helm_memory_project on helm_memory(project);
create index idx_helm_memory_sync_ready on helm_memory(sync_ready) where sync_ready = true;
create index idx_helm_memory_type on helm_memory(project, agent, memory_type);

-- Enable RLS (service role key bypasses all policies)
alter table helm_memory enable row level security;

-- Service role has full access (used by Helm agents)
create policy "service_role_full_access" on helm_memory
  using (true)
  with check (true);
