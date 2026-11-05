import { useEffect, useRef, useState } from 'react'
import { api, sessionId } from '../api'
import { Md } from './ui'

const KIND_ICON = { stage: '◆', persona: '◉', dashboard: '◔', kpi: '#', data: '⬡', catalog: '▦', agent: '✦', skill: '/', tool: '⚙', pursuit: '◈', pursuit_stage: '◈', kit: '▤', kit_template: '▤', winroom: '★', quality: '✓', section: '✓', lifecycle: '⟿' }

export default function Chat({ lens, context, ask, onNavigate, onClose }) {
  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const end = useRef(null)
  const sid = sessionId()

  const send = async (text) => {
    const m = (text ?? input).trim()
    if (!m || busy) return
    setInput('')
    setMsgs((x) => [...x, { role: 'user', content: m }])
    setBusy(true)
    try {
      const r = await api.post('/api/chat', { message: m, session_id: sid, context })
      setMsgs((x) => [...x, { role: 'assistant', content: r.reply, cards: r.cards, suggestions: r.suggestions }])
    } catch (e) {
      setMsgs((x) => [...x, { role: 'assistant', content: 'The API is not reachable: ' + e.message }])
    } finally { setBusy(false) }
  }

  useEffect(() => { if (!msgs.length) send('Where do I start?') }, []) // eslint-disable-line
  useEffect(() => { if (ask) send(ask.text) }, [ask]) // eslint-disable-line
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy])

  return (
    <section className="chat">
      <header className="chat-head">
        <div><div className="chat-title">FlyHigh guide</div><div className="chat-sub">{lens === 'sales' ? 'Sales lens · ask about stages, gates, templates, scores' : 'Delivery lens · ask about steps, agents, skills, shared pursuit stages'}</div></div>
        <button className="icon-btn" onClick={onClose} aria-label="Close">×</button>
      </header>
      <div className="chat-body">
        {msgs.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.role === 'assistant' ? <Md text={m.content} /> : m.content}
            {m.cards?.length > 0 && (
              <div className="msg-cards">
                {m.cards.map((c, j) => (
                  <button key={j} className="msg-card" onClick={() => onNavigate(c.view, c.ref)}>
                    <span className="mc-icon">{KIND_ICON[c.kind] || '→'}</span>
                    <span><b>{c.title}</b><small>{c.subtitle}</small></span>
                  </button>
                ))}
              </div>
            )}
            {m.suggestions?.length > 0 && i === msgs.length - 1 && (
              <div className="suggest">{m.suggestions.map((s) => <button key={s} onClick={() => send(s)}>{s}</button>)}</div>
            )}
          </div>
        ))}
        {busy && <div className="msg assistant typing"><span /><span /><span /></div>}
        <div ref={end} />
      </div>
      <form className="chat-input" onSubmit={(e) => { e.preventDefault(); send() }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder={lens === 'sales' ? 'e.g. What does gate G5 need?' : 'e.g. Which skills build RBAC?'} />
        <button className="btn primary" disabled={busy}>Send</button>
      </form>
    </section>
  )
}
