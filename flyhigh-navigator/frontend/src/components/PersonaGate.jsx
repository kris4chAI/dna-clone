import { useEffect, useState } from 'react'
import { api, getPersona } from '../api'

export default function PersonaGate({ onChoose }) {
  const [roles, setRoles] = useState([])
  useEffect(() => { api.get('/api/lens/roles').then(setRoles) }, [])
  const current = getPersona()
  const group = (lens) => roles.filter((r) => r.lens === lens)

  return (
    <div className="gate-screen">
      <div className="gate-card">
        <div className="eyebrow">FlyHigh Navigator</div>
        <h1>Who are you on this pursuit?</h1>
        <p className="lede">Your persona sets your lens. Sales personas run the pursuit lifecycle, from RFP signal to orals. Delivery personas run the implementation lifecycle, from Discover to monitoring. Both lenses share the final pursuit stages, where the plan, red team and orals hand over to delivery.</p>
        <div className="gate-cols">
          {[['sales', 'Sales lens', 'Pursuit lifecycle · win room · response quality'], ['delivery', 'Delivery lens', 'Implementation lifecycle · toolkit · shared pursuit stages 5, 8, 9']].map(([lens, title, sub]) => (
            <div key={lens} className={`gate-col ${lens}`}>
              <div className="gate-col-head"><span className={`lens-dot ${lens}`} /><b>{title}</b><small>{sub}</small></div>
              {group(lens).map((r) => (
                <button key={r.code} className={`role ${r.code === current ? 'on' : ''}`} onClick={() => onChoose(r.code)}>
                  <b>{r.name}</b><small>{r.owns}</small>
                </button>
              ))}
            </div>
          ))}
        </div>
        <p className="muted small">The lens is enforced by the API as well as the menu. In production, map it to your identity provider's groups.</p>
      </div>
    </div>
  )
}
