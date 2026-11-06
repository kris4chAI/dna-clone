import { useEffect, useState } from 'react'
import { api } from '../api'
import { Chip, Empty } from '../components/ui'

export default function Kit({ me, focus, onNavigate }) {
  const [kit, setKit] = useState(null)
  const [tid, setTid] = useState(focus ? Number(focus) : null)
  const [sheetId, setSheetId] = useState(null)
  const [sheet, setSheet] = useState(null)
  const [tab, setTab] = useState('templates')

  useEffect(() => {
    api.get('/api/kit').then((k) => {
      setKit(k)
      const first = (focus && k.templates.find((t) => t.id === Number(focus))) || k.templates.find((t) => t.sheets.length)
      if (first) { setTid(first.id); setSheetId(first.sheets[0]?.id ?? null) }
    })
  }, [focus])
  const loadSheet = () => sheetId && api.get(`/api/kit/sheets/${sheetId}`).then(setSheet)
  useEffect(() => { setSheet(null); loadSheet() }, [sheetId]) // eslint-disable-line

  if (!kit) return <div className="page">Loading…</div>
  const t = kit.templates.find((x) => x.id === tid)
  const pick = (x) => { setTid(x.id); setSheetId(x.sheets[0]?.id ?? null) }

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">Pursuit kit · stage templates and aids</div>
          <h1>Fill each stage's template in place</h1>
          <p className="lede">The Word and Excel templates from the pursuit kit, turned into editable sheets saved to Postgres. Download the original file any time. FlyHigh samples are client-confidential and stay in the pursuit folder.</p>
        </div>
      </header>
      <div className="tabs" style={{ marginBottom: 12 }}>
        <button className={tab === 'templates' ? 'on' : ''} onClick={() => setTab('templates')}>Templates and aids</button>
        <button className={tab === 'skills' ? 'on' : ''} onClick={() => setTab('skills')}>Skills and tools</button>
      </div>

      {tab === 'skills' && (
        <div className="cards">
          {kit.skills.map((s) => (
            <div key={s.id} className="card" style={{ cursor: 'default' }}>
              <div className="card-title"><Chip tone={s.type === 'Skill package' ? 'agent' : s.type === 'Tool' ? 'tool' : 'skill'}>{s.name}</Chip></div>
              <p>{s.contributes}</p>
              <div className="card-sub">{s.type} · stages {s.stages}</div>
            </div>
          ))}
        </div>
      )}

      {tab === 'templates' && (
        <div className="split">
          <aside className="list">
            {kit.stages.map((s) => {
              const ts = kit.templates.filter((x) => x.stage_num === s.num)
              return (
                <div key={s.code}>
                  <div className={`list-group ${s.locked ? 'dim' : ''}`}>{s.num}. {s.name} · {s.gate_code}{s.locked && ' · pursuit only'}</div>
                  {ts.map((x) => (
                    <button key={x.id} className={`list-item ${x.id === tid ? 'on' : ''}`} onClick={() => pick(x)}>
                      <b><span className={`fmt fmt-${x.format}`}>{x.format}</span> {x.file.replace(/\.(xlsx|docx|pptx)$/, '')}</b>
                      <small>{x.sample ? 'FlyHigh sample' : `${x.sheets.length} sheet${x.sheets.length === 1 ? '' : 's'}`}</small>
                    </button>
                  ))}
                </div>
              )
            })}
          </aside>
          <div className="detail">
            {!t && <Empty>Pick a template.</Empty>}
            {t && (
              <>
                <div className="persona-head">
                  <div>
                    <Chip tone={t.sample ? 'ev' : 'agent'}>{t.sample ? 'FlyHigh sample · internal' : 'Template'}</Chip>
                    <h2>{t.file}</h2>
                    <div className="muted">{t.folder}</div>
                  </div>
                  {t.download && <a className="btn primary" href={api.downloadUrl(t.id)}>Download original</a>}
                </div>
                {!t.sheets.length && <div className="note">This sample is referenced for the stage but not loaded into the app. Open it from the pursuit folder.</div>}
                {t.sheets.length > 1 && (
                  <div className="tabs" style={{ margin: '12px 0' }}>
                    {t.sheets.map((s) => <button key={s.id} className={s.id === sheetId ? 'on' : ''} onClick={() => setSheetId(s.id)}>{s.name} <small>{s.rows}</small></button>)}
                  </div>
                )}
                {t.file.startsWith('Commercials and value model') && <CommercialsRun reload={loadSheet} onNavigate={onNavigate} />}
                {sheet && <Sheet key={sheet.id + ':' + (sheet.rows || []).map((r) => JSON.stringify(r.data)).join('|').length} sheet={sheet} reload={loadSheet} />}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function CommercialsRun({ reload, onNavigate }) {
  const [r, setR] = useState(null)
  const go = async () => { setR(await api.post('/api/skills/rfp-commercials-model/run', { params: {} })); reload() }
  return (
    <div className="engine-bar">
      <button className="btn primary" onClick={go}>Run rfp-commercials-model</button>
      <span className="small">{r ? r.summary : 'Prices the options from hours and the rate card, applies term discounts, totals TCO and computes client-retained ROI. INDICATIVE.'}</span>
      <button className="link" onClick={() => onNavigate('skills', 'rfp-commercials-model')}>Open skill →</button>
    </div>
  )
}

function Sheet({ sheet, reload }) {
  const docx = sheet.template.format === 'docx'
  const add = async () => {
    const blank = Object.fromEntries(sheet.columns.map((c) => [c, '']))
    await api.post(`/api/kit/sheets/${sheet.id}/rows`, blank); reload()
  }
  return (
    <section className="panel sheet">
      <h4>{sheet.title}</h4>
      {sheet.guidance && <p className="muted small">{sheet.guidance}</p>}
      {docx ? (
        <div className="doc-sections">
          {sheet.rows.map((r) => <DocSection key={r.id} row={r} />)}
        </div>
      ) : (
        <div className="grid-wrap">
          <table className="grid">
            <thead><tr>{sheet.columns.map((c) => <th key={c}>{c}</th>)}<th /></tr></thead>
            <tbody>{sheet.rows.map((r) => <Row key={r.id} row={r} cols={sheet.columns} reload={reload} />)}</tbody>
          </table>
        </div>
      )}
      {!docx && <button className="add-link" onClick={add}>+ Add row</button>}
    </section>
  )
}

function Row({ row, cols, reload }) {
  const [d, setD] = useState(row.data)
  const [dirty, setDirty] = useState(false)
  const save = async () => { if (!dirty) return; await api.put(`/api/kit/rows/${row.id}`, d); setDirty(false) }
  const bracket = (v) => typeof v === 'string' && /^\[.*\]$/.test(v)
  return (
    <tr className={dirty ? 'dirty' : ''}>
      {cols.map((c) => (
        <td key={c}>
          <input className={bracket(d[c]) ? 'placeholder' : ''} value={d[c] ?? ''} onChange={(e) => { setD({ ...d, [c]: e.target.value }); setDirty(true) }} onBlur={save} />
        </td>
      ))}
      <td className="row-act">
        {row.origin === 'curated' && <span className="origin" title={row.updated_by}>Curated</span>}
        <button className="link" onClick={async () => { if (confirm('Delete row?')) { await api.del(`/api/kit/rows/${row.id}`); reload() } }}>×</button>
      </td>
    </tr>
  )
}

function DocSection({ row }) {
  const [d, setD] = useState(row.data)
  const [state, setState] = useState('')
  const save = async () => { setState('Saving…'); await api.put(`/api/kit/rows/${row.id}`, d); setState('Saved') }
  return (
    <div className="doc-sec">
      <b>{d.Section}</b>
      <small>{d.Guidance}</small>
      <textarea rows={4} value={d.Response || ''} placeholder="[Write here]" onChange={(e) => { setD({ ...d, Response: e.target.value }); setState('') }} onBlur={save} />
      <span className="muted small">{state}</span>
    </div>
  )
}
