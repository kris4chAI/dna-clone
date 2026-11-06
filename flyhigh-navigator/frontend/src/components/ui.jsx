import { useState } from 'react'

const inlineMd = (s, k) => {
  const parts = String(s).split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)/g)
  return parts.map((p, i) =>
    p.startsWith('**') ? <strong key={k + '-' + i}>{p.slice(2, -2)}</strong>
      : p.startsWith('`') ? <code key={k + '-' + i}>{p.slice(1, -1)}</code>
        : p.startsWith('*') && p.length > 2 ? <em key={k + '-' + i}>{p.slice(1, -1)}</em>
          : p)
}

/** Small markdown renderer: headings, paragraphs, bullet and numbered lists, tables, code fences, frontmatter. */
export function Md({ text, compact }) {
  const lines = String(text || '').replace(/^---\n[\s\S]*?\n---\n/, '').split('\n')
  const out = []
  let i = 0
  while (i < lines.length) {
    const l = lines[i]
    if (l.startsWith('```')) {
      const buf = []; i++
      while (i < lines.length && !lines[i].startsWith('```')) buf.push(lines[i++])
      out.push(<pre key={i} className="code">{buf.join('\n')}</pre>); i++; continue
    }
    const h = l.match(/^(#{1,4})\s+(.*)/)
    if (h) { const T = `h${Math.min(h[1].length + (compact ? 3 : 1), 6)}`; out.push(<T key={i} className="md-h">{inlineMd(h[2], i)}</T>); i++; continue }
    if (/^\s*\|/.test(l)) {
      const rows = []
      while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(lines[i++])
      const cells = rows.filter((r) => !/^\s*\|[\s:|-]+\|\s*$/.test(r)).map((r) => r.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim()))
      out.push(<div key={i} className="md-table"><table className="tbl"><thead><tr>{cells[0].map((c, j) => <th key={j}>{inlineMd(c, j)}</th>)}</tr></thead>
        <tbody>{cells.slice(1).map((r, x) => <tr key={x}>{r.map((c, j) => <td key={j}>{inlineMd(c, `${x}-${j}`)}</td>)}</tr>)}</tbody></table></div>)
      continue
    }
    if (/^\s*([-*]|\d+\.)\s+/.test(l)) {
      const ordered = /^\s*\d+\./.test(l); const items = []
      while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) items.push(lines[i++].replace(/^\s*([-*]|\d+\.)\s+/, ''))
      const L = ordered ? 'ol' : 'ul'
      out.push(<L key={i}>{items.map((t, j) => <li key={j}>{inlineMd(t.replace(/^\[( |x)\]\s*/, (m) => (m.includes('x') ? '☑ ' : '☐ ')), j)}</li>)}</L>); continue
    }
    if (l.trim()) out.push(<p key={i}>{inlineMd(l, i)}</p>)
    i++
  }
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
