-- FlyHigh Navigator schema (PostgreSQL 14+)
-- `origin` = 'seed' for rows loaded from the proposal, 'curated' for rows added or edited in the UI.

DROP TABLE IF EXISTS taf_scenario_run, taf_upload, taf_result, taf_run, taf_case, aw_triage, aw_test_type, aw_mapping, aw_module, aw_defect, aw_result, aw_cycle, aw_cicd, aw_plan, aw_release, aw_device, aw_engine,
  aw_script, aw_component, aw_dataset, aw_case, aw_suite, aw_story,
  pmo_readiness, pmo_check, pmo_kpi, pmo_usecase, pmo_raid, pmo_estimate, pb_doc,
  skill_execution, skill_run, gate_decision, section_round, lens_role, lens, access_rule, pursuit_stage, pursuit_artefact, pursuit_skill, pursuit_ref,
  kit_template, kit_sheet, kit_row, response_section, rubric_criterion, section_score, section_musthave,
  chat_message, guide_progress, stage_component, component, stage, phase,
  journey_step, persona, insight_question, insight_dashboard,
  attribute, data_entity, subject_area, domain, kpi, conformed_dim, data_layer CASCADE;
DROP VIEW IF EXISTS search_index CASCADE;

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

-- agents, skills, tools, frameworks (accelerator services), snowflake components
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

-- Persona journeys
CREATE TABLE persona (
  id SERIAL PRIMARY KEY, code TEXT UNIQUE, segment TEXT, name TEXT NOT NULL, roles TEXT, wants TEXT,
  journey TEXT, goals TEXT, pains TEXT, kpis TEXT, note TEXT, slide INT, origin TEXT DEFAULT 'seed'
);
CREATE TABLE journey_step (
  id SERIAL PRIMARY KEY, persona_id INT REFERENCES persona(id) ON DELETE CASCADE,
  seq INT, name TEXT NOT NULL, question TEXT, experience TEXT, metrics TEXT, doing TEXT, today TEXT,
  origin TEXT DEFAULT 'seed'
);

-- Insights
CREATE TABLE insight_dashboard (
  id SERIAL PRIMARY KEY, code TEXT UNIQUE, name TEXT NOT NULL, audience TEXT, roles TEXT, surface TEXT,
  headline TEXT, guardrail TEXT, persona_code TEXT, slide INT, origin TEXT DEFAULT 'seed'
);
CREATE TABLE insight_question (
  id SERIAL PRIMARY KEY, dashboard_id INT REFERENCES insight_dashboard(id) ON DELETE CASCADE,
  seq INT, kind TEXT, question TEXT, answer TEXT, origin TEXT DEFAULT 'seed'
);

-- Industry data model
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

-- ---------------------------------------------------------------------------
-- Persona lens
-- ---------------------------------------------------------------------------
-- A lens is a workspace for a group of personas. 'available' = FALSE shows it as coming soon.
CREATE TABLE lens (
  code TEXT PRIMARY KEY, name TEXT NOT NULL, tagline TEXT, description TEXT, available BOOLEAN NOT NULL DEFAULT TRUE, seq INT
);
CREATE TABLE lens_role (
  code TEXT PRIMARY KEY, name TEXT NOT NULL, lens TEXT NOT NULL REFERENCES lens(code),
  owns TEXT, agent_support TEXT, seq INT
);
-- resource: 'screen' | 'pursuit_stage' | 'skill'; lenses: every lens allowed to open it
CREATE TABLE access_rule (
  resource TEXT NOT NULL, code TEXT NOT NULL, label TEXT,
  lenses TEXT[] NOT NULL, reason TEXT,
  PRIMARY KEY (resource, code)
);

-- ---------------------------------------------------------------------------
-- Pursuit lifecycle (AI Native Pursuit Engineering)
-- ---------------------------------------------------------------------------
CREATE TABLE pursuit_stage (
  id SERIAL PRIMARY KEY, code TEXT UNIQUE NOT NULL, num INT NOT NULL, name TEXT NOT NULL,
  loop TEXT, gate_code TEXT, gate TEXT, approvers TEXT, purpose TEXT, critical BOOLEAN, lane TEXT,
  artefacts JSONB, skills JSONB, tools JSONB, questions JSONB, inputs JSONB, samples JSONB, extra JSONB
);
CREATE TABLE pursuit_artefact (
  id SERIAL PRIMARY KEY, name TEXT, stages TEXT, owner TEXT, format TEXT, drafted_by TEXT, system_of_record BOOLEAN
);
CREATE TABLE pursuit_skill (id SERIAL PRIMARY KEY, name TEXT, type TEXT, contributes TEXT, stages TEXT);
-- reference lists: dependencies, human inputs, objections, method facts
CREATE TABLE pursuit_ref (id SERIAL PRIMARY KEY, kind TEXT, seq INT, data JSONB);

-- Pursuit kit: templates (docx/xlsx) turned into editable sheets
CREATE TABLE kit_template (
  id SERIAL PRIMARY KEY, stage_num INT, folder TEXT, file TEXT, format TEXT, sample BOOLEAN, download TEXT
);
CREATE TABLE kit_sheet (
  id SERIAL PRIMARY KEY, template_id INT REFERENCES kit_template(id) ON DELETE CASCADE,
  seq INT, name TEXT, title TEXT, guidance TEXT, columns JSONB
);
CREATE TABLE kit_row (
  id SERIAL PRIMARY KEY, sheet_id INT REFERENCES kit_sheet(id) ON DELETE CASCADE,
  seq INT, data JSONB, origin TEXT DEFAULT 'seed', updated_by TEXT
);

-- Response sections and rubric
CREATE TABLE rubric_criterion (code TEXT PRIMARY KEY, seq INT, name TEXT, weight INT, full_marks TEXT);
CREATE TABLE response_section (
  id SERIAL PRIMARY KEY, num INT, name TEXT, slides TEXT, slide_count INT, proves TEXT, must_haves JSONB,
  baseline INT, missing TEXT, fixes TEXT, blocked_by TEXT, weight NUMERIC, owner_lens TEXT
);
CREATE TABLE section_score (
  section_id INT REFERENCES response_section(id) ON DELETE CASCADE, criterion TEXT REFERENCES rubric_criterion(code),
  score INT CHECK (score BETWEEN 0 AND 4), evidence TEXT, updated_by TEXT, updated_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (section_id, criterion)
);
CREATE TABLE section_musthave (
  section_id INT REFERENCES response_section(id) ON DELETE CASCADE, idx INT, met BOOLEAN, PRIMARY KEY (section_id, idx)
);

-- Skills studio
CREATE TABLE skill_run (
  id SERIAL PRIMARY KEY, skill TEXT, kind TEXT, persona TEXT, mode TEXT, params JSONB, summary TEXT, output JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE skill_execution (
  id SERIAL PRIMARY KEY, run_id INT REFERENCES skill_run(id) ON DELETE CASCADE, file TEXT, persona TEXT, result JSONB,
  executed_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE gate_decision (
  id SERIAL PRIMARY KEY, stage_code TEXT, gate_code TEXT, approver TEXT NOT NULL, decision TEXT, conditions TEXT,
  recorded_by TEXT, decided_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE section_round (
  id SERIAL PRIMARY KEY, section_id INT REFERENCES response_section(id) ON DELETE CASCADE, round INT, score NUMERIC,
  musts_met BOOLEAN, fixes TEXT, recorded_by TEXT, created_at TIMESTAMPTZ DEFAULT now()
);

-- One searchable index across everything, used by the conversational assistant

-- ---------------------------------------------------------------------------
-- PMO lens: Snowflake AI Native Delivery Playbook
-- ---------------------------------------------------------------------------
CREATE TABLE pb_doc (key TEXT PRIMARY KEY, data JSONB NOT NULL);   -- playbook content, one row per section
CREATE TABLE pmo_readiness (
  track TEXT NOT NULL, qid INT NOT NULL, score INT CHECK (score BETWEEN 0 AND 3), note TEXT,
  updated_by TEXT, updated_at TIMESTAMPTZ DEFAULT now(), PRIMARY KEY (track, qid)
);
CREATE TABLE pmo_check (
  stage TEXT NOT NULL, archetype TEXT NOT NULL, idx INT NOT NULL, done BOOLEAN NOT NULL DEFAULT FALSE,
  updated_by TEXT, updated_at TIMESTAMPTZ DEFAULT now(), PRIMARY KEY (stage, archetype, idx)
);
CREATE TABLE pmo_kpi (
  id SERIAL PRIMARY KEY, seq INT, category TEXT, name TEXT, what TEXT, source TEXT, target TEXT, cadence TEXT, capture TEXT,
  actual TEXT, status TEXT CHECK (status IN ('green','amber','red','na')) DEFAULT 'na', note TEXT,
  updated_by TEXT, updated_at TIMESTAMPTZ
);
CREATE TABLE pmo_usecase (
  id SERIAL PRIMARY KEY, seq INT, archetype TEXT, stage TEXT, activity TEXT,
  value TEXT, rep TEXT, comp TEXT, risk TEXT, automation TEXT, prereq TEXT, origin TEXT DEFAULT 'seed'
);
CREATE TABLE pmo_raid (
  id SERIAL PRIMARY KEY, kind TEXT NOT NULL CHECK (kind IN ('Risk','Assumption','Issue','Dependency','Decision')),
  title TEXT NOT NULL, detail TEXT, owner TEXT, due TEXT, severity TEXT DEFAULT 'Medium', status TEXT DEFAULT 'Open',
  origin TEXT DEFAULT 'seed', created_by TEXT, created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE pmo_estimate (
  id SERIAL PRIMARY KEY, name TEXT, params JSONB, result JSONB, created_by TEXT, created_at TIMESTAMPTZ DEFAULT now()
);


-- ---------------------------------------------------------------------------
-- Assurance lens: assurance workbench
-- ---------------------------------------------------------------------------
CREATE TABLE aw_story (id SERIAL PRIMARY KEY, key TEXT UNIQUE, title TEXT, feature TEXT, persona TEXT, narrative TEXT,
  acceptance JSONB, source TEXT, priority TEXT);
CREATE TABLE aw_suite (id SERIAL PRIMARY KEY, name TEXT, source_kind TEXT, source_ref TEXT, llm TEXT, version INT,
  created_by TEXT, created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE aw_case (id SERIAL PRIMARY KEY, suite_id INT REFERENCES aw_suite(id) ON DELETE CASCADE, key TEXT, title TEXT,
  story_key TEXT, feature TEXT, type TEXT, priority TEXT, steps JSONB, expected TEXT, automation TEXT, origin TEXT DEFAULT 'generated',
  test_type TEXT);
-- lakehouse test catalogue: test types by platform layer (1-6) and cross-cutting discipline (7-9)
CREATE TABLE aw_test_type (code TEXT PRIMARY KEY, seq INT, layer INT, layer_name TEXT, name TEXT, what TEXT, checks JSONB, tools JSONB,
  skills JSONB, owner TEXT, gate TEXT, automation TEXT);
CREATE TABLE aw_dataset (id SERIAL PRIMARY KEY, name TEXT, schema_source TEXT, entity TEXT, scenarios TEXT[], rows JSONB, sql TEXT,
  created_by TEXT, created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE aw_component (id SERIAL PRIMARY KEY, kind TEXT, name TEXT, description TEXT);
CREATE TABLE aw_script (id SERIAL PRIMARY KEY, case_id INT REFERENCES aw_case(id) ON DELETE CASCADE, framework TEXT, app TEXT, file TEXT,
  keywords JSONB, code TEXT, created_by TEXT, created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE aw_engine (id SERIAL PRIMARY KEY, name TEXT UNIQUE, type TEXT, status TEXT, expires DATE, platform TEXT DEFAULT 'Simulator');
CREATE TABLE aw_device (id SERIAL PRIMARY KEY, name TEXT, type TEXT, platform TEXT, environment TEXT);
CREATE TABLE aw_release (id SERIAL PRIMARY KEY, name TEXT, description TEXT, start_date DATE, release_date DATE);
CREATE TABLE aw_plan (id SERIAL PRIMARY KEY, name TEXT, release_id INT REFERENCES aw_release(id), case_ids INT[] DEFAULT '{}', suite TEXT,
  last_execution TIMESTAMPTZ);
CREATE TABLE aw_cicd (id SERIAL PRIMARY KEY, name TEXT, pipeline TEXT, release_id INT REFERENCES aw_release(id), failure_analysis BOOLEAN,
  self_healing BOOLEAN, config TEXT, schedule TEXT);
CREATE TABLE aw_cycle (id SERIAL PRIMARY KEY, name TEXT, plan_id INT REFERENCES aw_plan(id), release_id INT REFERENCES aw_release(id),
  engine TEXT, device TEXT, started TIMESTAMPTZ, ended TIMESTAMPTZ, status TEXT DEFAULT 'Executing', trigger TEXT,
  total INT, passed INT, failed INT, skipped INT, self_healed INT, self_healing BOOLEAN, failure_analysis BOOLEAN, created_by TEXT);
CREATE TABLE aw_result (id SERIAL PRIMARY KEY, cycle_id INT REFERENCES aw_cycle(id) ON DELETE CASCADE, case_id INT REFERENCES aw_case(id),
  status TEXT, duration_ms INT, root_cause TEXT, detail TEXT, resolution TEXT, self_healed BOOLEAN);
CREATE TABLE aw_defect (id SERIAL PRIMARY KEY, key TEXT, title TEXT, severity TEXT, status TEXT, case_id INT REFERENCES aw_case(id),
  feature TEXT, component TEXT, cycle_id INT REFERENCES aw_cycle(id), cause TEXT, created_at TIMESTAMPTZ DEFAULT now(), failure_id TEXT);
CREATE TABLE aw_module (id SERIAL PRIMARY KEY, path TEXT UNIQUE, module TEXT, kind TEXT, keywords TEXT, lines INT, covered INT,
  changed BOOLEAN DEFAULT FALSE);
CREATE TABLE aw_mapping (case_id INT REFERENCES aw_case(id) ON DELETE CASCADE, module_id INT REFERENCES aw_module(id) ON DELETE CASCADE,
  score NUMERIC, PRIMARY KEY (case_id, module_id));


-- ---------------------------------------------------------------------------
-- TAF data checks (merged from the TAF operator app) and failure triage
-- ---------------------------------------------------------------------------
CREATE TABLE taf_case (
  test_id TEXT NOT NULL, suite TEXT NOT NULL CHECK (suite IN ('TAF','EXTERNAL')), check_id TEXT,
  test_type TEXT NOT NULL CHECK (test_type IN ('COLUMN','TEMPLATE','SQL','MANUAL')), severity TEXT,
  requirement_group TEXT, requirement_id TEXT, requirement_title TEXT, sheet_name TEXT, functional_category TEXT, load_type TEXT,
  target_table TEXT, target_column TEXT, date_column TEXT, tenant_column TEXT,
  assertion_name TEXT, assertion_params JSONB, template_name TEXT, template_params JSONB, sql_expression TEXT,
  expected_result TEXT, explanation TEXT, owner TEXT, source_ref TEXT, lakehouse_type TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE, deactivated_by TEXT, deactivated_at TIMESTAMPTZ, updated_at TIMESTAMPTZ DEFAULT now(),
  origin TEXT DEFAULT 'seed', PRIMARY KEY (test_id, suite)
);
CREATE TABLE taf_run (
  run_id TEXT PRIMARY KEY, engine TEXT NOT NULL, test_scope TEXT, started_at TIMESTAMPTZ DEFAULT now(), finished_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'Running', run_scope TEXT, triggered_by TEXT, upstream_pipeline_run TEXT, input_source TEXT,
  filter_mode TEXT, date_source TEXT, params JSONB, total_tests INT DEFAULT 0, pass_count INT DEFAULT 0, fail_count INT DEFAULT 0,
  warn_count INT DEFAULT 0, error_count INT DEFAULT 0, manual_count INT DEFAULT 0, not_run_count INT DEFAULT 0,
  notes TEXT, log TEXT, created_by TEXT
);
CREATE TABLE taf_result (
  run_id TEXT REFERENCES taf_run(run_id) ON DELETE CASCADE, test_id TEXT, suite TEXT, check_id TEXT, test_type TEXT, severity TEXT,
  status TEXT CHECK (status IN ('Pass','Fail','Warn','Error','Skipped','Manual','Info','Not_Run','Blocked')),
  violation_count INT, expected_result TEXT, actual_result TEXT, executed_sql TEXT, sample_rows JSONB, duration_ms INT,
  executed_at TIMESTAMPTZ DEFAULT now(), filter_applied TEXT, filter_skipped_reason TEXT, error_message TEXT,
  PRIMARY KEY (run_id, test_id, suite)
);
CREATE TABLE taf_upload (id SERIAL PRIMARY KEY, filename TEXT, path TEXT, bytes INT, imported INT, engine TEXT, created_by TEXT,
  created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE taf_scenario_run (id SERIAL PRIMARY KEY, run_id TEXT, scenario_id TEXT, scenario TEXT, status TEXT, violation_count INT,
  duration_ms INT, evidence JSONB, sql_used TEXT, error_message TEXT, engine TEXT, executed_at TIMESTAMPTZ DEFAULT now());
-- one triage row per failure (failure_id = test_id::run_id for data checks, case key::C<cycle> for test cases)
CREATE TABLE aw_triage (failure_id TEXT PRIMARY KEY, source TEXT, recommended_fix TEXT, resolved BOOLEAN NOT NULL DEFAULT FALSE,
  resolved_by TEXT, resolved_at TIMESTAMPTZ, defect_id INT REFERENCES aw_defect(id) ON DELETE SET NULL, updated_at TIMESTAMPTZ DEFAULT now());

-- Assurance settings: kept across reseeds (not in the DROP list) so connections and credentials survive upgrades
CREATE TABLE IF NOT EXISTS aw_asset (code TEXT PRIMARY KEY, name TEXT NOT NULL, color TEXT, needs TEXT[] NOT NULL DEFAULT '{}', description TEXT,
  screen TEXT, tab TEXT, enabled BOOLEAN NOT NULL DEFAULT TRUE, seq INT);
CREATE TABLE IF NOT EXISTS aw_conn (id SERIAL PRIMARY KEY, kind TEXT NOT NULL CHECK (kind IN ('llm','alm','storage','db','parser')), provider TEXT NOT NULL,
  name TEXT NOT NULL, config JSONB NOT NULL DEFAULT '{}', secret_enc TEXT, file_name TEXT, file_size BIGINT,
  test_status TEXT, test_message TEXT, tested_at TIMESTAMPTZ, created_by TEXT, created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now());
CREATE UNIQUE INDEX IF NOT EXISTS aw_conn_name ON aw_conn (kind, lower(name));
CREATE TABLE IF NOT EXISTS aw_conn_assign (kind TEXT NOT NULL, asset TEXT NOT NULL, conn_ref TEXT NOT NULL, PRIMARY KEY (kind, asset));

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
  UNION ALL SELECT 'kpi', k.id::text, k.name, concat_ws(' ', k.domain, k.formula, k.source_fact) FROM kpi k
  UNION ALL SELECT 'pursuit_stage', p.code, p.name, concat_ws(' ', p.purpose, p.gate_code, p.gate, p.approvers, p.artefacts::text, p.skills::text, p.questions::text) FROM pursuit_stage p
  UNION ALL SELECT 'pursuit_artefact', a.id::text, a.name, concat_ws(' ', a.owner, a.format, a.drafted_by, a.stages) FROM pursuit_artefact a
  UNION ALL SELECT 'pursuit_skill', s.id::text, s.name, concat_ws(' ', s.type, s.contributes, s.stages) FROM pursuit_skill s
  UNION ALL SELECT 'kit_template', t.id::text, t.file, concat_ws(' ', t.folder, t.format) FROM kit_template t
  UNION ALL SELECT 'section', r.id::text, r.name, concat_ws(' ', r.proves, r.missing, r.fixes) FROM response_section r
  UNION ALL SELECT 'pmo_kpi', k.id::text, k.name, concat_ws(' ', k.category, k.what, k.source, k.target) FROM pmo_kpi k
  UNION ALL SELECT 'pmo_raid', r.id::text, r.title, concat_ws(' ', r.kind, r.detail, r.owner, r.status) FROM pmo_raid r
  UNION ALL SELECT 'pmo_usecase', u.id::text, u.activity, concat_ws(' ', u.archetype, u.stage, u.automation, u.prereq) FROM pmo_usecase u
  UNION ALL SELECT 'aw_case', c.id::text, c.title, concat_ws(' ', c.key, c.story_key, c.feature, c.type, c.expected) FROM aw_case c
  UNION ALL SELECT 'aw_test_type', t.code, t.name, concat_ws(' ', t.layer_name, t.what, t.checks::text, t.tools::text, t.skills::text) FROM aw_test_type t
  UNION ALL SELECT 'aw_defect', d.id::text, d.title, concat_ws(' ', d.key, d.severity, d.status, d.feature, d.component) FROM aw_defect d
  UNION ALL SELECT 'taf_case', c.test_id, coalesce(c.requirement_title, c.test_id), concat_ws(' ', c.suite, c.test_type, c.target_table, c.target_column, c.assertion_name, c.template_name, c.explanation) FROM taf_case c;
