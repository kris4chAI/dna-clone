import { useEffect, useState } from 'react'
import { api } from '../api'

const DIMS = ['Business value (1–5)', 'Delivery certainty (1–5)', 'Domain and solution fit (1–5)', 'Commercials and TCO (1–5)', 'Trust and MSA terms (1–5)']
const DIM_SHORT = ['Value', 'Delivery', 'Fit', 'Commercials', 'Trust']
const VENDORS = ['Niche Consulting', 'Boutique Snowflake firm', 'Tier-1 consulting', 'Mid-sized SI']
const STATUS = ['Not started', 'In progress', 'Done']
const rag = (v) => (v >= 4 ? 'g' : v >= 3 ? 'a' : 'r')

export default function WinRoom() {
  const [w, setW] = useState(null)
  const load = () => api.get('/api/winroom').then(setW)
  useEffect(() => { load() }, [])
  if (!w) return <div className="page">Loading…</div>

  const summary = w['Summary'].rows.filter((r) => typeof r['Score (1–5)'] === 'number')
  const people = [...w['Executive scorecard'].rows.map((r) => ({ ...r, group: 'Executive' })), ...w['Evaluator scorecard'].rows.map((r) => ({ ...r, group: 'Evaluator' }))]
    .filter((r) => typeof r['Influence (1–3)'] === 'number')
  const rubric = w['Competitor rubric'].rows.filter((r) => typeof r.Weight === 'number' && r.Weight < 1)
  const totals = w['Competitor rubric'].rows.find((r) => r.Criterion === 'Weighted score')
  const actions = w['Action items'].rows
  const red = people.filter((p) => p['Overall (1–5)'] < 3).length
  const group = summary.find((s) => s.Measure.startsWith('Whole buying group'))

  const setStatus = async (a, status) => {
    const { id, ...data } = a
    await api.put(`/api/kit/rows/${id}`, { ...data, Status: status }); load()
  }

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">Win room · stages 3 and 8 · sales lens only</div>
          <h1>Score the response the way the buyer will</h1>
          <p className="lede">FlyHigh buying group: {people.length} people scored on five dimensions, a competitor rubric of rival archetypes, and only the pending actions that lift the score. Internal only, never client-facing.</p>
        </div>
        <div className={`g7 ${group?.['Score (1–5)'] >= 4 && red === 0 ? 'pass' : 'hold'}`}>
          <small>Gate G7 test</small>
          <b>{group?.['Score (1–5)']}</b>
          <span>group score · target 4.0, {red} in red</span>
        </div>
      </header>

      <div className="tiles">
        {summary.map((s) => (
          <div key={s.Measure} className={`tile rag-${rag(s['Score (1–5)'])}`}>
            <b>{s['Score (1–5)'].toFixed(2)}</b>
            <span>{s.Measure}</span>
            <small>{s.Change > 0 ? `▲ ${s.Change}` : s.Change < 0 ? `▼ ${s.Change}` : '—'} vs previous run</small>
          </div>
        ))}
      </div>

      <section className="panel">
        <h4>Buying group</h4>
        <div className="grid-wrap">
          <table className="tbl heat">
            <thead><tr><th>Stakeholder</th><th>Role</th><th>Infl.</th>{DIM_SHORT.map((d) => <th key={d}>{d}</th>)}<th>Overall</th><th>Gap to close</th><th>Actions</th></tr></thead>
            <tbody>
              {people.map((p) => (
                <tr key={p.id}>
                  <td><b>{p.Stakeholder}</b><small className="block muted">{p.group}</small></td>
                  <td className="small">{p.Role}</td>
                  <td>{p['Influence (1–3)']}</td>
                  {DIMS.map((d) => <td key={d} className={`h h-${rag(p[d])}`}>{p[d]}</td>)}
                  <td><span className={`ragpill ${rag(p['Overall (1–5)'])}`}>{p['Overall (1–5)']}</span></td>
                  <td className="small muted">{p['Gap to close']}</td>
                  <td className="small mono">{p['Action IDs']}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <h4>Competitor rubric · archetypes, not named firms</h4>
        <div className="rubric-legend">{VENDORS.map((v, i) => <span key={v}><i className={`v v${i}`} />{v} {totals && <b>{totals[v]}</b>}</span>)}</div>
        <div className="rubric">
          {rubric.map((r) => (
            <div key={r.Criterion} className="rub-row">
              <div className="rub-label"><b>{r.Criterion}</b><small>{Math.round(r.Weight * 100)}% · {r['Where Niche Consulting must press']}</small></div>
              <div className="rub-bars">
                {VENDORS.map((v, i) => (
                  <div key={v} className="rub-bar"><i className={`v v${i}`} style={{ width: `${(r[v] / 5) * 100}%` }} /><span>{r[v]}</span></div>
                ))}
              </div>
              <div className={`rub-lead ${r['Niche Consulting lead vs best rival'] >= 0 ? 'pos' : 'neg'}`}>{r['Niche Consulting lead vs best rival'] > 0 ? '+' : ''}{r['Niche Consulting lead vs best rival']}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <h4>Pending actions that lift the score</h4>
        <table className="tbl">
          <thead><tr><th>ID</th><th>Action</th><th>Lifts</th><th>Owner</th><th>Due</th><th>Lift</th><th>Status</th></tr></thead>
          <tbody>
            {actions.map((a) => (
              <tr key={a.id} className={a.Status === 'Done' ? 'done-row' : ''}>
                <td className="mono">{a.ID}</td><td>{a.Action}</td><td className="small muted">{a['Stakeholders lifted']}</td>
                <td className="small">{a['Niche Consulting owner (role)']}</td><td className="small">{a.Due}</td><td>+{a['Expected lift']}</td>
                <td><select value={a.Status} onChange={(e) => setStatus(a, e.target.value)}>{STATUS.map((s) => <option key={s}>{s}</option>)}</select></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}
