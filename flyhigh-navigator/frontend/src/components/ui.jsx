import { useState } from 'react'

/** Tiny markdown: **bold**, *italic*, `code`, "- " bullets, blank lines. */
export function Md({ text }) {
  const inline = (s, k) => {
    const parts = s.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g)
    return parts.map((p, i) =>
      p.startsWith('**') ? <strong key={k + i}>{p.slice(2, -2)}</strong>
        : p.startsWith('`') ? <code key={k + i}>{p.slice(1, -1)}</code>
          : p.startsWith('*') && p.length > 2 ? <em key={k + i}>{p.slice(1, -1)}</em>
            : p)
  }
  const out = []
  let list = []
  const flush = () => { if (list.length) { out.push(<ul key={'u' + out.length}>{list}</ul>); list = [] } }
  ;(text || '').split('\n').forEach((line, i) => {
    if (/^\s*-\s+/.test(line)) list.push(<li key={i}>{inline(line.replace(/^\s*-\s+/, ''), i)}</li>)
    else { flush(); if (line.trim()) out.push(<p key={i}>{inline(line, i)}</p>) }
  })
  flush()
  return <div className="md">{out}</div>
}

export function Chip({ children, tone = 'default', onClick, title }) {
  return <span className={`chip chip-${tone}${onClick ? ' clickable' : ''}`} onClick={onClick} title={title}>{children}</span>
}

export function Origin({ origin }) {
  return origin === 'curated' ? <span className="origin">Curated</span> : null
}

export function Empty({ children }) {
  return <div className="empty">{children}</div>
}

/** Generic edit modal. fields: [{key,label,type,options,placeholder}] */
export function Editor({ title, fields, initial = {}, onSave, onClose, onDelete }) {
  const [data, setData] = useState(() => ({ ...initial }))
  const [busy, setBusy] = useState(false)
  const set = (k, v) => setData((d) => ({ ...d, [k]: v }))
  const save = async (e) => {
    e.preventDefault()
    setBusy(true)
    try { await onSave(data); onClose() } catch (err) { alert(err.message) } finally { setBusy(false) }
  }
  return (
    <div className="modal-back" onMouseDown={onClose}>
      <form className="modal" onMouseDown={(e) => e.stopPropagation()} onSubmit={save}>
        <h3>{title}</h3>
        {fields.map((f) => (
          <label key={f.key} className="field">
            <span>{f.label}</span>
            {f.type === 'textarea' ? (
              <textarea rows={3} value={data[f.key] ?? ''} placeholder={f.placeholder} onChange={(e) => set(f.key, e.target.value)} />
            ) : f.type === 'select' ? (
              <select value={data[f.key] ?? ''} onChange={(e) => set(f.key, e.target.value)}>
                <option value="">—</option>
                {f.options.map((o) => <option key={o.value ?? o} value={o.value ?? o}>{o.label ?? o}</option>)}
              </select>
            ) : (
              <input type={f.type || 'text'} value={data[f.key] ?? ''} placeholder={f.placeholder}
                onChange={(e) => set(f.key, f.type === 'number' ? Number(e.target.value) : e.target.value)} required={f.required} />
            )}
          </label>
        ))}
        <div className="modal-actions">
          {onDelete && <button type="button" className="btn danger" onClick={async () => { if (confirm('Delete this item?')) { await onDelete(); onClose() } }}>Delete</button>}
          <span style={{ flex: 1 }} />
          <button type="button" className="btn ghost" onClick={onClose}>Cancel</button>
          <button className="btn primary" disabled={busy}>{busy ? 'Saving…' : 'Save'}</button>
        </div>
      </form>
    </div>
  )
}

export function CurationBanner({ children }) {
  return (
    <div className="curation">
      <div className="curation-tag">Curation workspace</div>
      <div>{children} <span className="muted">Seeded from reference content. Anything you add or edit is saved to Postgres and tagged <em>Curated</em>.</span></div>
    </div>
  )
}
