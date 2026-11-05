import { useEffect, useState } from 'react'
import { api } from '../api'

const LOOP_OF = (n) => (n <= 6 ? 'Build' : n === 7 ? 'Review' : n === 8 ? 'Review + Fix' : 'Fix')

export default function Lifecycle({ me, onNavigate }) {
  const [d, setD] = useState(null)
  const [rules, setRules] = useState([])
  useEffect(() => {
    api.get('/api/lifecycle').then(setD)
    api.get('/api/lens/access').then(setRules)
  }, [])
  if (!d) return <div className="page">Loading…</div>
  const lens = d.lens
  const pRules = rules.filter((r) => r.resource === 'pursuit_stage')
  const sRules = rules.filter((r) => r.resource === 'screen')
  const first = lens === 'sales' ? d.pursuit[0] : d.implementation[0]

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">Lifecycle overview · {lens === 'sales' ? 'sales lens' : 'delivery lens'}</div>
          <h1>From RFP signal to a monitored platform</h1>
          <p className="lede">One flow, two lenses. Sales personas run the nine-gate pursuit. Delivery personas run the ten-step implementation. Both lenses share the final pursuit stages, where effort, red team and orals hand over to delivery.</p>
        </div>
        <div className="you-card">
          <span className={`lens-dot ${lens}`} />
          <div><small>Signed in as</small><b>{me.persona.name}</b><small>{me.persona.owns}</small></div>
        </div>
      </header>

      <section className="lc">
        <div className="lc-row-head">
          <b>Pursuit lifecycle</b><span>AI Native Sales Engineering · 9 stages · gates G0–G8</span>
        </div>
        <div className="lc-row">
          {d.pursuit.map((s) => (
            <button key={s.code} className={`lc-node ${s.locked ? 'locked' : ''} ${s.audience === 'shared' ? 'shared' : 'sales'}`}
              disabled={s.locked} onClick={() => onNavigate('pursuit', s.code)} title={s.locked ? 'Not in your lens' : s.gate}>
              <span className="lc-loop">{LOOP_OF(s.num)}</span>
              <span className="lc-num">{s.num}</span>
              <span className="lc-name">{s.name}</span>
              <span className="lc-gate">{s.gate_code}</span>
              {s.audience === 'shared' && <span className="lc-shared">Shared</span>}
              {s.locked && <span className="lc-lock">Sales only</span>}
            </button>
          ))}
        </div>
        <div className="lc-handover">
          <span>Award, mobilize and handover</span>
          <small>Stage 5 loading and plan seed mobilization · stage 9 orals plan feeds Discover</small>
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
        <div className="lc-legend">
          <span><i className="sw sales" />Sales lens</span><span><i className="sw shared" />Shared by both lenses</span>
          <span><i className="sw delivery" />Delivery lens</span><span><i className="sw locked" />Not in your lens</span>
        </div>
      </section>

      <div className="two">
        <section className="panel next-card">
          <h4>Your next step</h4>
          <p><b>{lens === 'sales' ? `Stage ${first.num} · ${first.name}` : `Step ${first.seq} · ${first.name}`}</b></p>
          <p className="muted">{lens === 'sales'
            ? 'Qualify the opportunity and take the bid decision at G0. The pursuit kit holds the bid memo and stakeholder map templates.'
            : 'Open Discover to draft the PRD at G1. In the pursuit you join at stage 5 to reconcile effort, at stage 8 to red-team the delivery sections, and at stage 9 for orals.'}</p>
          <button className="btn primary" onClick={() => onNavigate(lens === 'sales' ? 'pursuit' : 'workflow', first.code)}>Open {first.name} →</button>
        </section>
        <section className="panel">
          <h4>Shared final pursuit stages</h4>
          {pRules.filter((r) => r.sales && r.delivery).map((r) => (
            <div key={r.code} className="shared-row">
              <b>{r.label}</b><span className="muted">{r.reason}</span>
            </div>
          ))}
        </section>
      </div>

      <section className="panel">
        <h4>Access by lens <span className="muted small" style={{ textTransform: 'none', letterSpacing: 0 }}>enforced by the API; rules live in the access_rule table</span></h4>
        <table className="tbl access">
          <thead><tr><th>Screen or stage</th><th className={lens === 'sales' ? 'hl' : ''}>Sales</th><th className={lens === 'delivery' ? 'hl' : ''}>Delivery</th><th>Why</th></tr></thead>
          <tbody>
            {[...sRules, ...pRules].map((r) => (
              <tr key={r.resource + r.code}>
                <td>{r.resource === 'pursuit_stage' ? <span className="muted">Pursuit · </span> : null}{r.label}</td>
                <td className={lens === 'sales' ? 'hl' : ''}>{r.sales ? <span className="yes">✓</span> : <span className="no">—</span>}</td>
                <td className={lens === 'delivery' ? 'hl' : ''}>{r.delivery ? <span className="yes">✓</span> : <span className="no">—</span>}</td>
                <td className="muted small">{r.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}
