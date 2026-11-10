import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import { api, getPersona } from '../api'

/* Assurance workbench · Settings: asset management and connections (LLM, ALM, storage, DB, parser). */

const KIND_SHORT = { llm: 'LLM', alm: 'ALM', storage: 'Storage', db: 'DB', parser: 'Parser' }
const STATUS = { ok: ['g', 'Connected'], failed: ['r', 'Failed'], unverified: ['a', 'Saved, not verified'] }

function useGet(path) {
  const [d, setD] = useState(null)
  const [err, setErr] = useState('')
  const reload = useCallback(() => api.get(path).then((x) => { setD(x); setErr('') }).catch((e) => setErr(e.message)), [path])
  useEffect(() => { reload() }, [reload])
  return [d, reload, err]
}

const Empty = () => (
  <div className="st-empty"><div className="st-empty-ic">☁</div><b>No Data to Display</b><span>No records found at this time.</span></div>
)

/* ---------------------------------------------------------------- page */
export default function Settings({ onNavigate }) {
  const [top, setTop] = useState('assets')
  const [spec] = useGet('/api/assurance/settings/spec')
  return (
    <div className="page">
      <header className="page-head">
        <div><div className="eyebrow">Assurance workbench · Settings</div><h1>Settings</h1>
          <p className="lede">Switch workbench assets on or off and connect them to the services they need: LLMs, ALM tools, storage, databases and document parsers.</p></div>
      </header>
      <div className="st-top">{[['assets', 'Asset Management'], ['connections', 'Connections']].map(([k, l]) => <button key={k} className={top === k ? 'on' : ''} onClick={() => setTop(k)}>{l}</button>)}</div>
      {top === 'assets' && <Assets onNavigate={onNavigate} goConnections={() => setTop('connections')} />}
      {top === 'connections' && spec && <Connections spec={spec} />}
    </div>
  )
}

/* ---------------------------------------------------------------- asset management */
function Assets({ onNavigate, goConnections }) {
  const [d, reload, err] = useGet('/api/assurance/settings/assets')
  const [busy, setBusy] = useState('')
  if (!d) return <div className="panel">{err || 'Loading…'}</div>
  const toggle = async (a) => { setBusy(a.code); try { await api.put(`/api/assurance/settings/assets/${a.code}`, { enabled: !a.enabled }); await reload() } catch (e) { alert(e.message) } finally { setBusy('') } }
  const ready = d.assets.filter((a) => a.enabled && a.ready).length
  return (
    <>
      <p className="small muted">{ready} of {d.assets.filter((a) => a.enabled).length} switched-on assets have every connection they need. A ticked chip means the connection is configured; <button className="link" onClick={goConnections}>open Connections</button> to add the rest.</p>
      <div className="st-assets">
        {d.assets.map((a) => (
          <div key={a.code} className={`st-asset ${a.enabled ? '' : 'off'}`}>
            <div className="st-asset-h">
              <span className="st-av" style={{ background: a.color }}>{a.name[0]}</span>
              <div className="st-asset-t"><b>{a.name}</b>
                <div className="st-chips">{a.needs.map((k) => { const c = a.connections[k]; return (
                  <span key={k} className={`st-chip ${c.ok ? 'ok' : ''}`} title={c.ok ? `${KIND_SHORT[k]}: ${c.via}` : `No ${KIND_SHORT[k]} connection configured for this asset`}>{c.ok ? '✓' : '○'} {KIND_SHORT[k]}</span>) })}</div>
              </div>
              <label className="st-switch" title={a.enabled ? 'Switch off' : 'Switch on'}>
                <input type="checkbox" checked={a.enabled} disabled={busy === a.code} onChange={() => toggle(a)} aria-label={`${a.name} enabled`} /><i />
              </label>
            </div>
            <p>{a.description}</p>
            {onNavigate && a.screen && <button className="link st-open" onClick={() => onNavigate(a.screen, a.tab)}>Open in the workbench →</button>}
          </div>
        ))}
      </div>
    </>
  )
}

/* ---------------------------------------------------------------- connections */
function Connections({ spec }) {
  const [kind, setKind] = useState('llm')
  const [d, reload, err] = useGet(`/api/assurance/settings/connections?kind=${kind}`)
  const [form, setForm] = useState(null)
  const [cfg, setCfg] = useState(false)
  const [tests, setTests] = useState({})
  const [open, setOpen] = useState({})
  const K = spec.kinds.find((k) => k.code === kind)
  const rows = d?.rows || []
  const groups = useMemo(() => { const g = {}; for (const r of rows) (g[r.provider_label] = g[r.provider_label] || []).push(r); return g }, [rows])
  const test = async (r) => {
    setTests((t) => ({ ...t, [r.id]: { status: 'running', message: 'Testing…' } }))
    try { const x = await api.post(`/api/assurance/settings/connections/${kind}/${encodeURIComponent(r.id)}/test`, {}); setTests((t) => ({ ...t, [r.id]: x })) } catch (e) { setTests((t) => ({ ...t, [r.id]: { status: 'failed', message: e.message } })) }
  }
  const del = async (r) => { if (!confirm(`Delete the connection "${r.name}"? Assets that use it lose their connection.`)) return; try { await api.del(`/api/assurance/settings/connections/${kind}/${r.id}`); reload() } catch (e) { alert(e.message) } }
  return (
    <section className="panel st-conn">
      <div className="st-bar">
        <div className="st-sub" role="tablist">{spec.kinds.map((k) => <button role="tab" aria-selected={k.code === kind} key={k.code} className={k.code === kind ? 'on' : ''} onClick={() => { setKind(k.code); setTests({}) }}>{k.label}</button>)}</div>
        <span style={{ flex: 1 }} />
        {K.configurable && <button className="btn ghost" onClick={() => setCfg(true)}>⚙ Configure Connection</button>}
        <button className="btn primary" onClick={() => setForm({})}>{K.add}</button>
      </div>
      {err && <div className="note warn">{err}</div>}
      {d && !rows.length && <Empty />}
      {Object.entries(groups).map(([g, list]) => (
        <div key={g} className="st-group">
          <button className="st-group-h" onClick={() => setOpen((o) => ({ ...o, [g]: !(o[g] ?? true) }))}>{(open[g] ?? true) ? '▾' : '▸'} {g} <small className="muted">{list.length}</small></button>
          {(open[g] ?? true) && <div className="st-cards">{list.map((r) => {
            const t = tests[r.id] || (r.test_status ? { status: r.test_status, message: r.test_message } : null)
            const [tone, word] = t ? (STATUS[t.status] || ['s', 'Testing']) : ['n', '']
            const used = Object.entries(d.assignments[kind] || {}).filter(([, v]) => v === r.id).map(([a]) => a)
            return (
              <div key={r.id} className="st-card">
                <div className="st-card-h"><span className="st-av">{r.name[0].toUpperCase()}</span>
                  <div><b>{r.name}</b><small>{r.provider_label}{r.origin === 'env' ? ' · from .env, read-only' : ''}</small></div></div>
                <dl className="st-kv">{[
                  ...Object.entries(r.config || {}).filter(([, v]) => v).slice(0, 4).map(([k, v]) => [k, k === 'target_asset' ? r.target_asset_name : String(v)]),
                  ...(r.file_name ? [['file', r.file_name]] : []),
                  ...Object.entries(r.secrets || {}).map(([k, v]) => [k, v, true]),
                  ...(used.length ? [['used by', used.includes('*') ? 'All assets' : `${used.length} asset${used.length > 1 ? 's' : ''}`]] : []),
                ].map(([k, v, m]) => <Fragment key={k}><dt>{k.replace(/_/g, ' ')}</dt><dd className={m ? 'mono' : undefined}>{v}</dd></Fragment>)}</dl>
                {t && <div className={`st-test ${tone}`}>{word && <b>{word}</b>} {t.message}</div>}
                <div className="st-card-f">
                  <button className="link" onClick={() => test(r)} disabled={t?.status === 'running'}>Test Connection</button>
                  <span style={{ flex: 1 }} />
                  {r.origin !== 'env' && <><button className="icon-btn sm" title="Edit" onClick={() => setForm(r)}>✎</button><button className="icon-btn sm danger" title="Delete" onClick={() => del(r)}>🗑</button></>}
                </div>
              </div>
            )
          })}</div>}
        </div>
      ))}
      <p className="small muted st-foot">Credentials are encrypted before they are stored and are never sent back to the browser (key: <span className="mono">{spec.key_source}</span>). Connections set in <span className="mono">.env</span> show here read-only.</p>
      {form && <ConnForm spec={spec} kind={kind} edit={form.id ? form : null} onClose={() => setForm(null)} onSaved={() => { setForm(null); reload() }} />}
      {cfg && <Configure kind={kind} label={K.code === 'llm' ? 'LLM' : 'parser'} onClose={() => setCfg(false)} onSaved={() => { setCfg(false); reload() }} />}
    </section>
  )
}

/* ---------------------------------------------------------------- add / edit connection */
function Field({ f, value, onChange, assets, edit, secretHint }) {
  const [show, setShow] = useState(false)
  const id = `st-${f.key}`
  const label = <label htmlFor={id}>{f.label}{f.required && <em className="req"> *</em>}</label>
  if (f.type === 'file') return null
  if (f.type === 'select') return <div className="field">{label}<select id={id} value={value ?? f.default ?? ''} onChange={(e) => onChange(e.target.value)}><option value="" disabled>Choose the {f.label.toLowerCase()}</option>{f.options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></div>
  if (f.type === 'asset') return <div className="field">{label}<select id={id} value={value || ''} onChange={(e) => onChange(e.target.value)}><option value="">Select target asset</option>{assets.map((a) => <option key={a.code} value={a.code}>{a.name}</option>)}</select></div>
  if (f.type === 'model') return <div className="field">{label}<input id={id} list={`${id}-l`} value={value || ''} placeholder={f.placeholder} onChange={(e) => onChange(e.target.value)} /><datalist id={`${id}-l`}>{f.options.map((o) => <option key={o} value={o} />)}</datalist></div>
  if (f.type === 'secret_text') return <div className="field wide">{label}<textarea id={id} rows={4} value={value || ''} placeholder={edit && secretHint ? `${secretHint} · leave blank to keep` : f.placeholder} onChange={(e) => onChange(e.target.value)} /></div>
  if (f.type === 'password') return (
    <div className="field">{label}<div className="st-pw"><input id={id} type={show ? 'text' : 'password'} autoComplete="new-password" value={value || ''}
      placeholder={edit && secretHint ? `${secretHint} · leave blank to keep` : f.placeholder || ''} onChange={(e) => onChange(e.target.value)} />
      <button type="button" className="icon-btn sm" onClick={() => setShow(!show)} title={show ? 'Hide' : 'Show'}>{show ? '◉' : '◎'}</button></div>{f.help && <small className="muted">{f.help}</small>}</div>)
  return <div className="field">{label}<input id={id} value={value ?? ''} placeholder={f.placeholder || ''} onChange={(e) => onChange(e.target.value)} />{f.help && <small className="muted">{f.help}</small>}</div>
}

function ConnForm({ spec, kind, edit, onClose, onSaved }) {
  const K = spec.kinds.find((k) => k.code === kind)
  const [provider, setProvider] = useState(edit?.provider || K.providers[0].code)
  const [name, setName] = useState(edit?.name || '')
  const [vals, setVals] = useState(() => edit ? { ...edit.config } : {})
  const [file, setFile] = useState(null)
  const [drag, setDrag] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const P = K.providers.find((p) => p.code === provider)
  const withDefaults = { ...Object.fromEntries(P.fields.filter((f) => f.default).map((f) => [f.key, f.default])), ...vals }
  const active = P.fields.filter((f) => !f.when || Object.entries(f.when).every(([k, v]) => String(withDefaults[k] ?? '') === v))
  const assets = spec.assets.filter((a) => a.needs.includes(kind))
  const missing = [!name.trim() && 'Connection Name', ...active.filter((f) => f.required && (f.type === 'file' ? !file && !edit?.file_name : f.secret ? !vals[f.key] && !edit?.secrets?.[f.key] : !String(withDefaults[f.key] ?? '').trim())).map((f) => f.label)].filter(Boolean)
  const pickProvider = (p) => { setProvider(p); if (!edit) setVals({}) }
  const save = async () => {
    setBusy(true); setErr('')
    try {
      if (kind === 'storage' && provider === 'local') {
        const fd = new FormData(); fd.append('name', name); fd.append('target_asset', vals.target_asset || ''); if (edit) fd.append('conn_id', edit.id); if (file) fd.append('file', file)
        const r = await fetch('/api/assurance/settings/connections/storage/local', { method: 'POST', headers: { 'X-Persona': getPersona() || '' }, body: fd })
        const j = await r.json(); if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`)
      } else {
        const config = {}, secrets = {}
        for (const f of active) { if (f.type === 'file') continue; const v = withDefaults[f.key]; if (f.secret) { if (v) secrets[f.key] = v } else if (v !== undefined && v !== '') config[f.key] = v }
        const body = { provider, name, config, secrets }
        if (edit) await api.put(`/api/assurance/settings/connections/${kind}/${edit.id}`, body); else await api.post(`/api/assurance/settings/connections/${kind}`, body)
      }
      onSaved()
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  const radios = kind === 'alm'
  return (
    <div className="modal-back" onMouseDown={onClose}><div className="modal wide st-modal" role="dialog" aria-label={`${edit ? 'Edit' : 'Add'} ${KIND_SHORT[kind]} connection`} onMouseDown={(e) => e.stopPropagation()}>
      <div className="st-modal-h"><h3>{edit ? 'Edit' : kind === 'storage' ? 'Add New' : 'Add'} {KIND_SHORT[kind]} Connection</h3><button className="icon-btn" onClick={onClose} aria-label="Close">⊗</button></div>
      {err && <div className="note warn">{err}</div>}
      {radios && <div className="field"><label>Provider<em className="req"> *</em></label><div className="st-radios">{K.providers.map((p) => <label key={p.code}><input type="radio" name="st-prov" checked={provider === p.code} onChange={() => pickProvider(p.code)} /> {p.label}</label>)}</div></div>}
      <div className="form-grid st-grid">
        <div className={`field ${radios ? 'wide' : ''}`}><label htmlFor="st-name">Connection Name<em className="req"> *</em></label><input id="st-name" value={name} placeholder="Enter connection name" onChange={(e) => setName(e.target.value)} /></div>
        {!radios && <div className="field"><label htmlFor="st-prov">{kind === 'db' ? 'Database Type' : kind === 'storage' ? 'Type' : 'Provider'}<em className="req"> *</em></label>
          <select id="st-prov" value={provider} disabled={K.providers.length === 1} onChange={(e) => pickProvider(e.target.value)}>{K.providers.map((p) => <option key={p.code} value={p.code}>{p.label}</option>)}</select></div>}
        {active.map((f) => <Field key={f.key} f={f} value={withDefaults[f.key]} assets={assets} edit={!!edit} secretHint={edit?.secrets?.[f.key]} onChange={(v) => setVals((s) => ({ ...s, [f.key]: v }))} />)}
      </div>
      {active.some((f) => f.type === 'file') && (
        <div className="field"><label>Upload file<em className="req"> *</em></label>
          <label className={`st-drop ${drag ? 'drag' : ''}`} onDragOver={(e) => { e.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]) }}>
            <input type="file" onChange={(e) => setFile(e.target.files[0] || null)} />
            {file ? <b>{file.name} <small className="muted">{(file.size / 1024).toFixed(1)} KB</small></b> : edit?.file_name ? <span>Current: <b>{edit.file_name}</b> · drop a file to replace it</span> : <span>Drag & drop your file here or <u>Choose file</u></span>}
          </label><small className="muted">Up to 25 MB. Kept in the app's data volume.</small></div>
      )}
      <div className="modal-actions"><span className="small muted">{missing.length ? `Required: ${missing.join(', ')}` : ''}</span><span style={{ flex: 1 }} />
        <button className="btn ghost" onClick={onClose}>Cancel</button><button className="btn primary" disabled={busy || missing.length > 0} onClick={save}>{busy ? 'Saving…' : edit ? 'Save' : 'Add'}</button></div>
    </div></div>
  )
}

/* ---------------------------------------------------------------- configure (assign to assets) */
function Configure({ kind, label, onClose, onSaved }) {
  const [d] = useGet(`/api/assurance/settings/assign/${kind}`)
  const [mode, setMode] = useState(null)
  const [all, setAll] = useState('')
  const [per, setPer] = useState({})
  const [err, setErr] = useState('')
  useEffect(() => { if (d && mode === null) { setMode(d.mode); setAll(d.all || ''); setPer(d.per_asset || {}) } }, [d, mode])
  if (!d || mode === null) return null
  const incomplete = mode === 'per_asset' ? d.assets.some((a) => !per[a.code]) : !all
  const save = async () => { setErr(''); try { await api.put(`/api/assurance/settings/assign/${kind}`, { mode, all, per_asset: per }); onSaved() } catch (e) { setErr(e.message) } }
  const Sel = ({ value, onChange, disabled }) => <select value={value || ''} disabled={disabled} onChange={(e) => onChange(e.target.value)}><option value="">Select connection</option>{d.options.map((o) => <option key={o.id} value={o.id}>{o.name} · {o.provider}</option>)}</select>
  return (
    <div className="modal-back" onMouseDown={onClose}><div className="modal wide st-modal" role="dialog" aria-label="Configure connection" onMouseDown={(e) => e.stopPropagation()}>
      <div className="st-modal-h"><h3>Configure Connection</h3><button className="icon-btn" onClick={onClose} aria-label="Close">⊗</button></div>
      {err && <div className="note warn">{err}</div>}
      {!d.options.length && <div className="note warn">Add a {label} connection first.</div>}
      <h5>Global</h5>
      <div className={`st-cfg ${mode === 'all' ? 'on' : ''}`}><label><input type="radio" checked={mode === 'all'} onChange={() => setMode('all')} /> Configure {label} connections for all assets</label><Sel value={all} onChange={setAll} disabled={mode !== 'all'} /></div>
      <h5>Individual assets</h5>
      <div className={`st-cfg col ${mode === 'per_asset' ? 'on' : ''}`}>
        <label><input type="radio" checked={mode === 'per_asset'} onChange={() => setMode('per_asset')} /> Configure {label} connections per asset</label>
        {mode === 'per_asset' && <div className="st-per">{d.assets.map((a) => <div key={a.code}><span>{a.name}<em className="req"> *</em></span><Sel value={per[a.code]} onChange={(v) => setPer((p) => ({ ...p, [a.code]: v }))} /></div>)}
          <small className="muted">* All assets must have a connection configured before saving.</small></div>}
      </div>
      <div className="modal-actions"><span style={{ flex: 1 }} /><button className="btn ghost" onClick={onClose}>Cancel</button><button className="btn primary" disabled={incomplete} onClick={save}>Save</button></div>
    </div></div>
  )
}
