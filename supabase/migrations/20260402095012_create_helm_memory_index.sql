-- Hammerfall Brain — Memory Index Table
-- Table of contents for helm_memory. Helm reads this first.
-- Prevents full table scans. Enables selective category loading.

create table if not exists helm_memory_index (
  id uuid primary key default gen_random_uuid(),
  project text not null,
  agent text not null,
  category text not null,
  summary text not null,        -- 2-3 sentences: what belongs in this category
  entry_count integer default 0, -- updated when entries are added
  date_range_start date,
  date_range_end date,
  last_updated timestamptz default now(),
  unique(project, agent, category)
);

create index idx_memory_index_project on helm_memory_index(project, agent);

alter table helm_memory_index enable row level security;
create policy "service_role_full_access" on helm_memory_index
  using (true) with check (true);

-- Seed categories for hammerfall-solutions/helm at migration time
insert into helm_memory_index (project, agent, category, summary) values
  ('hammerfall-solutions', 'helm', 'architecture',
   'Structural decisions about the pipeline and system design. Covers what was built, what was cut, and the reasoning behind each architectural choice.'),
  ('hammerfall-solutions', 'helm', 'environment',
   'Tooling, credentials, and platform-specific behaviour. Windows/WSL quirks, Docker conflicts, Git credential issues, Supabase key formats.'),
  ('hammerfall-solutions', 'helm', 'decisions',
   'Explicit choices made during sessions with reasoning documented. The canonical record of what was decided and why.'),
  ('hammerfall-solutions', 'helm', 'people',
   'Maxwell working style, correction patterns, and preferences. How to work with Maxwell effectively.'),
  ('hammerfall-solutions', 'helm', 'projects',
   'Per-project summaries, status, and key outcomes. One entry per project lifecycle event.'),
  ('hammerfall-solutions', 'helm', 'patterns',
   'Recurring approaches that work, anti-patterns to avoid, and things that keep coming up across projects.'),
  ('hammerfall-solutions', 'helm', 'north_stars',
   'Non-negotiables, core principles, and things that must not change under pressure. The foundational operating rules.');
