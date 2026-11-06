import { useEffect, useState } from 'react'
import { api, getPersona } from '../api'

export default function PersonaGate({ onChoose }) {
  const [lenses, setLenses] = useState([])
  useEffect(() => { api.get('/api/lens/list').then(setLenses) }, [])
  const current = getPersona()

  return (
    <div className="gate-screen">
      <div className="gate-card wide">
        <div className="eyebrow">FlyHigh Navigator</div>
        <h1>Who are you on FlyHigh?</h1>
        <p className="lede">Your persona sets your lens. Pursuit personas run the pursuit, from RFP signal to orals. Delivery personas run the implementation, from Discover to monitoring. The PMO runs the program with the AI Native Delivery Playbook: readiness, planning, estimation, KPIs, RACI and governance. The final pursuit stages are shared, where the plan and orals hand over to delivery and the PMO.</p>
        <div className="gate-cols">
          {lenses.map((l) => (
            <div key={l.code} className={`gate-col ${l.code} ${l.available ? '' : 'soon'}`}>
              <div className="gate-col-head"><span className={`lens-dot ${l.code}`} /><b>{l.name}</b><small>{l.tagline}</small></div>
              {l.available ? l.roles.map((r) => (
                <button key={r.code} className={`role ${r.code === current ? 'on' : ''}`} onClick={() => onChoose(r.code)}>
                  <b>{r.name}</b><small>{r.owns}</small>
                </button>
              )) : <div className="soon-note"><b>Coming soon</b><small>{l.description}</small></div>}
            </div>
          ))}
        </div>
        <p className="muted small">The lens is enforced by the API as well as the menu. In production, map it to your identity provider's groups.</p>
      </div>
    </div>
  )
}
