import { useEffect, useState } from 'react'
import { api } from '../api'

const LOOP_OF = (n) => (n <= 6 ? 'Build' : n === 7 ? 'Review' : n === 8 ? 'Review + Fix' : 'Fix')
const NEXT = {
  pursuit: { view: 'pursuit', text: 'Qualify the opportunity and take the bid decision at G0. The pursuit kit holds the bid memo and stakeholder map templates.' },
  assurance: { view: 'aw_overview', text: 'Open the assurance workbench: generate test cases from the user stories, run the pilot plans with self-healing, and watch coverage, defects and the regression impact of every change.' },
  delivery: { view: 'workflow', text: 'Open Discover to draft the PRD at G1. In the pursuit you join at stage 5 to reconcile effort, at stage 8 to red-team the delivery sections, and at stage 9 for orals.' },
  pmo: { view: 'playbook', text: 'Read the playbook primer, score each track on the readiness scorecard, then plan waves back from the licence dates. You join the pursuit at stage 5 (effort becomes the mobilization baseline) and stage 9 (hand-over).' },
}

export default function Lifecycle({ me, onNavigate }) {
  const [d, setD] = useState(null)
  const [rules, setRules] = useState([])
  useEffect(() => {
    api.get('/api/lifecycle').then(setD)
    api.get('/api/lens/access').then(setRules)
  }, [])
  if (!d) return <div className="page">Loading…</div>
  const lens = d.lens
  const lenses = d.lenses.filter((l) => l.available)
  const soon = d.lenses.filter((l) => !l.available)
  const pRules = rules.filter((r) => r.resource === 'pursuit_stage')
  const sRules = rules.filter((r) => r.resource === 'screen')
  const name = (code) => d.lenses.find((l) => l.code === code)?.name || code
  const first = lens === 'pursuit' ? { label: `Stage ${d.pursuit[0].num} · ${d.pursuit[0].name}`, ref: d.pursuit[0].code }
    : lens === 'delivery' ? { label: `Step ${d.implementation[0].seq} · ${d.implementation[0].name}`, ref: d.implementation[0].code }
      : lens === 'assurance' ? { label: 'Assurance workbench · overview', ref: '' }
      : { label: 'Delivery playbook · primer', ref: '' }
  const nx = NEXT[lens] || NEXT.delivery

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">Lifecycle overview · {name(lens).toLowerCase()}</div>
          <h1>From RFP signal to a monitored platform</h1>
          <p className="lede">One flow, four lenses. Pursuit personas run the nine-gate pursuit. Delivery personas run the ten-step implementation, and assurance personas test it in the assurance workbench. The PMO runs the program around it with the AI Native Delivery Playbook: readiness, plan, execute and optimize. The final pursuit stages hand over to delivery and the PMO.</p>
        </div>
        <div className="you-card">
          <span className={`lens-dot ${lens}`} />
          <div><small>Signed in as</small><b>{me.persona.name}</b><small>{me.persona.owns}</small></div>
        </div>
      </header>

      <section className="lc">
        <div className="lc-row-head">
          <b>Pursuit lifecycle</b><span>AI Native Pursuit Engineering · 9 stages · gates G0–G8</span>
        </div>
        <div className="lc-row">
          {d.pursuit.map((s) => (
            <button key={s.code} className={`lc-node ${s.locked ? 'locked' : ''} ${s.audience === 'shared' ? 'shared' : 'pursuit'}`}
              disabled={s.locked} onClick={() => onNavigate('pursuit', s.code)} title={s.locked ? 'Not in your lens' : s.gate}>
              <span className="lc-loop">{LOOP_OF(s.num)}</span>
              <span className="lc-num">{s.num}</span>
              <span className="lc-name">{s.name}</span>
              <span className="lc-gate">{s.gate_code}</span>
              {s.audience === 'shared' && <span className="lc-shared">Shared</span>}
              {s.locked && <span className="lc-lock">Pursuit only</span>}
            </button>
          ))}
        </div>
        <div className="lc-handover">
          <span>Award, mobilize and handover</span>
          <small>Stage 5 loading and plan seed mobilization · stage 9 orals plan feeds Discover and the PMO's Align phase</small>
        </div>
        <div className="lc-row-head">
          <b>Program office</b><span>AI Native Delivery Playbook · 6 stages · readiness, plan, setup, execute, optimize</span>
        </div>
        <div className="lc-row prog">
          {d.program.map((s) => (
            <button key={s.code} className={`lc-node pmo ${s.locked ? 'locked' : ''}`} disabled={s.locked}
              onClick={() => onNavigate(s.code === 'primer' ? 'playbook' : s.code === 'readiness' ? 'readiness' : 'roadmap', s.code)} title={s.locked ? 'Not in your lens' : s.name}>
              <span className="lc-num">{s.seq}</span>
              <span className="lc-name">{s.name}</span>
              <span className="lc-gate small">{s.code === 'readiness' ? 'Qualify each track' : s.code === 'execute' ? 'Waves · G1–G3' : s.code === 'optimize' ? 'KPIs vs baseline' : 'PMO'}</span>
              {s.locked && <span className="lc-lock">PMO only</span>}
            </button>
          ))}
        </div>
        <div className="lc-row-head">
          <b>Implementation lifecycle</b><span>Snowflake modernization · 10 steps · human gates G1–G3</span>
        </div>
        <div className="lc-row impl">
          {d.implementation.map((s) => (
            <button key={s.code} className={`lc-node delivery ${s.locked ? 'locked' : ''}`} disabled={s.locked}
              onClick={() => onNavigate('workflow', s.code)} title={s.locked ? 'Not in your lens' : s.gate}>
              <span className="lc-num">{s.seq}</span>
              <span className="lc-name">{s.name}</span>
              <span className="lc-gate small">{s.lead_role}</span>
              {s.locked && <span className="lc-lock">Delivery only</span>}
            </button>
          ))}
        </div>
        <div className="lc-row-head">
          <b>Assurance workbench</b><span>Design · execution · analytics · maintenance · tests every implementation step and wave</span>
        </div>
        <div className="lc-row aw">
          {d.assurance.map((s) => (
            <button key={s.code} className={`lc-node assurance ${s.locked ? 'locked' : ''}`} disabled={s.locked}
              onClick={() => onNavigate(s.code)} title={s.locked ? 'Not in your lens' : s.hint}>
              <span className="lc-num">{s.seq}</span>
              <span className="lc-name">{s.name}</span>
              <span className="lc-gate small">{s.hint}</span>
              {s.locked && <span className="lc-lock">Assurance only</span>}
            </button>
          ))}
        </div>
        <div className="lc-legend">
          <span><i className="sw pursuit" />Pursuit lens</span><span><i className="sw shared" />Shared final stages</span>
          <span><i className="sw pmo" />PMO lens</span><span><i className="sw delivery" />Delivery lens</span><span><i className="sw assurance" />Assurance lens</span><span><i className="sw locked" />Not in your lens</span>
        </div>
      </section>

      <div className="two">
        <section className="panel next-card">
          <h4>Your next step</h4>
          <p><b>{first.label}</b></p>
          <p className="muted">{nx.text}</p>
          <button className="btn primary" onClick={() => onNavigate(nx.view, first.ref)}>Open {first.label.split(' · ').pop()} →</button>
        </section>
        <section className="panel">
          <h4>Shared final pursuit stages</h4>
          {pRules.filter((r) => r.lenses.length > 1).map((r) => (
            <div key={r.code} className="shared-row">
              <b>{r.label} <span className="lens-tags">{r.lenses.map((l) => <i key={l} className={`lens-pill ${l}`}>{name(l).replace(' lens', '')}</i>)}</span></b><span className="muted">{r.reason}</span>
            </div>
          ))}
        </section>
      </div>

      <section className="panel">
        <h4>Access by lens <span className="muted small" style={{ textTransform: 'none', letterSpacing: 0 }}>enforced by the API; rules live in the access_rule table</span></h4>
        <table className="tbl access">
          <thead><tr><th>Screen or stage</th>{lenses.map((l) => <th key={l.code} className={lens === l.code ? 'hl' : ''}>{l.name.replace(' lens', '')}</th>)}<th>Why</th></tr></thead>
          <tbody>
            {[...sRules, ...pRules].map((r) => (
              <tr key={r.resource + r.code}>
                <td>{r.resource === 'pursuit_stage' ? <span className="muted">Pursuit · </span> : null}{r.label}</td>
                {lenses.map((l) => <td key={l.code} className={lens === l.code ? 'hl' : ''}>{r.lenses.includes(l.code) ? <span className="yes">✓</span> : <span className="no">—</span>}</td>)}
                <td className="muted small">{r.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {soon.length > 0 && <p className="muted small" style={{ marginTop: 8 }}>Coming soon: {soon.map((l) => `${l.name} (${l.tagline})`).join(', ')}. Add a lens by inserting a row in <code>lens</code> and listing it in <code>access_rule.lenses</code>.</p>}
      </section>
    </div>
  )
}
