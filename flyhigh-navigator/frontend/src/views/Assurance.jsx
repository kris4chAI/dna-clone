import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { Chip, Editor, Empty, Md } from '../components/ui'

/* Assurance lens: the assurance workbench (overview, design, execution, analytics, maintenance). */

const Tabs = ({ tabs, tab, setTab }) => (
  <div className="tabs" style={{ margin: '4px 0 14px' }}>
    {tabs.map(([k, l]) => <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l}</button>)}
  </div>
)
const Head = ({ crumb, title, lede, children }) => (
  <header className="page-head">
    <div><div className="eyebrow">Assurance workbench · {crumb}</div><h1>{title}</h1>{lede && <p className="lede">{lede}</p>}</div>
    {children && <div className="status-pills">{children}</div>}
  </header>
)
const useLoad = (path, deps = []) => {
  const [d, setD] = useState(null)
  const [err, setErr] = useState('')
  const reload = () => api.get(path).then(setD).catch((e) => setErr(e.message))
  useEffect(() => { reload() }, deps) // eslint-disable-line react-hooks/exhaustive-deps
  return [d, setD, reload, err]
}
const ST = { passed: 'g', failed: 'r', skipped: 'a', Open: 'r', 'In progress': 'a', Closed: 'g', Critical: 'r', Major: 'a', Minor: 'n', Completed: 'g', Executing: 's' }
const Pill = ({ s, children }) => <span className={`pm-rag ${ST[s] || 'n'}`}>{children || s}</span>
const TYPE_TONE = { functional: 'default', data: 'snow', security: 'purple', performance: 'agent', negative: 'default', api: 'snow', ui: 'agent' }
const fmt = (d) => (d ? new Date(d).toLocaleString() : '—')
const LlmNote = ({ on, status }) => (on
  ? <div className="note">LLM drafting available ({status?.provider} · {status?.model}). Engines here are deterministic; use the skills studio's “Draft with LLM” for richer wording.</div>
  : <div className="note">Engines run deterministically. Configure an LLM in <code>.env</code> to add “Draft with LLM” in the skills studio.</div>)

/* ---------------------------------------------------------------- Overview */
export function AwOverview({ onNavigate }) {
  const [d] = useLoad('/api/assurance/overview')
  const [pillar, setPillar] = useState('design')
  if (!d) return <div className="page">Loading…</div>
  const c = d.counts
  const p = d.pillars.find((x) => x.code === pillar)
  const can = (v) => onNavigate && v
  return (
    <div className="page">
      <Head crumb="Overview" title="Assure every wave: design, run, analyse and maintain the tests"
        lede="The assurance workbench generates test cases, test data and scripts from FlyHigh's user stories and data model, runs them with self-healing and failure analysis, reports coverage and defects for each release, and keeps the regression suite aligned with the code that changes." />
      <div className="aw-kpis">
        {[[c.stories, 'user stories', `${c.covered} covered`], [c.cases, 'test cases', `${c.suites} suite versions`], [c.datasets, 'test data sets', `${c.scripts} scripts`],
          [c.cycles, 'execution cycles', `${c.self_healed} self-healed`], [c.passed, 'passed', `${c.failed} failed · ${c.skipped} skipped`], [c.open_defects, 'open defects', `${c.changed} of ${c.modules} modules changed`]]
          .map(([v, l, s]) => <div key={l} className="aw-kpi"><b>{v}</b><span>{l}</span><small>{s}</small></div>)}
      </div>
      <section className="aw-hero">
        <div className="aw-hero-head">{d.pillars.map((x) => <button key={x.code} className={pillar === x.code ? 'on' : ''} onClick={() => setPillar(x.code)}>{x.name}</button>)}</div>
        <div className="aw-tools">{p.tools.map(([t, desc]) => <div key={t} className="aw-tool"><b>{t}</b><span>{desc}</span></div>)}</div>
      </section>
      <div className="aw-pillars">
        {d.pillars.map((x) => (
          <button key={x.code} className="aw-pillar" onClick={() => can(1) && onNavigate(`aw_${x.code}`)}>
            <span className={`aw-ic ${x.code}`}>{{ design: '✎', execution: '▶', analytics: '◔', maintenance: '⟲' }[x.code]}</span><b>{x.name}</b><small>{x.tools.length} components →</small>
          </button>
        ))}
      </div>
      <LlmNote on={d.llm} status={d.llm_status} />
    </div>
  )
}

/* ---------------------------------------------------------------- Design */
export function AwDesign() {
  const [suite, setSuite] = useState(null)
  const [d, setD, reload] = useLoad(`/api/assurance/design${suite ? `?suite_id=${suite}` : ''}`, [suite])
  const [tab, setTab] = useState('cases')
  const [modal, setModal] = useState(null)
  const [view, setView] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  if (!d) return <div className="page">Loading…</div>
  const act = async (fn) => { setBusy(true); setErr(''); try { await fn() } catch (e) { setErr(e.message) } finally { setBusy(false) } }
  const comps = (k) => d.framework.filter((f) => f.kind === k)
  return (
    <div className="page">
      <Head crumb="Design" title="Generate test cases, test data and scripts"
        lede="Test cases come from user stories (FlyHigh's persona journeys and the Jira backlog) or from FSD, BRD, UI/UX and API documents. Test data comes from the data model or a schema file. Scripts are keyword-driven over reusable components." />
      <Tabs tab={tab} setTab={setTab} tabs={[['cases', 'Test case generator'], ['data', 'Test data generator'], ['scripts', 'Test script generator'], ['stories', `User stories (${d.stories.length})`]]} />
      {err && <div className="note warn">{err}</div>}

      {tab === 'cases' && (
        <div className="aw-split">
          <section className="panel">
            <div className="toolbar"><h4 style={{ margin: 0 }}>Version history</h4><span style={{ flex: 1 }} />
              <button className="btn primary" onClick={() => setModal('gen')}>+ Generate test cases</button>
              <button className="btn ghost" onClick={() => setModal('import')}>Import</button></div>
            <table className="tbl"><thead><tr><th>Test suite</th><th>Source</th><th>Engine</th><th>Cases</th><th>When</th><th /></tr></thead>
              <tbody>{d.suites.map((s) => (
                <tr key={s.id} className={s.id === d.suite_id ? 'aw-sel' : ''} onClick={() => setSuite(s.id)} style={{ cursor: 'pointer' }}>
                  <td><b>{s.name}</b></td><td className="small">{s.source_ref}</td><td className="small">{s.llm}</td><td>{s.cases}</td><td className="small">{fmt(s.created_at)}</td>
                  <td><button className="icon-btn" title="Delete suite" onClick={(e) => { e.stopPropagation(); if (confirm('Delete this suite?')) act(async () => { await api.del(`/api/assurance/design/suites/${s.id}`); setSuite(null); reload() }) }}>✕</button></td>
                </tr>))}</tbody></table>
            {!d.suites.length && <Empty>No suites yet.</Empty>}
          </section>
          <section className="panel">
            <h4>Test cases <small>{d.cases.length}</small></h4>
            <div className="md-table" style={{ maxHeight: 620, overflow: 'auto' }}><table className="tbl">
              <thead><tr><th>Key</th><th>Title</th><th>Type</th><th>Priority</th><th>Story</th><th>Automation</th></tr></thead>
              <tbody>{d.cases.map((c) => (
                <tr key={c.id} onClick={() => setView({ kind: 'case', c })} style={{ cursor: 'pointer' }}>
                  <td className="mono small">{c.key}</td><td>{c.title}</td><td><Chip tone={TYPE_TONE[c.type]}>{c.type}</Chip></td>
                  <td><Pill s={c.priority === 'High' ? 'Critical' : c.priority === 'Medium' ? 'Major' : 'Minor'}>{c.priority}</Pill></td>
                  <td className="small">{c.story_key}</td><td className="small">{c.automation}</td></tr>))}</tbody>
            </table></div>
          </section>
        </div>
      )}

      {tab === 'data' && <DataTab d={d} reload={reload} act={act} busy={busy} setView={setView} />}

      {tab === 'scripts' && (
        <div className="aw-script">
          <aside className="panel">
            <h4>Automatic script generation</h4>
            {[['app', 'Applications'], ['component', 'Reusable components'], ['suite', 'Standard test suite'], ['service', 'Services']].map(([k, l]) => (
              <details key={k} open={k === 'component'}><summary><b>{l}</b> <small className="muted">{comps(k).length}</small></summary>
                {comps(k).map((f) => <div key={f.id} className="aw-comp"><span className="mono">{f.name}</span><small className="muted">{f.description}</small></div>)}</details>
            ))}
          </aside>
          <section className="panel">
            <ScriptGen d={d} act={act} busy={busy} reload={reload} setView={setView} />
          </section>
        </div>
      )}

      {tab === 'stories' && (
        <section className="panel"><div className="md-table"><table className="tbl">
          <thead><tr><th>Key</th><th>Story</th><th>Feature</th><th>Source</th><th>Priority</th><th>Acceptance criteria</th></tr></thead>
          <tbody>{d.stories.map((s) => <tr key={s.id}><td className="mono small">{s.key}</td><td><b>{s.title}</b><div className="muted small">{s.narrative}</div></td><td className="small">{s.feature}</td>
            <td className="small">{s.source}</td><td className="small">{s.priority}</td><td className="small"><ul>{s.acceptance.map((a) => <li key={a}>{a}</li>)}</ul></td></tr>)}</tbody>
        </table></div></section>
      )}

      {modal === 'gen' && <GenWizard stories={d.stories} onClose={() => setModal(null)} onDone={(s) => { setModal(null); setSuite(s.id); reload() }} />}
      {modal === 'import' && <Editor title="Import test cases (CSV)" initial={{ text: 'title,story,feature,type,priority,steps,expected\nOTIF tile matches certified value,FLY-101,BI modernization,functional,High,Sign in; Open dashboard; Read OTIF,Value equals golden query' }}
        fields={[{ key: 'text', label: 'CSV with a header row', type: 'textarea' }]} onClose={() => setModal(null)}
        onSave={async (v) => { const s = await api.post('/api/assurance/design/cases/import', { text: v.text }); setSuite(s.id); reload() }} />}
      {view && <Viewer v={view} onClose={() => setView(null)} />}
    </div>
  )
}

function GenWizard({ stories, onClose, onDone }) {
  const [step, setStep] = useState(1)
  const [src, setSrc] = useState('stories')
  const [from, setFrom] = useState('ALM')
  const [feature, setFeature] = useState('')
  const [pick, setPick] = useState([])
  const [docType, setDocType] = useState('FSD/BRD')
  const [text, setText] = useState('')
  const [name, setName] = useState('')
  const [err, setErr] = useState('')
  const features = [...new Set(stories.map((s) => s.feature))]
  const list = stories.filter((s) => (!feature || s.feature === feature) && (from === 'ALM' ? s.source.startsWith('Jira') || true : true))
  const go = async () => {
    setErr('')
    try {
      const body = src === 'stories' ? { source: 'stories', story_ids: pick.length ? pick : list.map((s) => s.id), name: name || undefined }
        : { source: 'document', doc_type: docType, doc_text: text, name: name || undefined }
      onDone(await api.post('/api/assurance/design/cases/generate', body))
    } catch (e) { setErr(e.message) }
  }
  return (
    <div className="modal-back" onMouseDown={onClose}>
      <div className="modal wide" onMouseDown={(e) => e.stopPropagation()}>
        {step === 1 && (<>
          <h3>How would you like to generate test cases?</h3>
          {[['stories', 'From user stories', 'Transform user stories (Jira, Rally, Azure DevOps, PDF, XLSX, DOCX, S3 or FlyHigh persona journeys) into comprehensive test cases.'],
            ['document', 'From other documents', 'Turn product documentation (FSD, BRD, UI/UX designs, API docs) into structured requirements, then into test cases.']].map(([k, t, s]) => (
            <button key={k} className={`aw-choice ${src === k ? 'on' : ''}`} onClick={() => setSrc(k)}><b>{t}</b><span>{s}</span></button>))}
          <div className="modal-actions"><small className="muted">Step 1 of 2</small><span style={{ flex: 1 }} /><button className="btn ghost" onClick={onClose}>Cancel</button><button className="btn primary" onClick={() => setStep(2)}>Continue</button></div>
        </>)}
        {step === 2 && src === 'stories' && (<>
          <h3>Extract user stories</h3>
          <div className="aw-seg">{[['ALM', 'ALM connection', 'Jira / Rally / Azure DevOps'], ['DOC', 'Requirement document', 'PDF / XLSX / DOCX'], ['S3', 'Other sources', 'S3']].map(([k, t, s]) =>
            <button key={k} className={from === k ? 'on' : ''} onClick={() => setFrom(k)}><b>{t}</b><small>{s}</small></button>)}</div>
          <p className="muted small">Connections are managed outside this demo; the FlyHigh backlog (persona journeys and the FLY project) is already loaded.</p>
          <label className="field"><span>Feature</span><select value={feature} onChange={(e) => { setFeature(e.target.value); setPick([]) }}><option value="">All features</option>{features.map((f) => <option key={f}>{f}</option>)}</select></label>
          <div className="aw-pick">{list.map((s) => <label key={s.id}><input type="checkbox" checked={pick.includes(s.id)} onChange={(e) => setPick((p) => (e.target.checked ? [...p, s.id] : p.filter((x) => x !== s.id)))} /> <span className="mono small">{s.key}</span> {s.title} <small className="muted">· {s.feature}</small></label>)}</div>
          <label className="field"><span>Suite name (optional)</span><input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Wave 1 regression" /></label>
          {err && <div className="note warn">{err}</div>}
          <div className="modal-actions"><small className="muted">Step 2 of 2 · {pick.length || list.length} stories</small><span style={{ flex: 1 }} /><button className="btn ghost" onClick={() => setStep(1)}>Back</button><button className="btn primary" onClick={go}>Extract and generate</button></div>
        </>)}
        {step === 2 && src === 'document' && (<>
          <h3>Which document would you like to use?</h3>
          <div className="aw-seg">{['FSD/BRD', 'UI/UX', 'API DOCS'].map((k) => <button key={k} className={docType === k ? 'on' : ''} onClick={() => setDocType(k)}><b>{k}</b></button>)}</div>
          <label className="field"><span>{docType === 'API DOCS' ? 'Endpoints, one per line (e.g. GET /shipments/{id})' : docType === 'UI/UX' ? 'Screens, one per line' : 'Requirements, one per line'}</span>
            <textarea rows={8} value={text} onChange={(e) => setText(e.target.value)} /></label>
          <label className="field"><span>Suite name (optional)</span><input value={name} onChange={(e) => setName(e.target.value)} /></label>
          {err && <div className="note warn">{err}</div>}
          <div className="modal-actions"><small className="muted">Step 2 of 2</small><span style={{ flex: 1 }} /><button className="btn ghost" onClick={() => setStep(1)}>Back</button><button className="btn primary" onClick={go}>Generate</button></div>
        </>)}
      </div>
    </div>
  )
}

function DataTab({ d, reload, act, busy, setView }) {
  const [src, setSrc] = useState('model')
  const [ent, setEnt] = useState(d.entities.find((e) => e.kind === 'fact')?.id || '')
  const [ddl, setDdl] = useState('CREATE TABLE fct_shipment (shipment_id NUMBER, customer_key NUMBER, ship_date DATE, delivered_date DATE, carrier_rate NUMBER(12,2), on_time_flag BOOLEAN, units NUMBER)')
  const [rows, setRows] = useState(24)
  const [sc, setSc] = useState(['valid', 'boundary', 'invalid'])
  const gen = () => act(async () => { const r = await api.post('/api/assurance/design/data/generate', src === 'model' ? { entity_id: Number(ent), rows, scenarios: sc } : { ddl, rows, scenarios: sc }); reload(); setView({ kind: 'data', id: r.id }) })
  return (
    <div className="aw-split">
      <section className="panel">
        <h4>Generate test data</h4>
        <div className="aw-seg">{[['model', 'From the data model', 'FlyHigh entities'], ['file', 'From schema file', 'SQL DDL or CSV header']].map(([k, t, s]) =>
          <button key={k} className={src === k ? 'on' : ''} onClick={() => setSrc(k)}><b>{t}</b><small>{s}</small></button>)}</div>
        {src === 'model' ? (
          <label className="field"><span>Entity</span><select value={ent} onChange={(e) => setEnt(e.target.value)}>{d.entities.map((e) => <option key={e.id} value={e.id}>{e.model} · {e.name} ({e.kind})</option>)}</select></label>
        ) : <label className="field"><span>Schema</span><textarea rows={5} value={ddl} onChange={(e) => setDdl(e.target.value)} /></label>}
        <div className="aw-sc">{['valid', 'boundary', 'invalid', 'masked'].map((s) => <label key={s}><input type="checkbox" checked={sc.includes(s)} onChange={(e) => setSc((o) => (e.target.checked ? [...o, s] : o.filter((x) => x !== s)))} /> {s}</label>)}
          <label>Rows <input type="number" min="1" max="200" value={rows} onChange={(e) => setRows(Number(e.target.value))} className="pm-num-in" /></label></div>
        <button className="btn primary" disabled={busy || !sc.length} onClick={gen}>Generate test data</button>
      </section>
      <section className="panel">
        <h4>Data sets</h4>
        <table className="tbl"><thead><tr><th>Name</th><th>Source</th><th>Rows</th><th>When</th></tr></thead>
          <tbody>{d.datasets.map((x) => <tr key={x.id} onClick={() => setView({ kind: 'data', id: x.id })} style={{ cursor: 'pointer' }}><td><b>{x.name}</b></td><td className="small">{x.schema_source}</td><td>{x.n}</td><td className="small">{fmt(x.created_at)}</td></tr>)}</tbody></table>
      </section>
    </div>
  )
}

function ScriptGen({ d, act, busy, reload, setView }) {
  const [caseId, setCaseId] = useState(d.cases[0]?.id || '')
  const [fw, setFw] = useState('Keyword driven')
  return (
    <>
      <div className="toolbar"><h4 style={{ margin: 0 }}>Test script generator</h4><span style={{ flex: 1 }} />
        <span className="small muted">Framework type</span>
        <select value={fw} onChange={(e) => setFw(e.target.value)}><option>Keyword driven</option><option>BDD</option></select></div>
      <label className="field"><span>Test case (from the selected suite)</span>
        <select value={caseId} onChange={(e) => setCaseId(e.target.value)}>{d.cases.map((c) => <option key={c.id} value={c.id}>{c.key} · {c.type} · {c.title.slice(0, 90)}</option>)}</select></label>
      <button className="btn primary" disabled={busy || !caseId} onClick={() => act(async () => { const s = await api.post('/api/assurance/design/scripts/generate', { case_id: Number(caseId), framework: fw }); reload(); setView({ kind: 'script', id: s.id }) })}>Generate script</button>
      <h5>Generated scripts</h5>
      <table className="tbl"><thead><tr><th>File</th><th>Case</th><th>Framework</th><th>Application</th></tr></thead>
        <tbody>{d.scripts.map((s) => <tr key={s.id} onClick={() => setView({ kind: 'script', id: s.id })} style={{ cursor: 'pointer' }}><td className="mono small">{s.file}</td><td className="small">{s.key} · {s.title.slice(0, 60)}</td><td className="small">{s.framework}</td><td className="small">{s.app}</td></tr>)}</tbody></table>
    </>
  )
}

function Viewer({ v, onClose }) {
  const [d, setD] = useState(v.kind === 'case' ? v.c : null)
  useEffect(() => {
    if (v.kind === 'data') api.get(`/api/assurance/design/data/${v.id}`).then(setD)
    if (v.kind === 'script') api.get(`/api/assurance/design/scripts/${v.id}`).then(setD)
  }, [v])
  return (
    <div className="modal-back" onMouseDown={onClose}>
      <div className="modal wide" onMouseDown={(e) => e.stopPropagation()}>
        {!d ? 'Loading…' : v.kind === 'case' ? (<>
          <h3>{d.key} · {d.title}</h3>
          <div className="chips"><Chip tone={TYPE_TONE[d.type]}>{d.type}</Chip><Chip>{d.priority}</Chip><Chip>{d.story_key}</Chip><Chip>{d.automation}</Chip></div>
          <h5>Steps</h5><ol>{d.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
          <h5>Expected result</h5><p>{d.expected}</p>
        </>) : v.kind === 'data' ? (<>
          <h3>{d.name}</h3><p className="muted small">{d.schema_source} · {d.rows.length} rows</p>
          <div className="md-table" style={{ maxHeight: 300, overflow: 'auto' }}><table className="tbl"><thead><tr>{Object.keys(d.rows[0] || {}).map((k) => <th key={k}>{k}</th>)}</tr></thead>
            <tbody>{d.rows.map((r, i) => <tr key={i}>{Object.keys(d.rows[0]).map((k) => <td key={k} className="small">{String(r[k] ?? 'NULL')}</td>)}</tr>)}</tbody></table></div>
          <h5>Snowflake load script</h5><pre className="code" style={{ maxHeight: 220, overflow: 'auto' }}>{d.sql}</pre>
        </>) : (<>
          <h3>{d.file}</h3><p className="muted small">{d.key} · {d.title} · {d.framework} · {d.app}</p>
          <table className="tbl"><thead><tr><th>#</th><th>Keyword</th><th>Arguments</th></tr></thead><tbody>{d.keywords.map((k) => <tr key={k.step}><td>{k.step}</td><td className="mono">{k.keyword}</td><td>{k.args}</td></tr>)}</tbody></table>
          <pre className="code" style={{ maxHeight: 280, overflow: 'auto' }}>{d.code}</pre>
          <button className="link" onClick={() => navigator.clipboard?.writeText(d.code)}>Copy script</button>
        </>)}
        <div className="modal-actions"><span style={{ flex: 1 }} /><button className="btn ghost" onClick={onClose}>Close</button></div>
      </div>
    </div>
  )
}

/* ---------------------------------------------------------------- Execution */
const FORMS = {
  engines: [{ key: 'name', label: 'Execution engine name', required: true }, { key: 'type', label: 'Type', type: 'select', options: ['Local', 'Cluster'] }, { key: 'expires', label: 'Expire date', type: 'date' }],
  devices: [{ key: 'name', label: 'Device name', required: true }, { key: 'type', label: 'Device type', type: 'select', options: ['Browser', 'Tablet', 'Mobile', 'Desktop app'] }, { key: 'platform', label: 'Platform' }, { key: 'environment', label: 'Environment', type: 'select', options: ['DEV', 'SIT', 'UAT', 'CI'] }],
  releases: [{ key: 'name', label: 'Release name', required: true }, { key: 'description', label: 'Description', type: 'textarea' }, { key: 'start_date', label: 'Start date', type: 'date' }, { key: 'release_date', label: 'Release date', type: 'date' }],
  cicd: [{ key: 'name', label: 'Execution name', required: true }, { key: 'pipeline', label: 'Pipeline', placeholder: 'GitHub Actions · repo / workflow' }, { key: 'config', label: 'CI/CD config info', type: 'textarea' }, { key: 'schedule', label: 'Schedule', placeholder: 'Daily 02:00 UTC' }],
}

export function AwExecution() {
  const [d, , reload] = useLoad('/api/assurance/execution')
  const [tab, setTab] = useState('report')
  const [sub, setSub] = useState('planning')
  const [form, setForm] = useState(null)
  const [cyc, setCyc] = useState(null)
  const [planEd, setPlanEd] = useState(null)
  const [run, setRun] = useState({ plan: '', engine: 'Snowflake DEV cluster', device: 'Chrome desktop', self_healing: true, failure_analysis: true })
  const [msg, setMsg] = useState('')
  useEffect(() => { if (d && !cyc && d.latest) setCyc(d.latest) }, [d]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (d && !run.plan && d.plans[0]) setRun((r) => ({ ...r, plan: d.plans[0].id })) }, [d]) // eslint-disable-line react-hooks/exhaustive-deps
  if (!d) return <div className="page">Loading…</div>
  const del = async (kind, id) => { if (confirm('Remove this item?')) { try { await api.del(`/api/assurance/execution/${kind}/${id}`); reload() } catch (e) { alert(e.message) } } }
  const start = async () => {
    setMsg('')
    try { const c = await api.post(`/api/assurance/execution/plans/${run.plan}/run`, run); setCyc(c); setTab('report'); reload() } catch (e) { setMsg(e.message) }
  }
  const Simple = ({ kind, cols, rows, keys, add }) => (
    <section className="panel">
      <div className="toolbar"><span style={{ flex: 1 }} /><button className="btn primary" onClick={() => setForm(kind)}>{add}</button></div>
      <table className="tbl"><thead><tr>{cols.map((c) => <th key={c}>{c}</th>)}<th /></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.id}>{keys.map((k, i) => <td key={i}>{typeof k === 'function' ? k(r) : r[k]}</td>)}<td><button className="icon-btn" onClick={() => del(kind, r.id)}>✕</button></td></tr>)}</tbody></table>
      {!rows.length && <Empty>No data</Empty>}
    </section>
  )
  const c = cyc
  return (
    <div className="page">
      <Head crumb="Execution" title="Run test plans on engines and devices, release by release"
        lede="Set up execution engines and devices, plan the cases for each release, run them manually, from CI/CD or on a schedule, with self-healing for UI locator changes and failure analysis on every failure.">
        <span className="spill">Built-in simulator · connect an engine to run for real</span>
      </Head>
      <Tabs tab={tab} setTab={setTab} tabs={[['report', 'Test execution report'], ['manage', 'Execution management'], ['engines', 'Execution engines'], ['devices', 'Devices'], ['releases', 'Releases']]} />

      {tab === 'engines' && <Simple kind="engines" add="Add new engine" cols={['Engine name and type', 'Status', 'Expire date', 'Setup engine']} rows={d.engines}
        keys={[(r) => <><b>{r.name}</b> <small className="muted">· {r.type}</small></>, (r) => <Pill s={r.expires && new Date(r.expires) < new Date() ? 'Open' : 'Completed'}>{r.expires && new Date(r.expires) < new Date() ? 'Expired' : r.status}</Pill>, 'expires',
          (r) => <span className="small muted">{r.type === 'Cluster' ? 'Key-pair auth to Snowflake DEV; Playwright grid' : 'Runs on the tester’s machine'}</span>]} />}
      {tab === 'devices' && <Simple kind="devices" add="Add new device" cols={['Device name', 'Device type', 'Platform', 'Environment']} rows={d.devices} keys={['name', 'type', 'platform', 'environment']} />}
      {tab === 'releases' && <Simple kind="releases" add="Add new release" cols={['Release name', 'Description', 'Start date', 'Release date']} rows={d.releases} keys={[(r) => <b>{r.name}</b>, 'description', 'start_date', 'release_date']} />}

      {tab === 'manage' && (<>
        <div className="tabs" style={{ marginBottom: 10 }}>{[['planning', 'Test planning'], ['execution', 'Test execution'], ['cicd', 'CI/CD based execution'], ['schedule', 'Test schedule']].map(([k, l]) => <button key={k} className={sub === k ? 'on' : ''} onClick={() => setSub(k)}>{l}</button>)}</div>
        {sub === 'planning' && (
          <section className="panel">
            <div className="toolbar"><span style={{ flex: 1 }} /><button className="btn primary" onClick={() => setPlanEd({ name: '', release_id: d.releases[0]?.id, case_ids: [] })}>Add new test plan</button></div>
            <table className="tbl"><thead><tr><th>Plan no</th><th>Plan name</th><th>Release</th><th>Number of test cases</th><th>Last execution</th><th /></tr></thead>
              <tbody>{d.plans.map((p) => <tr key={p.id}><td>{p.id}</td><td><b>{p.name}</b> <small className="muted">{p.suite}</small></td><td className="small">{p.release}</td><td>{p.n}</td><td className="small">{fmt(p.last_execution)}</td>
                <td><button className="btn ghost small" onClick={() => { setRun((r) => ({ ...r, plan: p.id })); setSub('execution') }}>Run →</button> <button className="icon-btn" onClick={() => del('plans', p.id)}>✕</button></td></tr>)}</tbody></table>
          </section>
        )}
        {sub === 'execution' && (
          <section className="panel">
            <h4>Selected test plan and settings</h4>
            <div className="form-grid aw-run">
              <label className="field"><span>Test plan</span><select value={run.plan} onChange={(e) => setRun({ ...run, plan: Number(e.target.value) })}>{d.plans.map((p) => <option key={p.id} value={p.id}>{p.name} · {p.n} cases</option>)}</select></label>
              <label className="field"><span>Global execution engine</span><select value={run.engine} onChange={(e) => setRun({ ...run, engine: e.target.value })}>{d.engines.map((x) => <option key={x.id}>{x.name}</option>)}</select></label>
              <label className="field"><span>Global device / browser</span><select value={run.device} onChange={(e) => setRun({ ...run, device: e.target.value })}>{d.devices.map((x) => <option key={x.id}>{x.name}</option>)}</select></label>
            </div>
            <div className="aw-sc"><label><input type="checkbox" checked={run.failure_analysis} onChange={(e) => setRun({ ...run, failure_analysis: e.target.checked })} /> Test failure analysis</label>
              <label><input type="checkbox" checked={run.self_healing} onChange={(e) => setRun({ ...run, self_healing: e.target.checked })} /> Self-healing</label></div>
            {msg && <div className="note warn">{msg}</div>}
            <button className="btn primary" onClick={start} disabled={!run.plan}>Start execution</button>
            <PlanCases plan={d.plans.find((p) => p.id === Number(run.plan))} cases={d.cases} />
          </section>
        )}
        {(sub === 'cicd' || sub === 'schedule') && <Simple kind="cicd" add="Add new CI/CD execution" cols={['Execution', 'Test failure analysis', 'UI self-healing', 'Release', 'CI/CD config info', sub === 'schedule' ? 'Schedule' : 'Pipeline']}
          rows={d.cicd} keys={[(r) => <b>{r.name}</b>, (r) => (r.failure_analysis ? '✓' : '—'), (r) => (r.self_healing ? '✓' : '—'), 'release', (r) => <span className="small">{r.config}</span>, sub === 'schedule' ? 'schedule' : 'pipeline']} />}
      </>)}

      {tab === 'report' && (<>
        {c && (
          <div className="aw-report">
            <section className="panel">
              <h4>Latest execution · {c.name}</h4>
              <div className="pm-stats big">
                <div><b>{c.total}</b><small>total test cases</small></div><div><b className="g">{c.passed}</b><small>passed</small></div>
                <div><b className="r">{c.failed}</b><small>failed</small></div><div><b className="a">{c.skipped}</b><small>skipped</small></div><div><b>{c.self_healed}</b><small>self-healed</small></div>
              </div>
              <div className="aw-bar"><i className="g" style={{ flex: c.passed }} /><i className="r" style={{ flex: c.failed }} /><i className="a" style={{ flex: c.skipped }} /></div>
              <p className="small muted">{c.release} · {c.engine} · {c.device} · {c.trigger} · {fmt(c.started)} → {fmt(c.ended)}</p>
            </section>
            <section className="panel">
              <h4>Results <small>failures first</small></h4>
              <div className="md-table" style={{ maxHeight: 360, overflow: 'auto' }}><table className="tbl">
                <thead><tr><th>Test case</th><th>Status</th><th>Root cause</th><th>Resolution</th><th>Duration</th></tr></thead>
                <tbody>{c.results.map((r) => <tr key={r.id}><td className="small"><span className="mono">{r.key}</span> {r.title.slice(0, 70)}</td>
                  <td><Pill s={r.status} />{r.self_healed && <span className="origin">Self-healed</span>}</td><td className="small">{r.root_cause || '—'}</td><td className="small muted">{r.resolution || ''}</td><td className="small">{(r.duration_ms / 1000).toFixed(1)} s</td></tr>)}</tbody>
              </table></div>
            </section>
          </div>
        )}
        <section className="panel">
          <h4>Overall test result summary <button className="btn ghost small" onClick={reload}>Refresh</button></h4>
          <table className="tbl"><thead><tr><th>Execution cycle</th><th>Start time</th><th>End time</th><th>Release</th><th>Status</th><th>Total</th><th>Passed</th><th>Failed</th><th>E-engine</th><th>Self-healed</th></tr></thead>
            <tbody>{d.cycles.map((x) => <tr key={x.id} className={c?.id === x.id ? 'aw-sel' : ''} onClick={() => api.get(`/api/assurance/execution/cycles/${x.id}`).then(setCyc)} style={{ cursor: 'pointer' }}>
              <td><b>{x.name}</b></td><td className="small">{fmt(x.started)}</td><td className="small">{fmt(x.ended)}</td><td className="small">{x.release}</td><td><Pill s={x.status} /></td>
              <td>{x.total}</td><td>{x.passed}</td><td>{x.failed}</td><td className="small">{x.engine}</td><td>{x.self_healed}</td></tr>)}</tbody></table>
        </section>
      </>)}

      {form && <Editor title={{ engines: 'Create new execution engine', devices: 'Add new device', releases: 'Add new release', cicd: 'Add new CI/CD execution' }[form]} initial={form === 'cicd' ? { release_id: d.releases[0]?.id, failure_analysis: true, self_healing: true } : {}}
        fields={FORMS[form]} onClose={() => setForm(null)} onSave={async (v) => { await api.post(`/api/assurance/execution/${form}`, v); reload() }} />}
      {planEd && <PlanEditor d={d} plan={planEd} onClose={() => setPlanEd(null)} onSaved={() => { setPlanEd(null); reload() }} />}
    </div>
  )
}

function PlanCases({ plan, cases }) {
  if (!plan) return null
  const ids = new Set(plan.case_ids)
  const rows = cases.filter((c) => ids.has(c.id))
  return (<>
    <h5>Selected test cases · {rows.length}</h5>
    <div className="md-table" style={{ maxHeight: 280, overflow: 'auto' }}><table className="tbl"><thead><tr><th>Key</th><th>Test case name</th><th>Type</th><th>Priority</th></tr></thead>
      <tbody>{rows.map((c) => <tr key={c.id}><td className="mono small">{c.key}</td><td className="small">{c.title}</td><td><Chip tone={TYPE_TONE[c.type]}>{c.type}</Chip></td><td className="small">{c.priority}</td></tr>)}</tbody></table></div>
  </>)
}

function PlanEditor({ d, plan, onClose, onSaved }) {
  const [p, setP] = useState(plan)
  const [type, setType] = useState('')
  const [err, setErr] = useState('')
  const list = d.cases.filter((c) => !type || c.type === type)
  const toggle = (id) => setP((o) => ({ ...o, case_ids: o.case_ids.includes(id) ? o.case_ids.filter((x) => x !== id) : [...o.case_ids, id] }))
  const save = async () => { try { await api.post('/api/assurance/execution/plans', { ...p, release_id: Number(p.release_id) || null }); onSaved() } catch (e) { setErr(e.message) } }
  return (
    <div className="modal-back" onMouseDown={onClose}>
      <div className="modal wide" onMouseDown={(e) => e.stopPropagation()}>
        <h3>Add new test plan</h3>
        <div className="form-grid aw-run">
          <label className="field"><span>Plan name</span><input value={p.name} onChange={(e) => setP({ ...p, name: e.target.value })} /></label>
          <label className="field"><span>Release</span><select value={p.release_id || ''} onChange={(e) => setP({ ...p, release_id: e.target.value })}>{d.releases.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}</select></label>
          <label className="field"><span>Standard suite</span><select value={p.suite || ''} onChange={(e) => setP({ ...p, suite: e.target.value })}><option value="">—</option>{['Smoke', 'Regression', 'Reconciliation', 'Security', 'Performance'].map((x) => <option key={x}>{x}</option>)}</select></label>
        </div>
        <div className="toolbar"><select value={type} onChange={(e) => setType(e.target.value)}><option value="">All types</option>{[...new Set(d.cases.map((c) => c.type))].map((t) => <option key={t}>{t}</option>)}</select>
          <button className="btn ghost small" onClick={() => setP((o) => ({ ...o, case_ids: [...new Set([...o.case_ids, ...list.map((c) => c.id)])] }))}>Select all shown</button>
          <span className="muted small">{p.case_ids.length} selected</span></div>
        <div className="aw-pick">{list.map((c) => <label key={c.id}><input type="checkbox" checked={p.case_ids.includes(c.id)} onChange={() => toggle(c.id)} /> <span className="mono small">{c.key}</span> {c.title.slice(0, 90)} <small className="muted">· {c.type}</small></label>)}</div>
        {err && <div className="note warn">{err}</div>}
        <div className="modal-actions"><span style={{ flex: 1 }} /><button className="btn ghost" onClick={onClose}>Cancel</button><button className="btn primary" onClick={save} disabled={!p.name || !p.case_ids.length}>Save plan</button></div>
      </div>
    </div>
  )
}

/* ---------------------------------------------------------------- Analytics */
export function AwAnalytics({ me }) {
  const [rel, setRel] = useState('')
  const [d, setD] = useLoad(`/api/assurance/analytics${rel ? `?release_id=${rel}` : ''}`, [rel])
  const [tab, setTab] = useState('feature')
  const [hot, setHot] = useState('critical')
  if (!d) return <div className="page">Loading…</div>
  const cov = d.stories ? Math.round((100 * d.covered) / d.stories) : 0
  const tested = d.stories ? Math.round((100 * d.tested) / d.stories) : 0
  const open = d.defects.filter((x) => x.status !== 'Closed')
  const canEdit = me?.lens === 'assurance'
  const setStatus = async (x, status) => { const n = await api.put(`/api/assurance/analytics/defects/${x.id}`, { status }); setD((o) => ({ ...o, defects: o.defects.map((y) => (y.id === n.id ? { ...y, ...n } : y)) })) }
  const sevs = ['Critical', 'Major', 'Minor']
  return (
    <div className="page">
      <Head crumb="Analytics · Test report summarizer" title="Is the release ready, and where is the risk?"
        lede="Coverage of user stories, results, feature readiness and hotspots; defects by severity; the tests to run first by impact and likelihood; and the tests that fail most, with root cause and resolution.">
        <select value={rel} onChange={(e) => setRel(e.target.value)}><option value="">All releases</option>{d.releases.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}</select>
      </Head>
      <Tabs tab={tab} setTab={setTab} tabs={[['feature', 'Feature-level test status'], ['defects', 'Defect impact analysis'], ['list', 'Defect impact analysis list'], ['impact', 'Impact-based test suggestion'], ['perf', 'Test case performance']]} />

      {tab === 'feature' && (<>
        <div className="aw-two">
          <section className="panel">
            <h4>User story details</h4>
            <div className="aw-big"><b>{d.stories}</b><span>Total user stories<small>extracted from the ALM and persona journeys to create test cases</small></span></div>
            <h5>User story coverage</h5>
            <div className="aw-gauge-row"><Ring pct={cov} label="covered by test cases" /><Ring pct={tested} label="tested in this scope" />
              <div><div className="aw-mini"><b>{d.covered}</b> covered</div><div className="aw-mini"><b>{d.stories - d.covered}</b> uncovered</div></div></div>
            <div className="note">Out of {d.stories} stories, {d.tested} are tested ({tested}% coverage). {d.stories - d.tested > 0 ? `Focus on the remaining ${d.stories - d.tested} untested stories.` : 'Every story has executed tests.'}</div>
          </section>
          <section className="panel">
            <h4>Overall test result summary</h4>
            <div className="aw-tiles">{[['Planned', d.planned], ['Actual', d.actual], ['Skipped', d.skipped], ['Passed', d.passed], ['Failed', d.failed]].map(([l, v]) => <div key={l} className={`aw-tile ${l.toLowerCase()}`}><b>{v}</b><span>{l}</span></div>)}</div>
            <h5>Feature readiness status</h5>
            <div className="aw-ready"><b>{d.features_ready}/{d.features_total}</b><span>features with no failing test</span></div>
            <table className="tbl"><thead><tr><th>Feature</th><th>Passed</th><th>Failed</th><th>Skipped</th><th /></tr></thead>
              <tbody>{d.features.map((f) => <tr key={f.feature}><td>{f.feature}</td><td>{f.passed}</td><td>{f.failed}</td><td>{f.skipped}</td><td><Pill s={f.failed ? 'failed' : 'passed'}>{f.failed ? 'Not ready' : 'Ready'}</Pill></td></tr>)}</tbody></table>
          </section>
        </div>
        <section className="panel">
          <h4>Hotspots and summary report</h4>
          <div className="tabs" style={{ marginBottom: 10 }}>{['critical', 'flaky', 'stable'].map((k) => <button key={k} className={hot === k ? 'on' : ''} onClick={() => setHot(k)}>{k[0].toUpperCase() + k.slice(1)} ({d.hotspots[k].length})</button>)}</div>
          <div className="md-table" style={{ maxHeight: 320, overflow: 'auto' }}><table className="tbl"><thead><tr><th>Test case</th><th>Priority</th><th>Runs</th><th>Failure rate</th><th>Self-healed</th></tr></thead>
            <tbody>{d.hotspots[hot].map((x) => <tr key={x.key}><td className="small"><span className="mono">{x.key}</span> {x.title.slice(0, 80)}</td><td className="small">{x.priority}</td><td>{x.runs}</td><td>{x.failure_rate}%</td><td>{x.healed}</td></tr>)}</tbody></table></div>
          {!d.hotspots[hot].length && <Empty>No data to display</Empty>}
        </section>
      </>)}

      {tab === 'defects' && (
        <div className="aw-two">
          <section className="panel">
            <h4>Defect details</h4>
            <div className="aw-tiles">{[['Total defects', d.defects.length], ['Open defects', open.length], ['Closed defects', d.defects.length - open.length]].map(([l, v]) => <div key={l} className="aw-tile"><b>{v}</b><span>{l}</span></div>)}</div>
            <div className="note">Prioritization of defects: severity and urgency follow the impact on trusted numbers and access — data and security defects on high-priority stories are critical.</div>
          </section>
          <section className="panel">
            <h4>Defect severity distribution</h4>
            {sevs.map((s) => <div key={s} className="pm-dim"><div><span>{s}</span><b>{d.severity[s] || 0}</b></div><i><em className={ST[s] === 'r' ? 'r' : ST[s] === 'a' ? 'a' : 's'} style={{ width: `${(100 * (d.severity[s] || 0)) / Math.max(1, d.defects.length)}%` }} /></i></div>)}
            <h5>By feature</h5>
            <table className="tbl"><thead><tr><th>Feature</th>{sevs.map((s) => <th key={s}>{s}</th>)}</tr></thead>
              <tbody>{Object.entries(d.by_suite).map(([f, v]) => <tr key={f}><td>{f}</td>{sevs.map((s) => <td key={s}>{v[s] || 0}</td>)}</tr>)}</tbody></table>
          </section>
        </div>
      )}

      {tab === 'list' && (
        <section className="panel"><div className="md-table"><table className="tbl">
          <thead><tr><th>Defect</th><th>Title</th><th>Severity</th><th>Feature</th><th>Component</th><th>Test case</th><th>Status</th></tr></thead>
          <tbody>{d.defects.map((x) => <tr key={x.id}><td className="mono small">{x.key}</td><td className="small">{x.title}<div className="muted">{x.cause}</div></td><td><Pill s={x.severity} /></td><td className="small">{x.feature}</td><td className="small">{x.component || '—'}</td><td className="mono small">{x.case_key}</td>
            <td>{canEdit ? <select value={x.status} onChange={(e) => setStatus(x, e.target.value)}>{['Open', 'In progress', 'Closed'].map((s) => <option key={s}>{s}</option>)}</select> : <Pill s={x.status} />}</td></tr>)}</tbody>
        </table></div>{!d.defects.length && <Empty>No data to display</Empty>}</section>
      )}

      {tab === 'impact' && (
        <section className="panel">
          <h4>High impact and high likelihood ({d.grid['High-High'].length})</h4>
          <p className="muted small">Impact comes from the test case priority; likelihood from its failure history and whether it maps to code that changed. Run the top-left cells first.</p>
          <div className="aw-grid">
            <span /><b>Likelihood: high</b><b>Medium</b><b>Low</b>
            {['High', 'Medium', 'Low'].map((i) => (<div key={i} style={{ display: 'contents' }}>
              <b className="aw-gl">Impact: {i.toLowerCase()}</b>
              {['High', 'Medium', 'Low'].map((l) => {
                const cell = d.grid[`${i}-${l}`]
                const tone = (i === 'High' && l !== 'Low') || (l === 'High' && i !== 'Low') ? 'r' : i === 'Low' && l === 'Low' ? 'g' : 'a'
                return <div key={l} className={`aw-cell ${tone}`}><b>{cell.length}</b>{cell.slice(0, 4).map((x) => <small key={x.key}><span className="mono">{x.key}</span> {x.title.slice(0, 44)}</small>)}{cell.length > 4 && <small className="muted">+{cell.length - 4} more</small>}</div>
              })}
            </div>))}
          </div>
        </section>
      )}

      {tab === 'perf' && (
        <section className="panel"><h4>Most failed test cases ({d.most_failed.length})</h4>
          <table className="tbl"><thead><tr><th>Test case ID</th><th>Test case</th><th>Failure rate (%)</th><th>Root cause</th><th>Resolution</th></tr></thead>
            <tbody>{d.most_failed.map((x) => <tr key={x.key}><td className="mono small">{x.key}</td><td className="small">{x.title}</td><td><b>{x.failure_rate}</b> <small className="muted">({x.fails}/{x.runs})</small></td><td className="small">{x.root_cause}</td><td className="small muted">{x.resolution}</td></tr>)}</tbody></table>
          {!d.most_failed.length && <Empty>No data to display</Empty>}</section>
      )}
    </div>
  )
}

function Ring({ pct, label }) {
  const r = 46; const c = 2 * Math.PI * r
  return (
    <div className="aw-ring"><svg viewBox="0 0 110 110" width="110" height="110" className="pm-gauge g">
      <circle cx="55" cy="55" r={r} className="bg" /><circle cx="55" cy="55" r={r} className="fg" style={{ stroke: '#7c5cff' }} strokeDasharray={`${(c * pct) / 100} ${c}`} transform="rotate(-90 55 55)" />
      <text x="55" y="61" textAnchor="middle">{pct}%</text></svg><small>{label}</small></div>
  )
}

/* ---------------------------------------------------------------- Maintenance */
export function AwMaintenance({ me, onNavigate }) {
  const [d, setD, reload] = useLoad('/api/assurance/maintenance')
  const [tab, setTab] = useState('mapping')
  const [sub, setSub] = useState('map')
  const [diff, setDiff] = useState('')
  const [rel, setRel] = useState('')
  const [msg, setMsg] = useState('')
  const [filter, setFilter] = useState('')
  const edit = me?.lens === 'assurance'
  const maps = useMemo(() => (d ? d.mappings.filter((m) => !filter || `${m.key} ${m.title} ${m.path}`.toLowerCase().includes(filter.toLowerCase())) : []), [d, filter])
  if (!d) return <div className="page">Loading…</div>
  const toggle = async (m) => setD(await api.put(`/api/assurance/maintenance/modules/${m.id}`, { changed: !m.changed }))
  const applyDiff = async () => setD(await api.post('/api/assurance/maintenance/diff', { paths: diff }))
  const plan = async () => { try { const p = await api.post('/api/assurance/maintenance/plan', { release_id: Number(rel) || null }); setMsg(`Created test plan “${p.name}” with ${p.case_ids.length} cases. Run it from Execution → Execution management.`) } catch (e) { setMsg(e.message) } }
  const codeCov = d.modules.filter((m) => m.lines).reduce((a, m) => [a[0] + m.covered, a[1] + m.lines], [0, 0])
  return (
    <div className="page">
      <Head crumb="Maintenance · High-impacted test cases" title="Keep the regression suite aligned with the code that changes"
        lede="Every test case is mapped to the code modules it exercises: dbt models, procedures, policies, semantic views, dashboards and harnesses. When files change, impact analysis picks the test cases to run and builds the regression plan.">
        {edit && <button className="btn ghost" onClick={async () => { await api.post('/api/assurance/maintenance/remap', {}); reload() }}>Generate mappings</button>}
      </Head>
      <Tabs tab={tab} setTab={setTab} tabs={[['mapping', 'Test case – code mappings'], ['impact', `Impact analysis (${d.impacted.length})`]]} />
      {tab === 'mapping' && (<>
        <div className="tabs" style={{ marginBottom: 10 }}>{[['map', 'Test case to source code mapping'], ['cov', 'Code coverage'], ['rec', 'Test case recommendation']].map(([k, l]) => <button key={k} className={sub === k ? 'on' : ''} onClick={() => setSub(k)}>{l}</button>)}</div>
        {sub === 'map' && (
          <section className="panel">
            <div className="toolbar"><span className="small muted">{d.mapped_cases} of {d.total_cases} test cases mapped to {d.modules.length} modules</span><span style={{ flex: 1 }} /><input className="search" placeholder="Filter by case or path" value={filter} onChange={(e) => setFilter(e.target.value)} /></div>
            <div className="md-table" style={{ maxHeight: 520, overflow: 'auto' }}><table className="tbl"><thead><tr><th>Test case</th><th>Type</th><th>Source code</th><th>Module</th><th>Mapping score</th></tr></thead>
              <tbody>{maps.slice(0, 400).map((m, i) => <tr key={i}><td className="small"><span className="mono">{m.key}</span> {m.title.slice(0, 70)}</td><td><Chip tone={TYPE_TONE[m.type]}>{m.type}</Chip></td><td className="mono small">{m.path}</td><td className="small">{m.module}</td>
                <td><div className="aw-score"><i style={{ width: `${m.score * 100}%` }} /></div><small>{m.score}</small></td></tr>)}</tbody></table></div>
            <p className="muted small">Mappings use the test case, its user story and each module's keywords. With an embedding model and a vector database connected, the same screen maps against the repository itself.</p>
          </section>
        )}
        {sub === 'cov' && (
          <section className="panel">
            <div className="aw-tiles">{[['Line coverage (SQL and code)', `${Math.round((100 * codeCov[0]) / Math.max(1, codeCov[1]))}%`], ['Modules with tests', `${d.modules.filter((m) => m.cases > 0).length}/${d.modules.length}`], ['Mapped test cases', `${d.mapped_cases}/${d.total_cases}`]].map(([l, v]) => <div key={l} className="aw-tile"><b>{v}</b><span>{l}</span></div>)}</div>
            <table className="tbl"><thead><tr><th>Module</th><th>Path</th><th>Kind</th><th>Mapped cases</th><th>Line coverage</th><th>Changed</th></tr></thead>
              <tbody>{d.modules.map((m) => <tr key={m.id}><td><b>{m.module}</b></td><td className="mono small">{m.path}</td><td className="small">{m.kind}</td><td>{m.cases}</td>
                <td>{m.lines ? <><div className="aw-score"><i style={{ width: `${(100 * m.covered) / m.lines}%` }} /></div><small>{Math.round((100 * m.covered) / m.lines)}% of {m.lines} lines</small></> : <small className="muted">n/a (dashboard)</small>}</td>
                <td>{edit ? <input type="checkbox" checked={m.changed} onChange={() => toggle(m)} /> : (m.changed ? '✓' : '—')}</td></tr>)}</tbody></table>
          </section>
        )}
        {sub === 'rec' && (
          <section className="panel"><h4>Test case recommendations</h4>
            {d.recommendations.map((r) => <div key={r.path} className="shared-row"><b>{r.module} <small className="muted mono">{r.path}</small></b><span className="muted">{r.suggest}. Currently {r.cases} mapped case(s).</span></div>)}
            {!d.recommendations.length && <Empty>Every module has at least two mapped test cases.</Empty>}
            {edit && <button className="btn ghost" style={{ marginTop: 10 }} onClick={() => onNavigate('aw_design')}>Generate cases in Design →</button>}
          </section>
        )}
      </>)}
      {tab === 'impact' && (<>
        {edit && (
          <section className="panel">
            <h4>What changed?</h4>
            <p className="muted small">Paste the output of <code>git diff --name-only main...HEAD</code>, or tick modules in Code coverage.</p>
            <textarea rows={4} style={{ width: '100%' }} value={diff} onChange={(e) => setDiff(e.target.value)} placeholder={'procs/sp_load_wms_incremental.sql\npolicies/rap_customer.sql'} />
            <div className="toolbar"><button className="btn primary" onClick={applyDiff} disabled={!diff.trim()}>Analyse impact</button><span style={{ flex: 1 }} />
              <select value={rel} onChange={(e) => setRel(e.target.value)}><option value="">No release</option>{d.releases.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}</select>
              <button className="btn ghost" onClick={plan} disabled={!d.impacted.length}>Create regression plan</button></div>
            {msg && <div className="note">{msg}</div>}
          </section>
        )}
        <section className="panel">
          <h4>Impacted test cases <small>changed: {d.modules.filter((m) => m.changed).map((m) => m.path).join(', ') || 'none'}</small></h4>
          <div className="md-table" style={{ maxHeight: 520, overflow: 'auto' }}><table className="tbl"><thead><tr><th>Risk</th><th>Test case</th><th>Type</th><th>Priority</th><th>Via module</th><th>Failures / runs</th></tr></thead>
            <tbody>{d.impacted.map((r) => <tr key={r.id}><td><b>{r.risk}</b></td><td className="small"><span className="mono">{r.key}</span> {r.title.slice(0, 80)}</td><td><Chip tone={TYPE_TONE[r.type]}>{r.type}</Chip></td><td className="small">{r.priority}</td><td className="small">{r.module}</td><td className="small">{r.fails}/{r.runs}</td></tr>)}</tbody></table></div>
          {!d.impacted.length && <Empty>No data to display. Mark what changed to see the impacted tests.</Empty>}
        </section>
      </>)}
    </div>
  )
}
