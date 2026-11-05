import { useEffect, useState } from 'react'
import { api } from './api'
import Chat from './components/Chat'
import Workflow from './views/Workflow'
import Catalog from './views/Catalog'
import Journeys from './views/Journeys'
import Insights from './views/Insights'
import DataModels from './views/DataModels'

const NAV = [
  { id: 'workflow', label: 'Guided workflow', hint: 'Discovery → monitoring', icon: '◆' },
  { id: 'catalog', label: 'Toolkit catalog', hint: 'Agents · skills · tools', icon: '▦' },
  { id: 'journeys', label: 'Persona journeys', hint: 'Curate · –20', icon: '◉' },
  { id: 'insights', label: 'Insights', hint: 'Curate · –24', icon: '◔' },
  { id: 'data', label: 'Data models', hint: 'Subject areas · KPIs', icon: '⬡' },
]

export default function App() {
  const [nav, setNav] = useState({ view: 'workflow', ref: 'discover' })
  const [chatOpen, setChatOpen] = useState(true)
  const [stats, setStats] = useState(null)
  const [stageCode, setStageCode] = useState('discover')
  const [ask, setAsk] = useState(null)

  useEffect(() => { api.get('/api/overview').then(setStats).catch(() => {}) }, [nav.view])

  const go = (view, ref) => {
    setNav({ view, ref })
    if (view === 'workflow' && ref) setStageCode(ref)
  }
  const askGuide = (text) => { setChatOpen(true); setAsk({ text, t: Date.now() }) }

  return (
    <div className={`shell ${chatOpen ? 'with-chat' : ''}`}>
      <aside className="side">
        <div className="brand">
          <div className="logo">K</div>
          <div><div className="brand-name">SAC SF Takeoff</div><div className="brand-sub">AI native delivery · Snowflake</div></div>
        </div>
        <nav>
          {NAV.map((n) => (
            <button key={n.id} className={`nav-item ${nav.view === n.id ? 'active' : ''}`} onClick={() => go(n.id, n.id === 'workflow' ? stageCode : '')}>
              <span className="nav-icon">{n.icon}</span>
              <span><span className="nav-label">{n.label}</span><span className="nav-hint">{n.hint}</span></span>
            </button>
          ))}
        </nav>
        {stats && (
          <div className="side-stats">
            {[['Stages', stats.stages], ['Agents', stats.agents], ['Skills', stats.skills], ['Tools', stats.tools],
              ['Frameworks', stats.frameworks], ['Snowflake', stats.snowflake], ['Personas', stats.personas], ['KPIs', stats.kpis]].map(([k, v]) => (
              <div key={k}><b>{v}</b><span>{k}</span></div>
            ))}
          </div>
        )}
        <div className="side-foot">Snowflake takeoff toolkit</div>
      </aside>

      <main className="main">
        {nav.view === 'workflow' && <Workflow code={stageCode} onSelect={(c) => go('workflow', c)} onAsk={askGuide} onNavigate={go} />}
        {nav.view === 'catalog' && <Catalog focus={nav.ref} onNavigate={go} />}
        {nav.view === 'journeys' && <Journeys focus={nav.ref} onAsk={askGuide} onNavigate={go} />}
        {nav.view === 'insights' && <Insights focus={nav.ref} onNavigate={go} />}
        {nav.view === 'data' && <DataModels focus={nav.ref} />}
      </main>

      <button className="chat-toggle" onClick={() => setChatOpen((o) => !o)}>{chatOpen ? '→' : 'Ask the guide'}</button>
      {chatOpen && <Chat context={{ view: nav.view, stage: nav.view === 'workflow' ? stageCode : undefined }} ask={ask} onNavigate={go} onClose={() => setChatOpen(false)} />}
    </div>
  )
}
