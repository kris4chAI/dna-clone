import { useEffect, useMemo, useState } from 'react'
import { api, getPersona, sessionId } from '../api'
import { Chip, Empty, Md } from '../components/ui'

export default function Skills({ me, focus, onNavigate }) {
  const [cat, setCat] = useState(null)
  const [sel, setSel] = useState(focus || '')
  const [term, setTerm] = useState('')
  useEffect(() => {
    api.get('/api/skills').then((c) => { setCat(c); setSel((s) => (s && c.skills.some((x) => x.name === s) ? s : c.skills[0]?.name)) })
  }, [])
  useEffect(() => { if (focus) setSel(focus.replace(/^\//, '')) }, [focus])

  const groups = useMemo(() => {
    if (!cat) return []
    const f = cat.skills.filter((s) => !term || `${s.name} ${s.title} ${s.description}`.toLowerCase().includes(term.toLowerCase()))
    const g = new Map()
    const key = (s) => s.kind === 'pursuit'
      ? [`P${String(s.stages[0].num).padStart(2, '0')}`, me.lens === 'delivery' ? 'Shared pursuit skills' : `Pursuit · stage ${s.stages.map((x) => x.num).join(', ')}`]
      : [`D${String(s.stage_seq).padStart(2, '0')}`, `${s.stage_seq}. ${s.stage_name}`]
    f.forEach((s) => { const [k, label] = key(s); const kk = me.lens === 'delivery' && s.kind === 'pursuit' ? 'Z' : k; if (!g.has(kk)) g.set(kk, { label, items: [] }); g.get(kk).items.push(s) })
    return [...g.entries()].sort((a, b) => a[0].localeCompare(b[0])).map(([, v]) => v)
  }, [cat, term, me.lens])

  if (!cat) return <div className="page">Loading…</div>
  const nPursuit = cat.skills.filter((s) => s.kind === 'pursuit').length
  const nDelivery = cat.skills.length - nPursuit

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">Skills studio · {me.lens} lens</div>
          <h1>{me.lens === 'sales' ? 'Run the pursuit skills on live pursuit data' : 'Generate Snowflake-ready artefacts, skill by skill'}</h1>
          <p className="lede">{me.lens === 'sales'
            ? 'Each pursuit skill runs as an engine over the kit, scorecard and rubric in this app, writes its results back, and hands you a ready-to-paste prompt for your LLM.'
            : 'Each implementation skill generates reviewable Snowflake SQL, schemachange, dbt, Terraform and runbooks. Download it as a .skill package, or execute reviewed SQL in a DEV account from here.'}</p>
        </div>
        <div className="status-pills">
          <span className="spill"><b>{nPursuit}</b> pursuit</span>
          {nDelivery > 0 && <span className="spill"><b>{nDelivery}</b> Snowflake delivery</span>}
          <span className={`spill ${cat.llm ? 'on' : ''}`} title="Set LLM_PROVIDER and LLM_API_KEY in .env">{cat.llm ? `LLM · ${cat.llm_status.provider} · ${cat.llm_status.model}` : 'LLM not configured · prompt mode'}</span>
          {me.lens === 'delivery' && <span className={`spill ${cat.snowflake.configured && cat.snowflake.execute_enabled ? 'on' : ''}`}>Snowflake {cat.snowflake.configured ? (cat.snowflake.execute_enabled ? `· ${cat.snowflake.account}` : 'read-only') : 'not connected'}</span>}
        </div>
      </header>

      <div className="split skills-split">
        <aside className="list">
          <input className="search" placeholder="Search skills…" value={term} onChange={(e) => setTerm(e.target.value)} style={{ width: '100%', marginBottom: 6 }} />
          {groups.map((g) => (
            <div key={g.label}>
              <div className="list-group">{g.label}</div>
              {g.items.map((s) => (
                <button key={s.name} className={`list-item ${s.name === sel ? 'on' : ''}`} onClick={() => setSel(s.name)}>
                  <b className={s.kind === 'delivery' ? 'mono' : ''}>{s.kind === 'delivery' ? `/${s.name}` : s.title}</b>
                  <small>{s.kind === 'delivery' ? `${s.title} · ${s.agent}` : s.name}</small>
                </button>
              ))}
            </div>
          ))}
        </aside>
        <div className="detail">{sel ? <SkillPanel key={sel} name={sel} me={me} cat={cat} onNavigate={onNavigate} /> : <Empty>Pick a skill.</Empty>}</div>
      </div>
    </div>
  )
}

function SkillPanel({ name, me, cat, onNavigate }) {
  const [sk, setSk] = useState(null)
  const [vals, setVals] = useState({})
  const [tab, setTab] = useState('run')
  const [res, setRes] = useState(null)
  const [busy, setBusy] = useState('')
  const [err, setErr] = useState('')
  const [file, setFile] = useState('')
  useEffect(() => {
    api.get(`/api/skills/${name}`).then((s) => { setSk(s); setVals(Object.fromEntries(s.fields.map((f) => [f.key, f.default ?? '']))) }).catch((e) => setErr(e.message))
  }, [name])
  if (err && !sk) return <Empty>{err}</Empty>
  if (!sk) return <div>Loading…</div>

  const run = async (mode) => {
    setBusy(mode); setErr('')
    try {
      const r = await api.post(`/api/skills/${name}/run`, { params: vals, mode, session_id: sessionId() })
      setRes(r); setFile(Object.keys(r.files)[0] || '')
      if (mode === 'prompt') { try { await navigator.clipboard.writeText(r.prompt) } catch { /* clipboard blocked */ } }
      api.get(`/api/skills/${name}`).then((s) => setSk((o) => ({ ...o, runs: s.runs })))
    } catch (e) { setErr(e.message) } finally { setBusy('') }
  }
  const delivery = sk.kind === 'delivery'

  return (
    <>
      <div className="persona-head">
        <div>
          <Chip tone={delivery ? 'snow' : 'agent'}>{delivery ? `Snowflake delivery skill · ${sk.package}` : 'Pursuit skill'}</Chip>
          <h2 className={delivery ? 'mono' : ''}>{delivery ? `/${sk.name}` : sk.title}</h2>
          <p>{delivery ? sk.description : sk.engine}</p>
          {delivery && <div className="muted small">{sk.agent} · stage <a className="link" onClick={() => onNavigate('workflow', sk.stage)}>{sk.stage}</a> · gate: {sk.gate}</div>}
          {delivery && <div className="chips" style={{ marginTop: 6 }}>{sk.snowflake.map((x) => <Chip key={x} tone="snow">{x}</Chip>)}</div>}
        </div>
        <a className="btn ghost" href={`/api/skills/${name}/package?persona_code=${encodeURIComponent(getPersona())}`}>Download .skill</a>
      </div>

      <div className="tabs" style={{ margin: '12px 0' }}>
        {[['run', 'Run'], ['md', 'SKILL.md'], ['runs', `History (${sk.runs.length})`]].map(([k, l]) => <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l}</button>)}
      </div>

      {tab === 'md' && <section className="panel skillmd"><Md text={sk.skill_md} compact /></section>}
      {tab === 'runs' && (
        <section className="panel">
          <table className="tbl"><thead><tr><th>#</th><th>When</th><th>By</th><th>Mode</th><th>Result</th><th /></tr></thead>
            <tbody>{sk.runs.map((r) => <tr key={r.id}><td>{r.id}</td><td className="small">{new Date(r.created_at).toLocaleString()}</td><td>{r.persona}</td><td>{r.mode}</td><td className="small">{r.summary}</td>
              <td><a className="link" href={`/api/skills/runs/${r.id}/zip?persona_code=${encodeURIComponent(getPersona())}`}>zip</a></td></tr>)}</tbody></table>
          {!sk.runs.length && <span className="muted">No runs yet.</span>}
        </section>
      )}

      {tab === 'run' && (
        <>
          <section className="panel">
            <h4>Inputs</h4>
            <div className="form-grid">
              {sk.fields.map((f) => <FieldInput key={f.key} f={f} v={vals[f.key]} set={(v) => setVals({ ...vals, [f.key]: v })} />)}
              {!sk.fields.length && <span className="muted">This skill reads its inputs from the pursuit kit (Commercials and value model).</span>}
            </div>
            <div className="run-bar">
              <button className="btn primary" disabled={!!busy} onClick={() => run('engine')}>{busy === 'engine' ? 'Running…' : delivery ? 'Generate artefacts' : 'Run engine'}</button>
              <button className="btn ghost" disabled={!!busy} onClick={() => run('prompt')}>Copy prompt for your LLM</button>
              <button className="btn ghost" disabled={!!busy || !cat.llm} title={cat.llm ? '' : 'Set LLM_PROVIDER and LLM_API_KEY in .env'} onClick={() => run('claude')}>{busy === 'claude' ? 'Drafting…' : `Draft with ${cat.llm ? cat.llm_status.provider : 'LLM'}`}</button>
              {err && <span className="err">{err}</span>}
            </div>
          </section>
          {res && <Result res={res} file={file} setFile={setFile} me={me} cat={cat} delivery={delivery} name={name} onNavigate={onNavigate} />}
        </>
      )}
    </>
  )
}

function FieldInput({ f, v, set }) {
  const area = ['textarea', 'lines', 'table'].includes(f.kind)
  return (
    <label className={`field ${area ? 'wide' : ''}`}>
      <span>{f.label}{f.kind === 'table' && <em> · CSV with header</em>}{f.kind === 'lines' && <em> · one per line</em>}</span>
      {f.kind === 'choice' || f.kind === 'pstage' ? (
        <select value={v ?? ''} onChange={(e) => set(e.target.value)}>{(f.options || []).map((o) => <option key={o}>{o}</option>)}</select>
      ) : f.kind === 'section' ? (
        <select value={v ?? ''} onChange={(e) => set(e.target.value)}><option value="">All sections</option>{Array.from({ length: 14 }, (_, i) => <option key={i + 1} value={i + 1}>Section {i + 1}</option>)}</select>
      ) : area ? (
        <textarea className="mono" rows={Math.min(10, Math.max(3, String(v || '').split('\n').length + 1))} value={v ?? ''} onChange={(e) => set(e.target.value)} />
      ) : (
        <input value={v ?? ''} onChange={(e) => set(e.target.value)} />
      )}
    </label>
  )
}

function Result({ res, file, setFile, me, cat, delivery, name, onNavigate }) {
  const [exec, setExec] = useState(null)
  const [confirm, setConfirm] = useState(false)
  const v = res.validation?.[file]
  const body = res.files[file] || ''
  const canExec = delivery && me.lens === 'delivery' && file.endsWith('.sql') && cat.snowflake.configured && cat.snowflake.execute_enabled
  const runExec = async () => {
    try { setExec(await api.post(`/api/skills/runs/${res.run_id}/execute`, { file, confirm })) } catch (e) { setExec({ error: e.message }) }
  }
  return (
    <section className="panel result">
      <div className="result-head">
        <div><h4>Result · run #{res.run_id}</h4><b>{res.summary}</b></div>
        <a className="btn ghost" href={`/api/skills/runs/${res.run_id}/zip?persona_code=${encodeURIComponent(getPersona())}`}>Download zip</a>
      </div>
      {res.notes?.length > 0 && <ul className="notes">{res.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>}
      {res.gate && <GatePanel gate={res.gate} />}
      {name === 'rfp-win-scorecard' && <button className="btn ghost" onClick={() => onNavigate('winroom')}>Open the win room →</button>}
      {name === 'rfp-section-loop' && <button className="btn ghost" onClick={() => onNavigate('quality')}>Open response quality →</button>}
      <div className="tabs files">{Object.keys(res.files).map((f) => <button key={f} className={f === file ? 'on' : ''} onClick={() => { setFile(f); setExec(null) }}>{f}</button>)}</div>
      <div className="file-bar">
        {v && <span className="vbadge">{v.statements} statements · {v.parsed} parsed by the SQL validator · {v.snowflake_only} Snowflake-specific (checked on execution){v.messages.length ? ` · ${v.messages[0]}` : ''}</span>}
        <button className="link" onClick={() => navigator.clipboard?.writeText(body)}>Copy</button>
      </div>
      {file.endsWith('.md') ? <div className="panel inner"><Md text={body} compact /></div> : <pre className="code big">{body}</pre>}
      {delivery && file.endsWith('.sql') && me.lens === 'delivery' && (
        <div className="exec">
          {canExec ? (
            <>
              <label><input type="checkbox" checked={confirm} onChange={(e) => setConfirm(e.target.checked)} /> A person reviewed this SQL; run it in {cat.snowflake.account} as {cat.snowflake.role}</label>
              <button className="btn primary" disabled={!confirm} onClick={runExec}>Execute on Snowflake</button>
            </>
          ) : <span className="muted small">To execute from here, connect a DEV account in .env (SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PRIVATE_KEY_FILE, SNOWFLAKE_ROLE, SNOWFLAKE_WAREHOUSE, SNOWFLAKE_ALLOW_EXECUTE=true) and restart. Or run <code>snow sql -f {file}</code>.</span>}
          {exec && <pre className="code">{JSON.stringify(exec, null, 2)}</pre>}
        </div>
      )}
      {res.claude && <div className="panel inner"><h4>LLM draft</h4><Md text={res.claude} compact /></div>}
      {res.claude_error && <div className="note warn">{res.claude_error}</div>}
      <details className="prompt"><summary>Prompt for your LLM (copied to the clipboard in prompt mode)</summary><pre className="code">{res.prompt}</pre></details>
    </section>
  )
}

export function GatePanel({ gate, onChange }) {
  const [d, setD] = useState({ approver: '', decision: 'Approved', conditions: '' })
  const [log, setLog] = useState(gate.decisions || [])
  const [err, setErr] = useState('')
  const save = async () => {
    setErr('')
    try { const r = await api.post('/api/skills/gate-decision', { stage: gate.stage, ...d }); setLog(r); onChange?.(r) } catch (e) { setErr(e.message) }
  }
  return (
    <div className={`gatebox ${gate.ready ? 'ready' : ''}`}>
      <b>{gate.gate_code} · {gate.ready ? 'ready for the gate' : 'not ready yet'}</b><span className="muted small"> · approver: {gate.approvers}</span>
      <div className="gate-form">
        <input placeholder="Approver name (required)" value={d.approver} onChange={(e) => setD({ ...d, approver: e.target.value })} />
        <select value={d.decision} onChange={(e) => setD({ ...d, decision: e.target.value })}>{['Approved', 'Approved with conditions', 'Rejected', 'Deferred'].map((x) => <option key={x}>{x}</option>)}</select>
        <input placeholder="Conditions" value={d.conditions} onChange={(e) => setD({ ...d, conditions: e.target.value })} />
        <button className="btn primary" onClick={save}>Record decision</button>
      </div>
      {!gate.ready && d.decision === 'Approved' && <span className="err">Not ready: questions or template inputs are still open. Record "Approved with conditions" and name them, or close them first.</span>}
      {err && <span className="err">{err}</span>}
      {log.map((x) => <div key={x.id} className="small">{new Date(x.decided_at).toLocaleDateString()} · <b>{x.decision}</b> by {x.approver}{x.conditions ? ` · ${x.conditions}` : ''} <span className="muted">(recorded by {x.recorded_by})</span></div>)}
    </div>
  )
}
