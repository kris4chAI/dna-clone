import { useEffect, useState } from 'react'
import { api } from '../api'
import { Chip, CurationBanner, Editor, Origin } from '../components/ui'

const KINDS = ['What happened', 'Why it happened', 'What will happen', 'What you can do']
const KIND_TONE = ['k1', 'k2', 'k3', 'k4']

export default function Insights({ focus, onNavigate }) {
  const [ds, setDs] = useState([])
  const [personas, setPersonas] = useState([])
  const [sel, setSel] = useState(focus ? Number(focus) : null)
  const [edit, setEdit] = useState(null)
  const load = () => api.get('/api/insights').then((r) => { setDs(r); setSel((s) => (s && r.some((d) => d.id === s) ? s : r[0]?.id)) })
  useEffect(() => { load(); api.get('/api/personas').then(setPersonas) }, [])
  useEffect(() => { if (focus) setSel(Number(focus)) }, [focus])
  const d = ds.find((x) => x.id === sel)
  const persona = d && personas.find((p) => p.code === d.persona_code)

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">2 Insight · dashboards</div>
          <h1>From signal to decision in one view</h1>
        </div>
        <button className="btn primary" onClick={() => setEdit({ t: 'insight_dashboard', d: {} })}>+ New dashboard</button>
      </header>
      <CurationBanner>Curate the insights each dashboard must deliver, framed as four questions: what happened, why, what will happen, and what you can do.</CurationBanner>

      <div className="tabs big">
        {ds.map((x) => <button key={x.id} className={x.id === sel ? 'on' : ''} onClick={() => setSel(x.id)}>{x.name}<small>{x.audience}</small></button>)}
      </div>

      {d && (
        <div className="dash">
          <div className="dash-head">
            <div>
              <h2>{d.headline} <Origin origin={d.origin} /></h2>
              <div className="muted">{d.audience} · {d.roles} · {d.surface}{d.slide ? ` · slide ${d.slide}` : ''}</div>
            </div>
            <div className="row-actions">
              {persona && <button className="btn ghost" onClick={() => onNavigate('journeys', String(persona.id))}>Persona journey →</button>}
              <button className="btn ghost" onClick={() => setEdit({ t: 'insight_dashboard', d })}>Edit</button>
            </div>
          </div>
          {d.guardrail && <div className="note warn">Scope guardrail · {d.guardrail}</div>}
          <div className="quad">
            {KINDS.map((k, i) => {
              const items = d.questions.filter((x) => x.kind === k)
              return (
                <div key={k} className={`quad-cell ${KIND_TONE[i]}`}>
                  <div className="quad-kind"><span>{i + 1}</span>{k}</div>
                  {items.map((x) => (
                    <div key={x.id} className="quad-q" onClick={() => setEdit({ t: 'insight_question', d: x })}>
                      <div className="qq">“{x.question}”</div>
                      <div className="qa">{x.answer}</div>
                      <Origin origin={x.origin} />
                    </div>
                  ))}
                  <button className="add-link" onClick={() => setEdit({ t: 'insight_question', d: { dashboard_id: d.id, kind: k, seq: i + 1 } })}>+ Add insight</button>
                </div>
              )
            })}
          </div>
          <div className="chips" style={{ marginTop: 12 }}><Chip tone="snow">Illustrative data</Chip><Chip tone="snow">Cortex Analyst</Chip><Chip tone="snow">Tableau Cloud</Chip></div>
        </div>
      )}

      {edit && (
        <Editor title={edit.d.id ? 'Edit' : 'Add'} initial={edit.d}
          fields={edit.t === 'insight_dashboard' ? [
            { key: 'name', label: 'Dashboard', required: true },
            { key: 'audience', label: 'Audience' }, { key: 'roles', label: 'Roles' },
            { key: 'surface', label: 'Surface (e.g. Tableau · Cortex Agents)' },
            { key: 'headline', label: 'Headline', type: 'textarea' },
            { key: 'persona_code', label: 'Linked persona', type: 'select', options: personas.map((p) => ({ value: p.code || '', label: p.name })) },
            { key: 'guardrail', label: 'Scope guardrail', type: 'textarea' },
          ] : [
            { key: 'kind', label: 'Question type', type: 'select', options: KINDS },
            { key: 'question', label: 'Question', type: 'textarea', required: true },
            { key: 'answer', label: 'Insight / visual that answers it', type: 'textarea' },
          ]}
          onSave={async (x) => { const r = edit.d.id ? await api.update(edit.t, edit.d.id, x) : await api.create(edit.t, x); if (edit.t === 'insight_dashboard' && !edit.d.id) setSel(r.id); load() }}
          onDelete={edit.d.id ? () => api.remove(edit.t, edit.d.id).then(load) : null}
          onClose={() => setEdit(null)} />
      )}
    </div>
  )
}
