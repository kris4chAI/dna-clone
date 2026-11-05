import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { Chip, CurationBanner, Editor, Origin } from '../components/ui'

const TABS = [['areas', 'Subject areas'], ['schemas', 'Schemas & attributes'], ['kpis', 'KPI library']]
const AUD = { E: 'Executive', O: 'Operational', C: 'External customer' }

export default function DataModels({ focus }) {
  const [m, setM] = useState(null)
  const [tab, setTab] = useState(TABS.some(([t]) => t === focus) ? focus : 'areas')
  const [edit, setEdit] = useState(null)
  const load = () => api.get('/api/datamodel').then(setM)
  useEffect(() => { load() }, [])
  useEffect(() => { if (TABS.some(([t]) => t === focus)) setTab(focus) }, [focus])
  if (!m) return <div className="page">Loading…</div>

  const save = (t, id) => async (d) => { id ? await api.update(t, id, d) : await api.create(t, d); load() }
  const del = (t, id) => (id ? () => api.remove(t, id).then(load) : null)

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">3 Data · logistics industry data model</div>
          <h1>Twenty subject areas on a conformed backbone</h1>
          <p className="lede">Reference: Databricks Transport &amp; Shipping model plus Oracle OTM and Fusion SCM subject areas, tailored to CJLA and checked against Oracle ADW in discovery.</p>
        </div>
      </header>
      <CurationBanner slides="25–29">Curate subject areas, facts, dimensions, attributes and certified KPIs for the logistics industry model.</CurationBanner>
      <div className="tabs">{TABS.map(([id, l]) => <button key={id} className={tab === id ? 'on' : ''} onClick={() => setTab(id)}>{l}</button>)}</div>

      {tab === 'areas' && <Areas m={m} setEdit={setEdit} />}
      {tab === 'schemas' && <Schemas m={m} setEdit={setEdit} />}
      {tab === 'kpis' && <Kpis m={m} setEdit={setEdit} />}

      {edit && (
        <Editor title={edit.d.id ? `Edit ${edit.d.name || ''}` : `Add ${edit.label}`} initial={edit.d}
          fields={fieldsFor(edit.t, m)} onSave={save(edit.t, edit.d.id)} onDelete={del(edit.t, edit.d.id)} onClose={() => setEdit(null)} />
      )}
    </div>
  )
}

function fieldsFor(t, m) {
  const areas = m.domains.flatMap((d) => d.areas).map((a) => ({ value: a.id, label: `${a.num}. ${a.name}` }))
  return {
    domain: [{ key: 'name', label: 'Domain', required: true }, { key: 'source', label: 'Source systems' }],
    subject_area: [{ key: 'domain_id', label: 'Domain', type: 'select', options: m.domains.map((d) => ({ value: d.id, label: d.name })) },
      { key: 'num', label: 'Number', type: 'number' }, { key: 'name', label: 'Subject area', required: true }, { key: 'entities', label: 'Entities', type: 'textarea' }],
    data_entity: [{ key: 'model', label: 'Model', type: 'select', options: ['Warehouse', 'Transportation', 'Automation & labor', 'Customer & commercial', 'Workforce & enterprise'] },
      { key: 'name', label: 'Table name', required: true }, { key: 'kind', label: 'Kind', type: 'select', options: ['fact', 'dim'] },
      { key: 'type', label: 'Type (Transaction, Snapshot, Accumulating, SCD1, SCD2…)' }, { key: 'description', label: 'Grain / description', type: 'textarea' },
      { key: 'subject_area_id', label: 'Subject area', type: 'select', options: areas }],
    attribute: [{ key: 'name', label: 'Attribute', required: true }, { key: 'role', label: 'Role', type: 'select', options: ['PK', 'FK', 'DD', 'measure', 'attribute', 'placeholder'] },
      { key: 'description', label: 'Description', type: 'textarea' }],
    kpi: [{ key: 'domain', label: 'Domain', type: 'select', options: [...new Set(m.kpis.map((k) => k.domain))] }, { key: 'name', label: 'KPI', required: true },
      { key: 'formula', label: 'Formula' }, { key: 'audiences', label: 'Audiences (E,O,C)' }, { key: 'source_fact', label: 'Source fact' },
      { key: 'owner', label: 'Owner' }, { key: 'grain', label: 'Grain' }],
    conformed_dim: [{ key: 'name', label: 'Conformed dimension', required: true }],
  }[t]
}

function Areas({ m, setEdit }) {
  return (
    <>
      <div className="domains">
        {m.domains.map((d) => (
          <div key={d.id} className="domain">
            <div className="domain-head"><b>{d.name}</b><small>{d.areas.length} subject areas · {d.source}</small></div>
            {d.areas.map((a) => (
              <div key={a.id} className="area" onClick={() => setEdit({ t: 'subject_area', d: a, label: 'subject area' })}>
                <span className="area-num">{a.num}</span>
                <div><b>{a.name} <Origin origin={a.origin} /></b><small>{a.entities}</small></div>
              </div>
            ))}
            <button className="add-link" onClick={() => setEdit({ t: 'subject_area', d: { domain_id: d.id }, label: 'subject area' })}>+ Add subject area</button>
          </div>
        ))}
        <button className="domain add" onClick={() => setEdit({ t: 'domain', d: {}, label: 'domain' })}>+ Add domain</button>
      </div>
      <div className="layers">
        {m.layers.map((l) => <div key={l.name} className={`layer l-${l.name.toLowerCase()}`}><b>{l.name}</b><span>{l.description}</span></div>)}
      </div>
      <section className="panel">
        <h4>Conformed dimensions · shared by every fact</h4>
        <div className="chips">
          {m.conformed.map((c) => <Chip key={c.id} tone="purple" onClick={() => setEdit({ t: 'conformed_dim', d: c, label: 'dimension' })}>{c.name}</Chip>)}
          <Chip onClick={() => setEdit({ t: 'conformed_dim', d: {}, label: 'dimension' })}>+ Add</Chip>
        </div>
      </section>
    </>
  )
}

function Schemas({ m, setEdit }) {
  const order = ['Warehouse', 'Transportation', 'Automation & labor']
  const models = [...new Set(m.entities.map((e) => e.model))].sort((a, b) => (order.indexOf(a) + 1 || 99) - (order.indexOf(b) + 1 || 99))
  const [model, setModel] = useState(models[0])
  const ents = m.entities.filter((e) => e.model === model)
  const [sel, setSel] = useState(null)
  const e = ents.find((x) => x.id === sel) || ents[0]
  return (
    <>
      <div className="toolbar">
        <div className="tabs">{models.map((x) => <button key={x} className={x === model ? 'on' : ''} onClick={() => { setModel(x); setSel(null) }}>{x}</button>)}</div>
        <button className="btn primary" onClick={() => setEdit({ t: 'data_entity', d: { model, kind: 'fact' }, label: 'table' })}>+ Add table</button>
      </div>
      <div className="split">
        <aside className="list">
          {['fact', 'dim'].map((k) => (
            <div key={k}>
              <div className="list-group">{k === 'fact' ? 'Facts' : 'Dimensions'}</div>
              {ents.filter((x) => x.kind === k).map((x) => (
                <button key={x.id} className={`list-item mono ${e && x.id === e.id ? 'on' : ''}`} onClick={() => setSel(x.id)}>
                  <b>{x.name}</b><small>{x.type} · {x.attributes.length} attrs</small>
                </button>
              ))}
            </div>
          ))}
        </aside>
        {e && (
          <div className="detail">
            <div className="persona-head">
              <div>
                <Chip tone={e.kind === 'fact' ? 'purple' : 'green'}>{e.kind === 'fact' ? 'FACT' : 'DIM'} · {e.type}</Chip> <Origin origin={e.origin} />
                <h2 className="mono">{e.name}</h2>
                <p>{e.description}</p>
                {e.subject_area && <div className="muted">Subject area: {e.subject_area}</div>}
              </div>
              <button className="btn ghost" onClick={() => setEdit({ t: 'data_entity', d: e, label: 'table' })}>Edit table</button>
            </div>
            {e.kind === 'fact' && e.attributes.some((a) => a.role === 'FK') && <Star fact={e} all={m.entities} />}
            <table className="tbl">
              <thead><tr><th>Attribute</th><th>Role</th><th>Description</th><th /></tr></thead>
              <tbody>
                {e.attributes.map((a) => (
                  <tr key={a.id}>
                    <td className="mono">{a.name}</td><td><span className={`role r-${a.role}`}>{a.role}</span></td><td>{a.description}<Origin origin={a.origin} /></td>
                    <td><button className="link" onClick={() => setEdit({ t: 'attribute', d: a, label: 'attribute' })}>Edit</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button className="add-link" onClick={() => setEdit({ t: 'attribute', d: { entity_id: e.id, role: 'attribute' }, label: 'attribute' })}>+ Add attribute</button>
          </div>
        )}
      </div>
    </>
  )
}

function Star({ fact, all }) {
  const fks = fact.attributes.filter((a) => a.role === 'FK')
  const dimFor = (fk) => {
    if (/date_key$/.test(fk)) return 'DIM_DATE'
    const d = all.find((x) => x.kind === 'dim' && x.attributes.some((a) => a.role === 'PK' && a.name === fk))
    return d?.name || fk.toUpperCase()
  }
  const W = 720, H = 300, cx = W / 2, cy = H / 2
  return (
    <svg className="star" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Star schema for ${fact.name}`}>
      {fks.map((f, i) => {
        const ang = (i / fks.length) * Math.PI * 2 - Math.PI / 2
        const x = cx + Math.cos(ang) * 270, y = cy + Math.sin(ang) * 115
        return (
          <g key={f.id}>
            <line x1={cx} y1={cy} x2={x} y2={y} />
            <rect x={x - 78} y={y - 15} width="156" height="30" rx="7" className="star-dim" />
            <text x={x} y={y - 1} className="star-t">{dimFor(f.name)}</text>
            <text x={x} y={y + 10} className="star-s">{f.name}</text>
          </g>
        )
      })}
      <rect x={cx - 100} y={cy - 22} width="200" height="44" rx="9" className="star-fact" />
      <text x={cx} y={cy + 5} className="star-ft">{fact.name}</text>
    </svg>
  )
}

function Kpis({ m, setEdit }) {
  const [aud, setAud] = useState('')
  const doms = useMemo(() => [...new Set(m.kpis.map((k) => k.domain))], [m])
  return (
    <>
      <div className="toolbar">
        <div className="tabs">
          <button className={!aud ? 'on' : ''} onClick={() => setAud('')}>All <small>{m.kpis.length}</small></button>
          {Object.entries(AUD).map(([k, l]) => <button key={k} className={aud === k ? 'on' : ''} onClick={() => setAud(k)}>{l} <small>{m.kpis.filter((x) => (x.audiences || '').includes(k)).length}</small></button>)}
        </div>
        <button className="btn primary" onClick={() => setEdit({ t: 'kpi', d: { audiences: 'O' }, label: 'KPI' })}>+ Add KPI</button>
      </div>
      <p className="muted">Each KPI is certified once (owner, grain, source fact and golden-query test) and published as a Snowflake semantic view. Source facts are suggested mappings to confirm in discovery.</p>
      <div className="kpi-grid">
        {doms.map((d) => (
          <div key={d} className="kpi-col">
            <h4>{d}</h4>
            {m.kpis.filter((k) => k.domain === d && (!aud || (k.audiences || '').includes(aud))).map((k) => (
              <div key={k.id} className="kpi" onClick={() => setEdit({ t: 'kpi', d: k, label: 'KPI' })}>
                <div className="kpi-top"><b>{k.name}</b><span className="aud">{(k.audiences || '').split(',').filter(Boolean).map((a) => <i key={a} className={`a-${a.trim()}`} title={AUD[a.trim()]}>{a.trim()}</i>)}</span></div>
                <div className="kpi-f">{k.formula}</div>
                {k.source_fact && <div className="kpi-src mono">{k.source_fact}</div>}
                <Origin origin={k.origin} />
              </div>
            ))}
          </div>
        ))}
      </div>
    </>
  )
}
