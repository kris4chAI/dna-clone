import { useCallback, useEffect, useRef, useState } from 'react'
import { api, getPersona } from '../api'
import DataTable from '../components/DataTable'
import { Empty } from '../components/ui'

/* TAF data checks inside the assurance workbench (merged from the TAF operator app).
   Data checks use TAF's statuses; UI, API and performance test cases keep passed/failed/skipped. */

export const TAF_STATUSES = ['Pass', 'Fail', 'Warn', 'Error', 'Skipped', 'Manual', 'Info', 'Not_Run', 'Blocked']
const CLS = { pass: 'g', passed: 'g', fail: 'r', failed: 'r', error: 'r', blocked: 'r', warn: 'a', partial: 'a', running: 's', info: 's',
  manual: 'n', skipped: 'n', not_run: 'n', no_data: 'n' }
export const Badge = ({ v }) => (v == null || v === '' ? <span className="muted">—</span> : <span className={`pm-rag ${CLS[String(v).toLowerCase()] || 'n'}`}>{String(v).replace('_', ' ')}</span>)
const Sev = ({ v }) => (v ? <span className={`taf-sev ${String(v).toLowerCase()}`}>{v}</span> : <span className="muted">—</span>)
export const fmtMs = (ms) => (ms == null || ms === '' ? '' : ms < 1000 ? `${ms} ms` : ms < 60000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`)
const fmt = (d) => (d ? new Date(d).toLocaleString() : '')

function useApi(path) {
  const [s, setS] = useState({ data: null, error: null, loading: true })
  const load = useCallback(() => { setS((o) => ({ ...o, loading: true })); api.get(path).then((data) => setS({ data, error: null, loading: false })).catch((error) => setS({ data: null, error, loading: false })) }, [path])
  useEffect(() => { load() }, [load])
  return { ...s, reload: load }
}

/** Metric strip computed from the rows on the page, so it never disagrees with the grid.
    statusKey=null shows no pass/fail (used where nothing has executed). */
export function MetricStrip({ rows, statusKey, extra = [], showTotal = true }) {
  const counts = {}
  if (statusKey) for (const r of rows || []) { const s = r[statusKey] == null ? 'Not_Run' : String(r[statusKey]); counts[s] = (counts[s] || 0) + 1 }
  const ordered = statusKey ? [...TAF_STATUSES.filter((s) => counts[s]), ...Object.keys(counts).filter((s) => !TAF_STATUSES.includes(s))] : []
  return (
    <div className="taf-metrics">
      {showTotal && <div className="taf-metric"><b>{(rows || []).length.toLocaleString()}</b><span>Total</span></div>}
      {ordered.map((s) => <div className="taf-metric" key={s}><b><Badge v={s} /> {counts[s]}</b><span>{s.replace('_', ' ')}</span></div>)}
      {extra.map((m) => <div className="taf-metric" key={m.label} title={m.title}><b>{typeof m.value === 'number' ? m.value.toLocaleString() : m.value}</b><span>{m.label}</span></div>)}
    </div>
  )
}

const Err = ({ e }) => (e ? <div className="note warn">{String(e.message || e)}</div> : null)

/* ---------------------------------------------------------------- Overview cards */
export function TafCards({ onNavigate }) {
  const d = useApi('/api/assurance/taf/dashboard')
  if (!d.data) return null
  const s = d.data.suites
  return (
    <section className="panel">
      <h4>Data checks (TAF) · latest run per suite <small>scenarios and distinct checks are counted separately: one failing query fails every scenario it covers</small></h4>
      <div className="taf-cards">
        {s.map((x) => {
          const pct = x.total ? Math.round((100 * x.pass_count) / x.total) : 0
          return (
            <div className="taf-card" key={x.suite}>
              <div className="taf-card-h"><b>{x.suite}</b><span className="mono small muted">{x.run_id} · {x.engine}</span></div>
              <div className="aw-bar"><i className="g" style={{ flex: pct }} /><i className="r" style={{ flex: 100 - pct }} /></div>
              <div className="taf-kv"><span>Scenarios</span><b>{x.total}</b><span>Pass / Fail / Warn / Error</span><b>{x.pass_count} / {x.fail_count} / {x.warn_count} / {x.error_count}</b>
                <span>Distinct checks</span><b>{x.distinct_checks}</b><span>Failed checks</span><b>{x.failed_checks}</b></div>
            </div>
          )
        })}
        <div className="taf-card"><div className="taf-card-h"><b>Runs</b><span className="small muted">{d.data.running} in progress</span></div>
          {d.data.runs.slice(0, 4).map((r) => <div key={r.run_id} className="taf-runline"><span className="mono small">{r.run_id}</span><Badge v={r.status} /><small className="muted">{r.engine}</small></div>)}
          {onNavigate && <button className="btn ghost small" onClick={() => onNavigate('aw_execution', 'taf')}>Run data checks →</button>}</div>
      </div>
    </section>
  )
}

/* ---------------------------------------------------------------- Test suite (control plane) */
export function TafSuite() {
  const [f, setF] = useState({ search: '', suite: '', category: '', active_only: false })
  const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v).map(([k, v]) => [k, String(v)])).toString()
  const d = useApi(`/api/assurance/taf/suite${qs ? `?${qs}` : ''}`)
  const [busy, setBusy] = useState(null)
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState(null)
  const rows = d.data?.rows || []
  const cats = [...new Set(rows.map((r) => r.functional_category).filter(Boolean))].sort()
  const toggle = async (r) => {
    setBusy(r.test_id); setErr(null)
    try { await api.post(`/api/assurance/taf/suite/${r.suite}/${encodeURIComponent(r.test_id)}/set-active`, { is_active: !r.is_active }); setMsg(`${r.test_id} ${r.is_active ? 'deactivated' : 'activated'} (verified). Takes effect on the next run.`); d.reload() } catch (e) { setErr(e) } finally { setBusy(null) }
  }
  const sync = async () => {
    setBusy('__sync'); setErr(null)
    try { const r = await api.post('/api/assurance/taf/suite/sync', {}); setMsg(`Synced: ${r.inserted} new case(s). Nothing you turned off was re-enabled.`); d.reload() } catch (e) { setErr(e) } finally { setBusy(null) }
  }
  return (
    <section className="panel">
      <div className="toolbar">
        <h4 style={{ margin: 0 }}>TAF test suite <small>which data checks are active; deactivated cases load as Not_Run on the next run, they do not vanish</small></h4>
        <span style={{ flex: 1 }} /><button className="btn ghost" onClick={sync} disabled={busy === '__sync'}>{busy === '__sync' ? 'Syncing…' : 'Sync from latest run'}</button>
      </div>
      <Err e={d.error || err} />{msg && <div className="note">{msg}</div>}
      <div className="toolbar">
        <input className="search" placeholder="Search id, title, table" value={f.search} onChange={(e) => setF({ ...f, search: e.target.value })} />
        <select value={f.suite} onChange={(e) => setF({ ...f, suite: e.target.value })}><option value="">All suites</option><option>TAF</option><option>EXTERNAL</option></select>
        <select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}><option value="">All categories</option>{cats.map((c) => <option key={c}>{c}</option>)}</select>
        <label className="small"><input type="checkbox" checked={f.active_only} onChange={(e) => setF({ ...f, active_only: e.target.checked })} /> Active only</label>
      </div>
      <MetricStrip rows={rows} statusKey={null} extra={[{ label: 'Active', value: rows.filter((r) => r.is_active).length }, { label: 'Inactive', value: rows.filter((r) => !r.is_active).length },
        { label: 'TAF', value: rows.filter((r) => r.suite === 'TAF').length }, { label: 'External', value: rows.filter((r) => r.suite === 'EXTERNAL').length }]} />
      <DataTable rows={rows} csvName="taf_test_suite.csv" rowKey={(r) => `${r.suite}:${r.test_id}`} columns={[
        { key: 'is_active', label: 'Active', width: 90, filterable: false, render: (r) => <button className={`btn small ${r.is_active ? 'primary' : 'ghost'}`} disabled={busy === r.test_id} onClick={() => toggle(r)}>{r.is_active ? 'Active' : 'Inactive'}</button> },
        { key: 'test_id', label: 'Test', mono: true, width: 120 }, { key: 'suite', label: 'Suite', width: 90 },
        { key: 'test_type', label: 'Type', width: 90 }, { key: 'severity', label: 'Severity', width: 90, render: (r) => <Sev v={r.severity} /> },
        { key: 'requirement_title', label: 'Scenario', width: 280 }, { key: 'functional_category', label: 'Category' }, { key: 'sheet_name', label: 'Sheet' },
        { key: 'target_table', label: 'Table', mono: true, width: 200 }, { key: 'assertion_name', label: 'Assertion / template', render: (r) => r.assertion_name || r.template_name || (r.test_type === 'SQL' ? 'SQL' : '—') },
        { key: 'lakehouse_type', label: 'Lakehouse test', render: (r) => (r.lakehouse_type ? `${r.lakehouse_type} ${r.lakehouse_name || ''}` : '—') },
        { key: 'last_status', label: 'Last result', render: (r) => <Badge v={r.last_status} /> }, { key: 'deactivated_by', label: 'Deactivated by' }, { key: 'source_ref', label: 'Authored at', mono: true },
      ]} />
    </section>
  )
}

/* ---------------------------------------------------------------- Run */
const MODE_HELP = { FULL: 'Every row. Slowest, most complete.', LATEST_LOAD: 'Only the newest load per table.', SINGLE_DATE: 'One business date.',
  DATE_RANGE: 'An inclusive date range.', INCREMENTAL: 'A rolling lookback window (default 1 day).', CDF_RANGE: 'Changes in a date range: Change Data Feed on Databricks, CHANGES on Snowflake.' }
const INITIAL = { engine: 'Simulator', test_scope: 'All Active Test Cases', run_scope: 'ALL', filter_mode: 'FULL', date_source: 'BUSINESS', filter_start_date: '', filter_end_date: '',
  lookback_days: '', filter_tenant_code: '', filter_period: '', filter_segment: '', sheet_filter: 'ALL', source_file_path: '', run_external_suite: 'yes', capture_records: 'yes',
  failure_max_rows: '10000', passing_sample_pct: '0', send_report: 'no', send_alerts: 'no', report_recipients: '', alert_recipients: '' }

function clientErrors(f) { // mirror of the backend checks for instant feedback; the backend re-validates
  const e = []
  if (f.filter_mode === 'LATEST_LOAD' && f.date_source === 'CDF') e.push('LATEST_LOAD cannot be combined with CDF.')
  if (f.filter_mode === 'SINGLE_DATE' && !f.filter_start_date) e.push('SINGLE_DATE needs a date.')
  if ((f.filter_mode === 'DATE_RANGE' || f.filter_mode === 'CDF_RANGE') && !(f.filter_start_date && f.filter_end_date)) e.push(`${f.filter_mode} needs a start and an end date.`)
  if (f.filter_start_date && f.filter_end_date && f.filter_start_date > f.filter_end_date) e.push('Start date is after end date.')
  if (f.test_scope === 'Client Specific Cases' && (!f.run_scope || f.run_scope === 'ALL') && !f.filter_tenant_code) e.push('Client Specific Cases needs a requirement-group tag or a tenant code.')
  return e
}

export function TafRun({ onOpenLog, onOpenResults }) {
  const cfg = useApi('/api/assurance/taf/config')
  const [f, setF] = useState(INITIAL)
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState(null)
  const [launched, setLaunched] = useState(null)
  const [status, setStatus] = useState(null)
  const timer = useRef(null)
  useEffect(() => () => clearTimeout(timer.current), [])
  if (!cfg.data) return <div className="panel">Loading…</div>
  const c = cfg.data
  const set = (k) => (v) => setF((s) => ({ ...s, [k]: v && v.target ? (v.target.type === 'checkbox' ? (v.target.checked ? 'yes' : 'no') : v.target.value) : v }))
  const errors = clientErrors(f)
  const needsDates = ['SINGLE_DATE', 'DATE_RANGE', 'CDF_RANGE'].includes(f.filter_mode)
  const eng = c.engines.find((x) => x.name === f.engine)
  const poll = (rid) => {
    clearTimeout(timer.current)
    api.get(`/api/assurance/taf/run-status/${rid}`).then((s) => { setStatus(s); if (!s.terminal) timer.current = setTimeout(() => poll(rid), 5000) })
      .catch((e) => { setStatus((s) => ({ ...(s || {}), poll_error: e.message })); timer.current = setTimeout(() => poll(rid), 10000) })
  }
  const upload = async () => {
    if (!file) return
    setBusy('upload'); setErr(null)
    try {
      const fd = new FormData(); fd.append('file', file); fd.append('engine', f.engine)
      const r = await fetch('/api/assurance/taf/upload', { method: 'POST', headers: { 'X-Persona': getPersona() || '' }, body: fd })
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`)
      setF((s) => ({ ...s, source_file_path: j.path })); setLaunched(null)
      setErr(j.imported ? { message: `Imported ${j.imported} external case(s) from ${file.name} into the test suite.` } : null)
    } catch (e) { setErr(e) } finally { setBusy('') }
  }
  const submit = async (e) => {
    e.preventDefault(); if (errors.length) return
    setBusy('run'); setErr(null); setStatus(null)
    try { const r = await api.post('/api/assurance/taf/execute', f); setLaunched(r); poll(r.run_id) } catch (e2) { setErr(e2) } finally { setBusy('') }
  }
  return (
    <>
      <form className="panel taf-form" onSubmit={submit}>
        <h4>Run data checks <small>a run is recorded the moment it starts, so closing this tab does not lose it</small></h4>
        <Err e={err} />
        <h5>Engine</h5>
        <div className="aw-seg">{c.engines.map((x) => <button type="button" key={x.name} className={f.engine === x.name ? 'on' : ''} onClick={() => setF({ ...f, engine: x.name })}><b>{x.name} {x.ready ? '' : '· not configured'}</b><small>{x.note}</small></button>)}</div>
        <h5>What to run</h5>
        <div className="taf-grid">
          <label className="field"><span>Test scope</span><select value={f.test_scope} onChange={set('test_scope')}>{c.scopes.map((s) => <option key={s}>{s}</option>)}</select>
            <small className="muted">{f.engine === 'Databricks' ? `Notebook chain: ${c.chains[f.test_scope].join(' → ')}` : `Runs ${c.scope_types[f.test_scope].join(', ')} checks`}</small></label>
          <label className="field"><span>Run scope (requirement group)</span><select value={f.run_scope} onChange={set('run_scope')}><option value="ALL">ALL</option>{c.groups.map((g) => <option key={g}>{g}</option>)}</select></label>
          <label className="field"><span>Sheet filter (external suite)</span><select value={f.sheet_filter} onChange={set('sheet_filter')}><option value="ALL">ALL</option>{c.sheets.map((g) => <option key={g}>{g}</option>)}</select></label>
          <div className="field"><span>Test-case file (optional)</span>
            <div className="toolbar" style={{ margin: 0 }}><input type="file" accept=".xlsx,.xlsm,.yaml,.yml,.json,.csv" onChange={(e) => setFile(e.target.files[0] || null)} />
              <button type="button" className="btn ghost small" disabled={!file || busy === 'upload'} onClick={upload}>{busy === 'upload' ? 'Uploading…' : 'Upload'}</button></div>
            <small className={f.source_file_path ? 'mono' : 'muted'}>{f.source_file_path ? <>Using {f.source_file_path} <button type="button" className="link" onClick={() => set('source_file_path')('')}>clear</button></> : f.engine === 'Databricks' ? 'Workbook or YAML goes to the TAF volume; blank uses the deployed workbook and cases/.' : 'YAML, JSON, CSV or Excel cases are imported into the EXTERNAL suite.'}</small></div>
        </div>
        <h5>Data scope</h5>
        <div className="taf-grid">
          <label className="field"><span>Filter mode</span><select value={f.filter_mode} onChange={set('filter_mode')}>{c.filter_modes.map((m) => <option key={m}>{m}</option>)}</select><small className="muted">{MODE_HELP[f.filter_mode]}</small></label>
          <label className="field"><span>Date source</span><select value={f.date_source} onChange={set('date_source')}>{c.date_sources.map((m) => <option key={m}>{m}</option>)}</select></label>
          {needsDates && <label className="field"><span>Start date</span><input type="date" value={f.filter_start_date} onChange={set('filter_start_date')} /></label>}
          {needsDates && f.filter_mode !== 'SINGLE_DATE' && <label className="field"><span>End date</span><input type="date" value={f.filter_end_date} onChange={set('filter_end_date')} /></label>}
          {f.filter_mode === 'INCREMENTAL' && <label className="field"><span>Lookback days</span><input type="number" min="1" value={f.lookback_days} onChange={set('lookback_days')} placeholder="1" /></label>}
          <label className="field"><span>Tenant code</span><input value={f.filter_tenant_code} onChange={set('filter_tenant_code')} placeholder="e.g. a customer code" /></label>
          <label className="field"><span>Period</span><input value={f.filter_period} onChange={set('filter_period')} placeholder="e.g. 2026" /></label>
          <label className="field"><span>Segment</span><input value={f.filter_segment} onChange={set('filter_segment')} /></label>
        </div>
        <small className="muted">Tables without the requested filter column record the skip reason on every result row.</small>
        <h5>Evidence and notification</h5>
        <div className="aw-sc">
          {[['run_external_suite', 'Run external suite'], ['capture_records', 'Capture failing rows'], ['send_report', 'Email run report'], ['send_alerts', 'Send quality alerts']].map(([k, l]) =>
            <label key={k}><input type="checkbox" checked={f[k] === 'yes'} onChange={set(k)} /> {l}</label>)}
        </div>
        <div className="taf-grid">
          <label className="field"><span>Failure rows cap per check</span><input type="number" min="0" value={f.failure_max_rows} onChange={set('failure_max_rows')} /></label>
          <label className="field"><span>Passing-row sample %</span><input type="number" min="0" max="100" step="0.1" value={f.passing_sample_pct} onChange={set('passing_sample_pct')} /><small className="muted">0 = off. Persisting passing rows costs money.</small></label>
          {f.send_report === 'yes' && <label className="field"><span>Report recipients</span><input value={f.report_recipients} onChange={set('report_recipients')} placeholder="a@x.com; b@x.com" /></label>}
          {f.send_alerts === 'yes' && <label className="field"><span>Alert recipients</span><input value={f.alert_recipients} onChange={set('alert_recipients')} /></label>}
        </div>
        {errors.length > 0 && <div className="note warn">{errors.map((x) => <div key={x}>{x}</div>)}</div>}
        <div className="toolbar"><button className="btn primary" type="submit" disabled={busy === 'run' || errors.length > 0 || !eng?.ready}>{busy === 'run' ? 'Starting…' : `Start run on ${f.engine}`}</button>
          <span className="muted small">Manual runs never fail for findings: findings make a run Partial. Zero executed checks is Error, never green.</span></div>
      </form>
      {launched && (
        <section className="panel">
          <h4>Run {launched.run_id}</h4>
          {launched.warnings?.map((w) => <div className="note warn" key={w}>{w}</div>)}
          <div className="taf-kv"><span>Engine</span><b>{launched.engine}</b>{launched.job_run_id && <><span>Job run id</span><b className="mono">{launched.job_run_id}</b></>}
            <span>Chain</span><b>{launched.chain.join(' → ')}</b>
            <span>State</span><b>{status ? `${status.life_cycle_state || ''}${status.result_state ? ' / ' + status.result_state : ''}${status.progress != null && !status.terminal ? ` · ${status.progress} checks done` : ''}` : 'submitted'}</b>
            {status?.manifest && status.terminal && <><span>Outcome</span><b><Badge v={status.manifest.status} /> <small className="muted">{status.manifest.notes}</small></b></>}
            {status?.run_page_url && <><span>Databricks</span><b><a href={status.run_page_url} target="_blank" rel="noreferrer">Open job run</a></b></>}</div>
          {status?.poll_error && <div className="note warn">Status poll failed, retrying: {status.poll_error}</div>}
          {status?.tasks?.length > 0 && <ul className="taf-tasks">{status.tasks.map((t) => <li key={t.task_key}><span className="mono">{t.task_key}</span> <Badge v={t.result_state || t.life_cycle_state} /></li>)}</ul>}
          <div className="toolbar"><button className="btn ghost small" onClick={() => onOpenLog?.(launched.run_id)}>View log</button>{status?.terminal && <button className="btn ghost small" onClick={() => onOpenResults?.(launched.run_id)}>Results</button>}</div>
        </section>
      )}
    </>
  )
}

/* ---------------------------------------------------------------- Results and assertions */
const RUN_PICK = (runs, value, onChange) => (
  <select value={value} onChange={(e) => onChange(e.target.value)}><option value="">Latest run</option>{runs.map((r) => <option key={r.run_id} value={r.run_id}>{r.run_id} · {r.engine} · {r.status}</option>)}</select>
)

export function TafResults({ runId: initial }) {
  const runs = useApi('/api/assurance/taf/runs')
  const [run, setRun] = useState(initial || '')
  const [view, setView] = useState('all')
  const [suite, setSuite] = useState('')
  const [open, setOpen] = useState(null)
  useEffect(() => { if (initial) setRun(initial) }, [initial])
  const params = new URLSearchParams({ ...(run ? { run_id: run } : {}), ...(suite ? { suite } : {}), ...(view !== 'all' ? { test_type: view } : {}) }).toString()
  const d = useApi(`/api/assurance/taf/results${params ? `?${params}` : ''}`)
  const rows = d.data?.rows || []
  const viol = rows.reduce((a, r) => a + (r.violation_count || 0), 0)
  const assertion = view !== 'all'
  return (
    <section className="panel">
      <div className="toolbar">
        <div className="tabs">{[['all', 'All results'], ['COLUMN', 'Column assertions'], ['TEMPLATE', 'Template assertions'], ['SQL', 'SQL assertions']].map(([k, l]) => <button key={k} className={view === k ? 'on' : ''} onClick={() => setView(k)}>{l}</button>)}</div>
        <span style={{ flex: 1 }} />
        {RUN_PICK(runs.data?.rows || [], run, setRun)}
        <select value={suite} onChange={(e) => setSuite(e.target.value)}><option value="">TAF + external</option><option>TAF</option><option>EXTERNAL</option></select>
        <button className="btn ghost small" onClick={() => { d.reload(); runs.reload() }}>Refresh</button>
      </div>
      <Err e={d.error} />
      {d.data?.run && <p className="small muted">Run <span className="mono">{d.data.run_id}</span> · {d.data.run.engine} · {d.data.run.test_scope} · {d.data.run.filter_mode}/{d.data.run.date_source} · <Badge v={d.data.run.status} /> {d.data.run.notes}</p>}
      <MetricStrip rows={rows} statusKey="status" extra={[{ label: 'Distinct checks', value: d.data?.distinct_checks || 0, title: 'One generated query can cover many scenarios' }, { label: 'Violations', value: viol }]} />
      <DataTable rows={rows} csvName={`taf_results_${view.toLowerCase()}.csv`} rowKey={(r) => `${r.suite}:${r.test_id}`} columns={[
        { key: 'test_id', label: 'Test', mono: true, width: 120, render: (r) => <a className="link mono" onClick={() => setOpen(r)}>{r.test_id}</a> },
        { key: 'suite', label: 'Suite', width: 90 }, { key: 'status', label: 'Status', width: 100, render: (r) => <Badge v={r.status} /> },
        { key: 'severity', label: 'Severity', width: 90, render: (r) => <Sev v={r.severity} /> }, { key: 'requirement_title', label: 'Scenario', width: 260 },
        ...(assertion ? [{ key: 'target_table', label: 'Table', mono: true, width: 190 }, { key: 'target_column', label: 'Column', mono: true },
          { key: 'assertion_name', label: 'Assertion', render: (r) => r.assertion_name || r.template_name || 'SQL' }] : [{ key: 'functional_category', label: 'Category' }, { key: 'check_id', label: 'Check', mono: true }]),
        { key: 'expected_result', label: 'Expected' }, { key: 'actual_result', label: 'Actual' }, { key: 'violation_count', label: 'Violations', width: 90 },
        { key: 'duration_ms', label: 'Duration', width: 90, render: (r) => fmtMs(r.duration_ms) }, { key: 'filter_applied', label: 'Scope applied' },
        { key: 'filter_skipped_reason', label: 'Scope skipped' }, { key: 'error_message', label: 'Error' }, { key: 'source_ref', label: 'Authored at', mono: true },
      ]} />
      {open && (
        <div className="modal-back" onMouseDown={() => setOpen(null)}><div className="modal wide" onMouseDown={(e) => e.stopPropagation()}>
          <h3>{open.test_id} · {open.requirement_title}</h3>
          <div className="taf-kv"><span>Status</span><b><Badge v={open.status} /></b><span>Violations</span><b>{open.violation_count ?? '—'}</b><span>Scope applied</span><b>{open.filter_applied}</b>
            {open.filter_skipped_reason && <><span>Scope skipped</span><b>{open.filter_skipped_reason}</b></>}{open.error_message && <><span>Error</span><b>{open.error_message}</b></>}</div>
          <h5>Executed SQL</h5><pre className="code">{open.executed_sql || '—'}</pre>
          {open.sample_rows?.length > 0 && <><h5>Sample rows</h5><pre className="code">{JSON.stringify(open.sample_rows, null, 2)}</pre></>}
          <div className="modal-actions"><span style={{ flex: 1 }} /><button className="btn ghost" onClick={() => setOpen(null)}>Close</button></div>
        </div></div>
      )}
    </section>
  )
}

/* ---------------------------------------------------------------- Run logs */
export function TafLogs({ runId }) {
  const runs = useApi('/api/assurance/taf/runs')
  const [sel, setSel] = useState(runId || '')
  const [tail, setTail] = useState(512)
  const [log, setLog] = useState(null)
  useEffect(() => { if (runId) setSel(runId) }, [runId])
  useEffect(() => { if (sel) api.get(`/api/assurance/taf/run-log/${sel}?tail_kb=${tail}`).then(setLog).catch((e) => setLog({ content: e.message })) }, [sel, tail])
  return (
    <section className="panel">
      <h4>Run logs <small>one consolidated log per run{runs.data?.reconciled ? ` · ${runs.data.reconciled} stranded run(s) closed` : ''}</small></h4>
      <DataTable rows={runs.data?.rows || []} csvName="taf_runs.csv" rowKey={(r) => r.run_id} columns={[
        { key: 'run_id', label: 'Run', mono: true, width: 220, render: (r) => <a className="link mono" onClick={() => setSel(r.run_id)}>{r.run_id}</a> },
        { key: 'engine', label: 'Engine', width: 100 }, { key: 'status', label: 'Status', width: 100, render: (r) => <Badge v={r.status} /> },
        { key: 'started_at', label: 'Started', render: (r) => fmt(r.started_at) }, { key: 'finished_at', label: 'Finished', render: (r) => fmt(r.finished_at) },
        { key: 'triggered_by', label: 'Trigger' }, { key: 'test_scope', label: 'Scope' }, { key: 'upstream_pipeline_run', label: 'Job run', mono: true },
        { key: 'total_tests', label: 'Total', width: 70 }, { key: 'pass_count', label: 'Pass', width: 70 }, { key: 'fail_count', label: 'Fail', width: 70 }, { key: 'error_count', label: 'Error', width: 70 }, { key: 'notes', label: 'Notes' },
      ]} />
      {sel && log && (<>
        <div className="toolbar"><b className="mono small">{sel}</b><span className="muted small">{log.source} {log.log_file}{log.truncated ? ' · truncated' : ''}</span><span style={{ flex: 1 }} />
          <label className="small">Tail <select value={tail} onChange={(e) => setTail(Number(e.target.value))}>{[64, 512, 2048, 20480].map((n) => <option key={n} value={n}>{n} KB</option>)}</select></label></div>
        <pre className="code taf-log">{log.content}</pre>
      </>)}
    </section>
  )
}

/* ---------------------------------------------------------------- Health scenarios */
export function TafScenarios({ edit }) {
  const d = useApi('/api/assurance/taf/scenarios')
  const [res, setRes] = useState({})
  const [busy, setBusy] = useState('')
  const [engine, setEngine] = useState('Workbench')
  const [err, setErr] = useState(null)
  const run = async (ids) => {
    setBusy(ids ? ids[0] : '__all'); setErr(null)
    try { const r = await api.post('/api/assurance/taf/scenarios/execute', { scenario_ids: ids, engine: engine === 'Databricks' ? 'Databricks' : undefined }); setRes((o) => ({ ...o, ...Object.fromEntries(r.rows.map((x) => [x.scenario_id, x])) })); d.reload() } catch (e) { setErr(e) } finally { setBusy('') }
  }
  const rows = d.data?.rows || []
  return (
    <section className="panel">
      <div className="toolbar"><h4 style={{ margin: 0 }}>Health scenarios <small>read-only checks on the test runs themselves; each states what it cannot prove</small></h4><span style={{ flex: 1 }} />
        {d.data?.databricks && <select value={engine} onChange={(e) => setEngine(e.target.value)}><option>Workbench</option><option>Databricks</option></select>}
        {edit && <button className="btn primary" disabled={!!busy} onClick={() => run(null)}>{busy === '__all' ? 'Running…' : 'Run all'}</button>}</div>
      <Err e={d.error || err} />
      <div className="taf-scen">{rows.map((s) => {
        const r = res[s.scenario_id]; const last = s.last_run
        const st = r?.status || last?.status
        return (
          <div key={s.scenario_id} className={`taf-sc ${st ? (CLS[st.toLowerCase()] || 'n') : ''}`}>
            <div className="taf-sc-h"><b>{s.scenario}</b><Badge v={st || 'not run'} /></div>
            <p className="small">{s.description}</p>
            <p className="small taf-caveat"><b>Cannot prove:</b> {s.caveat}</p>
            <div className="toolbar" style={{ margin: 0 }}><small className="muted">{s.kind === 'find' ? 'Finds offending rows' : 'Summary'}{(r || last) ? ` · ${r?.violation_count ?? last?.violation_count ?? '—'} row(s) · ${fmtMs(r?.duration_ms ?? last?.duration_ms)}` : ''}{last && !r ? ` · last ${fmt(last.executed_at)}` : ''}</small>
              <span style={{ flex: 1 }} />{edit && <button className="btn ghost small" disabled={!!busy} onClick={() => run([s.scenario_id])}>{busy === s.scenario_id ? '…' : 'Run'}</button>}</div>
            {(r?.evidence || last?.evidence)?.length > 0 && <details><summary className="small">Evidence</summary><pre className="code">{JSON.stringify(r?.evidence || last?.evidence, null, 1)}</pre></details>}
            {(r?.error_message || last?.error_message) && <div className="note warn small">{r?.error_message || last?.error_message}</div>}
          </div>
        )
      })}</div>
    </section>
  )
}

/* ---------------------------------------------------------------- Failure triage */
function FixEditor({ row, edit, onSaved }) {
  const [v, setV] = useState(row.recommended_fix || '')
  const [busy, setBusy] = useState(false)
  if (!edit) return <span className="small">{row.recommended_fix || <span className="muted">{row.suggested_fix ? `Suggested: ${row.suggested_fix}` : '—'}</span>}</span>
  const save = async (resolved) => { setBusy(true); try { await api.post(`/api/assurance/triage/${encodeURIComponent(row.failure_id)}/resolve`, { recommended_fix: v, resolved }); onSaved() } catch (e) { alert(e.message) } finally { setBusy(false) } }
  return (
    <div className="taf-fix">
      <textarea rows={2} value={v} placeholder={row.suggested_fix || 'Recommended fix'} onChange={(e) => setV(e.target.value)} />
      <div><button className="btn ghost small" disabled={busy} onClick={() => save(false)}>Save fix</button>
        {row.resolved ? <button className="btn ghost small" disabled={busy} onClick={() => save(false)}>Reopen</button> : <button className="btn primary small" disabled={busy || !v.trim()} onClick={() => save(true)}>Resolve</button>}</div>
    </div>
  )
}

export function Triage({ edit }) {
  const [inc, setInc] = useState(false)
  const [scope, setScope] = useState('latest')
  const d = useApi(`/api/assurance/triage?include_resolved=${inc}&scope=${scope}`)
  const rows = d.data?.rows || []
  const raise = async (r) => { try { const x = await api.post(`/api/assurance/triage/${encodeURIComponent(r.failure_id)}/defect`, {}); alert(`Raised ${x.key}`); d.reload() } catch (e) { alert(e.message) } }
  return (
    <section className="panel">
      <div className="toolbar"><h4 style={{ margin: 0 }}>Failure triage <small>every failed data check and test case lands here; record a fix and resolve, or raise a linked defect when it needs a code change</small></h4><span style={{ flex: 1 }} />
        <select value={scope} onChange={(e) => setScope(e.target.value)}><option value="latest">Latest runs</option><option value="all">All runs</option></select>
        <label className="small"><input type="checkbox" checked={inc} onChange={(e) => setInc(e.target.checked)} /> Include resolved</label></div>
      <Err e={d.error} />
      {d.data && <MetricStrip rows={rows} statusKey="status" extra={[{ label: 'Open', value: d.data.counts.open }, { label: 'High severity open', value: d.data.counts.high }, { label: 'Linked defects', value: d.data.counts.with_defect }, { label: 'Resolved', value: d.data.counts.resolved }]} />}
      <DataTable rows={rows} csvName="failure_triage.csv" rowKey={(r) => r.failure_id} maxCellChars={120} columns={[
        { key: 'failure_id', label: 'Failure', mono: true, width: 200 }, { key: 'source', label: 'Source', width: 100 }, { key: 'suite', label: 'Suite', width: 90 },
        { key: 'severity', label: 'Severity', width: 90, render: (r) => <Sev v={r.severity} /> }, { key: 'status', label: 'Status', width: 90, render: (r) => <Badge v={r.status} /> },
        { key: 'title', label: 'Scenario', width: 260 },
        { key: 'recommended_fix', label: 'Recommended fix', width: 300, filterable: false, render: (r) => <FixEditor key={`${r.failure_id}:${r.recommended_fix}:${r.resolved}`} row={r} edit={edit} onSaved={d.reload} /> },
        { key: 'defect_key', label: 'Defect', width: 130, render: (r) => (r.defect_key ? <span><b className="mono">{r.defect_key}</b> <Badge v={r.defect_status} /></span> : edit && !r.resolved ? <button className="btn ghost small" onClick={() => raise(r)}>Raise defect</button> : '—') },
        { key: 'violation_count', label: 'Violations', width: 90 }, { key: 'actual_result', label: 'Actual' }, { key: 'error_message', label: 'Error / root cause' },
        { key: 'run_id', label: 'Run', mono: true }, { key: 'engine', label: 'Engine' }, { key: 'resolved_by', label: 'Resolved by' }, { key: 'resolved_at', label: 'Resolved at', render: (r) => fmt(r.resolved_at) },
      ]} />
      {!rows.length && !d.loading && <Empty>No open failures.</Empty>}
    </section>
  )
}
