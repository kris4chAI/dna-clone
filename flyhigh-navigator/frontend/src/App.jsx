import { useEffect, useState } from 'react'
import { api, getPersona, setPersona } from './api'
import Chat from './components/Chat'
import PersonaGate from './components/PersonaGate'
import Lifecycle from './views/Lifecycle'
import Pursuit from './views/Pursuit'
import Kit from './views/Kit'
import WinRoom from './views/WinRoom'
import Quality from './views/Quality'
import Workflow from './views/Workflow'
import Catalog from './views/Catalog'
import Journeys from './views/Journeys'
import Insights from './views/Insights'
import DataModels from './views/DataModels'
import Skills from './views/Skills'

const NAV = [
  { group: 'Start', items: [{ id: 'lifecycle', label: 'Lifecycle overview', hint: 'Pursuit → implementation', icon: '⟿' },
    { id: 'skills', label: 'Skills studio', hint: 'Run pursuit + Snowflake skills', icon: '⚡' }] },
  { group: 'Pursuit lifecycle', items: [
    { id: 'pursuit', label: 'Pursuit stages', hint: 'G0 → G8 · signal to orals', icon: '◈' },
    { id: 'kit', label: 'Pursuit kit', hint: 'Templates · aids · skills', icon: '▤' },
    { id: 'winroom', label: 'Win room', hint: 'Scorecard · rubric · actions', icon: '★' },
    { id: 'quality', label: 'Response quality', hint: '14 sections · rubric', icon: '✓' },
  ] },
  { group: 'Solution content', items: [
    { id: 'journeys', label: 'Persona journeys', hint: 'Curate', icon: '◉' },
    { id: 'insights', label: 'Insights', hint: 'Curate', icon: '◔' },
    { id: 'data', label: 'Data models', hint: 'Subject areas · KPIs', icon: '⬡' },
  ] },
  { group: 'Implementation lifecycle', items: [
    { id: 'workflow', label: 'Guided workflow', hint: 'Discover → monitor', icon: '◆' },
    { id: 'catalog', label: 'Toolkit catalog', hint: 'Agents · skills · tools', icon: '▦' },
  ] },
]

export default function App() {
  const [me, setMe] = useState(null)
  const [gate, setGate] = useState(!getPersona())
  const [nav, setNav] = useState({ view: 'lifecycle', ref: '' })
  const [chatOpen, setChatOpen] = useState(true)
  const [stageCode, setStageCode] = useState('discover')
  const [pStage, setPStage] = useState('')
  const [ask, setAsk] = useState(null)

  const loadMe = () => {
    if (!getPersona()) return
    api.get('/api/lens/me').then((m) => {
      setMe(m)
      setPStage(m.pursuit_stages.includes('signal') ? 'signal' : 'delivery')
    }).catch(() => { setPersona(null); setGate(true) })
  }
  useEffect(loadMe, [])

  const choose = (code) => { setPersona(code); setGate(false); setNav({ view: 'lifecycle', ref: '' }); setMe(null); loadMe() }
  const can = (id) => me?.screens.includes(id)
  const go = (view, ref) => {
    if (!can(view)) view = 'lifecycle'
    setNav({ view, ref })
    if (view === 'workflow' && ref) setStageCode(ref)
    if (view === 'pursuit' && ref) setPStage(ref)
  }
  const askGuide = (text) => { setChatOpen(true); setAsk({ text, t: Date.now() }) }

  if (gate || !me) return gate ? <PersonaGate onChoose={choose} /> : <div className="boot">Loading…</div>
  const lens = me.lens
  const v = nav.view

  return (
    <div className={`shell lens-${lens} ${chatOpen ? 'with-chat' : ''}`} key={me.persona.code}>
      <aside className="side">
        <div className="brand">
          <div className="logo">F</div>
          <div><div className="brand-name">FlyHigh Navigator</div><div className="brand-sub">Pursuit to delivery · AI native</div></div>
        </div>
        <button className="who" onClick={() => setGate(true)} title="Switch persona">
          <span className={`lens-dot ${lens}`} />
          <span><b>{me.persona.name}</b><small>{lens === 'sales' ? 'Sales lens' : 'Delivery lens'} · switch</small></span>
        </button>
        <nav>
          {NAV.map((g) => {
            const items = g.items.filter((n) => can(n.id))
            if (!items.length) return null
            return (
              <div key={g.group} className="nav-group">
                <div className="nav-group-label">{g.group}</div>
                {items.map((n) => (
                  <button key={n.id} className={`nav-item ${v === n.id ? 'active' : ''}`} onClick={() => go(n.id, n.id === 'workflow' ? stageCode : n.id === 'pursuit' ? pStage : '')}>
                    <span className="nav-icon">{n.icon}</span>
                    <span><span className="nav-label">{n.label}</span><span className="nav-hint">{n.hint}</span></span>
                  </button>
                ))}
              </div>
            )
          })}
        </nav>
        <div className="side-foot">ABC Retail · FlyHigh · AI Native Sales Engineering</div>
      </aside>

      <main className="main">
        {v === 'lifecycle' && <Lifecycle me={me} onNavigate={go} />}
        {v === 'pursuit' && <Pursuit me={me} code={pStage} onSelect={(c) => go('pursuit', c)} onAsk={askGuide} onNavigate={go} />}
        {v === 'kit' && <Kit me={me} focus={nav.ref} onNavigate={go} />}
        {v === 'winroom' && <WinRoom onNavigate={go} />}
        {v === 'quality' && <Quality me={me} onNavigate={go} />}
        {v === 'skills' && <Skills me={me} focus={nav.ref} onNavigate={go} />}
        {v === 'workflow' && <Workflow code={stageCode} onSelect={(c) => go('workflow', c)} onAsk={askGuide} onNavigate={go} />}
        {v === 'catalog' && <Catalog focus={nav.ref} onNavigate={go} />}
        {v === 'journeys' && <Journeys focus={nav.ref} onAsk={askGuide} onNavigate={go} />}
        {v === 'insights' && <Insights focus={nav.ref} onNavigate={go} />}
        {v === 'data' && <DataModels focus={nav.ref} />}
      </main>

      <button className="chat-toggle" onClick={() => setChatOpen((o) => !o)}>{chatOpen ? '→' : 'Ask the guide'}</button>
      {chatOpen && <Chat key={me.persona.code} lens={lens}
        context={{ view: v, stage: v === 'workflow' ? stageCode : undefined, pstage: v === 'pursuit' ? pStage : undefined }}
        ask={ask} onNavigate={go} onClose={() => setChatOpen(false)} />}
    </div>
  )
}
