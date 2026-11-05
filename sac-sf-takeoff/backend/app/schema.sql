-- Keystone Navigator schema (PostgreSQL 14+)
-- `origin` = 'seed' for rows loaded from the proposal, 'curated' for rows added or edited in the UI.

DROP TABLE IF EXISTS chat_message, guide_progress, stage_component, component, stage, phase,
  journey_step, persona, insight_question, insight_dashboard,
  attribute, data_entity, subject_area, domain, kpi, conformed_dim, data_layer CASCADE;
DROP VIEW IF EXISTS search_index;

CREATE TABLE phase (
  num INT PRIMARY KEY, name TEXT NOT NULL, months TEXT, output TEXT
);

CREATE TABLE stage (
  id SERIAL PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  seq INT NOT NULL,
  name TEXT NOT NULL,
  phase INT REFERENCES phase(num),
  slide INT,
  lead_role TEXT, mode TEXT, gate TEXT, summary TEXT,
  key_steps JSONB DEFAULT '[]', outputs JSONB DEFAULT '[]', extra JSONB DEFAULT '{}'
);

-- agents, skills, tools, frameworks (Helio services), snowflake components
CREATE TABLE component (
  id SERIAL PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('agent','skill','tool','framework','snowflake')),
  name TEXT NOT NULL,
  category TEXT,
  description TEXT,
  origin TEXT DEFAULT 'seed',
  UNIQUE (kind, name)
);

CREATE TABLE stage_component (
  stage_id INT REFERENCES stage(id) ON DELETE CASCADE,
  component_id INT REFERENCES component(id) ON DELETE CASCADE,
  parent_id INT REFERENCES component(id) ON DELETE CASCADE, -- agent that uses the skill/tool
  seq INT DEFAULT 0
);
CREATE INDEX ON stage_component(stage_id);
CREATE INDEX ON stage_component(component_id);

CREATE TABLE guide_progress (
  session_id TEXT NOT NULL, stage_code TEXT NOT NULL, step_index INT NOT NULL,
  done BOOLEAN DEFAULT TRUE, updated_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (session_id, stage_code, step_index)
);

-- Persona journeys (slides 18-20)
CREATE TABLE persona (
  id SERIAL PRIMARY KEY, code TEXT UNIQUE, segment TEXT, name TEXT NOT NULL, roles TEXT, wants TEXT,
  journey TEXT, goals TEXT, pains TEXT, kpis TEXT, note TEXT, slide INT, origin TEXT DEFAULT 'seed'
);
CREATE TABLE journey_step (
  id SERIAL PRIMARY KEY, persona_id INT REFERENCES persona(id) ON DELETE CASCADE,
  seq INT, name TEXT NOT NULL, question TEXT, experience TEXT, metrics TEXT, doing TEXT, today TEXT,
  origin TEXT DEFAULT 'seed'
);

-- Insights (slides 21-24)
CREATE TABLE insight_dashboard (
  id SERIAL PRIMARY KEY, code TEXT UNIQUE, name TEXT NOT NULL, audience TEXT, roles TEXT, surface TEXT,
  headline TEXT, guardrail TEXT, persona_code TEXT, slide INT, origin TEXT DEFAULT 'seed'
);
CREATE TABLE insight_question (
  id SERIAL PRIMARY KEY, dashboard_id INT REFERENCES insight_dashboard(id) ON DELETE CASCADE,
  seq INT, kind TEXT, question TEXT, answer TEXT, origin TEXT DEFAULT 'seed'
);

-- Industry data model (slides 25-29)
CREATE TABLE domain (id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL, source TEXT, origin TEXT DEFAULT 'seed');
CREATE TABLE subject_area (
  id SERIAL PRIMARY KEY, domain_id INT REFERENCES domain(id) ON DELETE CASCADE,
  num INT, name TEXT NOT NULL, entities TEXT, origin TEXT DEFAULT 'seed'
);
CREATE TABLE data_layer (name TEXT PRIMARY KEY, seq INT, description TEXT);
CREATE TABLE conformed_dim (id SERIAL PRIMARY KEY, name TEXT UNIQUE, origin TEXT DEFAULT 'seed');
CREATE TABLE data_entity (
  id SERIAL PRIMARY KEY, model TEXT, name TEXT NOT NULL, kind TEXT CHECK (kind IN ('fact','dim')),
  type TEXT, description TEXT, subject_area_id INT REFERENCES subject_area(id) ON DELETE SET NULL,
  origin TEXT DEFAULT 'seed'
);
CREATE TABLE attribute (
  id SERIAL PRIMARY KEY, entity_id INT REFERENCES data_entity(id) ON DELETE CASCADE,
  name TEXT NOT NULL, role TEXT, description TEXT, origin TEXT DEFAULT 'seed'
);
CREATE TABLE kpi (
  id SERIAL PRIMARY KEY, domain TEXT, name TEXT NOT NULL, formula TEXT, audiences TEXT,
  source_fact TEXT, owner TEXT, grain TEXT, certified BOOLEAN DEFAULT TRUE, origin TEXT DEFAULT 'seed'
);

CREATE TABLE chat_message (
  id SERIAL PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, payload JSONB, created_at TIMESTAMPTZ DEFAULT now()
);

-- One searchable index across everything, used by the conversational assistant
CREATE VIEW search_index AS
  SELECT 'stage' AS kind, s.code AS ref, s.name AS title,
         concat_ws(' ', s.summary, s.lead_role, s.gate, s.key_steps::text, s.outputs::text) AS body
    FROM stage s
  UNION ALL SELECT c.kind, c.id::text, c.name, concat_ws(' ', c.category, c.description) FROM component c
  UNION ALL SELECT 'persona', p.id::text, p.name, concat_ws(' ', p.segment, p.roles, p.wants, p.goals, p.pains, p.kpis) FROM persona p
  UNION ALL SELECT 'journey_step', j.persona_id::text, j.name, concat_ws(' ', j.question, j.experience, j.metrics, j.doing) FROM journey_step j
  UNION ALL SELECT 'dashboard', d.id::text, d.name, concat_ws(' ', d.audience, d.roles, d.surface, d.headline) FROM insight_dashboard d
  UNION ALL SELECT 'insight', q.dashboard_id::text, q.question, concat_ws(' ', q.kind, q.answer) FROM insight_question q
  UNION ALL SELECT 'subject_area', sa.id::text, sa.name, sa.entities FROM subject_area sa
  UNION ALL SELECT 'entity', e.id::text, e.name, concat_ws(' ', e.model, e.type, e.description) FROM data_entity e
  UNION ALL SELECT 'kpi', k.id::text, k.name, concat_ws(' ', k.domain, k.formula, k.source_fact) FROM kpi k;
