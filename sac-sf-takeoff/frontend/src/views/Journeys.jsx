import { useEffect, useState } from 'react'
import { api } from '../api'
import { Chip, CurationBanner, Editor, Empty, Origin } from '../components/ui'

const PERSONA_FIELDS = [
  { key: 'name', label: 'Persona', required: true },
  { key: 'segment', label: 'Segment', type: 'select', options: ['Operational', 'Executive', 'External customer', 'Partner', 'Other'] },
  { key: 'journey', label: 'Journey set', type: 'select', options: ['Internal', 'Customer', 'Automation', 'New'] },
  { key: 'roles', label: 'Roles' },
  { key: 'wants', label: 'Wants', type: 'textarea' },
  { key: 'goals', label: 'Goals', type: 'textarea' },
  { key: 'pains', label: 'Pain today', type: 'textarea' },
  { key: 'kpis', label: 'KPIs that matter (comma separated)' },
  { key: 'note', label: 'Notes / guardrails', type: 'textarea' },
]
const STEP_FIELDS = [
  { key: 'seq', label: 'Order', type: 'number' },
  { key: 'name', label: 'Moment', required: true },
  { key: 'question', label: 'Question they ask', type: 'textarea' },
  { key: 'experience', label: 'Experience that answers it' },
  { key: 'metrics', label: 'Metrics shown' },
  { key: 'doing', label: 'What they are doing', type: 'textarea' },
  { key: 'today', label: 'Today (pain)', type: 'textarea' },
]

export default function Journeys({ focus, onAsk }) {
  const [ps, setPs] = useState([])
  const [sel, setSel] = useState(focus ? Number(focus) : null)
  const [edit, setEdit] = useState(null)
  const load = () => api.get('/api/personas').then((r) => { setPs(r); setSel((s) => s && r.some((p) => p.id === s) ? s : r[0]?.id) })
  useEffect(() => { load() }, [])
  useEffect(() => { if (focus) setSel(Number(focus)) }, [focus])

  const p = ps.find((x) => x.id === sel)
  const groups = ['Internal', 'Customer', 'Automation', 'New'].map((g) => [g, ps.filter((x) => (x.journey || 'New') === g)]).filter(([, l]) => l.length)

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">1 Experience · persona journeys</div>
          <h1>The same certified metrics from shift floor to boardroom</h1>
        </div>
        <button className="btn primary" onClick={() => setEdit({ t: 'persona', d: { journey: 'New' } })}>+ New persona</button>
      </header>
      <CurationBanner>Curate persona-based user journeys: who they are, the moments that matter, the question at each moment and the experience that answers it.</CurationBanner>

      <div className="split">
        <aside className="list">
          {groups.map(([g, l]) => (
            <div key={g}>
              <div className="list-group">{g} journeys</div>
              {l.map((x) => (
                <button key={x.id} className={`list-item ${x.id === sel ? 'on' : ''}`} onClick={() => setSel(x.id)}>
                  <b>{x.name}</b><small>{x.segment} · {x.steps.length} moments</small>
                </button>
              ))}
            </div>
          ))}
        </aside>

        {p ? (
          <div className="detail">
            <div className="persona-head">
              <div>
                <Chip tone={p.segment === 'Executive' ? 'purple' : p.segment === 'External customer' ? 'green' : 'default'}>{p.segment}</Chip> <Origin origin={p.origin} />
                <h2>{p.name}</h2>
                <div className="muted">{p.roles}{p.slide ? ` · slide ${p.slide}` : ''}</div>
                <p className="wants"><span>Wants</span>{p.wants}</p>
              </div>
              <div className="row-actions">
                <button className="btn ghost" onClick={() => onAsk(`Show the ${p.name} journey`)}>Ask guide</button>
                <button className="btn ghost" onClick={() => setEdit({ t: 'persona', d: p })}>Edit persona</button>
              </div>
            </div>
            {(p.goals || p.pains || p.kpis) && (
              <div className="three">
                {p.goals && <div className="panel"><h5>Goals</h5><p>{p.goals}</p></div>}
                {p.pains && <div className="panel"><h5>Pain today</h5><p>{p.pains}</p></div>}
                {p.kpis && <div className="panel"><h5>KPIs that matter</h5><div className="chips">{p.kpis.split(',').map((k) => <Chip key={k} tone="out">{k.trim()}</Chip>)}</div></div>}
              </div>
            )}
            {p.note && <div className="note">{p.note}</div>}

            <div className="journey">
              {p.steps.map((s, i) => (
                <div key={s.id} className="jstep" onClick={() => setEdit({ t: 'journey_step', d: s })}>
                  <div className="jstep-head"><span className="jnum">{i + 1}</span>{s.name}<Origin origin={s.origin} /></div>
                  {s.doing && <div className="jrow"><span>Doing</span>{s.doing}</div>}
                  <div className="jq">“{s.question}”</div>
                  {s.today && <div className="jrow today"><span>Today</span>{s.today}</div>}
                  <div className="jexp"><span>With takeoff</span><b>{s.experience}</b><small>{s.metrics}</small></div>
                </div>
              ))}
              <button className="jstep add" onClick={() => setEdit({ t: 'journey_step', d: { persona_id: p.id, seq: p.steps.length + 1 } })}>+ Add moment</button>
            </div>
          </div>
        ) : <Empty>Pick or create a persona.</Empty>}
      </div>

      {edit && (
        <Editor title={edit.d.id ? 'Edit' : 'Add'} initial={edit.d}
          fields={edit.t === 'persona' ? PERSONA_FIELDS : STEP_FIELDS}
          onSave={async (d) => {
            const r = edit.d.id ? await api.update(edit.t, edit.d.id, d) : await api.create(edit.t, d)
            if (edit.t === 'persona' && !edit.d.id) setSel(r.id)
            load()
          }}
          onDelete={edit.d.id ? () => api.remove(edit.t, edit.d.id).then(load) : null}
          onClose={() => setEdit(null)} />
      )}
    </div>
  )
}
