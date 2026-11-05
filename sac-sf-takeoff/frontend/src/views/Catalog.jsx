import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { Chip, Editor, Origin } from '../components/ui'

const KINDS = [
  { id: 'agent', label: 'Agents', tone: 'agent' },
  { id: 'skill', label: 'Skills', tone: 'skill' },
  { id: 'tool', label: 'Tools', tone: 'tool' },
  { id: 'framework', label: 'Frameworks · Helio', tone: 'fw' },
  { id: 'snowflake', label: 'Snowflake', tone: 'snow' },
]

export default function Catalog({ focus, onNavigate }) {
  const [all, setAll] = useState([])
  const [stages, setStages] = useState([])
  const [kind, setKind] = useState(KINDS.some((k) => k.id === focus) ? focus : 'agent')
  const [term, setTerm] = useState('')
  const [edit, setEdit] = useState(null)
  const load = () => api.get('/api/components').then(setAll)
  useEffect(() => { load(); api.get('/api/stages').then(setStages) }, [])

  const list = useMemo(() => all.filter((c) => c.kind === kind &&
    (!term || `${c.name} ${c.category} ${c.description} ${c.used_by.join(' ')}`.toLowerCase().includes(term.toLowerCase()))), [all, kind, term])
  const groups = useMemo(() => {
    const g = {}
    list.forEach((c) => { (g[c.category || 'Other'] ||= []).push(c) })
    return Object.entries(g).sort((a, b) => b[1].length - a[1].length)
  }, [list])

  // stage × kind coverage matrix
  const matrix = useMemo(() => stages.map((s) => ({
    s, counts: KINDS.map((k) => all.filter((c) => c.kind === k.id && c.stages.some((x) => x.code === s.code)).length),
  })), [stages, all])
  const max = Math.max(1, ...matrix.flatMap((r) => r.counts))
  const tone = KINDS.find((k) => k.id === kind).tone

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">Toolkit catalog · slides 30–37</div>
          <h1>Every agent, skill, tool and framework</h1>
          <p className="lede">AI tools are interchangeable, chosen per team, estate and approval model. Agents draft, skills are invoked by hand, every change clears a human review.</p>
        </div>
      </header>

      <section className="panel">
        <h4>Coverage by stage</h4>
        <div className="matrix">
          <div className="mx-row mx-head"><span />{KINDS.map((k) => <span key={k.id}>{k.label.split(' ')[0]}</span>)}</div>
          {matrix.map(({ s, counts }) => (
            <div key={s.code} className="mx-row">
              <button className="mx-stage" onClick={() => onNavigate('workflow', s.code)}>{s.seq}. {s.name}</button>
              {counts.map((n, i) => <span key={i} className={`mx-cell t-${KINDS[i].tone}`} style={{ '--a': n / max }}>{n || ''}</span>)}
            </div>
          ))}
        </div>
      </section>

      <div className="toolbar">
        <div className="tabs">
          {KINDS.map((k) => <button key={k.id} className={kind === k.id ? 'on' : ''} onClick={() => setKind(k.id)}>{k.label} <small>{all.filter((c) => c.kind === k.id).length}</small></button>)}
        </div>
        <input className="search" placeholder="Search…" value={term} onChange={(e) => setTerm(e.target.value)} />
        <button className="btn primary" onClick={() => setEdit({ kind })}>+ Add</button>
      </div>

      {groups.map(([cat, items]) => (
        <section key={cat} className="cat-group">
          <h4>{cat} <small>{items.length}</small></h4>
          <div className="cards">
            {items.map((c) => (
              <div key={c.id} className="card" onClick={() => setEdit(c)}>
                <div className="card-title"><Chip tone={tone}>{c.name}</Chip><Origin origin={c.origin} /></div>
                {c.description && <p>{c.description}</p>}
                {c.used_by.length > 0 && <div className="card-sub">Used by {c.used_by.join(', ')}</div>}
                <div className="chips">{c.stages.sort((a, b) => a.seq - b.seq).map((s) => (
                  <Chip key={s.code} onClick={(e) => { e.stopPropagation(); onNavigate('workflow', s.code) }}>{s.seq}. {s.name}</Chip>))}
                  {!c.stages.length && <span className="muted small">Interchangeable option</span>}
                </div>
              </div>
            ))}
          </div>
        </section>
      ))}

      {edit && (
        <Editor title={edit.id ? `Edit ${edit.name}` : 'Add to catalog'} initial={edit}
          fields={[
            { key: 'kind', label: 'Type', type: 'select', options: KINDS.map((k) => ({ value: k.id, label: k.label })) },
            { key: 'name', label: 'Name', required: true },
            { key: 'category', label: 'Category / capability' },
            { key: 'description', label: 'Description', type: 'textarea' },
          ]}
          onSave={(d) => (edit.id ? api.update('component', edit.id, d) : api.create('component', d)).then(load)}
          onDelete={edit.id ? () => api.remove('component', edit.id).then(load) : null}
          onClose={() => setEdit(null)} />
      )}
    </div>
  )
}
